# ARC Lifecycle Router

## Purpose

Route an ARC request into the smallest lawful mode. Modes are peers, not mandatory stages in one universal sequence.

| Mode | Use when | Required admission | Terminal output / lawful handoff |
|---|---|---|---|
| `SOURCE_RECONCILIATION` | source carriers, Book A/B/C, operative wording, version identity, or source provenance is unresolved | exact Rule/subrule target and source artifacts | reconciled source packet or exact hold; may hand off to `TEXT_REMEDIATION`, V2 source build, or stop |
| `TEXT_REMEDIATION` | live Rule text, stale vector, or receipt metadata is wrong | source-reconciled exact target set | independently verified repair/invalidation/receipt state; may hand off only after Stage D |
| `PATHWAY_DISCOVERY` | discover triggers, prerequisites, exceptions, remedies, or downstream Rule pathways | source-proved Rule text/version adequate for candidate discovery | no-write candidate packet + discard/no-write ledger; may hand off to `PATHWAY_VALIDITY` or stop |
| `PATHWAY_VALIDITY` | test candidate pathway against source, related subrules, context, and contrary authority | candidate packet + source proof | validation decisions/holds; may hand off to `PHASE_A_HANDOFF` or semantic candidate workflow |
| `PHASE_A_HANDOFF` | transfer reviewed candidates to another worker/lane | exact candidate IDs, proof spans, unresolved items, verification limits | bounded handoff packet; never production approval |
| `SEMANTIC_PRODUCTION` | build/review/promote governed ARC semantics | choose one reviewed V2 workflow lane and valid manifest | V2 Stage 0-15 lane closeout at the correct source/production level |
| `RETRIEVAL_RELEASE` | production objects exist but answer-set eligibility is not yet released | verified production lineage + release packet | authorized retrieval state with smoke-test/freshness evidence |
| `ROLLBACK` | reverse a bounded migration or recover from verified bad postimage | exact migration/prestate/rollback evidence | restored or explicitly held state + readback + metadata/retrieval consequences |
| `APPENDIX_MEASUREMENT` | measure before/after ARC quality without necessarily mutating graph | explicit metric definitions and typed denominator snapshots | revisioned measurement artifacts and attributed deltas |
| `LEGACY_REQUALIFICATION` | existing ARC graph objects were created under older contracts and a changed rule may affect them | producing workflow/version/source evidence | PRESERVED, REQUALIFICATION_REQUIRED, QUARANTINED, or exact hold |

## Routing rules

1. Prefer the narrowest mode that directly owns the requested operation.
2. Do not run source repair merely because semantic review is requested if source proof is already fingerprint-valid.
3. Do not run semantic production merely because a text repair completed; hand off only when the user/campaign requires it.
4. Do not force retrieval release through a new production-promotion run when production objects are already independently closed.
5. Direct rollback and Appendix measurement remain lawful entry modes.
6. Current-law/court-facing/filing-ready work is outside ARC production completion and requires its own higher-use gate.

## V2 semantic lane contract

When routing to `SEMANTIC_PRODUCTION`, the reviewed V2 Stage 0-15 sequence in `promotion-stage-playbook.md` is the sole numbered semantic lifecycle. The router does not introduce competing stage numbers.

## Pacing

The remediation A/B/C/D lane retains its one-nudge rule and mandatory C/D separation. Other modes follow their own governing contract and may close multiple safe non-write transitions in one request when the contract permits it.
