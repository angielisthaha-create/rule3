# Workflow State Machine

## Contents

- Purpose
- Canonical states
- One-nudge rule
- Resume precedence
- Concurrency rebase
- Batch order
- Final remainder

## Purpose

Use this file to resume an active ARC Rule production-text campaign without collapsing stages, replaying stale corroborator state, or accidentally performing two nudges at once.

## Canonical states

### Source stage

`TEXT_TRANCHE_SELECTED_READ_ONLY`

-> source comparison + required corroborator closure ->

`TEXT_REPAIR_CANDIDATES_SOURCE_RECONCILED_PREWRITE`

Possible alternatives:

- `TEXT_RECONCILIATION_HOLD`
- `TEXT_RECONCILIATION_REBASED_EXTERNAL_REPAIR_HOLD`

### Operator stage

`TEXT_REPAIR_OPERATOR_BUILDING_NO_DOMAIN_WRITE`

-> exact-N specialization/receipt-identity audit + null-safe preimage guards + mirrored atomic-preimage eligibility + positive/negative guard closure + PLAN + unauthorized APPLY proof ->

`TEXT_REPAIR_OPERATOR_REGISTERED_AND_FALSIFICATION_GREEN_NO_DOMAIN_WRITE`

Possible alternative:

`TEXT_REPAIR_OPERATOR_BLOCKED`

If the executable module/wrapper, authorization logic, verifier, rollback logic, receipt-identity specialization, or registry binding changes after a green Stage B verdict, invalidate that verdict and return to `TEXT_REPAIR_OPERATOR_BUILDING_NO_DOMAIN_WRITE`. Fresh Stage-B recertification must complete before any Stage C authorization or APPLY.

### Apply stage

`OWNER_AUTHORIZATION_BOUND_TO_FROZEN_SCOPE`

-> fresh preimage read + rerun guards/PLAN -> single APPLY -> immediate safety readback/regression ->

`TEXT_REPAIR_APPLIED_PENDING_INDEPENDENT_VERIFICATION`

If tool state is uncertain:

`WRITE_COMMIT_STATE_UNKNOWN_DO_NOT_RETRY`

A platform/registry refusal before script execution is not this state. Record it as a control-plane refusal and use the approved action-specific path without weakening guards. If the refusal reveals a missing required registry argument or stale executable binding, correct the control plane, treat changed executable identity as a new Stage-B certification subject when applicable, and rerun certification.

Once an owner-authorized APPLY actually starts, its authorization becomes consumed even if recovery later proves `NOT_COMMITTED`. A retry always needs a fresh authorization; executable/registry changes additionally require fresh Stage B.

### Verification stage

`TEXT_REPAIR_APPLIED_PENDING_INDEPENDENT_VERIFICATION`

-> independent exact readback + receipt verification including phase/stage/campaign identity + topology comparison under the same canonicalizer ID/version + regression ->

`TEXT_REPAIR_AND_STALE_VECTOR_INVALIDATION_APPLIED_AND_INDEPENDENTLY_VERIFIED`

Preferred lane substate:

`TEXT_REPAIRED / STALE_VECTOR_INVALIDATED / FRESH_EMBEDDING_NOT_REQUESTED`


### Stale-vector-only invalidation lane

Use parallel states when text is already source-faithful but stale vector/metadata remains:

`STALE_VECTOR_INVALIDATION_SOURCE_RECONCILED_PREWRITE`

-> exact-N invalidation operator + null-safe/mirrored eligibility certification ->

`STALE_VECTOR_INVALIDATION_OPERATOR_GREEN_NO_DOMAIN_WRITE`

-> separately authorized invalidation-only APPLY + immediate safety readback ->

`STALE_VECTOR_INVALIDATED_PENDING_INDEPENDENT_VERIFICATION`

-> later read-only Stage D ->

`STALE_VECTOR_INVALIDATION_INDEPENDENTLY_VERIFIED_FRESH_EMBEDDING_NOT_REQUESTED`

Never use a text-repair state label when `UnifiedRule.text` was not mutated.

### Receipt-metadata remediation lane

A receipt identity defect discovered after otherwise-correct domain verification is a separate governed lane:

`RECEIPT_METADATA_DEFECT_HELD`

-> exact receipt preimage + exact-one operator Stage B ->

`RECEIPT_METADATA_REPAIR_OPERATOR_GREEN_NO_DOMAIN_WRITE`

-> fresh owner-authorized exact metadata correction plus separate corrective receipt ->

`RECEIPT_METADATA_REPAIR_APPLIED_PENDING_INDEPENDENT_VERIFICATION`

-> later read-only Stage D ->

`RECEIPT_METADATA_REPAIR_INDEPENDENTLY_VERIFIED`

Do not mutate Rule nodes or silently rewrite the historical receipt without a corrective audit trail.

### Denominator closure

If Stage D closes the final frozen remainder, first distinguish the enacted/current parent denominator from repealed or obsolete negative controls. Negative controls remain separately frozen and do not count as repair candidates.

`RULE_FAMILY_TEXT_REMEDIATION_DENOMINATOR_CLOSED`

Follow the exact frozen closeout. If it calls for workflow/skill review:

`POST_DENOMINATOR_SKILL_AUDIT_REQUIRED`

Do not automatically select the next Rule family.

## One-nudge rule

A user instruction `proceed with next batch/steps` advances one state transition only.

Examples:

- after source reconciliation, perform operator build/falsification only;
- after operator build, consume the new `proceed` as one-time owner authorization for that exact frozen APPLY scope only;
- after APPLY, perform Stage D independent verification only;
- after final Stage D, perform the frozen post-denominator next step only.

Immediate Stage C safety readback/regression does not consume Stage D. Stage C and Stage D are always separate nudges.

## Resume precedence

Use the following precedence:

1. latest verified closeout artifact;
2. exact graph state/readback;
3. frozen manifest/packet/receipt hashes;
4. required corroborator artifacts and external-repair receipts;
5. chat summary/history.

If chat, artifacts, corroborators, or current graph state disagree, stop and reconcile before writing.

## Concurrency rebase

If another governed lane repairs a candidate after an earlier Book B/C snapshot or Stage A observation:

- verify the external receipt and current live postimage against Book A;
- convert the row to `HOLD_ALREADY_SOURCE_RECONCILED_EXTERNAL_REPAIR` when source-faithful;
- if Stage B was not yet frozen, rebuild the exact target set and hashes;
- if Stage B was already frozen, HOLD Stage C and recertify rather than mutating the frozen packet.

## Batch order

Preserve the parent cohort's frozen order. Do not sort numerically unless the parent manifest itself uses numeric order.

Record an ordered `name+uid` hash for every tranche.

## Final remainder

Use the established campaign batch size until the final remainder. Do not pad a final remainder with already-completed or out-of-cohort Rules.
