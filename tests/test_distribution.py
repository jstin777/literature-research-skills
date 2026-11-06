import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest

import yaml

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import manage


class DistributionTests(unittest.TestCase):
    def test_search_install_includes_access_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(prefix='skill install ') as tmp:
            dest=Path(tmp)/'skills'
            with contextlib.redirect_stdout(io.StringIO()): manage.install(dest,['literature-search-review'])
            self.assertTrue((dest/'paper-fulltext-access/SKILL.md').is_file())
            marker=dest/'literature-search-review/private-note.txt';marker.write_text('keep')
            with self.assertRaises(ValueError): manage.install(dest,['literature-search-review'])
            self.assertEqual(marker.read_text(),'keep')
            self.assertFalse((dest/'multi-agent-research-review').exists())

    def test_frontmatter_and_explicit_only_policy(self):
        for name in manage.SKILLS:
            text=(ROOT/'skills'/name/'SKILL.md').read_text()
            meta=yaml.safe_load(text.split('---',2)[1])
            self.assertEqual(meta['name'],name)
            self.assertIsInstance(meta['description'],str)
            agent=yaml.safe_load((ROOT/'skills'/name/'agents/openai.yaml').read_text())
            self.assertEqual(agent['policy']['allow_implicit_invocation'],name!='multi-agent-research-review')

    def test_toml_quotes_actual_paths_and_forwards_key_names_only(self):
        out=io.StringIO()
        with contextlib.redirect_stdout(out): manage.config(['openalex-local','asta'],'toml')
        parsed=tomllib.loads(out.getvalue())['mcp_servers']
        self.assertEqual(parsed['asta']['args'],[str(ROOT/'connectors/literature-access/asta_proxy.py')])
        self.assertEqual(parsed['openalex-local']['env_vars'],['OPENALEX_API_KEY'])
        self.assertNotIn('env',parsed['openalex-local'])

    def test_portable_paths_are_resolvable_under_plugin_root(self):
        for row in manage.configurations(['openalex-local','semantic-scholar','literature-access'],True).values():
            self.assertTrue((ROOT/row['args'][0].replace('${PLUGIN_ROOT}/','')).is_file())
            self.assertEqual(row['type'],'stdio')

    def test_no_python_dependencies_needed_for_catalogue_help(self):
        result=subprocess.run([sys.executable,'-S',str(ROOT/'skills/literature-search-review/scripts/catalogue.py'),'--help'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':unittest.main()
