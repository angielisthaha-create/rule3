---
name: arc-rules-production-lifecycle
description: "Govern the Alberta Rules of Court lifecycle in LexGraph/Neo4j through one routed skill: source and three-book reconciliation, exact Rule text remediation, source/version closure, no-write pathway discovery and validity review, candidate handoff, reviewed V2 semantic production, retrieval release, rollback, Appendix measurement, and legacy requalification. Use for ARC Rules 1-15 source repair, version/provenance work, pathway analysis, semantic promotion, retrieval release, rollback, campaign resumption, or migration from predecessor ARC skills."
---

# ARC Rules Production Lifecycle

## Operating model

Use one ARC owner skill with explicit modes. Do **not** force every task through one linear master stage sequence.

Select exactly one primary mode from `references/lifecycle-router.md`:

- `SOURCE_RECONCILIATION`
- `TEXT_REMEDIATION`
- `PATHWAY_DISCOVERY`
- `PATHWAY_VALIDITY`
- `PHASE_A_HANDOFF`
- `SEMANTIC_PRODUCTION`
- `RETRIEVAL_RELEASE`
- `ROLLBACK`
- `APPENDIX_MEASUREMENT`
- `LEGACY_REQUALIFICATION`

A mode may hand off to another mode only when its own exit contract closes. Never treat the presence of downstream graph objects as proof that an upstream gate passed.

## Controlling sources

Use active instructions in this order:

1. this `SKILL.md` and `references/lifecycle-router.md`;
2. the mode-specific reference named by the router;
3. `references/compatibility-ledger.md` for V1/V2 decisions;
4. the reviewed semantic V2 contract in `promotion-stage-playbook.md`, `promotion-contracts.md`, `rule-workflow.md`, and `manifest-schema.md` when `SEMANTIC_PRODUCTION` or `RETRIEVAL_RELEASE` uses that contract;
5. immutable source artifacts, exact live graph state, and bound migration/verification receipts.

Archived predecessor instructions are provenance only unless `references/compatibility-ledger.md` explicitly preserves them. Never silently blend V1 and V2 semantics.

## Global invariants

- Apply `proof first -> role second -> authority third -> application fourth`.
- Separate source evidence, candidate interpretation, semantic qualification, production materialization, retrieval eligibility, current-law verification, court-facing approval, and filing readiness.
- Discovery is no-write with respect to production semantics. Candidate packets must not contain executable write Cypher.
- Never invent burdens, standards, factors, exceptions, blockers, alternatives, remedies, authority status, current-law state, or adjudication to improve a metric.
- Preserve exact source carriers, hashes, locators, identity/version context, and contrary evidence.
- Preserve repealed/obsolete rows as negative temporal or identity controls; never pad the current-parent denominator with them.
- Apply eligibility gates before similarity ranking.
- Live Neo4j reads/writes belong to `whitebox-neo4j-operator`; always target the explicit database and use registry-resolved schema with bounded exact IDs.
- When current-law, appeal-status, adverse-authority, or case-treatment closure is required, compose with `legal-research-workbench` and authoritative external sources. Do not infer current law from ARC production status.
- For Appendix DOCX/PDF outputs, use the applicable document/PDF render-and-verify workflow; a generated file is not verified merely because it exists.
- Treat uncertain write outcome as unknown until exact readback establishes commit state.

## Conditional three-book source gate

Read `references/three-book-source-gate.md` whenever the campaign declares Book A/B/C evidence relevant.

Use `three_book_mode`:

- `REQUIRED` - all declared required carriers must close before the dependent source/text gate can close;
- `OPTIONAL_CORROBORATION` - use available books as corroborating/adversarial evidence, but their absence does not itself block if the controlling source gate independently closes;
- `NOT_APPLICABLE` - do not manufacture Book A/B/C requirements.

Do not assume the user's three ARC books are primary or secondary. Bind each actual artifact through the source registry before assigning evidentiary weight. Track origin/derivation so copied carriers are not counted as independent corroboration.

No majority vote, silent text merge, or unexplained normalization is allowed. Establish version identity before substantive wording comparison. `VERSION_IDENTITY_UNRESOLVED` is a hold, not an invitation to choose the cleaner text.

## Text-remediation lane

Use `TEXT_REMEDIATION` only when live Rule text/vector/receipt state itself needs remediation. Read `references/text-remediation-control-plane.md` plus the existing remediation references.

Preserve the four-stage fail-closed cycle:

A. source reconciliation and exact candidate freeze;
B. exact-N operator build/falsification and PLAN, with no domain write;
C. exact bounded APPLY plus immediate safety readback only;
D. later independent verification.

**Stage C and Stage D are always separate nudges.** The remediation one-nudge rule applies to this hardened lane, stale-vector-only invalidation, and receipt-metadata repair unless another campaign explicitly adopts it. Do not impose that pacing rule on unrelated semantic-production stages.

Before APPLY require all four safety properties:

- **G4F footprint equality** - mutation and rollback target the same exact identities/properties;
- **G4H payload binding** - executed payload is hash-bound to the reviewed payload;
- **G4L operation-enforced batch bound** - an N+1 payload fails inside the operation;
- **G4D verifier discrimination** - the same guard path passes a known-good packet and rejects known-bad controls.

Also require topology canonicalizer ID/version, null-safe preimage equality, mirrored atomic-preimage eligibility, exact receipt identity, and executable-change recertification. Standing WhiteBox owner authority permits tool execution but does not replace the operation-bound manifest/receipt/authorization evidence required by this remediation contract.

Special remediation sublanes remain active and separate:

- **Stale-vector-only invalidation** preserves `text`, `source`, `full_text`, labels, relationships, and topology while removing only the frozen stale vector/metadata footprint plus its receipt.
- **Receipt-governance defects** use their own exact-preimage, corrective-receipt, rollback, APPLY, and later independent-verification lane; never silently rewrite historical receipt metadata.

## Semantic-production lane

`SEMANTIC_PRODUCTION` uses the reviewed **V2 Stage 0-15 ledger as the only numbered semantic lifecycle**. Do not create a second Gate/Level/Stage 0-15 system.

Read `promotion-stage-playbook.md` and `manifest-schema.md`. New manifests use `arc-rule-batch-v3`. `scripts/validate_rule_manifest.py` must pass before a manifest can control execution.

Preserve the V2 lane model:

- `SOURCE_BUILD`
- `CANDIDATE_ENVELOPE_INGEST`
- `SOURCE_GRAPH_MATERIALIZATION`
- `OFFICIAL_SOURCE_CLOSURE`
- `PRODUCTION_PROMOTION`
- `RETRIEVAL_RELEASE`

Direct `ROLLBACK` and `APPENDIX_MEASUREMENT` remain top-level modes and are not redefined as extra V2 stage numbers.

Keep source/version evidence carriers distinct from production semantic identities: proving a Rule/version in the source layer does not itself create or qualify a production `RuleProvisionVersion`.

## Dependency invalidation

Read `references/dependency-invalidation.md` whenever a source text, Rule/version identity, pathway-validity decision, semantic qualification, production carrier, or retrieval predicate changes.

A changed lower-layer fingerprint does not erase history. It must:

1. identify directly affected downstream objects;
2. mark only dependent proof/qualification/retrieval predicates stale or held;
3. remove retrieval eligibility where the changed dependency can affect returned legal meaning;
4. enqueue bounded requalification/reverification;
5. reuse unrelated PASS receipts whose dependency fingerprints remain unchanged.

Do not globally rebuild ARC merely because a file, chat, worker, or non-semantic convenience artifact changed.

## Compatibility and legacy material

Read `references/compatibility-ledger.md` before using any V1/V2 difference. Only areas explicitly classified `PRESERVED`, `SUPERSEDED`, or `INCOMPATIBLE` are resolved. Any unenumerated material difference is `UNRESOLVED` and must be compared before use.

Use `LEGACY_REQUALIFICATION` for existing graph material created under predecessor contracts when a changed governing rule can affect its proof, semantics, temporal validity, or retrieval eligibility. Never automatically grandfather or automatically rebuild all legacy objects.

## Retrieval, rollback, and Appendix boundaries

- `RETRIEVAL_RELEASE` requires production-reader compatibility, retrieval smoke tests, proof/source lineage, **retrieval-release authorization**, and explicit freshness/current-law limits.
- `ROLLBACK` must restore or invalidate not only migration-scoped domain objects but any candidate lifecycle, release, retrieval, reader, or metric metadata that depended on the rolled-back state. Preserve audit history.
- `APPENDIX_MEASUREMENT` uses explicit typed denominators. Do not refer to a single universal "ARC denominator".

## Denominator discipline

Name each denominator explicitly, including where applicable:

- source/text-remediation denominator;
- three-book/source-closure denominator;
- candidate-admission denominator;
- semantic-family completion denominator;
- Appendix metric denominator;
- retrieval-release denominator;
- current-parent denominator and separately frozen negative controls.

Freeze population definition, snapshot, inclusions, exclusions, hash, and completion predicate.

## Resume precedence

For every mode, use:

1. latest independently verified closeout for that mode;
2. exact current graph/readback state;
3. frozen manifest/packet/receipt and dependency fingerprints;
4. required source/corroborator/official-source artifacts;
5. conversation history.

If these conflict, hold and reconcile before mutation.

## Required mode references

- Router and admission/exit rules: `references/lifecycle-router.md`
- Three books: `references/three-book-source-gate.md`
- Text remediation: `references/text-remediation-control-plane.md`, `references/workflow-state-machine.md`, `references/packet-contracts.md`, `references/failure-modes.md`, `references/concurrency-and-closure.md`, `references/output-contract.md`
- Pathway discovery: `references/pathway-discovery.md`, `references/pathway-ontology.md`, `references/pathway-relationship-model.md`, `references/pathway-rule-family-routing.md`, `references/pathway-discard-ledger.md`
- Pathway validity/manual review: `references/pathway-validity.md`, `references/pathway-manual-validation-checklist.md`, `references/pathway-adversarial-review.md`
- Candidate handoff: `references/pipeline-candidate-handoff.md`
- V2 semantic lifecycle: `references/promotion-stage-playbook.md`, `references/promotion-contracts.md`, `references/rule-workflow.md`, `references/manifest-schema.md`, `references/metric-improvement-map.md`, `references/recovery-and-timeout.md`
- Retrieval/rollback/measurement: `references/pipeline-retrieval-release.md`, `references/pipeline-rollback.md`, `references/pipeline-appendix-metrics.md`
- Compatibility: `references/compatibility-ledger.md`, `references/pipeline-version-compatibility.md`
- Dependency invalidation: `references/dependency-invalidation.md`
- Legacy requalification: `references/legacy-requalification.md`
- Deployment transition: `references/deployment-transition.md`
- Source/merge provenance: `references/source-provenance.md`, `references/merge-manifest.json`

## Validation before distribution

Run all of the following on the exact final candidate:

```text
scripts/validate_hardening_contract.py
scripts/run_adversarial_replay.py
scripts/pathway-discovery/scripts/self_test.py
scripts/integration_self_test.py
scripts/validate_merge_manifest.py
```

Then run the skill validator/package workflow. Treat component PASS as component evidence only; the merged skill is accepted only when the integration/adversarial suite also passes.
