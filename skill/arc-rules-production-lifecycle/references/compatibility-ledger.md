# ARC Merge Compatibility Ledger

## Rule

Do not use blanket "V2 controls wherever different." Resolve material differences explicitly.

| Area | Disposition | Governing treatment |
|---|---|---|
| Source/version closure | `PRESERVED` | Keep exact source/version identity and official-source closure requirements. Three-book evidence is an optional/required campaign profile, not a substitute for official-source/version closure. |
| Discovery no-write separation | `PRESERVED` | Candidate discovery remains distinct from semantic production. |
| Candidate vs production identity | `PRESERVED` | Review candidates remain nonproduction and keep lineage after promotion. |
| Promotion controls | `SUPERSEDED_BY_V2` | Use reviewed V2 promotion packet, canary, family-promotion, closure, rollback, and Appendix rules. |
| Retrieval release | `SUPERSEDED_BY_V2` | Keep release distinct from materialization and require release authorization. |
| Exact-UID canary / rollback / readback | `PRESERVED_STRENGTHENED` | Keep exact identities, bounded writes, rollback, independent readback, and no broad cleanup. |
| Text remediation A/B/C/D | `PRESERVED_SPECIALIST` | This specialist lane is additive; it does not redefine semantic V2 stages. |
| Pathway discovery/validity | `PRESERVED_WITH_SOURCE_BOUNDARY` | Keep no-write discovery/validity. Any shortcut treating unverified internal Rule text as sufficient source authority is superseded by source-integrity requirements. |
| Current law / court-facing / filing-ready | `PRESERVED_SEPARATE` | Never infer from source repair, semantic promotion, or retrieval release. |
| Live graph execution | `UPDATED_IMPLEMENTATION_OWNER` | Route current live Neo4j operations through `whitebox-neo4j-operator`; this updates execution tooling, not ARC semantic meaning. |
| Any other material V1/V2 semantic difference | `UNRESOLVED` | Compare the source contracts and record `PRESERVED`, `SUPERSEDED`, or `INCOMPATIBLE` with evidence before use. |

## Required disposition record

For every newly encountered material V1/V2 difference, record:

- source V1 rule and locator/hash;
- source V2 rule and locator/hash;
- exact difference;
- disposition: `PRESERVED`, `SUPERSEDED`, `INCOMPATIBLE`, or `UNRESOLVED`;
- reason/evidence;
- affected schema/scripts/manifests;
- migration/requalification consequence.

`UNRESOLVED` blocks use of the disputed rule as controlling policy.
