import importlib.util
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import httpx

ROOT=Path(__file__).resolve().parents[1]


class SemanticTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        with patch.dict(os.environ,{'SEMANTIC_SCHOLAR_STATE':self.tmp.name}):
            spec=importlib.util.spec_from_file_location('semantic_under_test',ROOT/'connectors/semantic-scholar/server.py')
            self.mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.mod)

    def use(self, handler):
        real=httpx.AsyncClient
        factory=lambda **kwargs:real(**kwargs,transport=httpx.MockTransport(handler))
        return patch.object(self.mod.httpx,'AsyncClient',side_effect=factory)

    async def test_cache_and_null_abstract_are_preserved_without_key_in_audit(self):
        calls=[]
        def handler(request):
            calls.append(request)
            self.assertEqual(request.headers['x-api-key'],'test-secret')
            return httpx.Response(200,json={'paperId':'fixture','abstract':None})
        with self.use(handler),patch.object(self.mod,'api_key',return_value='test-secret'):
            first=await self.mod.get_paper('DOI:10.1234/example')
            second=await self.mod.get_paper('DOI:10.1234/example')
        self.assertFalse(first['provenance']['cached']);self.assertTrue(second['provenance']['cached'])
        self.assertIsNone(first['data']['abstract']);self.assertEqual(len(calls),1)
        with sqlite3.connect(self.mod.DB) as db:
            self.assertNotIn('test-secret',str(db.execute('SELECT * FROM audit').fetchall()))

    async def test_long_rate_limit_is_explicit_error_without_retries(self):
        calls=[]
        def handler(request):
            calls.append(request);return httpx.Response(429,headers={'Retry-After':'3600'})
        with self.use(handler),patch.object(self.mod,'api_key',return_value=''):
            with self.assertRaisesRegex(ValueError,'HTTP 429'):await self.mod.get_paper('fixture')
        self.assertEqual(len(calls),1)

    async def test_empty_identifier_and_excessive_offset_rejected(self):
        with self.assertRaises(ValueError):self.mod.paper_path(' ')
        with self.assertRaises(ValueError):await self.mod.search_papers('example',100,950)


if __name__=='__main__':unittest.main()
