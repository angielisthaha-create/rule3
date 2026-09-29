# ARC metric-improvement map

## Purpose

Use this map to identify which Appendix metrics can be moved legitimately by ARC rule work. Never treat it as permission to create unsupported topology.

| Semantic family | Potentially addressable metric | Legitimate improvement path | Common failure |
|---|---|---|---|
| Deontic | `GLOBAL-DEONTIC.DEONTIC_REASONING_WIRED` | Create explicit operators and connect each to its governed proposition or test with exact proof | Creating isolated operators increases only the denominator |
| Legal test | `TEST-QUAL.CORE_QUALIFIED` | Promote only tests with governed elements, authority, exact proof, threshold, and applicable burden/standard/exceptions/factors | Promoting summaries with only `elements` or `threshold` properties |
| Issue | `ISSUE-LAYER.decided_or_resolved` | Requires case/matter ownership plus a deciding or resolving relationship | Rule issue templates enter the issue denominator but cannot be adjudicated |
| Remedy | `SOTA-REMEDY-GATEWAY.CANONICAL_GATEWAY_ROUTABLE` | Model remedy, blocker, alternative, trigger, and proof as a complete governed route | Treating every remedial sentence as a gateway |
| Rule version | `SOTA-VERSIONED-LAW.*` | Ingest official source version with version, in-force, current, and applies-as-of topology | Secondary commentary creates version nodes but leaves temporal families at zero |
| Proposition | `GLOBAL-INTEGRITY-PROP.*`, `PROP-BRIDGE.*` | Stable UID, singleton owner, exact proofline, source/canonical separation, normalization bridge | Canonicalizing unqualified source statements |
| Adverse treatment | `GLOBAL-ADVERSE-CANDOUR.*` | Requires proposition-scoped treatment and reliable treated/treating authority identity | Rule commentary alone usually cannot establish case treatment |
| Argument/evidence | `GLOBAL-ARGUMENT-EVIDENCE.*` | Connect actual arguments and evidentiary objects to reasoning objects | Re-labelling text spans as evidence |
| Current law | court-facing/current-law boundaries | Official verification and temporal certification | Setting Boolean flags without official proof |

## Metrics generally not solved by ARC rule extraction alone

Do not promise direct improvement to these through rule text work alone:

- case holding ownership;
- structured case citation resolution;
- claim-audit runtime;
- GoldenQuery run history;
- GDS active projections;
- case-level reasoning-chain readiness;
- proposition-level case treatment;
- official statute source trust unless official legislation is ingested;
- answer-quality benchmark scores.

Rule semantics may provide substrate for those systems, but separate case-law, legislation, CI, retrieval, or answer-audit work is required.

## Delta interpretation

For every observed movement, report:

```text
metric_id
previous numerator / denominator
current numerator / denominator
absolute delta
percentage-point delta
expected by migration? yes/no
migration-specific supporting count
classification
limitations
```

A larger total is not automatically an improvement. Prefer percentage-point movement and completion counts over raw totals.

## Candidate-envelope-only batches

A `CANDIDATE_ENVELOPE_INGEST` batch using `PROVISIONAL_ENVELOPE_ONLY` is normally classified as `SUBSTRATE_ONLY`:

- it may create quarantined `ReviewCandidate` envelopes and ingestion-lineage relationships;
- it must not create production labels or canonical target relationships;
- it must not claim Appendix numerator movement;
- it must not enlarge production denominators;
- it may defer Appendix regeneration when the architecture/metric baseline fingerprint is preserved and a post-write architecture audit confirms zero quarantine leakage.

Reassess the Appendix trigger before any later source-graph materialization, promotion, release-status change, temporal certification, or schema/metric-definition change.
