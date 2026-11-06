# Search decisions and reproducibility

Read the sections relevant to framing, query construction, citation expansion, or formal reporting. Provider behavior below was checked on 6 October 2026; inspect the actual current tool schema and responses before relying on an adapter feature.

## 1. Declare the task before optimizing retrieval

Default: a documented targeted search, scaled to the user’s requested output, using full-text evidence for substantive scientific conclusions. A short request for useful papers can use identity-checked metadata/abstracts for provisional relevance without making unverified full-text claims. “All relevant papers” is an objective; there is no reliable completeness certificate from an AI, overlap count, citation graph, or stopped search.

| Mode | Search and completion implications |
| --- | --- |
| Targeted review | Deliberate database/discovery branches, selected diverse seeds, gap-led additions, disclosed practical limits. Do not call it systematic. |
| Scoping review/evidence map | Broad concepts and designs; define charting fields. Formal scoping work needs an appropriate protocol and reporting methods, not merely a larger targeted search. |
| Systematic review | Protocol-defined sources, eligibility, reproducible strategies, screening/extraction arrangements, disagreement resolution, and appropriate bias appraisal. Document AI-only decisions and departures. Database choice depends on the question; PubMed plus OpenAlex is not universally sufficient. Seek specialist/librarian strategy review where appropriate. |
| Supplied corpus only | Inventory and assess supplied sources. Do not discover/add papers without authorization. Record gaps as unanswered or request a scope change. Log a corpus-accounting event rather than inventing a search. |
| Experimental-design review | Search operational definitions, competing mechanisms, measurement validity, discriminating manipulations, and failure cases as well as findings. |
| Update | Resume the original protocol/register. Include newly published AND newly indexed older records where relevant; a publication-date cutoff alone can miss indexing changes. Retain old events and log the update. |

Define the question as neutral subquestions, not a preferred answer. Identify population/system, phenomenon/intervention/exposure, comparison, operational measures, and relevant designs. Use PICO/PECO or another framework only when it fits. Distinguish similarly named constructs with different measures. State inclusion/exclusion criteria, date/language restrictions and rationale, treatment of preprints/reviews/retractions, evidence policy, downloads, sources, limits, and outputs in the protocol. Ask only about ambiguities that change these choices; otherwise proceed with explicit assumptions.

## 2. Build complementary branches

1. Create a concept table: each essential facet, synonyms/acronyms, controlled terms, competing names, and distinctions that must survive synthesis. Known papers can suggest terminology but cannot define the entire search.
2. Construct a broad independent branch: OR within a facet, AND between essential facets. Add native controlled vocabulary and title/abstract terms where supported. Avoid requiring every outcome, mechanism, method, or comparator; relevant papers may not name them in their abstracts.
3. Translate to each chosen platform's real syntax. PubMed queries, OpenAlex text/filter/OQL queries, and semantic requests are different requests. Verify controlled headings and field tags rather than guessing.
4. Inspect compact hits for concept coverage and implausible absences. Thin results: check spelling, mapping, restrictive filters/facets, old terminology, and indexing delay. Excessive noise: add a scientifically relevant discriminating facet rather than an access/popularity filter.
5. Add branches for underrepresented populations, methods, alternative explanations, negative/null findings, and terminology revealed by relevant sources. Avoid a required “negative” keyword: opposing findings may not be labeled that way.

For broad biomedical work, use PubMed plus one complementary discovery route where available. Across other disciplines select a suitable subject database; consider domain repositories, conference literature, books, registries, theses, or gray literature when the question requires them. A library catalog/resolver helps holdings and access; it is not a substitute for every subject database.

Use OpenAlex first for complementary cross-field discovery/citation lookup when its available interface supports the need. Semantic Scholar can substitute or fill an identified gap. Do not query both automatically. Asta can add a separate body-passage discovery branch for method-specific questions, unfamiliar wording, conspicuous omissions, or drafting gaps; follow [asta.md](asta.md). Its metadata/citation tools overlap Semantic Scholar and should substitute for an overlapping call rather than automatically duplicate it. Verify capabilities rather than assuming a plugin exposes every API feature.

Semantic search helps when wording varies, Boolean hits are thin, or a plausible conceptual branch is missing. Submit neutral natural-language questions plus distinct branches for competing concepts. Inspect candidates with the same eligibility criteria. Ranked caps and reranking influence what is seen. OpenAlex's documented semantic search uses titles/abstracts, has a capped result set, and does not search an obtained local full-text library. Log the actual limit. A local summary search serves retrieval within a known collection; it cannot discover absent papers and can hide details omitted from summaries. [OpenAlex semantic-search documentation](https://help.openalex.org/api/semantic-search/)

## 3. Select seeds and expand deliberately

After initial independent searches, choose identity-checked papers plausibly relevant from their abstracts or metadata. Read full text later for eligibility/evidence. Seed status is provisional until confirmed; discovering from an unread seed does not make its claims usable.

For targeted reviews, choose a small initial set representing uncovered subquestions, operational measures, methods/populations, groups, periods, and competing findings. Three to six primary papers plus a useful overview is a workload starting point, not a validated optimum, cap, or completion test. Avoid only user-supplied, supportive, famous, freely accessible, recent, or same-study seeds. Choose by branch coverage; use an additional seed when it offers a missing branch or lineage rather than another instance of an already covered one.

Record seed ID, reason, branch, discovery route, status, and planned backward/forward directions. Follow both directions using one primary index initially; retain provider and pagination. Check obtained reference lists for foundational methods and consequential missing edges. A citation edge is not endorsement, replication, or eligibility; similarity is not a citation edge. Missing index references are known limitations. [OpenAlex citation documentation](https://help.openalex.org/data/works/citations/)

Use a second index when a seed or known relationship is absent, errors persist, a branch is conspicuously empty, a central unresolved question warrants broader coverage, or the protocol requires it. Log why and the additional yield. A connector may internally use the same provider as another interface; record that provider if exposed. ResearchRabbit/Connected Papers can help visualize lineages or find similar candidates but are optional and may overlap existing searches. A graph picture is not evidence that coverage is complete.

For systematic citation searching, generally use all included records from the primary search as seeds and consider two indexes where available, with departures justified. Do not apply the targeted seed sampling shortcut while claiming this coverage. [TARCiS recommendations 4 and 6](https://www.bmj.com/content/385/bmj-2023-078384)

## 4. Record what actually ran

Preserve the exact submitted tool name/HTTP endpoint/browser input and parameters before execution; append returned details and status afterward. Record platform, underlying provider, UTC date, purpose/branch, applied and default filters, ordering/reranking, requested caps, processed pages/cursors, reported total, actual IDs, raw compact-result path, and limitation. Preserve failures and refinements, not just the final successful query. Sanitize credentials/signed tokens; record a reproducible request without secrets.

Keep separate fields for submitted request, returned effective query, canonical query, provider-native translation, and replay URL. Use `not_exposed` when hidden. A connector's effective query is not automatically the database's internal translation. Exact submitted parameters remain useful even when the internal search cannot be perfectly replayed. Native interfaces/indexes change over time; reproducibility is a documented method and snapshot, not guaranteed identical future hits.

Adapter observations to verify at use:

- The available PubMed connector exposed `query`, `effectiveQuery`, `appliedFilters`, and `searchUrl`. These did not expose NLM automatic term mapping in the probes. Consult PubMed Search Details when mapping matters or formal reporting requires it. [PubMed Help](https://pubmed.ncbi.nlm.nih.gov/help/)
- The local OpenAlex MCP exposes submitted API parameters, pagination, and request provenance; follow [openalex-local.md](openalex-local.md) when using it. Inspect default retraction exclusion and other defaults; disable scope conflicts where possible or disclose them.
- Semantic Scholar API requests can preserve endpoint, query, fields, filters, and pagination; a particular connector may expose less. Log the actual interface. [Semantic Scholar API](https://api.semanticscholar.org/api-docs)

Do not screen only top hits and label all matches screened. Paginate within the declared plan, or record remaining pages/frontier and why. A cap, unknown total, inaccessible full text, and excluded paper are different conditions.

## 5. Stop, audit, and reopen when warranted

Account for each planned branch, seed/direction pass, retrieved record, exclusion, pending candidate, and deferred response. For targeted work, finish the declared passes and necessary gap searches within disclosed limits. Diminishing yield is informative but cannot establish recall. Formal work follows its protocol's stopping rules.

During provisional writing, audit unsupported major claims, unexplained disagreements, one-group dependence, incompatible measures, missing methods/populations, and claims of “no evidence.” Search consequential gaps, screen additions consistently, record amendments, and allow the new evidence to change the answer. Supplied-corpus mode records gaps without expanding; formal changes require protocol documentation. Final methods should name actual sources/branches, dates, seed sampling, restrictions, and unresolved limits; the detailed machine record remains separate.
