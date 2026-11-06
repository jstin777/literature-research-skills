#!/usr/bin/env python3
"""Fetch current upstream tool contracts on request, without republishing them."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'connectors/literature-access'))
from core import ASTA_URL, asta_key
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def refresh():
    key = asta_key()
    async with asyncio.timeout(30):
        async with streamablehttp_client(ASTA_URL, headers={'x-api-key': key} if key else None,
                                         timeout=5, sse_read_timeout=15) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                if not result.tools or result.nextCursor:
                    raise ValueError('Empty or paginated schema; existing schema retained.')
                data = json.dumps([t.model_dump(mode='json', by_alias=True, exclude_none=True) for t in result.tools], indent=2).encode()
    target = ROOT/'connectors/literature-access/asta-tools.json'
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix='.schema-')
    try:
        with os.fdopen(fd, 'wb') as f: f.write(data)
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    print(json.dumps({'tools': len(result.tools), 'sha256': hashlib.sha256(data).hexdigest()}))


if __name__ == '__main__':
    try: asyncio.run(refresh())
    except Exception as e:
        print(f'Asta schema refresh failed ({type(e).__name__}); existing schema retained.', file=sys.stderr)
        raise SystemExit(1)
