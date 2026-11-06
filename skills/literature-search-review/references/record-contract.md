# Records, helpers, and writer handoff

Read this when initializing/resuming a run, populating records, exporting views, or handing the corpus to another writer. Helpers run locally, without network access or scientific decisions. Use one authoritative register and one writer at a time. Equivalent manual records are acceptable when Python/helpers are unavailable; report checks not performed.

## Layout and initialization

Choose an authorized artifact root appropriate to the environment. Save only outputs needed for the task; do not put the detailed search trail inside the review. Resolve actual paths before linking files or handing them to another agent.

| Path under the run root | Purpose |
| --- | --- |
| `search-records/protocol.md` | Question/subquestions, operational distinctions, eligibility, mode, evidence policy, sources/branches, seed policy, dates, limits, assumptions, deliverables, and amendments. |
| `search-records/papers.jsonl` | Authoritative paper-level register, independent states, identity/access proof, exclusions, source locations, relationships, and unresolved reasons. |
| `search-records/search-log.jsonl` | Exact query, seed, citation, corpus, and amendment events with scope/accounting. |
| `search-records/access-log.jsonl` | Per-paper routes, outcomes, verification, failure classes, and human interventions; no secrets. |
| `search-records/checkpoint.json` | Phase, queued work, processed branches/seeds, pending human inputs, accepted limitations, and next actions. |
| `working/evidence.jsonl` | Compact question-relevant evidence, original-source locators, and verification flags. |
| `working/source-text/`, `working/raw-results/` | Reusable native source text/compact results. For substantial handoffs retain obtained text when feasible or reference existing local originals; document remote-only/missing sources. Not a rich library. |
| `working/handoff.md` | Substantial agent handoff: actual root, requested deliverable/writer, protocol, complete index/evidence/source paths, coverage, pending limits, and next actions. |
| `review/` | Requested prose and useful source/evidence/index views; brief human methods links to separate records. |
| `downloads/` | Requested article files only; exported manifest can live in `review/`. |
| `library/` | Optional justified Markdown notes, summaries, embeddings, or graphs. No Obsidian requirement. |

Use the helper's actual absolute path, replacing `<skill>` and `<run>` below; these are placeholders, not literal directories. Standard Python 3.9+ is sufficient for `catalogue.py` and HTML/text checks. PDF parsing optionally uses `pypdf`; use another available reader if absent. No helper installs dependencies automatically.

```bash
python3 <skill>/scripts/catalogue.py init --root <run> --question "The neutral research question"
```

Defaults: targeted mode, full-text evidence, downloads off. Add `--downloads` only when requested. Modes: `targeted`, `scoping`, `systematic`, `supplied_corpus`, `design`, `update`; policy: `full_text` or explicitly authorized `abstract_only`. Initialization refuses existing records. For an update/resume load the existing checkpoint, do not initialize over it. Finish the protocol before scientific screening and set `protocol_ready: true`; this is an agent planning attestation, not human approval.

## Paper records and states

Input files may be a JSON object, array of objects, or JSONL. Use real values from retrieval, never copy illustrative proof fields as if verified. A minimal discovery record is:

```json
{
  "paper_id": "P0001",
  "title": "Title returned by the source",
  "identifiers": {"doi": "10.1234/example"},
  "discovery_routes": [{"event_id": "S-example", "source": "Actual database"}]
}
```

The example DOI is a syntax example, not a real citation. Optional `paper_id` is assigned when missing; retain that stable ID. The helper merges only matching exact normalized DOI/PMID/PMCID/OpenAlex IDs or an explicit existing internal ID/alias. It preserves discovery routes and proposed aliases. Conflicting titles/IDs or identifiers bridging two records stop the entire update without writing partial records. Resolve identity manually; do not force a false merge. Near-duplicate titles with different DOIs remain separate. Relationships use `related_papers` entries with ID, relation, and basis; `study_id` is assigned only when a shared study is established.

Bibliographic fields: `title`, structured `authors`, `year`, `venue`, `publication_type`, `volume`, `issue`, `start_page`, `end_page`, `article_url`, `identifiers`. Preserve individual names as `{"family":"Rethlefsen","given":"Melissa L."}`; collective authors as `{"collective":"PRISMA-S Group"}`; unresolved parsing as `{"literal":"Exact displayed name"}`. Do not concatenate collective and individual fields. RIS exports repeat `AU` entries and retain Unicode.

| Field | Allowed values; initial default is first |
| --- | --- |
| `eligibility_status` | `unscreened`, `potentially_eligible`, `included`, `excluded`, `unresolved` |
| `abstract_status` | `not_fetched`, `complete`, `missing`, `partial` |
| `full_text_status` | `not_attempted`, `verified`, `partial`, `unavailable`, `waiting_user` |
| `evidence_status` | `not_extracted`, `extracted_unverified`, `verified_for_question`, `needs_followup`, `abstract_only` |
| `download_status` | `not_requested`, `pending`, `pdf_verified`, `html_print_verified`, `unresolved` |

Normalize connector responses into this contract before helper import; tool envelopes and vendor status labels are not paper records. For the local OpenAlex response/state mapping, read [openalex-local.md](openalex-local.md); for Asta paper/snippet results, read [asta.md](asta.md). Preserve native status and warnings as provenance; normalization does not establish full-text access or evidence verification.

`included` is a scientific eligibility judgment, not automatic evidence readiness. `substantively_cited: true` also requires source/evidence accounting, even for background papers outside primary-study inclusion. Set `review_role` (subquestion/background/counterevidence/etc.) and later `review_treatment` (synthesized, discussed separately, grouped with established related report, handed off for a search-only task, or omission with reason). Every included ID must receive a treatment; citation frequency is not treatment quality.

- `identity_verification`: `status: verified` requires observed `title`, authoritative `source`, `checked_at`, and observed `identifiers` when identifiers are known. Compare stored and observed values; preserve unresolved conflicts. The helper checks agreement, not whether the source was actually consulted.
- `exclusion`: excluded records need `criterion`, `stage` (`metadata`/`abstract`/`full_text`), and `basis` referencing the source information supporting the decision. Missing abstracts/access do not satisfy an exclusion criterion by themselves.
- `source_locations`: array of objects containing source URL/path, host, publication version, format, retrieval time, and warnings. Keep path and stable article URL, not expiring session credentials. Main-body reading does not verify every figure.
- `source_reuse`: for a substantial handoff, an object with `status: local`, `remote_only`, or `unavailable`, plus `coverage` and `limitations` (use `none observed` where appropriate). `local` points to readable, nonempty `source_locations[].path` files, absolute or relative to the run. Optional `paths` selects the currently reusable paths from that register; otherwise all recorded paths are checked. This allows preservation of obsolete historical locations without declaring them currently usable. Reuse an existing authorized original rather than copying it just for the handoff. `remote_only` needs a stable original `source_locations[].url` and a `reason` why a reusable local source was not retained; `unavailable` also needs a `reason`. Describe main-body coverage and relevant graphics/supplement gaps. Reopening limits do not change full-text/evidence/download states or constitute human acceptance of access limits.
- `full_text_verification`: `source`, `checked_at`, `main_body_complete: true` required for verified full text. Set only after actual inspection of article/sections/truncation. Add needed completeness warnings and observed limits.
- `download_verification`: for a verified PDF or HTML-print PDF, require `path`, `source_url`, `version`, `checked_at`, `identity_checked: true`, and `readability_checked: true`; add checksum/page count and warnings from inspection. Paths may be absolute or relative to the run. The catalogue checks file existence/nonemptiness/PDF signature; this does not prove readability or completeness.
- `unresolved_reason`, `warnings`, and checkpoint queues preserve unfinished work rather than hiding it in prose.

```bash
python3 <skill>/scripts/catalogue.py upsert --root <run> --input <paper-input.json>
```

## Search/access events

Before submission, persist exact parameters in a pending event or checkpoint. `record` appends search/access events and adds timestamp/event ID when omitted. To close an existing attempt, append a complete record with the same `event_id`; do not edit history. The latest event for each ID determines ready-state accounting. Each appended version must contain its full required fields, not only a status patch. Keep event IDs distinct across different attempts.

For query/citation events, required helper fields are `event_type`, `purpose`, `source`, `submitted_request` (nonempty object), and `retrieved_paper_ids` (including an empty array before retrieval); timestamps are added automatically. Citation events additionally require `direction` (`backward`, `forward`, or explicitly `similarity`) and `seed_paper_ids`. Other event types: `seed_selection`, `corpus`, `amendment`. `status`: `pending`, `complete`, `limited`, or `failed`; the last two unresolved states require resolution or a documented limited completion. `limited` requires `limitations`.

Also record these operational fields, even though the helper cannot establish their truth:

```json
{
  "event_id": "S-example",
  "event_type": "query",
  "purpose": "Independent branch for a specified subquestion",
  "source": "Actual platform/interface",
  "provider": "Underlying provider or not_exposed",
  "submitted_request": {"tool": "Actual tool", "parameters": {"query": "Exact submitted query"}},
  "effective_query": "not_exposed",
  "canonical_query": "not_exposed",
  "native_translation": "not_exposed",
  "replay_url": "not_exposed",
  "filters": {},
  "default_filters": "not_exposed",
  "ordering": "not_exposed",
  "requested_cap": null,
  "pages_processed": [],
  "reported_total": null,
  "retrieved_paper_ids": [],
  "raw_results_path": null,
  "status": "pending"
}
```

Replace unknowns only with returned/observed information. Preserve raw compact records when practical. Map every retrieved result to a paper/alias or a documented invalid-record disposition; reported match counts, raw records, unique papers, screened papers, included papers, and established studies are different counts. Upsert before referencing assigned paper IDs in finalized events. Seed-selection events include seed IDs, reasons, represented branches, provisional/confirmed status, and planned directions. Corpus events inventory supplied records; amendments preserve what changed and why.

Access events contain `paper_id`, route/entry URL, browser/profile when relevant, outcome, failure class, source/version, verification, and authentication intervention without credentials. These outcomes are not query-completion statuses; a recorded failed access attempt does not by itself block an otherwise resolved review.

```bash
python3 <skill>/scripts/catalogue.py record --root <run> --kind search --input <event-input.json>
python3 <skill>/scripts/catalogue.py record --root <run> --kind access --input <access-input.json>
```

## Evidence and original-source retrieval

Every included/substantively cited paper needs compact rows by claim/subquestion for its role. Required extraction fields are `paper_id`, `subquestion`, `design`, `sample`, operational `measure`, author `finding`, `uncertainty`, consequential `limitations`/counterevidence, separate reviewer `inference`, `supporting_context`, and `locators`.

- `sample` identifies the population/species and independent sampling unit; distinguish participants/animals from sessions, trials, or recorded units when relevant.
- `finding` retains the question-relevant comparison and consequential numbers, units, or effect direction. `uncertainty` retains reported precision/statistical support and limits without inventing it.
- `supporting_context` is a short string: a clearly labelled exact excerpt or faithful table/figure/equation description/transcription, including enough context to interpret the finding. It accompanies the original locators; it is not an independent scientific source or a substitute for needed Methods/figure checks.
- `locators` is a nonempty array of objects with original `source` and `location` strings (real page/section/table/figure/supplement label). Add a practical saved-text anchor when available. Do not cite only a generated summary or invent page numbers. Search the original and inspect surrounding context.

Populate every field with relevant information or an explicit reason such as `not reported: no interval provided` or `not applicable: theoretical paper without an empirical sample`. Keep `not yet checked` distinct from absence in the source; a consequential unchecked detail makes the row `needs_followup`. Reviewer inference may say `none: descriptive extraction only`, especially for an independent evidence map. Do not pad rows with generic limitations or invent sample sizes/conclusions. Readiness checks enforce field presence and locator structure, not adequacy or truth.

`verification_status`: `unverified`, `verified`, `abstract_only`, `needs_followup`. Verified/abstract-only rows require a finding and source locators. Use `required_components` only for needed items: objects with `component`, original `locator`, and `status: checked` or `unresolved`. A verified row cannot retain a required unresolved component. Main article availability and evidence verification are independent.

```bash
python3 <skill>/scripts/catalogue.py record --root <run> --kind evidence --input <evidence-input.json>
```

Evidence gets a stable `E0001`-style ID when omitted. Reusing its `evidence_id` updates that row; preserve earlier material in a revision field/cache when needed. Do not leave obsolete unresolved rows alongside verified replacements unintentionally. The helper checks references and flags, not nuanced entailment.

`source_files.py` leaves the source untouched and prints compact JSON. An optional extraction output saves actual native text; it is not a publication PDF or a fully faithful Markdown conversion:

```bash
python3 <skill>/scripts/source_files.py <actual-file.pdf> --expect pdf --report-out <inspection.json>
python3 <skill>/scripts/source_files.py <actual-file.pdf> --expect pdf --text-out <working-source.txt>
```

PDF text extraction with `--text-out` covers all pages and labels real page numbers; inspection alone samples first/middle/last pages. Exit codes: 0 mechanical pass, 1 failure, 2 unresolved (such as missing PDF parser or little extractable text). Both modes explicitly leave article identity, completeness, and claim verification false. Use `--doi`/`--title` only as diagnostic cues. HTML logins masquerading as PDFs fail type checks; original figures/tables still require inspection.

## Completion, export, and handoff

Checkpoint initial flags are false. Set `search_plan_accounted`, `gap_audit_done`, and `limitations_reported` true only when actually satisfied; keep `pending_papers`, `pending_queries`, `deferred_fetches`, human-input status, and next actions current. Resolve queues or explicitly account for scope limits, without deleting unfinished work from the record. A paper with human-accepted access limits may remain unresolved in the register while being removed from the pending-action queue with the decision preserved.

Explicit human acceptance uses an entry in `accepted_access_limitations` or `accepted_download_limitations` with `paper_id`, `reason`, `accepted_by: user`, and `source_message` identifying/quoting the actual human response. Acceptance allows named limitations to remain visible; it does not verify a claim, force inclusion, or authorize abstract-only inference beyond the accepted scope. Never fabricate acceptance or derive it from silence.

```bash
python3 <skill>/scripts/catalogue.py validate --root <run>
python3 <skill>/scripts/catalogue.py validate --root <run> --ready
python3 <skill>/scripts/catalogue.py validate --root <run> --handoff
python3 <skill>/scripts/catalogue.py summary --root <run>
python3 <skill>/scripts/catalogue.py export --root <run> --formats sources index evidence
```

Basic validation checks local consistency; `--ready` additionally checks completion attestations, latest search-event states, queues, candidate dispositions, identity/full-text/evidence, populated extraction fields, structured original locators, and requested downloads. `--handoff` implies `--ready` and also checks the handoff document and each used paper's source-reuse fields/local file readability. Remote-only or unavailable sources produce explicit warnings; the helper does not contact them or establish the recipient's authentication. Neither mode validates search sufficiency, scientific interpretation, or whether a locator supports a claim. Exports can be provisional and do not imply ready status. Default exports are source table and included index; request `--formats sources index evidence` for a substantial handoff. `--formats ... ris` adds verified bibliographic records for included/substantively cited papers, and `downloads` adds their delivery manifest. RIS links stable article URLs and does not bundle attachments. Do not export fabricated bibliography entries to satisfy the guard.

### Handoff contents and recipient checks

For an ordinary request, a separate fresh-context writer drafts from the compact handoff. Follow [writer-handoff.md](writer-handoff.md) for the role boundary and user-goal brief. A small discovery-only candidate list may use equivalent compact manual records with explicit abstract/access labels; it is not a verified full-text evidence handoff and must not be presented as passing `--handoff`. Before writing/handoff, generate/read the entire compact included index and evidence register in batches. Track every included ID's treatment, including inconvenient/null/conflicting findings. Retrieve originals by ID/subquestion, not merely semantic top hits.

For a substantial agent handoff, write `working/handoff.md` with:

1. Actual absolute artifact root, the substantive user request and corrections, purpose and desired final outcome, deliverable, constraints, assumptions, evidence mode, and writer ownership: fresh ordinary writer, existing receiving writer, or descriptive map for explicitly requested multi-agent stage 1. Let the user request determine the prose structure; include the required routing-status notice for an ordinary answer.
2. Protocol/checkpoint and authoritative register paths, full included index, evidence rows/exports, original source paths/URLs, and source-reuse coverage/limits.
3. Completed branches and seed passes, known disagreements and undercovered branches, candidate dispositions, pending work, and any human-accepted limitations with their recorded basis.
4. Specific next actions by paper/evidence ID and subquestion, including tables/figures/supplements that need checking. Separate repeated verification of an existing claim from extraction of a new detail or discovery of a new paper.
5. Actual readiness-check result and outstanding errors/warnings; label incomplete packages provisional.

Verify the receiving agent can read the root, index, evidence, and required original sources before depending on them. A file check in the collecting context cannot establish access in another context. A fresh recipient starts with the user-goal brief, whole compact index, relevant evidence and material limits, without inherited retrieval history; it then then selectively reads originals for important claims, context, new details, or independent auditing. Reuse available source files and prior routes before reacquiring a paper. A passed handoff check is structural readiness with disclosed limits, not a guarantee that no further source reading is needed.

**Compatibility:** existing records remain readable and exportable under basic validation. Stricter `--ready` checks require the additional extraction fields; `--handoff` requires source reuse and the handoff document. On resume, fill missing fields from actual original-source inspection, or keep the package provisional. Do not bulk rewrite historical records, guess missing values, or retroactively mark them ready.

Deliver brief human methods plus links to separate exact records, requested prose/tables, stable verified article links, local download links and manifest when requested, and unresolved limits. Citation graphs, standalone summaries, rich notes, embeddings, and reference-manager exports are conditional. For substantial unrequested library processing ask once with its purpose/cost; no paper-count cutoff or assumed token savings. An optional comparison uses the same papers/questions with fresh writers, with and without rich notes, counting creation and reuse; it is not a prerequisite to ordinary searches.
