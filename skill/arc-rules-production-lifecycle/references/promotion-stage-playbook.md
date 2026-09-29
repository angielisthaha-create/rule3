# ARC Rules 1-15 Stage 0-15 playbook

## Integration scope

This is the sole numbered Stage 0-15 lifecycle for the reviewed semantic-production contract. Top-level ARC router modes such as text remediation, pathway discovery, rollback, Appendix-only measurement, and legacy requalification are not alternate Stage/Level/Gate sequences.

## Purpose

Within `SEMANTIC_PRODUCTION`, use this one authoritative Stage 0-15 sequence. Do not create a second semantic Gate or Level numbering system. Each stage has an input, output, admission rule, and prohibited shortcut.

## Workflow lanes

Declare one lane:

- `SOURCE_BUILD`
- `CANDIDATE_ENVELOPE_INGEST`
- `SOURCE_GRAPH_MATERIALIZATION`
- `OFFICIAL_SOURCE_CLOSURE`
- `PRODUCTION_PROMOTION`
- `RETRIEVAL_RELEASE`

A lane may leave later stages `PENDING`, `BLOCKED`, or `NOT_APPLICABLE` only through the manifest rules. For current Rule 3 candidate batches, use `CANDIDATE_ENVELOPE_INGEST`.

## Stage ledger

| Stage | Name | Required output | Admission rule | Prohibited shortcut |
|---:|---|---|---|---|
| 0 | Scope and authority | Manifest, source hash, database, lane, permissions | Exact target and authority recorded | Starting work with ambiguous scope |
| 1 | Manual TXT-first source build | Direct TXT-derived records, spans, hashes | Counts, offsets, and target order close | Using prior JSON as segmentation authority |
| 2 | Source evidence closure | Materialized source graph or provisional exact-source envelope | One approved source-materialization mode closes | Treating envelope-only evidence as canonical source graph |
| 3 | Review-candidate materialization | Quarantined source-attributed candidates | One UID and evidence ledger per candidate | Applying production labels during ingest |
| 4 | Stage 1 cumulative closure | Flat ZIP, ledger, checksums, rollback evidence | All targets and families close exactly | Claiming closure from partial family reports |
| 5 | Official-source comparison | Provision decisions and temporal blockers | Official identity and normalization rules sealed | Treating commentary as current law |
| 6 | Amended manifest admission | One-time bounded authorization | Prior package immutable; action exact | Silent scope expansion |
| 7 | Metadata/semantic correction | Correction packet and closed review decisions | Missing components explicitly named | Vague `needs review` |
| 8 | Appendix baseline/metric design | Trigger decision; baseline and metric contract when required | Denominator risk assessed before promotion | Rebuilding Appendix for nonproduction-only batches |
| 9 | Promotion packet/rollback | Exact production identities and rollback | Counts, lineage, and rollback verified | Relabeling candidates without lineage |
| 10 | Production canary | One exact production slice and verification | Same shape intended for full apply | Using candidate-envelope ingest as a production canary |
| 11 | Family promotion | Bounded family commits | Each family independently verified | One oversized transaction |
| 12 | Independent closure | Exact lineage, proof, topology, safety flags | Zero missing/extra/duplicate/residue | Trusting write counters alone |
| 13 | Post-promotion Appendix | Revisioned artifacts and delta when triggered | Every figure verified | Generating without a trigger or overwriting prior revision |
| 14 | Policy/retrieval validation | Policy, benchmark, lineage, freshness artifacts | Correctness and freshness separated | Calling stale evidence a query failure |
| 15 | Lane closure | Final manifest, checksums, limitations, rollback | All admitted objects terminal; deferrals valid | Closing with unspecified pending work |

## Stage 2 source-materialization modes

### `GRAPH_MATERIALIZED`

Create and verify:

```text
SourceDocument -> SourceFile -> TextChunk -> TextSpan
```

Require exact ownership, hashes, offsets, counts, and zero orphans. Stage 2 may be `CLOSED`.

### `PROVISIONAL_ENVELOPE_ONLY`

Use when source-graph materialization is unavailable, unauthorized, or deferred. Preserve the exact evidence ledger in the review candidate or a bound evidence packet:

- source package and record hashes;
- artifact filenames and hashes;
- span UIDs, offsets, and quote hashes;
- target key and proposed singleton anchor;
- embedded candidate UID ledger;
- explicit nonproduction and unresolved-identity controls.

Stage 2 must be `CLOSED_WITH_LIMITATIONS`. Stage 3 may proceed only for quarantined candidates. Stages 9-13 remain blocked until source materialization or a governor-approved equivalent proof model closes the limitation.

## Successful dependency order for production promotion

Use this order only in the `PRODUCTION_PROMOTION` lane:

1. proof lines and propositions;
2. deontic operators wired to propositions/tests;
3. legal tests, elements/factors, explicit burdens/standards, and governed dispositions;
4. reusable issue frames without fabricated adjudication;
5. remedy gateways with sourced triggers, blockers, and alternatives;
6. rule-provision versions with temporal restrictions preserved;
7. optional treatment, bridge, adverse-authority, or temporal families when independently supported.

## Stage transitions

Record transitions with the manifest `stage_ledger`. Do not create a separate Level sequence.

Every transition must identify:

- `stage_id` and stage name;
- previous and next status;
- authorizing manifest ID;
- exact candidate UIDs/families;
- evidence package SHA-256;
- allowed and prohibited actions;
- authorization consumed/unused state;
- closing verification artifact or explicit limitation.

Use these status values:

```text
PENDING
ADMITTED
IN_PROGRESS
CLOSED
CLOSED_WITH_LIMITATIONS
BLOCKED
NOT_APPLICABLE
ROLLED_BACK
```

## Separate identities and lineage

Default to separate production identities:

```text
(:ProductionLabel {uid, migration_id, release flags})
  -[:PROMOTED_FROM_CANDIDATE]->
(:ReviewCandidate {uid, source evidence, review status})
```

Do not destroy or overwrite review candidates. Set terminal lifecycle fields only after independent verification.

For envelope-only candidate ingestion, do not create a canonical target relationship. Store the proposed singleton `Section` UID as a property until identity is resolved.

## Release-control ladder

Keep these distinct:

1. source record exists;
2. provisional envelope exists;
3. review candidate exists;
4. candidate reviewed;
5. production object created;
6. controlled source-attribution retrieval allowed;
7. unrestricted production eligible;
8. current-law verified;
9. court-facing/filing-ready.

A lower state never implies a higher one.

## Appendix trigger and closure

Set Appendix generation as required only when a batch may change production topology, release status, current-law status, schema/metric fingerprints, or an Appendix numerator/denominator.

For a candidate-only envelope batch:

- use `appendix.mode=DEFERRED_NONPRODUCTION`;
- set `generation_required=false`;
- retain the current architecture/metric baseline fingerprint and audit run ID;
- do not create a new Appendix revision.

For promotion-relevant work, capture the prior revision before promotion and build the next revision after independent closure. Verify observed timestamps, fingerprints, every figure, exact changed metrics, and migration attribution.

## Lane closure decisions

Use one of:

- `CLOSED_CANDIDATE_ENVELOPES_NONPRODUCTION`
- `CLOSED_SOURCE_GRAPH_MATERIALIZED`
- `CLOSED_PROMOTED_CONTROLLED_RETRIEVAL`
- `CLOSED_SOURCE_ONLY`
- `CLOSED_WITH_TEMPORAL_BLOCKER`
- `PARTIAL_NEEDS_NUDGE`
- `BLOCKED_SCHEMA_OR_IDENTITY`
- `ROLLED_BACK`

Never use plain `complete` without the release, source-materialization, and temporal level.
