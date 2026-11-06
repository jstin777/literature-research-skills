"""Same Asta tool schemas, with hard deadlines, caching and per-tool cooldowns."""
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from core import AstaGuard, ASTA_URL, asta_key

ROOT = Path(__file__).resolve().parent


async def worker():
    request = json.loads(sys.stdin.read())
    key = asta_key()
    headers = {"x-api-key": key} if key else None
    try:
        async with streamablehttp_client(ASTA_URL, headers=headers, timeout=5, sse_read_timeout=25) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(request["name"], request["arguments"])
                print(result.model_dump_json(by_alias=True), flush=True)
    except Exception as e:
        # Do not print transport headers or exceptions that might contain credentials.
        from core import error_result
        print(json.dumps(error_result("transport_error", type(e).__name__)), flush=True)


async def serve():
    schema_path = ROOT / "asta-tools.json"
    if not schema_path.is_file():
        raise SystemExit("Run scripts/refresh_asta_schema.py before enabling guarded Asta.")
    schemas = json.loads(schema_path.read_text())
    server = Server("asta-guarded", version="0.1.0", instructions=(
        "Asta's original scientific corpus tools, forwarded unchanged through a local reliability wrapper. "
        "Each remote call has a hard process deadline. Successful responses are cached for 24 hours. "
        "A timed-out passage search opens a 15-minute per-tool cooldown; working metadata tools remain available. "
        "If a failed passage search specifies exact paper_ids, the wrapper can recover lexical passages from up to three public PMC copies. "
        "Such results are explicitly labeled partial_recovery with their actual scope and source provenance. "
        "An error or open circuit is not an empty result or evidence of absent literature. "
        "Use other scholarly databases for discovery, or literature-access search_article_passages for one known PMC article. "
        "These alternatives have different coverage; never label a metadata search as full-text passage search."
    ))
    guard = AstaGuard()

    @server.list_tools()
    async def list_tools():
        tools = [types.Tool.model_validate(x) for x in schemas]
        for tool in tools:
            if tool.name == "snippet_search":
                tool.description = (tool.description or "") + "\nLocal reliability wrapper: hard deadline; per-tool cooldown after failure. Exact paper_ids can receive explicitly labeled partial_recovery from lexical public-PMC paragraphs, with original section links. Broad corpus searches never silently fall back to metadata or narrower snippets."
        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name not in {x["name"] for x in schemas}:
            raise ValueError("Unknown Asta tool")
        result = await guard.call(name, arguments)
        # Asta declares snippet_searchOutput as {result: object|null}.
        # Keep the advertised output contract for a locally recovered response too.
        data = result.get("structuredContent")
        if name == "snippet_search" and data and data.get("status") == "partial_recovery":
            result["structuredContent"] = {"result": data}
            result["content"] = [{"type": "text", "text": json.dumps(result["structuredContent"])}]
        return types.CallToolResult.model_validate(result)

    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(worker() if "--worker" in sys.argv else serve())
