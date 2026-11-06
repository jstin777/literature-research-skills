# Dependencies and services

The skills themselves are Markdown/YAML instructions. They have **no mandatory Python, Node, API-key, Zotero or Obsidian dependency** for manual use in a capable host. The following table separates implementation from external capabilities.

| Component | Included | Runtime/account requirement |
| --- | --- | --- |
| Three skill folders | Full instructions, references and agent metadata | Host capable of following skills and reading references |
| Record catalogue | Python source and offline tests | Python standard library; release tested on 3.12 |
| Source-file inspection | Python source | Optional `pypdf==7.0.0`; no OCR |
| OpenAlex Local | MCP server and tests | Python 3.12 + connector lock; your OpenAlex key strongly recommended and needed for cursor paging past page one |
| Semantic Scholar | MCP server | Same lock; anonymous calls may be throttled; your key for endpoints/limits requiring it |
| Literature Access | MCP server, parser, recovery tests | Same lock; public PMC HTML and Europe PMC JATS only |
| Guarded Asta | Proxy and recovery implementation | Same lock; opt-in schema fetch; Ai2 endpoint/terms and your key when needed |
| PubMed MCP | Configuration example and upstream link | External hosted service, or separately managed upstream deployment |
| Scite MCP | Configuration and account setup | External Scite sign-in; paid plan or trial according to its setup page |
| LibKey | Standalone access skill | Supported interactive browser; institutional entitlement where needed |
| Browser/PDF viewer | Capability guidance | Receiving host’s supported tools; no browser binaries or sessions bundled |
| Multi-agent execution | Review instructions | Real fresh-context delegation; host/model usage costs apply |
| Zotero/Obsidian | Optional integration guidance | Separate installation; [reading-workflow template](https://github.com/jstin777/zotero-obsidian-workflow) |

The pinned connector stack is `mcp==1.30.0`, `httpx==0.28.1`, `beautifulsoup4==4.14.3` and every transitive package in [connectors.lock.txt](../requirements/connectors.lock.txt). Development adds `PyYAML==6.0.3`. No Node/pnpm dependency is needed for this distribution. The lock is a tested version set, not a vendored offline wheel archive or a hash-pinned supply-chain lock. A fresh installation downloads packages from the configured package index.

Queries go to the selected provider. Local caches/audit records can contain research queries, metadata and public source text. They remain private and are excluded from release artifacts. Browser authentication and cloud-plugin accounts are never exported.

## Verified setup references

- [OpenAI skills](https://learn.chatgpt.com/docs/build-skills), [MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli), and [portable plugin packaging](https://developers.openai.com/plugins/build/plugins).
- [OpenAlex authentication](https://help.openalex.org/api/authentication/): anonymous basic use is available; accounts/keys affect paging and budgets. See current provider limits before large runs.
- [Semantic Scholar API](https://api.semanticscholar.org/api-docs/): request your own key through the provider if needed.
- [Ai2 Asta MCP and license agreement](https://allenai.org/asta/resources/mcp).
- [PubMed MCP deployment](https://pubmed.caseyjhand.com/) and [upstream source](https://github.com/cyanheads/pubmed-mcp-server): this is a third-party interface to NCBI, not an NCBI-operated MCP endpoint.
- [Scite setup and authentication](https://scite.ai/mcp): requires a paid plan or free trial; not supplied by the separate Zotero plugin.
- [LibKey](https://libkey.io/) and [Europe PMC REST API](https://europepmc.org/RestfulWebService).

Service terms and remote versions can change independently of this release. Remote services cannot be pinned by a local requirements file. See the compatibility report for what was actually exercised.
