# ARC Rules 1-15 promotion-stage playbook

## Purpose

Reproduce the successful Rule 7 structure for every ARC rule batch. Each stage has an input, output, admission gate, and prohibited shortcut.

## Stage ledger

| Stage | Name | Required output | Admission gate | Prohibited shortcut |
|---:|---|---|---|---|
| 0 | Scope and authority | Batch manifest, source hash, database identity, permissions | Exact target and authority recorded | Starting extraction or writes with ambiguous scope |
| 1 | Manual TXT-first source build | Direct TXT-derived records, chunks, spans, hashes | Counts and offsets close exactly | Using prior JSON as the segmentation authority |
| 2 | Source/text graph materialization | SourceDocument, SourceFile, TextChunk, TextSpan | Zero ownership/hash/orphan violations | Semantic candidates before exact evidence exists |
| 3 | Commentary/candidate materialization | ReviewCandidate families linked to exact spans | One UID and evidence ledger per candidate | Applying production labels during ingest |
| 4 | Stage 1 cumulative closure | Flat ZIP, ledger, SHA256SUMS, rollback evidence | All generated families closed or exactly absent | Claiming completion from separate family reports only |
| 5 | Official-source comparison | Per-provision decisions and temporal blockers | Official source identity and normalization rules sealed | Treating secondary commentary as current law |
| 6 | Amended manifest admission | One-time bounded authorization | Prior package immutable; action and scope exact | Silent scope expansion or original-packet mutation |
| 7 | Metadata/semantic correction | New correction packet and terminal review decisions | All missing components named | Vague `needs review` decisions |
| 8 | Appendix baseline/metric design | Pre-write audits, completion predicates, expected deltas | Denominator risk assessed | Choosing labels before reading metric definitions |
| 9 | Promotion packet/rollback | Exact production identities, relationships, release controls | Packet counts and rollback verified | Relabeling candidates without lineage |
| 10 | Canary apply/verify/rollback | One exact production slice and zero residue | Same shape intended for full apply | Migration-wide cleanup or unlabeled UID scans |
| 11 | Family promotion | Bounded family commits in dependency order | Each family independently verified | One oversized all-family transaction |
| 12 | Independent closure | Exact 1:1 lineage, proof, topology, safety flags | Zero missing/extra/duplicate/residue | Trusting write counters as verification |
| 13 | Appendix R<N> build | Metadata/conformance dirs; MD/DOCX/PDF; delta | Every figure verified; prior run preserved | Overwriting prior revision or comparing wrong fields |
| 14 | Policy/retrieval validation | Policy, benchmark, lineage and smoke artifacts | Query correctness and freshness separately reported | Calling a stale-evidence gate a query failure |
| 15 | Lane closure | Final manifest, checksums, limitations, rollback | All admitted candidates terminal | Closing with unspecified pending work |

## Successful Rule 7 dependency order

Use the following default order across Rules 1-15 unless the source requires a narrower variant:

1. **Proof lines and propositions**
   - Create exact proof objects from TextSpan evidence.
   - Create separate production propositions.
   - Link production to review candidate and proof.

2. **Deontic operators**
   - Promote only explicit modalities.
   - Wire each operator to the exact governed proposition or legal test.
   - This is the path to `DEONTIC_REASONING_WIRED`, not operator count alone.

3. **Legal tests**
   - Add exact authority, proof, elements, factors and decision rule.
   - Add burdens and standards only when explicit.
   - Create established architecture/retrieval companion records so coverage denominators do not regress.
   - Accept that only a subset may qualify as core-complete.

4. **Issues**
   - Promote reusable rule questions as issue frames/templates.
   - Do not fabricate `RAISED_BY`, `DECIDED`, or `RESOLVED` case paths.
   - Rule work may increase issue inventory without increasing decided-issue numerators.

5. **Remedy gateways**
   - Model available remedy, trigger, blockers and alternatives from exact source content.
   - A gateway may be useful but not strictly routable if blockers or alternatives are absent.

6. **Rule-provision versions**
   - Preserve official-match metadata and source hashes.
   - Keep current-law/court-facing/production-eligible flags false while the temporal gap remains open.

7. **Optional families**
   - Treatment, adverse authority, bridge and temporal objects require independent source support.
   - An empty source array is a closed zero family, not a reason to fabricate candidates.

## Gate transitions

Use explicit statuses:

```text
LEVEL_0_SOURCE_INTAKE
LEVEL_1_SOURCE_CLOSED
LEVEL_2_FILE_SIDE_ADMITTED
LEVEL_3_SEMANTIC_REVIEW_CLOSED
LEVEL_4_PROMOTION_PACKET_VERIFIED
LEVEL_5_CANARY_PASSED
LEVEL_6_FAMILY_PROMOTED
LEVEL_7_INDEPENDENTLY_VERIFIED
LEVEL_8_APPENDIX_VERIFIED
LEVEL_9_CONTROLLED_RELEASE_VALIDATED
CLOSED_WITH_LIMITATIONS
```

A transition must identify:

- previous and next state;
- authorizing manifest ID;
- exact candidate UIDs/families;
- evidence package SHA-256;
- allowed operation;
- prohibited operations;
- consumed/unused authorization status;
- closing verification artifact.

## Separate identities and lineage

Default to separate production identities. Preserve review history:

```text
(:ProductionLabel {uid, migration_id, release flags})
  -[:PROMOTED_FROM_CANDIDATE]->
(:ReviewCandidate {candidate_uid, source evidence, review status})
```

Do not destroy or overwrite the review candidate. Set terminal candidate lifecycle fields only after independent verification.

## Release-control ladder

Keep these distinct:

1. candidate exists;
2. candidate reviewed;
3. production object created;
4. controlled source-attribution retrieval allowed;
5. unrestricted production eligible;
6. current-law verified;
7. court-facing/filing-ready.

A lower level never implies a higher one.

## Appendix A closure

Before promotion, capture R<N-1>. After promotion, create R<N>.

Verification requires:

- audit execution succeeded even if readiness remains false;
- metadata/conformance observed timestamps recorded;
- schema and metric-definition fingerprints preserved;
- PDF and DOCX figures checked against artifact values;
- zero skipped figures;
- exact changed metrics reported;
- unrelated changes separated from migration-attributable changes.

## Lane closure decision

Use one of:

- `CLOSED_PROMOTED_CONTROLLED_RETRIEVAL`
- `CLOSED_SOURCE_ONLY`
- `CLOSED_WITH_TEMPORAL_BLOCKER`
- `PARTIAL_NEEDS_NUDGE`
- `BLOCKED_SCHEMA_OR_IDENTITY`
- `ROLLED_BACK`

Never use plain `complete` without stating the release and temporal level.
