# Updates, privacy and releases

## Private state

Back up research records, checkpoints, evidence, handoffs and source files in their private research workspace. If a record points to a connector’s native source cache, preserve that source and checksum before clearing the cache. API response caches can usually be rebuilt; their old provenance timestamps cannot. Store API keys in your own protected backup/password manager if desired. This repository’s ignore rules do not make a public research directory private.

The release builder uses an explicit file allowlist, not a recursive copy of a live installation. It excludes keys, personal `local-settings.json`, caches, SQLite databases, runtime tool schemas, downloaded papers and working research. Do not add those files to the release manifest. Public examples/tests must be synthetic or contain only deliberately chosen public identifiers.

## Upgrade or uninstall

Record the release tag and back up private settings before upgrading. Extract a new release to a new folder and test it before changing registrations. The skill installer refuses overwrites: back up the old skill directories, remove or move them yourself, then install the new version. Restore only recipient-specific settings after reviewing changes.

When relocating the source checkout, recreate its venv and regenerate MCP paths. Do not move a Python venv and assume its absolute interpreter paths remain valid. Reconfigure only the relevant server blocks; preserve unrelated host settings. Stop/restart affected MCP processes before replacing their code.

To uninstall, remove the chosen skill folders or plugin, remove the corresponding MCP blocks through your host’s supported flow, stop those servers and remove their source directory after preserving any referenced source files. This project installs no LaunchAgent, background scheduler, global Python package, browser extension or automatic Git hook.

## Release procedure

1. Update source, `plugin.json` version, dependency pins if needed, and compatibility/changelog evidence.
2. Install `requirements/dev.txt` in a fresh Python 3.12 venv; run `scripts/test.py`, `scripts/smoke.py` and `pip check`.
3. Review every new file, then update `release-files.json`. Run `scripts/check_release.py`. Inspect the Git staging area/history for unintended data; automated patterns cannot prove the absence of all secrets.
4. Run `scripts/build_release.py`; inspect ZIP inventories and checksums. Rebuild after source edits. Keep one canonical source folder per skill; individual assets are generated from it.
5. Publish one version tag with the complete source bundle, skills plugin, three skill ZIPs, optional connectors and `SHA256SUMS.txt`. Report live failures and untested host workflows honestly.

The committed lock pins every Python package version, while external MCP services and their schemas remain independent. Changes in an upstream API may need new connector tests. Do not relabel a registration smoke test as an end-to-end scientific validation.
