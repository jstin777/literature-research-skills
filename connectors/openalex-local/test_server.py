"""Deterministic coverage of truncation, incomplete retrieval and HTTP failure paths."""
import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
import server


def work(number, abstract=None, doi=None, pmid=None):
    return {"id": f"https://openalex.org/W{number}", "display_name": f"Paper {number}",
            "doi": doi, "ids": {"pmid": pmid} if pmid else {}, "abstract_inverted_index": abstract}


def page(rows, total, cursor=None):
    return {"results": rows, "meta": {"count": total, "next_cursor": cursor, "cost_usd": 0.0001}}


class TextAndIdentifiers(unittest.TestCase):
    def test_reconstruction_keeps_order_and_repeated_words(self):
        self.assertEqual(server.abstract_text({"risk": [0, 3], "and": [1], "loss": [2]}), "risk and loss risk")

    def test_short_does_not_masquerade_as_complete(self):
        row = work(1, {"a" * 120: [0]})
        shortened = server.format_work(row, "short", 100)
        full = server.format_work(row, "full", 100)
        self.assertEqual(shortened["abstract_status"], "truncated")
        self.assertTrue(shortened["abstract_truncated"])
        self.assertEqual(shortened["abstract_full_chars"], 120)
        self.assertEqual(full["abstract"], "a" * 120)
        self.assertEqual(full["abstract_status"], "complete")

    def test_missing_and_not_requested_are_distinct(self):
        self.assertEqual(server.format_work(work(1))["abstract_status"], "missing")
        result = server.format_work(work(1, {"secret": [0]}), "none")
        self.assertEqual(result["abstract_status"], "not_requested")
        self.assertIsNone(result["abstract"])

    def test_malformed_positions_are_flagged_not_reordered(self):
        for index in ({"a": [0, 0]}, {"a": [1]}, {"a": [-1]}, {"a": ["0"]}):
            result = server.format_work(work(1, index))
            self.assertEqual(result["abstract_status"], "malformed")
            self.assertIsNone(result["abstract"])

    def test_aliases_and_doi_case(self):
        self.assertEqual(server.normalize_id("https://openalex.org/w123"), ("openalex", "W123"))
        self.assertEqual(server.normalize_id("https://doi.org/10.5334/CPSY.86"), ("doi", "10.5334/cpsy.86"))
        self.assertEqual(server.normalize_id("https://pubmed.ncbi.nlm.nih.gov/28126210/"), ("pmid", "28126210"))

    def test_identifiers_cannot_be_arbitrary_fetch_urls_or_filter_injection(self):
        for value in ("https://example.com", "W12|W13", "doi:10.1234/a,is_retracted:true"):
            with self.assertRaises(ValueError):
                server.normalize_id(value)

    def test_year_range_and_retraction_filter(self):
        self.assertEqual(server.filters("", 2017, 2026), "publication_year:>2016,publication_year:<2027,is_retracted:false")
        with self.assertRaises(ValueError):
            server.filters("", 2026, 2017)
        with self.assertRaises(ValueError):
            server.filters("is_retracted:true")


class HTTPAndRetrieval(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original_client = server._client
        self.key_patch = patch.object(server, "api_key", return_value="")
        self.key_patch.start()
        self.requests = []

    async def asyncTearDown(self):
        server._client = self.original_client
        self.key_patch.stop()
        self.temp.cleanup()

    def use(self, responder):
        def handle(request):
            self.requests.append(request)
            return responder(request)
        server._client = server.APIClient(Path(self.temp.name) / "cache.sqlite3", httpx.MockTransport(handle), interval=0)
        return server._client

    async def test_three_pages_yield_complete_set(self):
        def response(request):
            offset = {"*": 0, "second": 100, "third": 200}[request.url.params["cursor"]]
            size = int(request.url.params["per_page"])
            rows = [work(i) for i in range(offset, min(offset + size, 218))]
            cursor = "second" if offset == 0 else "third"
            return httpx.Response(200, json=page(rows, 218, cursor))
        self.use(response)
        result = await server.list_citations("W1", limit=1000, abstract_mode="none")
        self.assertEqual(result["returned"], 218)
        self.assertEqual(result["pagination"]["pages_fetched"], 3)
        self.assertTrue(result["pagination"]["result_set_complete"])
        self.assertIsNone(result["pagination"]["next_cursor"])
        self.assertEqual(len({w["id"] for w in result["results"]}), 218)
        self.assertTrue(all(int(r.url.params["per_page"]) <= 100 for r in self.requests))

    async def test_bounded_set_supplies_continuation(self):
        self.use(lambda r: httpx.Response(200, json=page([work(i) for i in range(100)], 218, "second")))
        result = await server.list_citations("W1", limit=100)
        self.assertFalse(result["pagination"]["result_set_complete"])
        self.assertFalse(result["pagination"]["exhausted"])
        self.assertEqual(result["pagination"]["next_cursor"], "second")

    async def test_continuation_tail_is_not_whole_result_set(self):
        self.use(lambda r: httpx.Response(200, json=page([work(201)], 218, None)))
        result = await server.list_citations("W1", limit=100, cursor="tail")
        self.assertTrue(result["pagination"]["exhausted"])
        self.assertFalse(result["pagination"]["result_set_complete"])

    async def test_duplicate_edges_do_not_duplicate_papers(self):
        def response(r):
            body = page([work(1), work(2)], 4, "second") if r.url.params["cursor"] == "*" else page([work(2), work(3)], 4, "third")
            if r.url.params["cursor"] == "third":
                body = page([work(4)], 4)
            return httpx.Response(200, json=body)
        self.use(response)
        result = await server.list_citations("W1", limit=4, page_size=2)
        self.assertEqual([w["id"] for w in result["results"]], ["W1", "W2", "W3", "W4"])

    async def test_second_page_failure_preserves_rows_and_resume_cursor(self):
        def response(r):
            return httpx.Response(200, json=page([work(1), work(2)], 4, "second")) if r.url.params["cursor"] == "*" else httpx.Response(400)
        self.use(response)
        result = await server.list_citations("W1", limit=4, page_size=2)
        self.assertEqual(result["returned"], 2)
        self.assertEqual(result["pagination"]["next_cursor"], "second")
        self.assertIn("HTTP 400", result["pagination"]["error"])
        self.assertFalse(result["pagination"]["result_set_complete"])

    async def test_missing_cursor_does_not_claim_completeness(self):
        self.use(lambda r: httpx.Response(200, json=page([work(1), work(2)], 4)))
        result = await server.list_citations("W1", limit=4, page_size=2)
        self.assertIn("Missing continuation", result["pagination"]["error"])
        self.assertFalse(result["pagination"]["result_set_complete"])

    async def test_repeated_cursor_stops(self):
        self.use(lambda r: httpx.Response(200, json=page([work(1), work(2)], 4, "*")))
        result = await server.list_citations("W1", limit=4, page_size=2)
        self.assertIn("repeated", result["pagination"]["error"])
        self.assertEqual(len(self.requests), 1)

    async def test_cache_and_refresh_are_observable(self):
        client = self.use(lambda r: httpx.Response(200, json=work(1)))
        first = await client.request("/works/W1")
        second = await client.request("/works/W1")
        refreshed = await client.request("/works/W1", refresh=True)
        self.assertFalse(first[1]["cached"])
        self.assertTrue(second[1]["cached"])
        self.assertEqual(first[1]["fetched_at"], second[1]["fetched_at"])
        self.assertFalse(refreshed[1]["cached"])
        self.assertEqual(len(self.requests), 2)

    async def test_expired_cache_fetches_again(self):
        client = self.use(lambda r: httpx.Response(200, json=work(1)))
        await client.request("/works/W1")
        with sqlite3.connect(client.db_path) as db:
            db.execute("UPDATE cache SET fetched=?", (time.time() - 86500,))
        _, provenance = await client.request("/works/W1")
        self.assertFalse(provenance["cached"])
        self.assertEqual(len(self.requests), 2)

    async def test_429_and_503_retry_then_success(self):
        responses = [httpx.Response(429, headers={"Retry-After": "0"}), httpx.Response(503, headers={"Retry-After": "0"}), httpx.Response(200, json=work(1))]
        client = self.use(lambda r: responses.pop(0))
        result, _ = await client.request("/works/W1")
        self.assertEqual(result["id"], "https://openalex.org/W1")
        self.assertEqual(len(self.requests), 3)

    async def test_permanent_error_does_not_retry_or_leak_body(self):
        client = self.use(lambda r: httpx.Response(401, text="secret response detail"))
        with self.assertRaisesRegex(ValueError, "HTTP 401") as error:
            await client.request("/works/W1")
        self.assertNotIn("secret", str(error.exception))
        self.assertEqual(len(self.requests), 1)

    async def test_invalid_json_is_explicit_error(self):
        client = self.use(lambda r: httpx.Response(200, text="not json"))
        with self.assertRaisesRegex(ValueError, "invalid JSON"):
            await client.request("/works/W1")

    async def test_credentials_only_in_header_and_isolate_cache(self):
        client = self.use(lambda r: httpx.Response(200, json=work(1)))
        with patch.object(server, "api_key", return_value="dummy-test-key"):
            _, provenance = await client.request("/works/W1")
        self.assertEqual(self.requests[0].headers["Authorization"], "Bearer dummy-test-key")
        self.assertNotIn("dummy-test-key", json.dumps(provenance))
        self.assertNotIn(b"dummy-test-key", client.db_path.read_bytes())
        _, provenance = await client.request("/works/W1")
        self.assertFalse(provenance["cached"])
        with self.assertRaises(ValueError):
            await client.request("/works/W1", {"api_key": "unsafe"})

    async def test_batch_preserves_order_duplicates_and_missing_ids(self):
        self.use(lambda r: httpx.Response(200, json=page([work(1), work(2)], 2)))
        result = await server.get_works(["W2", "W1", "W2", "W999"])
        self.assertEqual([i["work"]["id"] if i["work"] else None for i in result["items"]], ["W2", "W1", "W2", None])
        self.assertEqual(result["unresolved_ids"], ["W999"])
        self.assertEqual(len(self.requests), 1)

    async def test_mixed_identifiers_use_separate_groups(self):
        def response(r):
            prefix = r.url.params["filter"].split(":", 1)[0]
            rows = {"openalex": [work(1)], "doi": [work(2, doi="https://doi.org/10.1234/test")], "pmid": [work(3, pmid="https://pubmed.ncbi.nlm.nih.gov/42")]}[prefix]
            return httpx.Response(200, json=page(rows, 1))
        self.use(response)
        result = await server.get_works(["PMID:42", "W1", "10.1234/test"])
        self.assertEqual([i["work"]["id"] for i in result["items"]], ["W3", "W1", "W2"])
        self.assertEqual(len(self.requests), 3)

    async def test_long_doi_batches_split_instead_of_exceeding_url_limit(self):
        def response(r):
            self.assertLessEqual(len(str(r.url).encode()), 4000)
            values = r.url.params["filter"].split(":", 1)[1].split("|")
            rows = [work(i, doi="https://doi.org/" + value) for i, value in enumerate(values)]
            return httpx.Response(200, json=page(rows, len(rows)))
        self.use(response)
        ids = [f"10.1234/{i}" + "a" * 80 for i in range(100)]
        result = await server.get_works(ids)
        self.assertEqual(result["found"], 100)
        self.assertGreater(len(self.requests), 1)

    async def test_batch_failure_retains_successful_groups(self):
        self.use(lambda r: httpx.Response(400) if r.url.params["filter"].startswith("doi:") else httpx.Response(200, json=page([work(1)], 1)))
        result = await server.get_works(["W1", "10.1234/test"])
        self.assertEqual(result["found"], 1)
        self.assertEqual(result["errors"][0]["identifier_kind"], "doi")
        self.assertEqual(result["unresolved_ids"], ["10.1234/test"])

    async def test_exhausted_reference_query_reports_stale_seed_ids(self):
        def response(r):
            if r.url.path == "/works/W1":
                return httpx.Response(200, json={"id":"https://openalex.org/W1", "referenced_works":["https://openalex.org/W2", "https://openalex.org/W3"], "referenced_works_count":2})
            return httpx.Response(200, json=page([work(2)], 1))
        self.use(response)
        result = await server.list_citations("W1", direction="references", limit=100)
        self.assertTrue(result["pagination"]["result_set_complete"])
        self.assertFalse(result["reference_coverage"]["all_seed_reference_ids_returned"])
        self.assertEqual(result["reference_coverage"]["not_returned_reference_ids"], ["W3"])


if __name__ == "__main__":
    unittest.main()
