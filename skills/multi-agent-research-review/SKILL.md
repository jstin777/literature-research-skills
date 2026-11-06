---
name: multi-agent-research-review
description: Conduct a staged scientific literature and experimental-design review with independent evidence mapping, advocate and adversarial evaluations, one cross-examination, conditional adjudication, synthesis, and separate citation and methods audits. Use only when the user explicitly requests this multi-agent workflow or its staged advocate/adversarial review. Ordinary paper searches, literature reviews, requests for rigor, and consequential topics do not activate it.
---

# Multi-Agent Research Review

Produce one coherent, source-backed scientific assessment using the user's research question, scope, evidence priorities, and requested deliverable. This skill defines the review architecture; it does not supply new research objectives.

## Connection to literature search

Use [literature-search-review](../literature-search-review/SKILL.md) for discovery, screening, acquisition, compact extraction, and the evidence handoff when it is available. Keep the skills separate: the search skill ordinarily supplies a compact packet to a separate fresh-context writer; this explicitly requested workflow replaces that ordinary writer with the staged evaluation, synthesis and audits below. Enter the search skill at this workflow’s stage 1, independent evidence mapping, never as a second review running alongside it.

Resolve the installed `literature-search-review` skill by name if the bundled relative path is unavailable; never assume a sibling installation. That skill invokes the standalone [paper-fulltext-access](../paper-fulltext-access/SKILL.md) skill for direct-URL LibKey recovery and initiates institutional-login readiness before discovery. Reuse the coordinator’s verified browser session; keep browser interaction with one owner.

The evidence mapper resumes any existing protocol, paper/evidence registers, source files, search/access logs, and checkpoint. Use their stable paper/evidence IDs and one authoritative artifact root. Read that skill's [record contract](../literature-search-review/references/record-contract.md) for the shared fields and handoff checks; do not maintain a second bibliography or repeat completed searches. If the search skill or helpers are unavailable, preserve equivalent records using the mapping requirements below and disclose the unperformed checks.

The mapper delivers a descriptive evidence package, not an initial persuasive draft. The coordinator checks coverage, pending limitations, and recipient access before launching A/B, and supplies both the same evidence snapshot without a prior assessment. Subsequent evidence additions go through the coordinator into the same register and are made available to both evaluators without adding debate rounds. Route specific missing claims, methods, or branches back to the mapper for targeted retrieval/extraction; supplied-corpus restrictions still apply.

Only run this architecture following the user’s explicit request. If delegation is unavailable, disclose that independent multi-agent review cannot be completed and offer a clearly labeled single-context assessment; do not label simulated roles as completed independent stages.

## Orchestration and independence

The coordinator manages dependencies, source access, handoffs, and completion. Use actual subagents provided by the host. Skill instructions do not themselves create isolated contexts; host-specific agent metadata is optional, and the explicit-invocation requirement in this document applies even when that metadata is ignored. Pass each role the user’s question, requested final outcome and constraints, relevant evidence, its role instructions, and an output location. The architecture does not prescribe the final prose’s outline. For a literature question without a proposed experiment, A develops the strongest defensible evidence interpretation and B challenges its support, alternatives and inference limits; apply experiment-specific checks only to an actual proposed design. Do not merely assign different headings to one undifferentiated answer and call it independent review.

If a needed tool, connector, or browser capability is unavailable, fails, or returns a partial error, the coordinator tells the user what failed, the observed reason, its effect, and the planned retry or fallback before continuing. Workers surface failures promptly so the coordinator can notify the user before the affected work proceeds. Log failures; continue with authorized alternatives without requiring approval solely for the notification.

- Begin with the evidence mapper. Launch A and B only after its evidence base is assembled.
- Give A and B the same evidence base but neither evaluator's conclusions. Use fresh contexts or restricted history so the initial evaluations are genuinely independent.
- After both initial evaluations are complete, give each the other's original conclusions for exactly one response. Neither response should depend on seeing the other's response first.
- The synthesis role is separate from the evidence mapper and from A and B. Citation and logic auditors are separate independent roles; neither sees the other's audit before producing its own.
- Respect available concurrency. A/B and the two final audits may run in parallel; dependent stages remain sequential.
- Do not create user-facing tasks merely to implement subagents. If model selection is unavailable, use available agents and disclose that limit. If delegation is unavailable, do not claim independent stages ran.

Preserve outputs and a brief stage-status record in a working directory. Each handoff should point to the actual completed files, not rely on ephemeral conversation summaries. An interrupted run resumes its incomplete stage from saved artifacts; it does not restart completed evaluations or gain extra debate rounds. Check for saved progress before retrying a stalled role, and prevent duplicate writers.

## Model allocation

Use stronger models selectively for consequential reasoning, not routine retrieval or bibliography work.

## Shared evidence discipline

Every role must distinguish:

1. **Empirical finding:** directly demonstrated in data or reported by the source.
2. **Evidence-supported inference:** interpretation supported by findings but not directly demonstrated.
3. **Methodological judgment/recommendation:** advice about design, modeling, analysis, or inference.
4. **Speculation/hypothesis:** plausible but insufficiently supported possibility.

Make these categories explicit where conflating them would change the argument. Fitted constructs are conditional on the model. Recording correlations are not interventions; intervention effects on task behavior do not automatically isolate a latent mechanism or general trait.

Honor the user's evidence hierarchy. For a comparative animal research question, an example hierarchy is: original target-species experiments; original human experimental/computational studies; other primate/animal experiments; meta-analyses/systematic reviews; theory/modeling; narrative reviews for discovery/context only. Adapt relevance to the supplied question rather than forcing animal evidence into unrelated topics. Trace central empirical claims to originals.

## 1. Independent evidence mapping

Gather and characterize evidence before advocating a design. Search the major concepts, seminal studies, recent work, competing accounts, measurement methods, and direct precedents for each proposed approach.

Use the connected search workflow in handoff mode. Each included or substantively used paper needs question-relevant evidence rows with exact original-source locations and short supporting context, plus reusable source paths or explicit reopening/access limits. Export/read the entire included index and evidence register; a prose summary alone is not the evidence package. When using the search helper, run `catalogue.py validate --handoff` before labelling the mapping ready. Preserve unresolved work and qualify a provisional package rather than treating a passed file/schema check as scientific verification.

Deliver an evidence map with:

- Original source identity and stable link/DOI; source type and access level (full text, abstract, metadata only).
- Population/species, independent sample size, task/design, manipulation or measurement, and relevant findings where verified.
- Relevance to the user's question, inferential limitations, contradictions, and unresolved gaps.
- A search record: date, search routes, representative query strings by concept, citation-following strategy, and coverage limits.

Distinguish a broad systematic concept search from a registered or exhaustive systematic review. Do not invent screening counts, claim complete coverage, or infer novelty from failure to find an exact precedent. Record inaccessible methods and undercovered literatures. Keep the map primarily descriptive.

## 2. Independent scientific evaluations

### A — Design advocate

Construct the strongest defensible case for the proposed approach: what it can establish, its strongest features, how weaknesses can be repaired, and appropriate interpretation boundaries. Address contradictory evidence rather than ignoring it. Identify the assumptions needed for each important inference.

### B — Adversarial methods reviewer

Attempt to falsify the approach independently of A. Examine alternative explanations, confounds, construct validity, identifiability, measurement reliability, model assumptions, sampling units, causal attribution, and generalization. Separate fixable weaknesses from fundamental incompatibilities.

When an experimental design is actually proposed, include a **Kill-the-Experiment Assessment**:

> Could the proposed experiment fail to answer its primary question even if data collection were technically successful?

For every potentially fatal issue, state the affected inference, why the data cannot support it, whether design/analysis/measurement/program changes can repair it, and the required repair. Recommend abandonment only for a fundamental incompatibility, not because another design is somewhat better. An experiment can be unfit for a broad claim while remaining useful for a narrower question.

Both evaluators should produce propositions that can be cross-examined, with evidence, assumptions, confidence/uncertainty, and consequences for the recommendation.

## 3. One cross-examination round

After both independent evaluations finish, exchange their original conclusions. Each evaluator responds once to substantive disagreements using exactly these classifications as applicable:

- **Agree**
- **Partially agree**
- **Disagree**
- **Insufficient evidence to resolve**

Explain the basis; add evidence only when needed. Do not permit repeated back-and-forth. The coordinator records what is resolved, what remains, and whether anything remaining is material.

## 4. Conditional adjudication

A disagreement is material only if its resolution could substantially change evidence interpretation, whether the experiment answers the question, validity of an important inference, or the final recommendation. Wording, emphasis, and minor confidence differences do not qualify. Missing practical information is not automatically an adversarial disagreement.

Only if a material disagreement survives the single response round, create one independent adjudicator. Supply the disputed proposition, both arguments, and relevant sources. The adjudicator independently inspects the evidence and chooses the better-supported interpretation or declares the evidence insufficient. Argument length or confidence carries no authority. Its ruling is final for this report. Preserve unresolved empirical uncertainty; do not force consensus or create recursive adjudicators.

## 5. Separate synthesis and draft

After reconciliation and any adjudication, a separate synthesis agent writes the draft. Read the shared protocol, full included index, evidence rows, source-reuse records, and unresolved queue before writing. Integrate the evidence and resolved critiques into one coherent assessment rather than concatenating role outputs. Cover the user's full scope, direct precedents, strengths, weaknesses, alternatives, practical recommendations, inference limits, and remaining uncertainties. Include the collective kill verdict and repairs where relevant to a proposed experiment. For other questions, synthesize the defensible evidence interpretation and remaining disputes in the form the user requested.

Carry forward the search record, source access limitations, evidence labels, and important unresolved disagreements. Restructure for coherence when necessary, but do not repeatedly regenerate the outline for minor findings. Save the draft for both auditors.

## 6. Independent final audits

Run these after synthesis; they may run in parallel. They produce correction reports, not competing new drafts.

**Citation and evidence auditor:** Verify source existence, identity, claim support, study characteristics, source type, and causal versus correlational representation. Inspect originals, not just metadata or the evidence map. Flag unsupported claims and inaccessible details; specify exact corrections or narrower wording. Any citation failure must be corrected or its unsupported claim removed before release.

Reuse available original-source files and inspect surrounding passages and needed tables/figures/supplements. Shared extraction reduces repeated acquisition; it does not replace independent original-source checks or make repeated summaries independent evidence. Return identified gaps to the coordinator for targeted follow-up rather than independently restarting discovery.

**Logic and methods auditor:** Inspect whether conclusions follow, constructs match measurements, designs support attributed inferences, alternative explanations are addressed, validation is noncircular, uncertainty is calibrated, and any surviving flaw fundamentally undermines the recommended strategy. Require focused revisions where needed. Do not initiate another agent debate.

## 7. One final revision and stop

Return the synthesized draft, both completed audits, any adjudication decisions, and relevant evidence to the synthesis agent for **one final revision**. Incorporate required corrections, retain meaningful uncertainty, and save the user's requested deliverable. Record a concise audit-disposition summary and actual model/workflow limitations; do not dump all intermediate role reports into the main answer.

After this revision:

- Do not restart adversarial review, create additional critics, revisit resolved disagreements, or ask another strongest-model reviewer to inspect wording changes.
- Do not force resolution of uncertain evidence.
- Check artifact integrity and required corrections before delivery; this is not another scientific review round. Narrow or remove any unresolved unsupported claim rather than publishing it as established.
- Report the final artifact and key recommendation concisely. The workflow terminates here.
