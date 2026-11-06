#!/usr/bin/env python3
"""Opt-in installation/configuration. Never edits an AI host's configuration."""
import argparse
import getpass
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ('literature-search-review', 'paper-fulltext-access', 'multi-agent-research-review')
SERVERS = {
    'openalex-local': ('openalex-local/server.py', ['OPENALEX_API_KEY']),
    'semantic-scholar': ('semantic-scholar/server.py', ['SEMANTIC_SCHOLAR_API_KEY']),
    'literature-access': ('literature-access/server.py', []),
    'asta': ('literature-access/asta_proxy.py', ['ASTA_TOOL_KEY', 'ASTA_API_KEY']),
}
KEYS = {'openalex-local': '.api-key', 'semantic-scholar': '.api-key', 'asta': '.asta-api-key'}


def install(destination, selected):
    destination = Path(destination).expanduser().resolve()
    names = list(dict.fromkeys(selected or SKILLS))
    if 'literature-search-review' in names and 'paper-fulltext-access' not in names:
        names.append('paper-fulltext-access')
    if 'multi-agent-research-review' in names:
        names = list(dict.fromkeys(names + list(SKILLS)))
    for name in names:
        target = destination / name
        if target.exists() or target.is_symlink():
            raise ValueError(f'Refusing to overwrite {target}; back up/remove the old installation first.')
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.literature-install-', dir=destination) as tmp:
        for name in names:
            shutil.copytree(ROOT / 'skills' / name, Path(tmp) / name,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'local-settings.json'))
        for name in names:
            (Path(tmp) / name).rename(destination / name)
    print('Installed: ' + ', '.join(names))


def configurations(names, portable=False):
    base = '${PLUGIN_ROOT}' if portable else str(ROOT)
    python = base + '/.venv/bin/python'
    result = {}
    for name in names:
        rel, envs = SERVERS[name]
        result[name] = {'command': python, 'args': [base + '/connectors/' + rel]}
        if portable:
            result[name]['type'] = 'stdio'
            result[name]['cwd'] = base
        else:
            result[name]['env_vars'] = envs
            result[name]['startup_timeout_sec'] = 30
            result[name]['tool_timeout_sec'] = 120
    return result


def config(names, fmt):
    rows = configurations(names, fmt == 'plugin')
    if fmt in {'json', 'plugin'}:
        if fmt == 'json':
            rows = {k: {a: b for a, b in v.items() if a in {'command', 'args'}} for k, v in rows.items()}
        result = {'mcpServers': rows}
        if fmt == 'plugin':
            result['$schema'] = 'https://agent-plugins.org/schemas/1.0.0/mcp.schema.json'
        print(json.dumps(result, indent=2))
    else:
        for name, row in rows.items():
            print(f'[mcp_servers.{json.dumps(name)}]')
            for key, value in row.items():
                print(f'{key} = {json.dumps(value)}')
            print()


def set_key(name):
    target = ROOT / 'connectors' / ('literature-access' if name == 'asta' else name) / KEYS[name]
    value = getpass.getpass(f'{name} API key (hidden): ').strip()
    if not value or any(c.isspace() for c in value):
        raise ValueError('Key must be nonempty and contain no whitespace.')
    fd, tmp = tempfile.mkstemp(prefix='.key-', dir=target.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(value + '\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    print('Saved locally with owner-only permissions. No key was printed.')


def doctor():
    print(f'Python {sys.version.split()[0]} — release target: 3.12')
    failed = sys.version_info[:2] < (3, 12)
    for name, expected in [('mcp','1.30.0'), ('httpx','0.28.1'), ('beautifulsoup4','4.14.3')]:
        try:
            version = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            version = 'missing'
        print(f'{name}: {version} (pinned {expected})')
        failed |= version != expected
    for name, file in KEYS.items():
        directory = 'literature-access' if name == 'asta' else name
        configured = (ROOT/'connectors'/directory/file).is_file() or any(os.environ.get(v) for v in SERVERS[name][1])
        print(f'{name} key: ' + ('configured; not verified' if configured else 'not configured'))
    print('Asta schema: ' + ('present' if (ROOT/'connectors/literature-access/asta-tools.json').is_file() else 'not initialized (optional)'))
    print('Offline checks only. Run scripts/smoke.py for local MCP startup; --live also contacts providers.')
    return int(failed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    ins = sub.add_parser('install-skills')
    ins.add_argument('--dest', required=True, help='Explicit host skill directory, e.g. ~/.agents/skills')
    ins.add_argument('--skill', action='append', choices=SKILLS)
    cfg = sub.add_parser('config')
    cfg.add_argument('--format', choices=['toml','json','plugin'], default='toml')
    cfg.add_argument('--server', action='append', choices=SERVERS)
    key = sub.add_parser('set-key'); key.add_argument('server', choices=KEYS)
    sub.add_parser('doctor')
    args = parser.parse_args()
    try:
        if args.command == 'install-skills': install(args.dest, args.skill)
        elif args.command == 'config': config(args.server or list(SERVERS)[:3], args.format)
        elif args.command == 'set-key': set_key(args.server)
        else: return doctor()
    except (ValueError, OSError) as e:
        parser.exit(1, str(e) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
