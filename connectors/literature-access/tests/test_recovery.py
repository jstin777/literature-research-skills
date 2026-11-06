import asyncio
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import AccessError, ArticleAccess, AstaGuard, Store, normalized_identifier, parse_pmc_html, parse_epmc_xml, process_result


def article_html(doi="10.1234/test", pmid="12345678"):
    text = "Probability and reward magnitude affect the subjective value of an offer. " * 15
    return f'''<html><head><meta name="citation_title" content="Test article">
    <meta name="citation_doi" content="{doi}"><meta name="citation_pmid" content="{pmid}"></head>
    <article><section class="body main-article-body">
    <section class="abstract"><h2>Abstract</h2><p>ABSTRACT_ONLY_SENTINEL</p></section>
    <section id="intro"><h2>Introduction</h2><p>{text}</p></section>
    <section id="results"><h2>Results</h2><p>{text}</p><p>Risk attitude changes with context.</p>
    <figure id="fig1"><figcaption><p>Figure caption about risk.</p></figcaption><img src="figure.jpg"></figure>
    <table id="tab1"><tr><th>Condition</th><th>Value</th></tr><tr><td>A</td><td>2</td></tr></table></section>
    <section id="discussion"><h2>Discussion</h2><p>{text}</p></section></section></article></html>'''


def article_xml():
    text = "The context affects reward probability and subjective value. " * 15
    return f'''<article><front><article-meta><article-id pub-id-type="pmc">123</article-id>
    <article-id pub-id-type="doi">10.1234/test</article-id><title-group><article-title>Test article</article-title></title-group>
    </article-meta></front><body><sec id="intro"><title>Introduction</title><p>{text}</p></sec>
    <sec id="results"><title>Results</title><p>{text}</p><p>{text}</p></sec>
    <sec id="discussion"><title>Discussion</title><p>{text}</p></sec></body></article>'''


class ParsingTests(unittest.TestCase):
    def test_identifier_normalization_and_rejection(self):
        self.assertEqual(normalized_identifier("https://doi.org/10.1523/JNEUROSCI.1235-14.2014"),
                         ("doi", "10.1523/jneurosci.1235-14.2014"))
        self.assertEqual(normalized_identifier("https://pmc.ncbi.nlm.nih.gov/articles/PMC6608411/"), ("pmcid", "PMC6608411"))
        self.assertEqual(normalized_identifier("PMID:25164656"), ("pmid", "25164656"))
        with self.assertRaises(AccessError):
            normalized_identifier('10.1234/test" OR *')
        with self.assertRaises(AccessError):
            normalized_identifier("https://localhost/private")

    def test_body_excludes_abstract_and_preserves_source_locators(self):
        data = parse_pmc_html(article_html(), "PMC123", ("doi", "10.1234/test"))
        self.assertNotIn("ABSTRACT_ONLY_SENTINEL", data["text"])
        self.assertIn("ABSTRACT_ONLY_SENTINEL", data["abstract"])
        self.assertEqual([x["id"] for x in data["outline"]], ["intro", "results", "discussion"])
        self.assertEqual(data["figures"][0]["id"], "fig1")
        self.assertFalse(data["scientific_claims_verified"])
        self.assertNotEqual(data["main_body_completeness"], "verified")

    def test_abstract_only_and_identity_mismatch_rejected(self):
        with self.assertRaisesRegex(AccessError, "without a detectable main body"):
            parse_pmc_html('<article><h1>Title</h1><section class="abstract">Text</section></article>', "PMC123")
        with self.assertRaisesRegex(AccessError, "does not match"):
            parse_pmc_html(article_html(), "PMC123", ("doi", "10.1234/other"))

    def test_equation_image_is_flagged_instead_of_silently_omitted(self):
        html = article_html().replace('</section></article>', '<table class="disp-formula" id="eq1"><tr><td><img src="formula.jpg"></td></tr></table></section></article>')
        data = parse_pmc_html(html, "PMC123")
        self.assertIn("[Equation image: inspect original #eq1]", data["text"])
        self.assertEqual(data["equations"][0]["id"], "eq1")
        self.assertTrue(data["equations"][0]["images"][0].endswith('/formula.jpg'))


class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name))

    async def test_network_fetch_cache_continuation_and_passage_scope(self):
        requests = []
        def handler(request):
            requests.append(str(request.url))
            return httpx.Response(200, text=article_html())
        access = ArticleAccess(self.store, httpx.MockTransport(handler))
        first = await access.fetch("PMC123", max_characters=500)
        self.assertTrue(first["response_truncated"])
        self.assertEqual(first["next_start_char"], 500)
        next_page = await access.fetch("PMC123", start_char=500, max_characters=500)
        self.assertTrue(next_page["cached"])
        self.assertNotEqual(first["text"], next_page["text"])
        self.assertEqual(len(requests), 1)
        passages = await access.passages("PMC123", "risk attitude context")
        self.assertEqual(passages["search_scope"], "one_retrieved_PMC_article")
        self.assertEqual(passages["passages"][0]["section"], "Results")
        self.assertTrue(passages["passages"][0]["source_url"].endswith("#results"))
        self.assertEqual(passages["source_sha256"], first["source_sha256"])
        no_match = await access.passages("PMC123", "UNMATCHABLE_WORD")
        self.assertEqual(no_match["passages"], [])
        self.assertEqual(no_match["search_scope"], "one_retrieved_PMC_article")

    async def test_identifier_resolution_requires_exact_match(self):
        def handler(request):
            if request.url.path.endswith("/search"):
                return httpx.Response(200, json={"resultList": {"result": [
                    {"doi": "10.1234/other", "pmcid": "PMC999"},
                    {"doi": "10.1234/test", "pmcid": "PMC123"}]}})
            return httpx.Response(200, text=article_html())
        data = await ArticleAccess(self.store, httpx.MockTransport(handler)).fetch("10.1234/test")
        self.assertEqual(data["identifiers"]["pmcid"], "PMC123")

    async def test_mismatched_html_not_cached(self):
        access = ArticleAccess(self.store, httpx.MockTransport(lambda r: httpx.Response(200, text=article_html(doi="10.1234/other"))))
        def resolve(client, kind, value):
            async def result(): return "PMC123"
            return result()
        access.resolve = resolve
        with self.assertRaises(AccessError):
            await access.fetch("10.1234/test")
        self.assertIsNone(self.store.cached("article:doi:10.1234/test"))

    async def test_retry_after_is_bounded_and_success_retried(self):
        calls = 0
        def handler(request):
            nonlocal calls
            calls += 1
            if calls == 1:
                return httpx.Response(429, headers={"Retry-After": "0"})
            return httpx.Response(200, text=article_html())
        await ArticleAccess(self.store, httpx.MockTransport(handler)).fetch("PMC123")
        self.assertEqual(calls, 2)

    async def test_long_rate_limit_does_not_sleep_or_retry(self):
        access = ArticleAccess(self.store, httpx.MockTransport(lambda r: httpx.Response(429, headers={"Retry-After": "3600"})))
        with self.assertRaises(AccessError):
            await asyncio.wait_for(access.fetch("PMC123"), 1)

    async def test_challenge_falls_back_to_jats_without_accepting_fake_body(self):
        def handler(request):
            if request.url.host == 'pmc.ncbi.nlm.nih.gov':
                return httpx.Response(200, text='<title>Checking your browser reCAPTCHA</title>')
            return httpx.Response(200, text=article_xml())
        data = await ArticleAccess(self.store, httpx.MockTransport(handler)).fetch("PMC123")
        self.assertEqual(data["source_format"], "europepmc_jats_xml")
        self.assertEqual(data["route_failures"][0]["status"], "challenge_page")
        self.assertTrue(data["source_path"].endswith('.xml'))
        self.assertIn('subjective value', data['text'])

    async def test_parser_upgrade_reuses_immutable_source_without_network(self):
        calls = 0
        def handler(request):
            nonlocal calls
            calls += 1
            return httpx.Response(200, text=article_html())
        access = ArticleAccess(self.store, httpx.MockTransport(handler))
        original = await access.article('PMC123')
        original.pop('parser_version')
        self.store.cache('article:pmcid:PMC123',original)
        upgraded = await access.article('PMC123')
        self.assertTrue(upgraded['cached'])
        self.assertEqual(upgraded['source_sha256'],original['source_sha256'])
        self.assertEqual(calls,1)

    async def test_timeout_circuit_is_persistent_and_per_operation(self):
        calls = []
        async def runner(args, payload, deadline):
            calls.append(payload["name"])
            if payload["name"] == "snippet_search":
                raise TimeoutError
            return {"content": [{"type": "text", "text": "metadata"}], "isError": False, "_meta": None}
        guard = AstaGuard(self.store, runner)
        first = await guard.call("snippet_search", {"query": "risk"})
        self.assertTrue(first["isError"])
        self.assertEqual(first["structuredContent"]["status"], "upstream_timeout")
        # New guard instance represents another MCP process using persisted health.
        second = await AstaGuard(Store(Path(self.tmp.name)), runner).call("snippet_search", {"query": "different"})
        self.assertEqual(second["structuredContent"]["status"], "circuit_open")
        self.assertEqual(calls, ["snippet_search"])
        metadata = await guard.call("get_paper", {"paper_id": "example"})
        self.assertFalse(metadata["isError"])
        cached = await guard.call("get_paper", {"paper_id": "example"})
        self.assertTrue(cached["_meta"]["literature_access"]["cached"])
        self.assertEqual(calls, ["snippet_search", "get_paper"])

    async def test_worker_deadline_really_terminates_process(self):
        marker = Path(self.tmp.name) / "survived"
        command = [sys.executable, "-c", "import time,pathlib; time.sleep(0.4); pathlib.Path(__import__('sys').argv[1]).write_text('bad')", str(marker)]
        started = time.monotonic()
        with self.assertRaises(TimeoutError):
            await process_result(command, {}, 0.05)
        self.assertLess(time.monotonic() - started, 1)
        await asyncio.sleep(0.5)
        self.assertFalse(marker.exists())

    async def test_scoped_fallback_keeps_failure_method_and_provenance_visible(self):
        async def runner(args, payload, timeout):
            raise TimeoutError
        access = ArticleAccess(self.store, httpx.MockTransport(lambda r: httpx.Response(200, text=article_html())))
        guard = AstaGuard(self.store, runner, article_access=access)
        result = await guard.call("snippet_search", {"query": "risk attitude", "paper_ids": "PMC123", "limit": 1})
        self.assertFalse(result["isError"])
        data = result["structuredContent"]
        self.assertEqual(data["status"], "partial_recovery")
        self.assertEqual(data["upstream_failure"]["status"], "upstream_timeout")
        self.assertEqual(data["actual_method"], "lexical_term_overlap")
        self.assertEqual(len(data["passages"]), 1)
        self.assertEqual(data["actual_scope"], "exact_requested_PMC_articles_only")
        self.assertTrue(data["recovered_articles"][0]["source_sha256"])

    async def test_scoped_lexical_no_match_is_not_success_or_negative_literature_evidence(self):
        async def runner(args, payload, timeout):
            raise TimeoutError
        access = ArticleAccess(self.store, httpx.MockTransport(lambda r: httpx.Response(200, text=article_html())))
        guard = AstaGuard(self.store, runner, article_access=access)
        result = await guard.call("snippet_search", {"query": "UNMATCHABLEWORD", "paper_ids": "PMC123", "limit": 1})
        self.assertTrue(result["isError"])
        self.assertEqual(result["structuredContent"]["status"], "upstream_timeout")
        self.assertEqual(result["structuredContent"]["scoped_recovery"]["status"], "no_lexical_matches")


if __name__ == "__main__":
    unittest.main()
