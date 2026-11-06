#!/usr/bin/env python3
"""Audit the explicit release manifest, including secrets and accidental runtime files."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_NAMES = {'local-settings.json','.api-key','.asta-api-key','.env','asta-tools.json'}
FORBIDDEN_PARTS = {'.venv','__pycache__','.local','state','downloads','search-records','working','review','library','.git'}
SECRET = re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9_-]{35,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
PERSONAL = re.compile(r'/(?:Users|home)/[A-Za-z0-9_.-]+/|[A-Z]:\\Users\\',re.I)


def files():
    names=json.loads((ROOT/'release-files.json').read_text())
    if len(names) != len(set(names)): raise ValueError('Duplicate release entry')
    return [ROOT/name for name in names]


def check():
    paths=files()
    for p in paths:
        rel=p.relative_to(ROOT)
        if '..' in rel.parts or p.is_symlink() or not p.is_file(): raise ValueError(f'Invalid release file: {rel}')
        if any(x in FORBIDDEN_PARTS for x in rel.parts) or p.name in FORBIDDEN_NAMES or p.suffix in {'.sqlite3','.pyc','.pdf','.log','.jsonl'}:
            raise ValueError(f'Runtime/private file in release: {rel}')
        data=p.read_text()
        if SECRET.search(data) or PERSONAL.search(data): raise ValueError(f'Possible secret/personal path in: {rel}')
    expected={'literature-search-review','paper-fulltext-access','multi-agent-research-review'}
    found={p.parent.name for p in paths if p.name=='SKILL.md'}
    if found != expected: raise ValueError('Missing/extra skill')
    print(f'Release audit passed: {len(paths)} text/source files, three skills; no runtime state.')
    return paths


if __name__ == '__main__': check()
