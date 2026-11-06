# Standalone use, capabilities and sharing

Read for setup, missing capabilities, export or use in another AI application. These skill folders contain instructions and optional local helpers. They do not require a plugin, this conversation, a particular model vendor, an institution, or the creator's accounts. Actual execution depends on what the receiving application lets the model do; a model's ability to read instructions does not supply tools.

## Resolve the supplied skills

Use the standalone [paper-fulltext-access](../../paper-fulltext-access/SKILL.md) skill for direct LibKey recovery. Install/load it alongside `literature-search-review`, or resolve it by skill name if the host stores skills in different locations. There is no private plugin install link or plugin account dependency. The access skill also works independently for known-paper retrieval.

The bundled [multi-agent-research-review](../../multi-agent-research-review/SKILL.md) is optional and explicitly invoked only. Its absence does not block an ordinary search and writer handoff. If explicitly requested but unavailable, disclose the missing workflow instead of claiming it ran.

## Use available tools by function

- Scholarly discovery: use suitable database interfaces, public APIs, website search or connected tools the recipient already has. Preserve the search preference order: a subject database (PubMed for biomedical work), OpenAlex for complementary discovery and primary citation tracing where supported, Semantic Scholar as a substitute/gap route, Asta for justified body-passage branches, and Scite as a bounded fallback. These are preferred sources, not required plugins. Other disciplines need suitable subject sources. Public web search can find candidates but does not establish equivalent database coverage.
- Source reading: inspect actual articles through available HTML, document, PDF or source-reading tools. A search snippet is not full-text evidence. Do not assume a tool name, endpoint, API key or local connector exists simply because an adapter reference describes it.
- Institutional recovery: use the access skill with a supported interactive browser the agent can control and the user can view/sign into. Respect the selected browser/profile; otherwise prefer an integrated browser when available. Without browser control, provide the direct LibKey link for user-assisted retrieval and continue public work. Do not imply autonomous recovery or copy authentication between browsers/agents.
- Context isolation: ordinary work uses a separate writer with no inherited search history when the host supports it. Without fresh-context delegation, retain the compact evidence handoff and disclose that the answer uses one context. A role label or a new section does not create an independent agent. Full multi-agent review requires actual delegation and an explicit request.
- Records: use an authorized working location or equivalent compact manual records. Optional helpers require Python 3.9+; use an available PDF reader, optionally `pypdf`, for PDF work. No package installation is required to read and follow the instructions manually. Do not claim helper validation ran when it did not.

Missing tools, rate limits, restricted browser control and unavailable subscriptions reduce what can be completed. State the observed effect and a useful permitted fallback. Do not install or reconfigure integrations automatically, invent API endpoints or silently substitute a narrower search while claiming the original coverage.

## Loading and invocation across applications

In a host supporting Agent Skills, install the full skill folders using that host's supported method. `SKILL.md`, `references/` and `scripts/` belong together. Keep supporting files available for selective reading, rather than loading the entire folder into every prompt. Descriptions identify when to use the skills; selection still depends on the host and model.

`agents/openai.yaml` is optional OpenAI-specific UI/invocation metadata. Other hosts may ignore it without losing the workflow instructions. The core instructions independently state that subject-based searches use the search skill, paywall recovery uses the access skill, and multi-agent review requires an explicit user request. Use the host's own configuration if it needs those rules registered elsewhere; metadata cannot guarantee enforcement in another product.

In a normal chat that cannot install skills, provide the entrypoint and make its referenced files available, then explicitly ask the AI to follow it for the task. File upload/pasting is manual guidance, not proof of persistent installation, automatic invocation or new capabilities. If the app cannot read a referenced file, supply the relevant file or section; do not pretend the entrypoint contains all conditional procedures.

No compatibility or accuracy guarantee is made for most models. A capable instruction-following model can interpret the workflow, but long evidence tasks need sufficient context, source-checking ability and tools. Smaller models may need more supervision. Cross-model and cross-application execution remain untested unless an actual run is reported.

## Personal settings and export

No institution, vault, reference manager, API key, local registration or absolute user path is bundled. Optional unshared `local-settings.json` may specify the recipient's browser/institution preferences and explicitly enabled library behavior. Settings do not prove authentication or authorize unrelated library changes. See [zotero-organization.md](zotero-organization.md) only for an authorized reference-manager workflow.

Share the skill folders and their relative supporting files; exclude personal settings, research runs, downloaded articles, sensitive logs, credentials, caches and bytecode. Browser sessions and institutional entitlements do not travel with an archive. Keep the search/access skills together for the integrated workflow, and keep the optional multi-agent skill on a compatible record contract.
