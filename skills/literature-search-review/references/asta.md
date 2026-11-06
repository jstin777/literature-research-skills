# Asta complementary discovery

Read when using the Asta Scientific Corpus Tool for an authorized outside-literature branch or a targeted evidence gap. This connection exposes search/lookup tools; it does not launch Asta's separate paper-finder agent or report writer.

## Place in the workflow

Keep the review question, criteria, database searches, paper register, evidence extraction, and synthesis under the existing coordinator. Use `snippet_search` to discover relevant body passages and new candidate papers when abstract searches may miss operational details, wording differs, or a draft exposes a consequential gap. For questions restricted to the local library, use local retrieval first; do not expand scope or upload local articles merely because Asta is available. Supplied-corpus mode must retain its corpus boundary.

Use a neutral subquestion and an explicit compact `limit` (for example 10–20 initially), then refine by uncovered subquestion when needed. This is a ranked starting batch, not an exhaustive query or a completion threshold. If revisiting specific candidates, `paper_ids` can restrict retrieval to known identifiers; the observed parameter is a comma-separated string. Do not treat its maximum supported list size as an instruction to bulk-query every paper.

The existing full-source access workflow obtains originals after discovery. Asta snippets remain partial material; unavailable papers stay unresolved. Verify original context, necessary tables/figures/supplements, scientific eligibility, and claim support before finalizing. Merge eligible leads into the same review register and record the additional unique yield. Asta discovery does not select papers for the working library or authorize Zotero intake.

## Actual tools and limits

Official endpoint: `https://asta-tools.allen.ai/mcp/v1` (Streamable HTTP). Local configured server name: `asta`. Inspect actual available schemas before calling. Rechecked 18 October 2026: anonymous initialization, tool discovery and metadata retrieval succeeded; both broad and paper-scoped passage searches stalled in bounded probes. The local registration now uses a guarded proxy preserving the original tool schemas, with hard deadlines, per-operation cooldowns and explicitly labeled recovery for exact PMC-linked paper scopes. See [connector-reliability.md](connector-reliability.md). Broad Asta passage retrieval remains unavailable in those probes; local lexical recovery is not equivalent corpus coverage. Access and limits may change. A higher-rate API key is optional when the public service suffices; do not save keys in review records.

- `snippet_search(query, limit, venues, paper_ids, inserted_before)` searches ranked excerpts from indexed titles, abstracts, and body text. Official documentation describes approximately 500-word excerpts excluding figure captions and bibliography. It covers the indexed corpus rather than every publication or institutional subscription.
- `get_paper`, `get_paper_batch`, title/relevance search, author lookup, and `get_citations` can resolve/enrich candidates or fill citation gaps. These use Semantic Scholar identities and substantially overlap the existing Semantic Scholar connector. Avoid duplicate lookups; repeated discovery of one paper is one work, not independent evidence.
- `inserted_before` is a corpus-insertion cutoff, not a publication-date filter. Apply unsupported eligibility filters by explicit screening, or choose a database that supports them; report how the restriction was implemented.
- Live schemas may differ from the documentation: the observed `snippet_search` default limit was 20, whereas the public page listed 250. Set the intended limit explicitly. Metadata fields/version mappings can also differ: a journal DOI lookup in the setup probe returned a 2017/preprint-linked record for a 2018 journal article. Compare actual identifiers/version/year with the original before normalization; do not overwrite known bibliographic identity from a fuzzy/merged provider record.

## Record and normalize

Before execution, record tool/endpoint, exact arguments, UTC date, branch purpose, restrictions, ordering, and requested cap. Preserve response warnings, actual IDs, and compact raw results. Use `not_exposed` for missing totals, query translations, replay URLs, pagination, or hidden ranking behavior; do not invent them or claim a top-k list exhausts the corpus. Count snippets and unique papers separately. Log timeouts/rate limits/partial results, disclose their effect, and use the existing database/access alternatives when needed.

Unwrap the actual tool response into paper records. Resolve the returned Semantic Scholar/CorpusId/DOI identifiers against existing aliases, enriching with authoritative metadata when necessary; preserve conflicting versions for identity review. Keep every returned passage linked to its paper, original article URL, returned source location when exposed, query, and raw response. API response offsets and generated relevance explanations are not original article locators. Reopen the original to establish durable section/page/figure locations.

Do not set `identity_verification.status: verified` from a search hit alone. Snippets alone mean at most `full_text_status: partial`; retain an already verified original state rather than downgrading it. Keep `evidence_status: not_extracted` until extraction, or `extracted_unverified` for provisional evidence rows. Snippets do not establish `main_body_complete`, `verified_for_question`, complete-abstract access, download delivery, or an exclusion. Vendor relevance scores/summaries are navigation aids, not scientific quality or claim verification.

## Sources

- [Official tools and parameters](https://allenai.org/asta/resources/mcp)
- [Asta corpus scope](https://allenai.org/asta/resources)
- [Separate Asta paper-finder agent workflow](https://github.com/allenai/asta-plugins/blob/main/plugins/asta-tools/skills/find-literature/SKILL.md)
