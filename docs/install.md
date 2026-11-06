# Installation

## 1. Install the skills

Choose **one** route:

1. Complete source release or Git clone: run `python3 scripts/manage.py install-skills --dest "$HOME/.agents/skills"` from the repository root. Add `--skill paper-fulltext-access` for only the access skill; selecting search automatically includes access, and selecting multi-agent review includes both companions. Existing folders are never overwritten.
2. Individual skill ZIP: extract its named folder into your host’s skill directory. Install access alongside search; install all three for the staged review. Keep references/scripts with `SKILL.md`.
3. Skills-only plugin ZIP: use a host that accepts the portable `plugin.json` format and its documented local import flow. The archive has three skills and no automatically enabled servers. Local plugin import in each application is not verified by this release.

Codex’s documented user skill directory is `~/.agents/skills`; a project can instead use `.agents/skills`. Other hosts may use other directories or require explicit loading. Do not duplicate the same skills in both a plugin and a folder. [Official skill installation guidance](https://learn.chatgpt.com/docs/build-skills).

Without installable skills, make the entrypoint and its referenced files available to the chat and explicitly ask it to follow the instructions. This is manual guidance, not persistent installation or new tools.

## 2. Select capabilities

For a useful reading list, the host needs scholarly/web discovery and metadata/abstract reading. For substantive findings, it needs actual original-source reading. A PDF reader with visual inspection is needed for figures, equations and scans. The optional `pypdf` helper extracts native text; it is not OCR or a visual verifier.

Full-text recovery needs an interactive browser that the host can control and the user can sign into. Direct LibKey links do not require a LibKey browser extension. An institution’s entitlement, user login and MFA remain separate. If control is unavailable, the user can open the link and supply an authorized source.

Ordinary evidence writing uses a separate writer with a fresh context when supported. The optional staged review requires actual independent agents and an explicit request. A single model simulating role headings is not equivalent. No particular model or subscription is mandated by the skill package.

## 3. Optional local tool stack

Install Python 3.12 from [python.org](https://www.python.org/downloads/macos/) or your trusted package manager. Run from the complete source checkout:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements/connectors.lock.txt
.venv/bin/python -m pip install -r requirements/helpers.txt
.venv/bin/python scripts/manage.py doctor
.venv/bin/python scripts/smoke.py
```

The first dependency file includes direct and transitive pins; PDF support is separate. No system-wide Python installation is modified. Then follow [connector setup](connectors.md) to register only the servers you want. Doctor reports local configuration; it does not establish account access or provider health.

## 4. First search

Ask for five papers on a neutral topic, with links and access labels, downloads off. Confirm that the answer distinguishes full text from abstract-only candidates and records search limits. For a substantive evidence synthesis, ask the agent to retain its records in a private working directory **outside this public repository**. The entrypoint routes to the shared record contract.

Known-paper test: supply a DOI and ask `paper-fulltext-access` to find readable full text. A successful page load is insufficient: verify article identity and body coverage. Do not expect a PDF when none was requested.

Explicit advanced invocation: “Use multi-agent-research-review to evaluate this question.” Confirm that real independent stages ran and that the final citation/methods audits are recorded. If delegation is unavailable, keep the limitation visible.

## Troubleshooting

- Skill absent: check the host’s directory/import format, the folder name and `SKILL.md`; refresh/restart the chat. Avoid duplicate names.
- Server absent: inspect the generated executable/argument paths, run `smoke.py`, then refresh the host. A transport smoke test does not prove an existing chat reloaded tools.
- Key configured but access denied: check provider activation/entitlement; never paste keys into research logs or public issues.
- HTTP 429 or timeout: respect cooldowns and provider budgets. Use a permitted alternate route and report its different coverage.
- Empty abstracts or missing PDFs: missing metadata is not a negative scientific finding. Inspect an authorized original source.
- Source/PDF parser warning: do not label partial, image-only or malformed content complete; inspect the original with suitable tools.
