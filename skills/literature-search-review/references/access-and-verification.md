# Access, complete sources, and article files

Use the actual browser/profile and current tool schema. Observed adapter behavior below was checked on 6 October 2026; it is not a universal property of every connector.

## Initiate institutional access before discovery

Use the standalone [paper-fulltext-access](../../paper-fulltext-access/SKILL.md) skill for institutional recovery; no plugin installation or share link is required. If the folders are installed separately, resolve it by skill name. Use the supplied skill files rather than hard-coding a provider-specific cache directory. It owns resolver navigation, browser choices, login handling, download mechanics and stopping; this reference owns the search caller's handoff and evidence accounting.

At the beginning of a new subject search, before search execution, ask for institutional readiness unless a session is already verified or the supplied originals make it unnecessary. Use an asynchronous input mechanism where available so public discovery can continue. For example:

> For subscription papers, please select your institution through LibKey and complete your library sign-in in the supported interactive browser when prompted. Which institution should I use? If you have no institutional access, I can continue with public sources.

Use a known institution rather than asking again. Open the access skill's direct LibKey route for a real known paper when available. If login cannot occur until a paper redirects to its publisher, record `login pending first challenge`; do not claim pre-authentication or invent a test article. When the challenge appears, show the same tab and ask the user to complete login/MFA there. Never request passwords in chat, inspect password values or export cookies. Resume after confirmation in the same browser session. One successful paper does not verify all subscriptions or all publishers.

Readiness is optional for public work. A user without an institution, declining sign-in, or waiting on MFA can still receive useful public evidence with access limitations. An expired session can need another prompt; initial readiness cannot guarantee uninterrupted autonomy. Do not ask again for each paper when the verified session still works. Optional personal settings are preferences, not proof of readiness, entitlement or authentication.

## Efficient recovery and subskill contract

1. Reuse authorized copies and working links; inspect prior records before retrying. Without an established paywall, try an obvious complete OA source or exact full-text tool. Accept complete HTML/native text when a PDF is not requested.
2. On a known paywall, subscription preview, institutional gate, or abstract-only result from a needed full-text retrieval, call `paper-fulltext-access` immediately as the first recovery route. A paper already paywalled by the caller goes directly to LibKey if no suitable source is already available. Do not first exhaust repositories or perform a PMID lookup solely for access. The direct route is `https://libkey.io/<DOI>`; the access skill handles supported alternative identifiers. No Nomad extension is required.
3. Pass the verified identifiers/title, caller's actual full-text need, content versus requested PDF mode, relevant version constraints, prior failed routes and access state. Keep browser interaction with a single owner and reuse the verified session. This retrieval call does not restart discovery or change eligibility.
4. Require the return to identify the actual source/version, stable link or readable absolute file path, main-body/needed-content status, concrete blocker if unresolved and any preserved sign-in tab. A resolver button, redirect, abstract or PDF viewer alone is not proof of retrieved complete text or a saved file.
5. If LibKey lacks coverage/entitlement, is unready, or the skill/browser is missing, use promising legal public or library alternatives and retain the unresolved candidate. Do not buy articles or request document delivery without authorization. Scite remains a bounded fallback for a specific unmet need, not automatic duplicate discovery.

A response ceiling, technical failure or missing section from an otherwise public source is not necessarily a paywall. Recover that same source's continuation or complete public body where possible. For PMC-linked papers, an available `literature-access` `fetch_pmc_fulltext` tool, public PMC HTML or Europe PMC JATS can recover failed structured responses. See [connector-reliability.md](connector-reliability.md). Do not impose this public-recovery branch before LibKey on an already established paywall. Metadata/abstract screening alone does not trigger unnecessary full-text recovery.

After two unchanged failures of the same route in a run, switch or queue it; do not retry the same failures independently in caller and subskill. Retry changed conditions such as confirmed login, a new endpoint or a different copy. Distinguish login pending/expired, missing entitlement, resolver coverage, CAPTCHA, network, parsing/truncation and download-tooling failures. Record stable routes and outcomes without signed URLs, credentials or cookies.

## Know what the response contains

Compact metadata, abstract, outline, selected passages, citation sentences, complete body, and source files are different artifacts. A title match and many characters do not prove complete main-body access. Inspect truncation flags, page/section limits, continuation links, and deferred IDs.

- With the observed PubMed full-text connector, inspect `maxCharacters`, `maxCharactersPerSection`, `maxSections`, and `maxResponseCharacters` independently, plus `deferred.ids`. Retrieve missing sections/pages or another complete source; queue deferred IDs. Do not mark a response ceiling as article unavailability.
- With the observed Scite connector, `read_fulltext` needs an actual body identified as `source: fulltext` and pagination to the end. `get_full_text` returned a lossy citation-sentence proxy. Search excerpts and that proxy do not satisfy full-text evidence. Verify the current adapter's semantics rather than relying on the tool's name.
- A browser tool may expose visible text from only part of a page. Check full article sections and dynamic content; an abstract landing page is not complete HTML.

Save practical native source text/cache when needed for evidence and handoff. This is not a user-requested downloadable publisher article. Use durable original headings, table/figure/equation labels, real PDF pages, supplement labels, and source paths. Session-dependent response offsets alone are poor durable locators.

## Verify identity before evidential use

Compare intended and observed title, authors (including exact collective authors), venue, dates, and known DOI/PMID/PMCID. Record authoritative metadata/source and the checked fields. Differences may reflect indexing dates, versions, or co-publications; resolve them rather than silently picking the nearest title. Syntax and resolver success are clues, not identity proof. A failed resolver is not proof of a fabricated citation.

Keep distinct DOI papers/versions and their relationships. Do not merge preprint and journal article, co-publications, corrections, or shared-cohort reports solely by fuzzy title. Label source host, publication version, and file format separately. A publisher PDF hosted by PMC is still a publisher version. Check available correction/retraction notices; retracted findings cannot quietly become valid evidence. Preserve unknown relationships rather than inventing independent-study counts.

Always check identity and main-body completeness before setting full-text availability to verified. Check specific tables, figures, equations, or supplements only when eligibility or a used claim depends on them. Record a needed component's original locator and `checked`/`unresolved` state. If unresolved, block the affected claim. Do not require a matrix of every unused component for every paper.

## Downloads requested versus reading only

Without downloads: complete HTML/native text or an existing PDF is sufficient. Do not spend extra calls hunting a PDF solely for file format. For substantial agent handoffs, retain obtained native text when feasible or reference an existing authorized local original; record source reuse, actual coverage, and graphic/supplement limits using the record contract. If caching is impractical, preserve the stable original URL and explain what must be reopened and why. This reading support does not authorize extra article downloads or rich-library processing. Necessary local extraction is normal reading work; a rich reusable corpus remains optional.

With downloads: seek an acceptable complete PDF first, preferably the publisher version. Record an accepted manuscript/preprint explicitly when using it; substantive version differences may require user clarification. If a suitable PDF is unavailable, print the complete original HTML through an actually supported browser/printing action. Label the result `html_print_verified`, keep original provenance, and inspect the produced file for identity, main body, readable pagination, and needed content. If printing is unsupported or incomplete, record an unresolved download. Do not present screenshots or a PDF reconstructed from extracted text as the requested original-HTML print. Saved HTML/native text can remain useful evidence while file delivery is unresolved.

For saved files, use `source_files.py` for container type, byte count, checksum, PDF page count, and text-extraction warnings. It never promotes paper states or checks claim truth/completeness. A PDF signature alone is not readability; a first-page DOI hit is not identity. Scanned PDFs require available visual inspection/OCR. Extraction can omit table structure, symbols, figure content, and external HTML assets. Inspect needed originals. Use available PDF readers if optional `pypdf` is absent; absence of that parser does not mean the article is unavailable.

## Missing full text must remain visible

After reasonable routes, ask for copies/access help in one prioritized batch of potentially eligible papers. Include title/identifier, relevance, attempted routes, and why the gap matters. Use a file-capable mechanism for actual uploads; a text-only question tool cannot receive files. Continue independent search/extraction.

Do not exclude by access or silently synthesize abstract-only findings under the full-text default. Keep affected conclusions provisional until resolved or the human explicitly accepts the named limitations. Record acceptance and the actual source message; silence, elapsed time, and an agent's own judgment are not acceptance. An accepted inaccessible candidate can remain unresolved and visible; it is not automatically included evidence. Already read full text with a failed download is a delivery gap, not an evidence gap.

## What checks establish

Deterministic checks establish local consistency: normalized IDs, collisions/conflicts, required record fields, foreign references, file existence/container, queues, state agreement, export counts, and missing locators. Completion flags and recorded identity/body/claim verification still depend on honest source inspection. Assess entailment, scientific methods, causal/construct claims, selective reporting, disagreements, and search gaps through original-source judgment; use independent expert/librarian review where warranted. Neither script establishes exhaustive literature coverage or measured token savings.
