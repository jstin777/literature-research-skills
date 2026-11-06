"""Read-only OpenAlex MCP: bounded pagination and explicit abstract coverage."""
import asyncio
import hashlib
import json
import logging
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import quote

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import Field

ROOT = Path(__file__).resolve().parent
STATE = Path(os.environ.get("OPENALEX_STATE", ROOT / "state"))
API = "https://api.openalex.org"
AbstractMode = Literal["none", "short", "full"]
Sort = Literal["relevance", "cited_by_count", "publication_date"]
Scope = Literal["title_abstract_keywords", "title_and_abstract", "title", "fulltext"]
BASE_FIELDS = "id,doi,ids,display_name,publication_year,publication_date,type,authorships,primary_location,open_access,best_oa_location,cited_by_count,is_retracted"
READ_ONLY = {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": True}


def utc(timestamp=None):
    return datetime.fromtimestamp(timestamp or time.time(), timezone.utc).isoformat()


def api_key():
    value = os.environ.get("OPENALEX_API_KEY", "").strip()
    path = ROOT / ".api-key"
    return value or (path.read_text().strip() if path.exists() else "")


def normalize_id(value):
    """Accept only identifiers, never an arbitrary URL or endpoint."""
    value = value.strip()
    value = re.sub(r"^https?://(www\.)?openalex\.org/", "", value, flags=re.I)
    if re.fullmatch(r"W\d+", value, flags=re.I):
        return "openalex", value.upper()
    value = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", value, flags=re.I)
    if re.fullmatch(r"10\.\d{4,9}/[^\s?#|,]+", value):
        return "doi", value.lower()
    value = re.sub(r"^https?://pubmed\.ncbi\.nlm\.nih\.gov/", "pmid:", value, flags=re.I).rstrip("/")
    if re.fullmatch(r"pmid:\d+", value, flags=re.I):
        return "pmid", value.split(":", 1)[1]
    raise ValueError("Use a W... OpenAlex ID, DOI/doi.org URL, or PMID:... identifier.")


def abstract_text(index):
    if not index:
        return None
    positions = {}
    for word, offsets in index.items():
        for position in offsets:
            if not isinstance(position, int) or position < 0 or position in positions:
                raise ValueError("Malformed abstract positions in OpenAlex record.")
            positions[position] = word
    if sorted(positions) != list(range(len(positions))):
        raise ValueError("Non-contiguous abstract positions in OpenAlex record.")
    return " ".join(positions[i] for i in range(len(positions)))


def fields(mode):
    return BASE_FIELDS + (",abstract_inverted_index" if mode != "none" else "")


def format_work(work, mode="full", short_chars=500):
    abstract = None
    warning = None
    if mode != "none":
        try:
            abstract = abstract_text(work.get("abstract_inverted_index"))
        except (ValueError, TypeError, AttributeError) as error:
            warning = str(error)
    truncated = mode == "short" and abstract is not None and len(abstract) > short_chars
    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    oa = work.get("open_access") or {}
    best = work.get("best_oa_location") or {}
    result = {
        "id": (work.get("id") or "").rsplit("/", 1)[-1],
        "openalex_url": work.get("id"), "doi": work.get("doi"),
        "identifiers": work.get("ids") or {}, "title": work.get("display_name"),
        "year": work.get("publication_year"), "publication_date": work.get("publication_date"),
        "type": work.get("type"), "venue": source.get("display_name"),
        "authors": [a.get("author", {}).get("display_name") for a in work.get("authorships", [])],
        "cited_by_count": work.get("cited_by_count"), "is_retracted": work.get("is_retracted"),
        "is_oa": oa.get("is_oa"), "oa_status": oa.get("oa_status"),
        "oa_url": oa.get("oa_url"), "pdf_url": best.get("pdf_url"),
        "abstract": abstract[:short_chars] + "…" if truncated else abstract,
        "abstract_status": "not_requested" if mode == "none" else ("malformed" if warning else ("missing" if abstract is None else ("truncated" if truncated else "complete"))),
        "abstract_truncated": truncated,
        "abstract_full_chars": len(abstract) if abstract is not None else None,
    }
    if warning:
        result["abstract_warning"] = warning
    # Full refers to the complete available index, not publisher verification.
    if "relevance_score" in work:
        result["relevance_score"] = work["relevance_score"]
    if "rerank_score" in work:
        result["rerank_score"] = work["rerank_score"]
    return result


class APIClient:
    def __init__(self, db_path=None, transport=None, interval=0.15):
        self.db_path = Path(db_path or STATE / "requests.sqlite3")
        self.db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with sqlite3.connect(self.db_path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, fetched REAL, data TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, at TEXT, url TEXT, cached INTEGER, status TEXT)")
        os.chmod(self.db_path, 0o600)
        self.transport = transport
        self.interval = interval
        self.lock = asyncio.Lock()
        self.last_request = 0.0

    def audit(self, url, cached, status):
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute("INSERT INTO audit(at,url,cached,status) VALUES (?,?,?,?)", (utc(), url, int(cached), str(status)))
            return cursor.lastrowid

    async def request(self, path, params=None, refresh=False):
        params = params or {}
        if any(k.lower() in {"api_key", "authorization"} for k in params):
            raise ValueError("Credentials must be configured outside tool arguments.")
        url = str(httpx.URL(API + path, params=params))
        key = api_key()
        fingerprint = hashlib.sha256((url + hashlib.sha256(key.encode()).hexdigest()).encode()).hexdigest()
        async with self.lock:
            with sqlite3.connect(self.db_path) as db:
                hit = db.execute("SELECT fetched,data FROM cache WHERE key=?", (fingerprint,)).fetchone()
            if not refresh and hit and time.time() - hit[0] < 86400:
                return json.loads(hit[1]), {"source_url": url, "fetched_at": utc(hit[0]), "cached": True, "audit_id": self.audit(url, True, 200)}
            headers = {"User-Agent": "OpenAlexLocalResearch/0.1.0"}
            if key:
                headers["Authorization"] = "Bearer " + key
            async with httpx.AsyncClient(timeout=25, follow_redirects=True, transport=self.transport) as client:
                for attempt in range(3):
                    interval = max(self.interval, 1.0) if "search.semantic" in params else self.interval
                    await asyncio.sleep(max(0, interval - (time.monotonic() - self.last_request)))
                    self.last_request = time.monotonic()
                    try:
                        response = await client.get(url, headers=headers)
                    except httpx.RequestError:
                        self.audit(url, False, "network-error")
                        if attempt < 2:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        raise ValueError("OpenAlex network request failed; no complete result was obtained.") from None
                    audit_id = self.audit(url, False, response.status_code)
                    if response.status_code == 200:
                        try:
                            data = response.json()
                        except ValueError:
                            raise ValueError("OpenAlex returned invalid JSON.") from None
                        fetched = time.time()
                        with sqlite3.connect(self.db_path) as db:
                            db.execute("DELETE FROM cache WHERE fetched<?", (fetched - 86400,))
                            db.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?)", (fingerprint, fetched, json.dumps(data)))
                        return data, {"source_url": url, "fetched_at": utc(fetched), "cached": False, "audit_id": audit_id}
                    if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                        try:
                            delay = float(response.headers.get("Retry-After", 2 ** (attempt + 1)))
                        except ValueError:
                            delay = 4
                        if delay <= 20:
                            await asyncio.sleep(max(0, delay))
                            continue
                    explanations = {400: "Invalid query or unsupported filter.", 401: "A valid API key may be required.", 403: "Access denied.", 404: "Identifier not found.", 429: "API budget/rate limit reached; try later or configure your own key."}
                    raise ValueError(f"OpenAlex HTTP {response.status_code}: " + explanations.get(response.status_code, "Service error; try later."))


_client = None


def client():
    global _client
    if _client is None:
        _client = APIClient()
    return _client


def filters(raw_filter="", from_year=None, to_year=None, include_retracted=False):
    if from_year is not None and to_year is not None and from_year > to_year:
        raise ValueError("from_year must not exceed to_year.")
    if re.search(r"(^|,)\s*is_retracted\s*:", raw_filter):
        raise ValueError("Use include_retracted rather than setting is_retracted in raw_filter.")
    parts = [raw_filter.strip()] if raw_filter.strip() else []
    if from_year is not None:
        parts.append(f"publication_year:>{from_year - 1}")
    if to_year is not None:
        parts.append(f"publication_year:<{to_year + 1}")
    if not include_retracted:
        parts.append("is_retracted:false")
    return ",".join(parts)


async def collect(params, limit, page_size, cursor, mode, short_chars, refresh=False):
    results, requests, seen, seen_cursors = [], [], set(), set()
    total = None
    exhausted, error = False, None
    current = cursor
    while len(results) < limit:
        if current in seen_cursors:
            error = "OpenAlex repeated its continuation cursor; stopped without claiming completeness."
            break
        seen_cursors.add(current)
        size = min(page_size, limit - len(results))
        page_params = dict(params, per_page=size, cursor=current)
        try:
            data, provenance = await client().request("/works", page_params, refresh)
        except ValueError as exc:
            if not results:
                raise
            error = str(exc)
            break
        meta = data.get("meta") or {}
        requests.append(dict(provenance, returned=len(data.get("results", [])), api_cost_usd_reported=meta.get("cost_usd"), query_translation=meta.get("x_query")))
        total = meta.get("count", total)
        rows = data.get("results", [])
        for row in rows:
            if row.get("id") not in seen:
                seen.add(row.get("id"))
                results.append(format_work(row, mode, short_chars))
        next_cursor = meta.get("next_cursor")
        if not rows or len(rows) < size or (cursor == "*" and total is not None and len(seen) >= total):
            exhausted, current = True, None
            break
        if not next_cursor:
            error = "Missing continuation cursor on a full page; completeness is unresolved."
            current = None
            break
        current = next_cursor
    costs = [p["api_cost_usd_reported"] for p in requests if not p["cached"]]
    return {"results": results, "returned": len(results), "total_results": total,
            "pagination": {"requested_limit": limit, "page_size": page_size, "pages_fetched": len(requests), "start_cursor": cursor, "next_cursor": current, "exhausted": exhausted, "result_set_complete": exhausted and cursor == "*" and error is None, "error": error},
            "query": params, "abstract_mode": mode, "requests": requests,
            "api_cost_usd_reported_this_call": sum(costs) if all(isinstance(v, (int, float)) for v in costs) else None,
            "limitations": ["Citation edges and metadata require verification; records are not independent studies.", "Complete abstracts mean complete available index text, not verified publisher text."]}


mcp = FastMCP("openalex-local", instructions=(
    "Read-only OpenAlex discovery with 100-record API pages and automatic bounded pagination. "
    "Abstract modes: none, short, full. Never exclude uncertain candidates solely from a truncated or missing abstract. "
    "Inspect pagination.result_set_complete/error and continuation cursors. For references also inspect reference_coverage; an exhausted query can omit stale seed IDs. Keep query and filters unchanged when resuming. "
    "Use get_works for batches of full abstracts. Source URLs, retrieval dates, cache and audit IDs are provided. "
    "This retrieves metadata/abstracts, not original full articles; verify scientific claims in original papers."
))
logging.getLogger("httpx").setLevel(logging.WARNING)


@mcp.tool(annotations=READ_ONLY)
async def search_works(query: Annotated[str, Field(max_length=2000)] = "",
                       limit: Annotated[int, Field(ge=1, le=1000)] = 100,
                       abstract_mode: AbstractMode = "short",
                       short_chars: Annotated[int, Field(ge=100, le=5000)] = 500,
                       search_in: Scope = "title_and_abstract", exact: bool = False,
                       raw_filter: str = "", from_year: Annotated[int | None, Field(ge=1000, le=3000)] = None,
                       to_year: Annotated[int | None, Field(ge=1000, le=3000)] = None,
                       sort: Sort = "relevance", include_retracted: bool = False,
                       page_size: Annotated[int, Field(ge=1, le=100)] = 100,
                       cursor: str = "*", refresh: bool = False) -> dict:
    """Keyword/Boolean search (AND OR NOT, quotes). Auto-fetch up to limit records in API pages of <=100. Use returned cursor with identical query/filters to resume. Full abstracts are optional; a bounded result is not exhaustive. No semantic reranking is applied."""
    if not query.strip() and not raw_filter.strip():
        raise ValueError("Provide a query or a filter rather than listing the entire database.")
    params = {"filter": filters(raw_filter, from_year, to_year, include_retracted), "select": fields(abstract_mode)}
    if query.strip():
        parameter = "search" if search_in == "fulltext" else "search." + search_in
        params[parameter + (".exact" if exact else "")] = query.strip()
    if sort != "relevance":
        params["sort"] = sort + ":desc"
    elif not query.strip():
        params["sort"] = "publication_date:desc"
    return await collect(params, limit, page_size, cursor, abstract_mode, short_chars, refresh)


@mcp.tool(annotations=READ_ONLY)
async def get_work(work_id: str, abstract_mode: AbstractMode = "full",
                   short_chars: Annotated[int, Field(ge=100, le=5000)] = 500,
                   refresh: bool = False) -> dict:
    """Resolve one OpenAlex ID, DOI or PMID and return metadata plus the complete available abstract by default. Does not retrieve article full text. Follows OpenAlex merged-ID redirects."""
    namespace, value = normalize_id(work_id)
    identifier = value if namespace == "openalex" else namespace + ":" + value
    work, provenance = await client().request("/works/" + quote(identifier, safe="/:"), {"select": fields(abstract_mode)}, refresh)
    return {"work": format_work(work, abstract_mode, short_chars), "provenance": provenance}


@mcp.tool(annotations=READ_ONLY)
async def get_works(work_ids: Annotated[list[str], Field(min_length=1, max_length=100)],
                    abstract_mode: AbstractMode = "full",
                    short_chars: Annotated[int, Field(ge=100, le=5000)] = 500,
                    refresh: bool = False) -> dict:
    """Retrieve up to 100 papers with full abstracts in batches, preserving input order. Accept mixed W IDs, DOIs and PMID:...; groups by kind and splits long URLs to respect the API limit. Reports missing/error IDs explicitly. Merged/alias IDs may need singleton get_work."""
    normalized = [normalize_id(value) for value in work_ids]
    records, requests, errors = {}, [], []
    for namespace in dict.fromkeys(ns for ns, _ in normalized):
        values = list(dict.fromkeys(v for ns, v in normalized if ns == namespace))
        chunks, chunk = [], []
        for value in values:
            candidate = chunk + [value]
            params = {"filter": namespace + ":" + "|".join(candidate), "per_page": len(candidate), "select": fields(abstract_mode)}
            if chunk and len(str(httpx.URL(API + "/works", params=params)).encode()) > 4000:
                chunks.append(chunk)
                chunk = [value]
            else:
                chunk = candidate
        if chunk:
            chunks.append(chunk)
        for chunk in chunks:
            params = {"filter": namespace + ":" + "|".join(chunk), "per_page": len(chunk), "select": fields(abstract_mode)}
            try:
                data, provenance = await client().request("/works", params, refresh)
            except ValueError as exc:
                errors.append({"identifier_kind": namespace, "requested_ids": chunk, "error": str(exc)})
                continue
            requests.append(provenance)
            for row in data.get("results", []):
                if namespace == "openalex":
                    identifier = row.get("id", "").rsplit("/", 1)[-1].upper()
                elif namespace == "doi":
                    identifier = re.sub(r"^https?://(dx\.)?doi.org/", "", row.get("doi") or "", flags=re.I).lower()
                else:
                    identifier = (row.get("ids", {}).get("pmid") or "").rstrip("/").rsplit("/", 1)[-1]
                records[(namespace, identifier)] = format_work(row, abstract_mode, short_chars)
    items = [{"requested_id": original, "status": "found" if key in records else "unresolved", "work": records.get(key)} for original, key in zip(work_ids, normalized)]
    return {"items": items, "requested": len(items), "found": sum(i["status"] == "found" for i in items), "unresolved_ids": [i["requested_id"] for i in items if i["status"] != "found"], "errors": errors, "requests": requests, "abstract_mode": abstract_mode}


@mcp.tool(annotations=READ_ONLY)
async def list_citations(work_id: str, direction: Literal["citing", "references"] = "citing",
                          limit: Annotated[int, Field(ge=1, le=1000)] = 100,
                          abstract_mode: AbstractMode = "short",
                          short_chars: Annotated[int, Field(ge=100, le=5000)] = 500,
                          from_year: Annotated[int | None, Field(ge=1000, le=3000)] = None,
                          to_year: Annotated[int | None, Field(ge=1000, le=3000)] = None,
                          include_retracted: bool = False,
                          page_size: Annotated[int, Field(ge=1, le=100)] = 100,
                          cursor: str = "*", refresh: bool = False) -> dict:
    """List papers citing a seed or its references. Auto-page up to 1000 records; each API page <=100. Resume using next_cursor and identical arguments. Backward search audits the seed's stored IDs against a complete query; inspect reference_coverage for missing IDs. Citation links do not imply support or a distinct study."""
    namespace, value = normalize_id(work_id)
    resolution = None
    seed = None
    if namespace != "openalex" or direction == "references":
        identifier = value if namespace == "openalex" else namespace + ":" + value
        seed_fields = "id,referenced_works,referenced_works_count" if direction == "references" else "id"
        seed, resolution = await client().request("/works/" + quote(identifier, safe="/:"), {"select": seed_fields}, refresh)
        value = seed["id"].rsplit("/", 1)[-1]
    relation = "cites" if direction == "citing" else "cited_by"
    params = {"filter": filters(f"{relation}:{value}", from_year, to_year, include_retracted), "select": fields(abstract_mode), "sort": "cited_by_count:desc"}
    result = await collect(params, limit, page_size, cursor, abstract_mode, short_chars, refresh)
    result.update(seed_id=value, direction=direction)
    if resolution:
        result["seed_resolution"] = resolution
        result["cost_note"] = "Reported cost covers list pages; the identifier-resolution request has no reported cost."
    if direction == "references":
        expected = {identifier.rsplit("/", 1)[-1] for identifier in seed.get("referenced_works", [])}
        returned = {work["id"] for work in result["results"]}
        comparison_complete = result["pagination"]["result_set_complete"]
        result["reference_coverage"] = {
            "seed_reference_count_reported": seed.get("referenced_works_count"),
            "seed_reference_ids_count": len(expected),
            "comparison_performed": comparison_complete,
            "all_seed_reference_ids_returned": expected.issubset(returned) if comparison_complete else None,
            "not_returned_reference_ids": sorted(expected - returned) if comparison_complete else None,
            "note": "An exhausted API query is not a complete bibliography. Filters, stale IDs or missing records can omit stored references; source-paper citations still require checking."
        }
    return result


@mcp.tool(annotations=READ_ONLY)
async def semantic_search(query: Annotated[str, Field(min_length=1, max_length=2000)],
                           limit: Annotated[int, Field(ge=1, le=50)] = 20,
                           abstract_mode: AbstractMode = "short",
                           short_chars: Annotated[int, Field(ge=100, le=5000)] = 500,
                           from_year: Annotated[int | None, Field(ge=1000, le=3000)] = None,
                           to_year: Annotated[int | None, Field(ge=1000, le=3000)] = None,
                           include_retracted: bool = False, refresh: bool = False) -> dict:
    """OpenAlex semantic matching by meaning. The provider returns at most 50 candidates; not exhaustive and not expandable by ordinary pagination. Full abstracts optional. No country/citation-count filters."""
    params = {"search.semantic": query, "per_page": limit, "filter": filters("", from_year, to_year, include_retracted), "select": fields(abstract_mode) + ",relevance_score"}
    data, provenance = await client().request("/works", params, refresh)
    return {"results": [format_work(w, abstract_mode, short_chars) for w in data.get("results", [])], "returned": len(data.get("results", [])), "provider_total": (data.get("meta") or {}).get("count"), "candidate_cap": 50, "query": params, "provenance": provenance, "limitations": ["Ranked semantic candidate set, not exhaustive literature coverage."]}


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
def connector_status() -> dict:
    """Report configuration without revealing credentials. Does not test connectivity."""
    return {"name": "openalex-local", "version": "0.1.0", "authentication": "api-key" if api_key() else "unauthenticated", "api_page_max": 100, "automatic_batch_max": 1000, "detail_batch_max": 100, "semantic_candidate_max": 50, "abstract_modes": ["none", "short", "full"], "cache_ttl_hours": 24, "audit_database": str(STATE / "requests.sqlite3")}


if __name__ == "__main__":
    mcp.run(transport="stdio")
