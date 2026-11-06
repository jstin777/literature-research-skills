# Connector reliability and honest recovery

Read when a literature tool stalls, is rate-limited, or cannot return the article body. Use current tool descriptions and actual result flags. Do not run a full connector benchmark before ordinary searches.

## Executable recovery versus research judgment

Keep network deadlines, bounded retries, source caching and endpoint-specific cooldowns in MCP code. The coordinating skill still decides search scope, alternative databases, source identity, evidence verification and how to report coverage. A healthy metadata lookup does not prove passage search or full-text retrieval works.

When independent requests run together, expose each completed result promptly. Do not hold all useful results behind a slow optional branch. A JavaScript Promise timeout may return while an underlying MCP call remains pending; prefer the connector's actual transport/process deadline. If the guarded connector is unavailable, make a bounded attempt and continue through an available alternative rather than repeating the same unresolved call.

## Optional recovery MCP

When available, the `literature-access` server may expose these capabilities; inspect the actual tools rather than assuming a local registration:

- `fetch_pmc_fulltext`: content retrieval by exact PMCID, PMID, DOI or canonical article URL. Public PMC HTML is sufficient for reading when structured routes fail; if HTML returns a browser challenge, the connector also tries Europe PMC JATS XML. Verified cached native sources remain reusable when a route becomes unavailable. DOI/PMID resolution uses Europe PMC; this tool does not cover every article or deliver a PDF.
- `search_article_passages`: lexical paragraph retrieval within **one exact retrieved PMC article**, with original section links, immutable-source path and checksum. This is a paper-specific reading aid, not broad semantic discovery.
- `connector_health`: saved capability-specific status; it does not make fresh requests. `not_tested` is not proof of health.

Use these tools when present. If absent, use available public article/Europe PMC routes and report the missing capability. Do not assume another user has a particular local connector directory or install it automatically. Do not assume a server newly registered in configuration is already available in the current chat. A fresh MCP transport test establishes local startup and functionality; it does not establish that the current chat has refreshed its tool inventory.

Follow `response_truncated` and `next_start_char` until all needed material is read. Source detection, identifiers, saved HTML and checksums are mechanical provenance checks. `main_body_completeness: requires_source_inspection` and `scientific_claims_verified: false` must remain unverified until actual inspection. Equation-image placeholders require looking at the original linked image; text extraction is not visual verification. Preserve the immutable HTML/XML and original section/figure/table locations.

## Guarded Asta

The local `asta` registration preserves Asta's original tool names and input schemas, forwarding them through a bounded worker. Its normal successful results are upstream results. Successful responses are cached; a passage timeout opens a cooldown for passage search only, leaving metadata tools usable. The default passage deadline is 12 seconds and the timeout cooldown is 15 minutes. These are local implementation settings, not claims about normal Asta latency or corpus availability.

If `snippet_search` fails and exact `paper_ids` were supplied, the wrapper can retrieve lexical paragraphs from up to three of the requested PMC-linked articles within a separate bounded recovery window. Inspect:

- `status: partial_recovery`, `actual_method`, `actual_scope` and `upstream_failure`;
- `recovered_articles`, `unresolved_paper_ids`, `deferred_paper_ids` and original passage URLs;
- whether a passage actually supports the claim in its original article context.

Do not describe that recovery as successful Asta semantic search. A broad query without paper IDs gets a real timeout/cooldown error; use PubMed/Europe PMC/OpenAlex or another available discovery route and disclose the missing Asta branch. A scoped lexical miss is not evidence that no relevant passage or paper exists.

An Asta tool key is optional local configuration and may improve limits according to Ai2's documentation. Neither working anonymous metadata nor a passage timeout proves that a missing key is the cause. Never invent a key, expose credentials, or submit a key-request form without authorization.

## Known distinctions from the October 2026 diagnosis

PubMed search, PubMed structured full-text recovery, the separately configured PubMed MCP, and public PMC article pages are different routes. A full-text chain can fail with no-body/500/403 while a public PMC body remains readable. A failed or truncated public route can use the verified public-article route before declaring it inaccessible. For an actual known paywall, invoke the separate access skill first; these recovery notes do not override that route. Semantic Scholar's anonymous pool can return 429 and then recover through its existing retry; preserve pacing and avoid parallel retry bursts.

These wrapper observations describe an optional originating installation, not bundled services or recipient defaults. Do not infer that a tool is currently healthy solely from a historical successful test.
