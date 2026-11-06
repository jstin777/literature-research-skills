# Third-party notices

MIT covers this repository’s original skills, helpers, local connector wrappers, tests and documentation. It does not cover third-party packages, hosted services, retrieved article content or provider data. No third-party package binaries, article corpus, API credentials or browser sessions are bundled.

| Direct dependency | Version | License / upstream |
| --- | --- | --- |
| MCP Python SDK (`mcp`) | 1.30.0 | MIT; https://github.com/modelcontextprotocol/python-sdk |
| HTTPX | 0.28.1 | BSD-3-Clause; https://github.com/encode/httpx |
| Beautiful Soup | 4.14.3 | MIT; https://www.crummy.com/software/BeautifulSoup/ |
| pypdf (optional) | 7.0.0 | BSD-3-Clause; https://github.com/py-pdf/pypdf |
| PyYAML (development) | 6.0.3 | MIT; https://github.com/yaml/pyyaml |

Transitive packages are pinned in `requirements/connectors.lock.txt`; [dependency-licenses.json](dependency-licenses.json) records distribution metadata for the tested stack. Each downloaded distribution supplies its own license. Consult the upstream package when metadata is incomplete; these notices do not relicense it.

OpenAlex, Semantic Scholar, Ai2 Asta, NCBI/PubMed/PMC, Europe PMC, LibKey and Scite retain their names, services, data rights and applicable terms. The PubMed MCP endpoint is a third-party deployment from [cyanheads/pubmed-mcp-server](https://github.com/cyanheads/pubmed-mcp-server); its source is linked, not copied. Asta schemas are fetched at recipient setup and excluded from publication. Returned papers, figures and full-text sources retain their original rights and must not be redistributed merely because a connector can retrieve them.

Plugin/schema formats and service references establish interoperability, not endorsement. Users obtain their own keys, accounts, institutional entitlements and paid access. The license does not confer those rights.
