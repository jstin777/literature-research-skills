#!/usr/bin/env python3
"""Exercise real MCP transports; live calls are opt-in and use public examples."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

ROOT = Path(__file__).resolve().parents[1]


async def local(name, rel, call, live, env):
    async with asyncio.timeout(55):
        async with stdio_client(StdioServerParameters(command=sys.executable,
                args=[str(ROOT/'connectors'/rel)], env=env)) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                status = {'server': name, 'transport': 'ok', 'tools': len(tools.tools)}
                if call and (live or name != 'asta'):
                    result = await session.call_tool(*call)
                    status['call'] = call[0]
                    status['result'] = 'error' if result.isError else 'ok'
                    # No article text, queries, credentials, or local paths in the report.
                if live and name == 'openalex-local':
                    result = await session.call_tool('search_works', {'query':'photosynthesis', 'limit':1, 'abstract_mode':'none'})
                    status['live_result'] = 'error' if result.isError else 'ok'
                if live and name == 'semantic-scholar':
                    result = await session.call_tool('get_paper', {'paper_id':'DOI:10.1038/nature12373'})
                    status['live_result'] = 'error' if result.isError else 'ok'
                if live and name == 'literature-access':
                    result = await session.call_tool('fetch_pmc_fulltext', {'identifier':'PMC6608411', 'max_characters':500})
                    status['live_result'] = 'error' if result.isError else 'ok'
                return status


async def main(live=False, asta=False):
    with tempfile.TemporaryDirectory(prefix='literature-smoke-') as tmp:
        env = dict(os.environ)
        for key, folder in [('OPENALEX_STATE','openalex'),('SEMANTIC_SCHOLAR_STATE','semantic'),('LITERATURE_ACCESS_STATE','access')]:
            env[key] = str(Path(tmp)/folder)
        rows = [('openalex-local','openalex-local/server.py',('connector_status', {})),
                ('semantic-scholar','semantic-scholar/server.py',('connector_status', {})),
                ('literature-access','literature-access/server.py',('connector_health', {}))]
        if asta:
            rows.append(('asta','literature-access/asta_proxy.py',None))
        failed = False
        for name, rel, call in rows:
            try:
                status = await local(name, rel, call, live, env)
                failed |= 'error' in status.values()
            except Exception as e:
                status = {'server':name, 'transport':'failed', 'exception':type(e).__name__}
                failed = True
            print(json.dumps(status), flush=True)
        return int(failed)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--live',action='store_true'); p.add_argument('--asta',action='store_true')
    args=p.parse_args()
    raise SystemExit(asyncio.run(main(args.live,args.asta)))
