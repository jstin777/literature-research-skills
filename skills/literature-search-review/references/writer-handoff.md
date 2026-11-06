# Collector, writer and context boundary

Read when assigning roles, preparing a packet, or returning evidence updates. The ordinary collector/writer split is authorized by this skill. The separate adversarial multi-agent review still requires an explicit user request.

## Choose one owner of the final output

By default the current coordinator collects and maintains the records, then launches one fresh writer. Use the host’s fresh-context/no-history delegation option so the writer does not inherit search attempts, raw results, access failures or the collector's tentative interpretation. Do not use a full-history fork and call it a clean context. Do not specify a model unless the user or environment requires it.

When an existing writer delegates collection, a fresh collector can instead return the packet to that writer. It receives the user brief and collection instructions, not the writer's speculative conclusions. Keep retrieval tool traffic in the collector's context where the host supports that isolation. Return the writer’s finished output to the coordinator for delivery. The coordinator checks task fidelity, required disclosures and material unsupported additions; it does not add new scientific claims from retrieval history without updating the shared evidence and writer. One agent owns shared browser interaction and register mutations; other agents request specific retrievals through that owner. A fresh collector is optional; a second competing writer is unnecessary.

If the host cannot delegate or share readable artifacts, retain the compact packet and disclose the isolation limit. Answer within actual capabilities rather than pretending independent contexts exist. File paths in one environment do not establish access in another.

## Writer brief

Preserve the user's original substantive request and later corrections. Remove credentials and irrelevant personal information. Include:

- The question, purpose/audience when known, requested final outcome and deliverable, constraints and exclusions. Separate stated requirements from collector assumptions. Do not substitute a neutral search query for the full user goal.
- The writer's assignment: use this evidence to produce that outcome; choose an appropriate organization unless the user provided one. Do not add a manuscript, formal review or experimental design to a request for a reading list or explanation.
- Evidence mode: a discovery-only candidate list, substantive verified evidence, a provisional package, or stage-1 mapping for an explicitly requested multi-agent review.
- Actual packet paths or the compact packet itself, its version/date, source access instructions and specific material limitations. Include the complete selected-paper index and relevant contrary/null findings, rather than only evidence favoring the likely answer.
- The routing state: ordinary writer, returning to an existing writer, or multi-agent stage 1. State whether multi-agent review was requested and actually completed. For ordinary writing require the bottom notice from `SKILL.md`.

The brief constrains evidence use and task fidelity; it does not prescribe the writer's prose sections, tone, length or argument beyond the user's request.

## Small discovery-only packet

For a short request for useful papers, supply identity-checked citations/stable links, why each is relevant, source type/version, what was actually read, access level, and known relevance or coverage limits. Abstract-based relevance is provisional. Do not present unread methods/results or full-text verification as established. No manuscript, full corpus dump or rich library is required. Preserve a short separate search trail and unresolved candidates. This does not satisfy a substantive full-text handoff gate.

## Substantive evidence packet

Use the record contract and its `--handoff` checks. The writer initially reads only the brief, whole compact included index, relevant evidence rows and material unresolved limits. Keep the authoritative register, exact queries, excluded hits and access logs on disk for traceability; they are not initial writer context. Link reusable originals and exact locations so the writer can verify important claims or inspect needed context without reconstructing the search.

Evidence rows retain design, population and independent sample unit, operational measure, relevant finding/numbers, uncertainty, limitations/counterevidence, reviewer inference separately, and original source locators. A summary is not independent evidence. The writer may inspect originals; do not forbid source checks to save context. Use DOI/stable publisher or repository URLs rather than session tokens. Do not transfer institutional cookies or assume the writer's browser shares authentication.

Before relying on files, the recipient must confirm it can read the index, a relevant evidence entry and a needed source. If not, the collector can provide a permitted compact excerpt or accessible original, or report a blocker; never mark access verified solely from its own file checks.

## Gap requests and stopping

The writer sends a specific missing claim, paper/evidence ID, required component or undercovered branch to the collector. The collector resumes the existing records, honors scope, and returns a compact delta plus changed evidence/limits. Do not return the full retrieval history, recursively launch writers, or restart completed searches. If new evidence changes a major conclusion, notify the writer of that consequence explicitly.

Complete declared targeted passes and necessary gap searches within disclosed limits. If limits stop work, deliver a useful provisional result with its material gaps. Do not silently expand a supplied corpus, imply exhaustiveness, accept access limitations for the user, or hide inaccessible competing evidence.
