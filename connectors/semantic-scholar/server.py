"""Read-only Semantic Scholar tools. Run with the adjacent virtual environment."""
import asyncio
import hashlib
import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import Field

ROOT = Path(__file__).resolve().parent
STATE = Path(os.environ.get("SEMANTIC_SCHOLAR_STATE", ROOT / "state"))
STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
FIELDS = "title,year,authors,abstract,url,externalIds,citationCount,openAccessPdf"
GRAPH = "https://api.semanticscholar.org/graph/v1"
RECOMMENDATIONS = "https://api.semanticscholar.org/recommendations/v1"
DB = STATE / "requests.sqlite3"
with sqlite3.connect(DB) as db:
    db.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, fetched REAL, data TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, at TEXT, method TEXT, url TEXT, body TEXT, cached INTEGER, status TEXT)")
os.chmod(DB, 0o600)

mcp = FastMCP("semantic-scholar", instructions=(
    "Search scientific papers, retrieve metadata and citation links, and discover related papers. "
    "Results include source URLs, retrieval dates and audit IDs. Null abstracts or PDF links mean missing data. "
    "Recommendations and citation counts do not establish evidence quality or exhaustive coverage. "
    "Fetch original papers before making claims about findings. Requests are paced, cached and retried."
))
lock = asyncio.Lock()
last_request = 0.0


def api_key():
    value = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "").strip()
    keyfile = ROOT / ".api-key"
    return value or (keyfile.read_text().strip() if keyfile.exists() else "")


def audit(method, url, body, cached, status):
    with sqlite3.connect(DB) as db:
        cur = db.execute("INSERT INTO audit(at,method,url,body,cached,status) VALUES (?,?,?,?,?,?)",
                         (datetime.now(timezone.utc).isoformat(), method, url, json.dumps(body), int(cached), status))
        return cur.lastrowid


async def request(method, base, path, params, body=None):
    global last_request
    url = str(httpx.URL(base + path, params=params))
    fingerprint = hashlib.sha256(json.dumps([method, url, body], sort_keys=True).encode()).hexdigest()
    async with lock:
        with sqlite3.connect(DB) as db:
            hit = db.execute("SELECT fetched,data FROM cache WHERE key=?", (fingerprint,)).fetchone()
        if hit and time.time() - hit[0] < 86400:
            return {"data": json.loads(hit[1]), "provenance": {
                "source_url": url, "fetched_at": datetime.fromtimestamp(hit[0], timezone.utc).isoformat(),
                "cached": True, "audit_id": audit(method, url, body, True, "200")}}
        key = api_key()
        headers = {"x-api-key": key} if key else {}
        async with httpx.AsyncClient(timeout=25, follow_redirects=False) as client:
            for attempt in range(3):
                await asyncio.sleep(max(0, (1.1 if key else 3.0) - (time.monotonic() - last_request)))
                last_request = time.monotonic()
                try:
                    response = await client.request(method, url, headers=headers, json=body if body is not None else None)
                except httpx.RequestError:
                    audit(method, url, body, False, "network-error")
                    if attempt < 2:
                        await asyncio.sleep(2 ** (attempt + 1))
                        continue
                    raise ValueError("Semantic Scholar could not be reached. Try again later.") from None
                audit_id = audit(method, url, body, False, str(response.status_code))
                if response.status_code == 200:
                    data = response.json()
                    fetched = time.time()
                    with sqlite3.connect(DB) as db:
                        db.execute("DELETE FROM cache WHERE fetched<?", (fetched - 86400,))
                        db.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?)", (fingerprint, fetched, json.dumps(data)))
                    return {"data": data, "provenance": {"source_url": url,
                        "fetched_at": datetime.fromtimestamp(fetched, timezone.utc).isoformat(),
                        "cached": False, "audit_id": audit_id}}
                if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                    try:
                        delay = float(response.headers.get("Retry-After", 2 ** (attempt + 2)))
                    except ValueError:
                        delay = 8
                    if delay <= 20:
                        await asyncio.sleep(max(1, delay))
                        continue
                explanations = {429: "The shared unauthenticated pool is busy, or your key's rate limit was reached. Try later; a personal key may improve access.",
                                401: "This endpoint needs a valid API key.", 403: "Semantic Scholar refused access to this endpoint.",
                                404: "Paper or endpoint not found. Check the identifier.",
                                400: "Invalid request. Check paper IDs, year filters, and pagination."}
                raise ValueError(f"Semantic Scholar HTTP {response.status_code}: " + explanations.get(response.status_code, "Service error; try later."))


def paper_path(paper_id):
    paper_id = paper_id.strip()
    if not paper_id:
        raise ValueError("Provide a Semantic Scholar paper ID or DOI-prefixed identifier, such as DOI:10.1038/nature14299.")
    return "/paper/" + quote(paper_id, safe="")


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
async def search_papers(query: Annotated[str, Field(min_length=1, max_length=1000)],
                        limit: Annotated[int, Field(ge=1, le=100)] = 10,
                        offset: Annotated[int, Field(ge=0, le=999)] = 0,
                        year: str = "", open_access_only: bool = False) -> dict:
    """Search papers by topic or title. Optional year: 2024, 2020-2026, or 2020-. Paginate with returned next offset. Search relevance is not exhaustive coverage."""
    if offset + limit > 1000:
        raise ValueError("Relevance search only supports the first 1000 results. Narrow your query or use search_papers_boolean.")
    params = {"query": query, "limit": limit, "offset": offset, "fields": FIELDS}
    if year:
        params["year"] = year
    if open_access_only:
        params["openAccessPdf"] = ""
    return await request("GET", GRAPH, "/paper/search", params)


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
async def search_papers_boolean(query: Annotated[str, Field(min_length=1, max_length=1000)],
                                 year: str = "", token: str = "",
                                 sort: Annotated[str, Field(pattern=r"^(paperId|publicationDate|citationCount):(asc|desc)$")] = "publicationDate:desc",
                                 open_access_only: bool = False) -> dict:
    """Search title/abstract with Boolean syntax: + AND, | OR, - NOT, quotes for phrases, parentheses for groups. Useful if relevance search is throttled. Returns up to 1000 metadata records per batch, ordered by date or citations rather than relevance. Pass returned token unchanged with the same query/filters for the next batch. Narrow queries to keep batches manageable."""
    params = {"query": query, "fields": "title,year,url,externalIds,citationCount,openAccessPdf", "sort": sort}
    if year:
        params["year"] = year
    if token:
        params["token"] = token
    if open_access_only:
        params["openAccessPdf"] = ""
    return await request("GET", GRAPH, "/paper/search/bulk", params)


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
async def get_paper(paper_id: str) -> dict:
    """Get paper metadata, abstract and available open-access PDF link by Semantic Scholar ID or DOI:... identifier. Does not retrieve full text."""
    return await request("GET", GRAPH, paper_path(paper_id), {"fields": FIELDS})


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
async def list_references(paper_id: str, limit: Annotated[int, Field(ge=1, le=100)] = 20,
                          offset: Annotated[int, Field(ge=0)] = 0) -> dict:
    """List papers cited BY the given paper. Follow the returned next offset for further pages."""
    return await request("GET", GRAPH, paper_path(paper_id) + "/references", {"fields": FIELDS, "limit": limit, "offset": offset})


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
async def list_citations(paper_id: str, limit: Annotated[int, Field(ge=1, le=100)] = 20,
                         offset: Annotated[int, Field(ge=0)] = 0) -> dict:
    """List papers that CITE the given paper. Follow the returned next offset for further pages."""
    return await request("GET", GRAPH, paper_path(paper_id) + "/citations", {"fields": FIELDS, "limit": limit, "offset": offset})


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
async def recommend_papers(positive_paper_ids: Annotated[list[str], Field(min_length=1, max_length=100)],
                           negative_paper_ids: Annotated[list[str], Field(max_length=100)] = [],
                           limit: Annotated[int, Field(ge=1, le=100)] = 10) -> dict:
    """Recommend papers using relevant seed papers and optional irrelevant examples. Use returned Semantic Scholar paperId values for seeds. May be throttled without a key."""
    return await request("POST", RECOMMENDATIONS, "/papers", {"fields": FIELDS, "limit": limit},
                         {"positivePaperIds": positive_paper_ids, "negativePaperIds": negative_paper_ids})


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
def connector_status() -> dict:
    """Report local connector configuration without exposing credentials. Does not test API availability."""
    authenticated = bool(api_key())
    return {"authentication": "api-key" if authenticated else "unauthenticated",
            "minimum_request_interval_seconds": 1.1 if authenticated else 3.0,
            "cache_ttl_hours": 24, "audit_database": str(DB)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
