# Compatibility and validation — 0.1.0

Checked **2026-11-06** on **macOS 26.6.2, Apple Silicon (arm64), Python 3.12.13**. This is an initial public release, not a guarantee that every host/provider/model combination works.

| Check | Result and limit |
| --- | --- |
| Fresh connector dependency install | Passed in a new Python 3.12 venv; all transitive versions pinned; `pip check` passed |
| Skill format and relative references | All three skills passed skill validation; supporting-file links resolve |
| Offline regressions | **100 passed**: 52 catalogue/source, 25 OpenAlex, 15 full-text/Asta recovery, 8 distribution/Semantic Scholar |
| Clean skill installation | Passed in a temporary path containing spaces; dependency selection and refusal to overwrite tested |
| Portable plugin manifest | Validated against the published 1.0.0 schema; this does not establish UI installation |
| Real local MCP transports | OpenAlex (6 tools), Semantic Scholar (7), Literature Access (3), guarded Asta (8) initialized and listed tools; local health/status calls passed |
| OpenAlex live call | One anonymous discovery query succeeded; authenticated pagination and semantic retrieval not exercised |
| Semantic Scholar live call | Anonymous metadata lookup returned **HTTP 429** after bounded retries; mocked cache, rate-limit and validation tests passed |
| Public article recovery | Full structured article PMC6608411 recovered from public PMC HTML, with paged text and source checksum; no scientific claims were verified by this test |
| Short/unstructured content | PMC1764525 (book review) failed the structured-body gate; subsequent Europe PMC XML route timed out. Short/scan-only sources can require manual reading |
| Europe PMC recovery | Tested offline with synthetic JATS and an HTML challenge; successful live XML recovery not established in this release |
| Asta | Live schema download and one anonymous metadata call passed. Broad passage search not revalidated; timeout/cooldown/partial recovery tested offline |
| PubMed remote MCP | v2.12.0 initialization and 12-tool discovery passed; no full scientific search audit |
| Scite | Official endpoint/account requirements documented; fresh OAuth login and paid/trial entitlement not tested |
| LibKey/institution login | Instructions included; no recipient-specific subscription/MFA session verified |
| Host installation | Codex CLI 0.166.0-alpha.5.1 present during packaging; actual host skill selection and plugin-import UI not acceptance-tested |
| Other platforms/models | Intel Mac, Windows, Claude/ChatGPT plugin import and cross-model behavior untested; Linux/macOS offline CI is configured |

The GitHub workflow runs offline tests, real local transport smoke checks, release auditing and ZIP builds on macOS and Ubuntu. Provider requests are opt-in, outside CI. The test count measures implementation regressions, not literature recall, scientific accuracy, or the benefit of independent agents.

Existing personal installed skills/connectors were not replaced or reconfigured. Testing used the new source tree and temporary research/cache state. No original research notes, papers, database exports, browser sessions or private runtime history were included in the release.
