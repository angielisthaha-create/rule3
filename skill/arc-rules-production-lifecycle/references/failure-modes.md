# Failure Modes and Hardening Lessons

## Contents

- [1–5: Core count, rollback, carrier, bound, and falsification controls](#1-zero-is-a-valid-count)
- [6–10: Authorization, timeout, embedding, source, and current-law boundaries](#6-unauthorized-apply-proof)
- [11–15: Wrapper/reporting, graph identity, concurrency, and three-book gates](#11-wrapperbase-reporting-ambiguity)
- [16–20: Source defects, cardinality, vector provenance, platform gates, Stage C/D](#16-first-hand-source-carriers-may-contain-extraction-defects)
- [21–25: Denominator transition, nullable equality, APPLY parity, authorization use, topology identity](#21-final-denominator-closure-is-not-permission-to-start-the-next-rule-family)
- [26–30: Receipt identity, specialization leakage, invalidation-only work, controls, registry arguments](#26-receipt-phasestagecampaign-is-part-of-the-postimage)

## 1. Zero is a valid count

Do not use truthiness expressions that convert `0` to a sentinel such as `-1`. A reconciliation with `holds: 0` must remain valid.

Use explicit `is None` checks for optional numeric fields.

## 2. Preserve exact prior text for rollback

A prior text SHA proves identity but cannot restore the value. Store the exact prior text in the rollback packet.

## 3. Guard `full_text` even when it is not mutated

A source-reconciled candidate may have been derived partly from the bounded `full_text` carrier. Freeze and recheck its hash before APPLY so silent carrier drift blocks the write.

## 4. Prevent N+1 acceptance

Do not rely only on caller-side truncation. The operation itself must reject a payload whose count exceeds the frozen authorized maximum.

## 5. Same-path negative tests

A verifier that only proves a good packet passes is incomplete. Known-bad mutations must travel through the same guard path and fail for the expected reason.

## 6. Unauthorized APPLY proof

Before owner authorization exists, call APPLY with every other execution flag satisfied. It must fail specifically at the external authorization gate and report no write.

Then independently read the graph to prove no mutation occurred.

## 7. Timeout means unknown state

Never retry a potentially started write after timeout/error. First inspect exact receipt and target postimages.

## 8. Embedding decoupling

Text correctness does not require immediate vector regeneration. The safe default is to invalidate a stale vector and leave it absent.

Do not make missing embeddings a failure condition for a text-repair campaign.

## 9. `full_text` is not automatically authoritative

It may contain following headings or other boundary material. Use it only after independent source comparison identifies the exact operative provision.

## 10. Source match is not current-law certification

A June/August consolidation match can support text repair while a later Gazette/current-law gap remains open. Keep the temporal hold explicit.

## 11. Wrapper/base reporting ambiguity

If a registered wrapper delegates to a base runner, freeze the wrapper SHA separately. Do not misreport an inherited base-module SHA as the wrapper identity.

## 12. Control-plane changes versus domain writes

Registering an operator or writing manifests is not a domain graph mutation. Report these separately.

## 13. Convenience-property miss is not graph absence

A zero-row lookup on an optional property such as `rule` does not prove the `UnifiedRule` is missing. Resolve the governed UID/name carrier before classifying absence.

## 14. Corroborator snapshots can go stale after concurrent repairs

Book B/C may correctly report an earlier dirty live row that has since been repaired by another governed lane. Reconcile current live text, the external repair receipt, and Book A before calling a conflict. If all close, use `HOLD_ALREADY_SOURCE_RECONCILED_EXTERNAL_REPAIR` and preserve the older finding as historical provenance.

## 15. Required three-book evidence is a gate

When the campaign requires Book A/B/C analysis, do not continue Stage A if a required Book B/C artifact is missing or materially incomplete. Corroborators never substitute for first-hand Book A proof.

## 16. First-hand source carriers may contain extraction defects

Do not blindly restore a duplicated or corrupted first-hand carrier byte sequence. Freeze the discrepancy and independently close the operative wording through the declared corroborating or official source before repair.

## 17. Operator cardinality inheritance is dangerous

A specialization cloned from an earlier exact-N operator may retain hard-coded counts, UIDs, hold exclusions, topology, or vector assumptions. Audit all specialization constants before registration. A count mismatch must fail closed before PLAN/APPLY.

If a defect is corrected after Stage B was already green, the corrected executable is a new certification subject. Any change to module/wrapper bytes, authorization logic, verifier, rollback logic, or registry binding invalidates the old Stage B verdict and any owner authorization tied to it. Re-enter Stage B, rerun the full same-path guard suite and PLAN, prove no-write state, and require a later fresh Stage C authorization.

## 18. Vector provenance may differ within one tranche

Do not assume every target shares one legacy vector family. Freeze vector hash/dimension and tracked metadata per row. Rollback must reconstruct each exact prior vector/metadata state without generating a fresh embedding.

## 19. Platform acknowledgement gates are not owner authorization

A write-capable registered entry may require platform acknowledgements even for a no-write guard action. A pre-execution refusal is a control-plane event, not semantic drift or a graph write. Prefer read-only PLAN/authorization companions. `execute`, `backup_confirmed`, and `yes_i_understand` never replace the separate exact owner-authorization artifact required for APPLY.

## 20. Stage C and Stage D must remain separate nudges

Stage C may perform immediate postwrite readback and regression to establish safe commit state, but independent Stage D verification belongs to the next user nudge. Do not collapse them merely because the immediate checks are green.

## 21. Final-denominator closure is not permission to start the next Rule family

After the last Stage D passes, freeze denominator closure and follow the explicit closeout next step. If a workflow/skill audit is required, perform that audit before Rule 7 or any other new graph work.


## 22. Neo4j nullable equality can reject a correct preimage

In Cypher, `NULL = NULL` does not evaluate true. Never use ordinary equality as the sole guard for nullable preimage fields such as owner/normalization metadata. Use explicit null-safe equality and test both null/value drift directions.

## 23. High-level guard parity does not prove APPLY eligibility

A guard/PLAN can be green while APPLY's actual atomic `MATCH`/`WHERE` rejects the row. Add a read-only eligibility probe that mirrors the complete APPLY predicate and require exact N/N eligibility before Stage C.

## 24. Started APPLY consumes the one-time authorization

Once an owner-authorized APPLY actually starts, treat that authorization as consumed even if exact recovery later proves `NOT_COMMITTED`. Never reuse it. A later attempt needs a new owner authorization; any executable or registry-binding change first requires fresh Stage B certification.

## 25. Topology hashes require canonicalizer identity

Two topology hashes produced by different canonicalization algorithms are not directly comparable. Freeze a canonicalizer ID/version with every governed topology fingerprint. Compare only like-for-like, or recompute under one declared canonicalizer.

## 26. Receipt phase/stage/campaign is part of the postimage

Do not verify a receipt only by migration ID, operation/version, status, verification, and hashes. Read back the declared `phase` and any stage/campaign identity. A wrong inherited phase is a governance defect even if the Rule postimage is correct.

## 27. Wrapper specialization can leak base receipt metadata

A thin wrapper may override operation/version/migration while delegated base APPLY code still hard-codes a prior campaign `phase` or other receipt field. Audit all receipt identity fields across wrapper and base code before Stage B closes, and ensure the verifier reads back what APPLY writes.

## 28. Stale-vector-only remediation is not text repair

When an external governed repair already made text source-faithful but the old vector remains, use a separate invalidation-only A/B/C/D lane. Do not rewrite clean text merely to clear the vector. Preserve text/source/full_text/topology and do not generate a fresh embedding.

## 29. Repealed controls are not denominator rows

Keep current/enacted parent denominator rows separate from repealed or obsolete temporal/identity controls. Do not count a negative control as a repair candidate, and do not infer current-law certification merely because the control is excluded.

## 30. Registration arguments are part of the executable contract

A registered write-capable operation may be refused before script execution if required control-plane arguments such as `migration_id` are missing, even for a no-write selftest action. Treat the refusal as no-write control-plane evidence. Correct the registry/CLI contract, and if executable or binding bytes change, recertify Stage B from scratch.
