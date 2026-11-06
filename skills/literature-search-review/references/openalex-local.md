# Local OpenAlex interface

Read when callable `openalex-local` tools are used for discovery, citation tracing, or abstract retrieval. This adapter was inspected on 7 October 2026; verify current schemas and returned fields. It is optional and does not supply article full text.

## Search scope

`search_works` defaults to `search_in="title_and_abstract"`. For broad cross-field discovery, normally specify `search_in="title_abstract_keywords"`; retain narrower title/abstract scope when required by the protocol or useful for a focused branch. Record the exact scope. Keyword/Boolean search and `semantic_search` are different requests. Keyword results have no semantic reranking. A `fulltext` search scope does not obtain readable full articles or verify claims.

Check applied filters: local defaults exclude retracted records. Include them when the question requires notices, historical claims, or retraction analysis, and preserve their status. Avoid access/popularity filters as eligibility shortcuts. Citation lists default to descending citation count; process the declared pass rather than screening only the most cited records.

## Bounded retrieval and abstracts

Start larger discovery/citation passes with `abstract_mode="none"` and a bounded `limit` appropriate to the plan. An API page holds at most 100 records; a keyword/citation call can collect up to 1,000. These are ceilings, not recommended batch sizes or recall guarantees. Increase limits when the planned pass needs more records, while retaining response-size and unprocessed-frontier accounting.

Use `get_works(work_ids=[...], abstract_mode="full")` for selected potentially relevant or uncertain records in batches of at most 100 IDs. Full mode returns the complete available indexed abstract. If a small pass benefits from reading every abstract, request full mode directly. `short` is optional preview/triage: truncated or missing abstracts cannot justify negative eligibility decisions on their own. Missing indexed abstracts may require another abstract source or article access.

`semantic_search` has a provider candidate ceiling of 50 and no ordinary continuation pagination. Larger keyword/citation limits do not expand that semantic set. Cover missing conceptual branches with distinct neutral queries or complementary discovery routes and record the cap.

## Normalize records before helper import

Unwrap `get_work.work`, successful `get_works.items[].work`, or list/search `results[]`; map bibliographic fields and exact identifiers to the paper contract. Preserve unresolved batch IDs and errors for follow-up; do not silently discard them. A singleton lookup can resolve a merged/alias ID when a batch cannot. Never pass the raw tool envelope directly to `catalogue.py upsert`.

| Native `abstract_status` | Register `abstract_status` |
| --- | --- |
| `complete` | `complete` |
| `missing` | `missing` |
| `truncated` | `partial` |
| `malformed` | `partial` |
| `not_requested` | `not_fetched` |

Keep native status, reconstruction/truncation warnings, and actual text when usable. `malformed` can have no usable text; preserve the unresolved reason and fetch another source. These mappings change abstract accounting only. Keep full-text, evidence, and download states at their existing values until separately inspected or verified. Unknown native states remain unresolved rather than being guessed complete.

## Pagination and reference coverage

Inspect `pagination.result_set_complete`, errors, and `next_cursor`. Resume with the same query, filters, search scope, sorting, and abstract mode, changing the cursor; log each request and aggregate/deduplicate actual returned IDs. Preserve caps, pending pages, deferred IDs, and errors. Exhaustion completes only the submitted query's result set.

Map `list_citations(direction="citing")` to a forward event and `direction="references"` to backward. For backward passes also inspect `reference_coverage.comparison_performed`, `all_seed_reference_ids_returned`, and `not_returned_reference_ids`. A false value flags a gap even when the query is exhausted; a null/unperformed comparison leaves coverage unknown. The current connector marks `result_set_complete` true only for an exhausted call starting at `cursor="*"`; resumed calls can reach `exhausted=true` while retaining an unperformed reference comparison. Account for the complete continuation chain and aggregate returned IDs separately. To resolve reference coverage, compare that aggregate with an available seed-ID inventory/source bibliography, or rerun from the initial cursor with a sufficient bounded limit when practical. Do not invent a successful coverage flag from a terminal cursor.

Preserve omitted IDs and the reported versus resolved reference counts. Filters, stale IDs, merges, and absent records can produce omissions; do not label every omitted ID an unavailable article. Check consequential gaps against the source paper's bibliography and, when warranted, another index. Mark the pass `limited` with a reason while gaps remain; a recovered gap needs its route and resolution logged. Even all stored seed IDs returned does not prove a complete source-paper bibliography.

## Reproducibility

Record source interface `openalex-local`, provider `OpenAlex`, exact submitted arguments, returned effective API parameters, request provenance, retrieval/cache times, counts, cursor/pages, actual IDs, and limitations. Preserve exposed provider translations only as returned; use `not_exposed` for absent fields. API-result exhaustion, abstract completeness, full-text access, and scientific evidence remain separate judgments.
