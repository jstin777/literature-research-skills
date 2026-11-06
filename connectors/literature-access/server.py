"""Read-only recovery tools for publicly accessible PMC articles."""
from mcp.server.fastmcp import FastMCP
import httpx
from core import ArticleAccess, Store, AccessError, asta_key

mcp = FastMCP("literature-access", instructions=(
    "Recover public PMC article bodies through article HTML and Europe PMC JATS XML when other tools fail. "
    "Fetch by exact PMCID, PMID or DOI; follow response_truncated/next_start_char to finish reading. "
    "search_article_passages searches ONE retrieved article, not a broad corpus. "
    "Tools preserve original HTML or XML, identifiers, original section links, extraction warnings and provenance. "
    "Main-body detection is mechanical; scientific evidence and visual completeness still require inspection. "
    "Asta's separately registered guarded proxy reports real failure and cooldown instead of hanging. "
    "Use connector_health to inspect persisted endpoint-specific state without new network calls."
))
access = ArticleAccess()


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
async def fetch_pmc_fulltext(identifier: str, start_char: int = 0, max_characters: int = 20000, refresh: bool = False) -> dict:
    """Retrieve a public PMC article body using HTML and Europe PMC JATS recovery. Accept PMCID, PMID, DOI or canonical URL. Immutable native source cache; explicit paging. No PDF download. Only PMC-linked articles are supported; no-body, challenge, identity mismatch and timeouts are errors, never empty success. Read original figures/equations when needed."""
    try:
        return await access.fetch(identifier, start_char, max_characters, refresh)
    except AccessError as e:
        raise ValueError(f"{e.code}: {e}") from None
    except TimeoutError:
        raise ValueError("deadline_exceeded: Public-article recovery exceeded 24 seconds. This route failure does not establish article inaccessibility.") from None
    except httpx.HTTPError as e:
        status = e.response.status_code if isinstance(e, httpx.HTTPStatusError) else "network"
        raise ValueError(f"upstream_failure: Public article route returned {status}; try another available access route. No article body was accepted.") from None


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
async def search_article_passages(identifier: str, query: str, limit: int = 5) -> dict:
    """Find literal paragraph passages in ONE exact PMC article using lexical term overlap, with source section links. Narrow fallback for paper-specific passage verification when Asta stalls. Does not discover papers or reproduce Asta's semantic corpus search. No matches means this query found no lexical match in this article only."""
    return await access.passages(identifier, query, limit)


@mcp.tool(annotations={"readOnlyHint": True})
async def connector_health() -> dict:
    """Report saved capability-specific Asta health and recovery configuration. Does not make network calls or expose keys; not_tested is not healthy."""
    store = Store()
    return {"name": "literature-access", "version": "0.1.0", "asta_api_key_configured": bool(asta_key()),
            "asta_passages": store.health("asta:snippet_search"), "asta_metadata": store.health("asta:get_paper"),
            "pmc_html": store.health("pmc_html"),
            "epmc_xml": store.health("epmc_xml"),
            "pmc_scope": "public PMC HTML; DOI/PMID resolved through Europe PMC", "article_request_deadline_seconds": 24,
            "source_cache": str(store.root), "notes": ["Asta failures are isolated by operation.",
             "An open circuit skips the same failing operation for its stated cooldown; it does not mean no literature exists."]}


if __name__ == "__main__":
    mcp.run()
