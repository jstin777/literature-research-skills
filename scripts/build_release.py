#!/usr/bin/env python3
"""Reproducible source/plugin/skill ZIPs from a reviewed file allowlist."""
import hashlib
import json
from pathlib import Path
import zipfile
from check_release import check, ROOT


def archive(path, rows):
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name, data in sorted(rows.items()):
            info=zipfile.ZipInfo(name,(2026,11,6,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644 << 16
            z.writestr(info,data)


def main():
    files=check()
    version=json.loads((ROOT/'plugin.json').read_text())['version']
    out=ROOT/'dist';out.mkdir(exist_ok=True)
    allrows={str(p.relative_to(ROOT)):p.read_bytes() for p in files}
    outputs=[]
    name=f'literature-research-skills-v{version}.zip'
    archive(out/name,{f'literature-research-skills/{k}':v for k,v in allrows.items()});outputs.append(name)
    name=f'literature-research-plugin-v{version}.zip'
    archive(out/name,{k:v for k,v in allrows.items() if k.startswith('skills/') or k in {'plugin.json','LICENSE','THIRD_PARTY_NOTICES.md','dependency-licenses.json'}});outputs.append(name)
    for skill in ('literature-search-review','paper-fulltext-access','multi-agent-research-review'):
        prefix=f'skills/{skill}/'
        rows={f'{skill}/{k[len(prefix):]}':v for k,v in allrows.items() if k.startswith(prefix)}
        rows[f'{skill}/LICENSE']=allrows['LICENSE']
        rows[f'{skill}/INSTALL.md']=(f'# {skill}\n\nInstall this folder in the skill directory supported by your host. '
            'See https://github.com/jstin777/literature-research-skills for setup and optional tools. '
            'Literature search uses paper-fulltext-access; install both for the integrated workflow. '
            'Multi-agent review can use both companions and requires an explicit request and real delegation. '
            'Installing instructions does not add browser control, database access or subscriptions.\n').encode()
        name=f'{skill}-v{version}.zip';archive(out/name,rows);outputs.append(name)
    # A source package for optional local tools; no auto-install hooks or binaries.
    name=f'literature-connectors-v{version}.zip'
    rows={k:v for k,v in allrows.items() if k.startswith(('connectors/','requirements/','docs/','examples/')) or k in {'LICENSE','THIRD_PARTY_NOTICES.md','dependency-licenses.json','scripts/manage.py','scripts/smoke.py','scripts/refresh_asta_schema.py'}}
    manifest={'$schema':'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json','name':'literature-connectors','version':version,'description':'Optional local scholarly discovery and full-text recovery MCP servers. Requires Python setup.','license':'MIT'}
    rows['plugin.json']=json.dumps(manifest,indent=2).encode()
    from manage import configurations
    rows['mcp.json']=json.dumps({'$schema':'https://agent-plugins.org/schemas/1.0.0/mcp.schema.json','mcpServers':configurations(['openalex-local','semantic-scholar','literature-access'],True)},indent=2).encode()
    rows['README.md']=allrows['docs/connectors.md']
    archive(out/name,rows);outputs.append(name)
    checks=''.join(f'{hashlib.sha256((out/n).read_bytes()).hexdigest()}  {n}\n' for n in sorted(outputs))
    (out/'SHA256SUMS.txt').write_text(checks)
    print('\n'.join(outputs))


if __name__=='__main__':main()
