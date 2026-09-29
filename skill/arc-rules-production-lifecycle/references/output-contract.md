# Output Contract

## Contents

- [Source-reconciliation closeout](#source-reconciliation-closeout)
- [Operator-build closeout](#operator-build-closeout)
- [Stage C APPLY closeout](#stage-c-apply-closeout)
- [Stage D independent-verification closeout](#stage-d-independent-verification-closeout)
- [Claim-safe phrases](#claim-safe-phrases)
- [Stale-vector-only invalidation closeout](#stale-vector-only-invalidation-closeout)
- [Receipt-metadata correction closeout](#receipt-metadata-correction-closeout)

## Source-reconciliation closeout

Report:

- `N<id> is complete. No Neo4j domain write and no embedding work occurred.`
- exact Rule list;
- candidate count and hold count, including valid zero-candidate/all-hold tranches;
- preserved source/full_text/invariants;
- any three-book gate result and external-repair holds;
- reconciliation artifact and SHA;
- closeout artifact and SHA;
- regression result;
- next nudge: pre-write operator build/falsification only, or the exact governed alternative if there are zero candidates.

## Operator-build closeout

Report:

- no domain write and no embedding generation;
- any control-plane files/registry changes separately from graph mutation;
- operator name/version and wrapper/specialization SHA;
- exact target count and excluded holds;
- guard result, including any discovered-and-fixed operator defect;
- PLAN result;
- unauthorized APPLY result;
- independent no-write readback;
- artifact path/SHA;
- next nudge: exact owner-authorized APPLY only.

## Stage C APPLY closeout

Report:

- exact applied count and UIDs;
- immediate text postimages match;
- source/full_text/topology unchanged;
- stale vector/meta absent;
- no fresh embeddings generated;
- receipt unique, hash-bound, and exact for `phase`/stage/campaign identity;
- immediate regression result;
- authorization/result/closeout artifact SHAs;
- state `TEXT_REPAIR_APPLIED_PENDING_INDEPENDENT_VERIFICATION`;
- next nudge: Stage D independent verification only.

Do not call the Stage C immediate readback independent Stage D verification.

## Stage D independent-verification closeout

Report:

- independent exact per-target postimages;
- source/full_text/topology invariants, with topology compared under the same canonicalizer ID/version;
- stale vector/meta absence and no fresh vectors;
- exact one receipt and all governing bindings, including `phase`/stage/campaign identity;
- higher-use gates false;
- fresh regression result;
- independent verification and closeout artifact SHAs;
- next nudge from the frozen campaign state.

If this closes the final denominator, state the completed Rule range explicitly and do not imply permission to start the next Rule family.

## Claim-safe phrases

Prefer:

- `source-reconciled repair candidate`
- `text repaired and stale vector invalidated`
- `fresh embedding not requested`
- `current-law certification remains open`
- `production/release/court-facing gates remain false`
- `historically accurate but stale corroborator snapshot`
- `already source-reconciled external repair hold`

Avoid unless separately proven:

- `current law`
- `production ready`
- `filing ready`
- `embedding repaired`
- `retrieval fully restored`


## Stale-vector-only invalidation closeout

Report:

- exact Rules whose text was already source-faithful;
- exact vector/metadata invalidation count;
- unchanged text/source/full_text/topology under the declared canonicalizer;
- no fresh embedding generation;
- unique invalidation receipt with exact phase/stage/campaign identity and bindings;
- Stage C immediate versus later Stage D status distinctly;
- state `STALE_VECTOR_INVALIDATED / FRESH_EMBEDDING_NOT_REQUESTED` after independent verification.

## Receipt-metadata correction closeout

Report separately from Rule remediation:

- exact target receipt and corrected metadata field/value;
- exact corrective receipt ID;
- preserved non-mutated target receipt properties;
- zero Rule-node/relationship/vector effects;
- Stage C immediate safety readback versus later independent Stage D;
- fresh regression result;
- any denominator/governance hold closed by the correction.
