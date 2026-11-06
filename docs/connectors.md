# Optional connector setup

Use a stable local checkout/extraction directory. For the connector ZIP, first extract it and create `.venv` **inside its root**; for the complete bundle, use its repository root:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements/connectors.lock.txt
.venv/bin/python scripts/manage.py doctor
.venv/bin/python scripts/smoke.py
```

## Local registration in Codex

Generate configuration for OpenAlex, Semantic Scholar and public-article recovery:

```sh
.venv/bin/python scripts/manage.py config
```

Review the printed TOML and add the chosen blocks to your existing `~/.codex/config.toml` without replacing other settings. The generator only prints; it never writes the host config. Use `--server openalex-local` to choose one server (repeat the flag for several). Paths are generated for the recipient’s location and are quoted safely for spaces. Keep the checkout in place after registration.

For another host, `config --format json` prints a conventional `mcpServers` object. JSON environment passing varies by host; use its credential UI/environment support or the hidden key prompt below. Use only one registration per server. Fresh chats may be required for new tools.

The optional connector ZIP also has a portable `plugin.json`/`mcp.json`. Its `${PLUGIN_ROOT}/.venv/bin/python` must exist at the **actual installed plugin root**. Hosts that copy plugins to a managed cache may not copy an already-created venv reliably; use the documented direct MCP registration instead. The archive has source and dependency pins, not executable environments. Plugin UI installation is not claimed tested.

## Own keys, when needed

Keep keys out of commands, chat messages and config examples. These prompts hide input and save a mode-0600 file beside the relevant server:

```sh
.venv/bin/python scripts/manage.py set-key openalex-local
.venv/bin/python scripts/manage.py set-key semantic-scholar
```

Alternatively supply `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`, or `ASTA_TOOL_KEY` through the server’s environment. Generated Codex config forwards these names. A GUI application does not necessarily inherit terminal environment variables. No keys are needed for offline tests or local startup checks. OpenAlex paging past the first page requires a key; anonymous success on one result does not prove paging access.

## Guarded Asta, separately enabled

The proxy preserves current upstream tool schemas and adds bounded calls, per-operation cooldowns and source-preserving recovery for exact PMC-linked scopes. A failed broad search is not silently replaced with a narrow search.

```sh
# Optional if your Asta access requires a key:
.venv/bin/python scripts/manage.py set-key asta
# Contacts the official endpoint and saves a local schema, never the key:
.venv/bin/python scripts/refresh_asta_schema.py
.venv/bin/python scripts/manage.py config --server asta
.venv/bin/python scripts/smoke.py --asta
```

Copy the printed block into host settings. The runtime schema is ignored by Git and excluded from release artifacts; rerun its refresh when upstream tools change. Existing schemas survive a failed refresh. Registration and tool discovery do not establish passage-search availability. Asta body snippets still need verification against originals.

## PubMed and Scite

These remote services have no local source/runtime dependency in this bundle. After reviewing the provider instructions:

```sh
codex mcp add pubmed --url https://pubmed.caseyjhand.com/mcp
codex mcp add scite --url https://api.scite.ai/mcp
codex mcp login scite
```

Scite uses the recipient’s OAuth sign-in and requires a paid plan or trial. PubMed’s example endpoint is operated by its upstream MCP maintainer; a recipient can instead deploy [its source](https://github.com/cyanheads/pubmed-mcp-server) or use an already-connected trusted PubMed tool. No third-party server binaries, cloud app IDs, authentication tokens or account access are redistributed. [Remote TOML example](../examples/remote-mcp.toml).

Scite’s MCP connection and its Zotero citation-column plugin are separate integrations. For the latter, follow the [Zotero workflow documentation](https://github.com/jstin777/zotero-obsidian-workflow). Citation tallies are navigation/context, not scientific validity scores.

## State and checks

Each local connector stores its private cache/audit files under `connectors/<name>/state/`. `OPENALEX_STATE`, `SEMANTIC_SCHOLAR_STATE` and `LITERATURE_ACCESS_STATE` can override those locations. Preserve native article sources referenced by research records before deleting caches. Smoke tests use temporary state and remove it afterward.

`scripts/smoke.py` tests real STDIO initialization, tool discovery and local health/status calls. `--live` additionally makes a small public lookup per provider. Asta `--asta` checks its local transport/schema only. Provider failures are reported as failures; no network tests run in offline CI.
