# Rule 7 hardening adversarial replay matrix

Use this matrix before release qualification of the skill after any control-plane edit that touches Stage B/C/D, receipt identity, topology, vector invalidation, denominator closure, or registered-operation execution.

The executable fixtures live in `scripts/adversarial_replay_fixtures.json` and are evaluated by `scripts/run_adversarial_replay.py`. The runner is offline and must not access Neo4j.

| ID | Historical failure / risk | Perturbation | Expected result | Governing control |
|---|---|---|---|---|
| AR-01 | N83 found stale inherited T17 receipt phase | Receipt phase changed to prior Parts 4-6 phase | REJECT | Stage D verifies exact receipt phase/stage/campaign identity |
| AR-02 | N75/N83 topology hashes came from different canonicalizers | Same graph-ish hash compared under a different canonicalizer ID | REJECT | Topology hash comparisons require identical canonicalizer ID/version |
| AR-03 | N79 `NULL = NULL` APPLY refusal | Expected nullable metadata is null and live value is null | ACCEPT | Null-safe equality treats null/null as equal |
| AR-04 | Nullable drift must still be detected | Expected null, live non-null | REJECT | Null-safe comparison plus null/value negative arms |
| AR-05 | N79 high-level guard/PLAN green but APPLY predicate rejected | Eligible count is N-1 | REJECT | Mirrored atomic-preimage probe requires exact N/N eligibility |
| AR-06 | One-time authorization reuse risk after started APPLY | APPLY started, later result NOT_COMMITTED | REJECT_REUSE | Started APPLY consumes authorization regardless of commit outcome |
| AR-07 | T18 stale-vector-only lane could accidentally rewrite clean text | Invalidation footprint includes `text` | REJECT | Invalidation-only footprint excludes text/source/full_text/topology |
| AR-08 | Rule 7.9 negative control could be counted as current denominator | Same UID appears in denominator and negative controls | REJECT | Denominator/control sets are frozen separately and disjoint |
| AR-09 | Obsolete workflow allowed Stage C + independent Stage D in one nudge | Same nudge declares APPLY and independent verification | REJECT | Stage C and Stage D are separate nudges |
| AR-10 | T17 wrapper inherited base receipt phase | Wrapper expected phase differs from delegated APPLY phase | REJECT | Wrapper/base receipt-identity audit covers every written receipt field |
| AR-11 | N85 registered selftest was refused for missing `migration_id` | Required registry argument omitted | REJECT | Registry/CLI arguments are part of executable contract |
| AR-12 | N72 executable-change hardening | Current executable SHA differs from Stage-B-certified SHA before APPLY | REJECT | Executable change invalidates Stage B and prior authorization |
| AR-13 | N84 active skill drifted from N72 release package | Editing base is active older hash, not release-qualified baseline | REJECT | Rebase updates on the frozen release-qualified package |
| AR-14 | Positive integrated control | All receipt/topology/eligibility/footprint/denominator/stage/registry/executable conditions valid | ACCEPT | Combined control path remains usable, not fail-everything |

Release qualification must require all frozen fixtures to produce their expected outcomes. A test runner bug, missing fixture, or unexpected result is a release blocker; do not weaken the fixture expectation to make the skill pass.
