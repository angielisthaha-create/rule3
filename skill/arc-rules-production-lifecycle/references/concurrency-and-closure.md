# Three-Book Concurrency and Campaign Closure

## Three-book source gate

When a campaign declares Book A/B/C closure as mandatory:

- Treat Book A first-hand source as the primary source-reconciliation evidence.
- Treat Book B and Book C as corroborating/adversarial evidence, not substitutes for Book A.
- Do not close Stage A while a required Book B/C artifact is missing or materially incomplete.
- Bind the exact corroborator artifact paths and SHA-256 values into the reconciliation or three-book gate artifact.

## Stale corroborator snapshots

Book B/C may describe a live defect that was accurate when inspected but was repaired by another governed lane before the current Stage A read.

Do not call this a substantive conflict automatically. Reconcile the timeline:

1. re-read the current exact Rule by governed UID;
2. read the external repair migration/receipt;
3. verify receipt status and exact readback state;
4. compare the current live operative body against Book A;
5. if the current row is source-faithful, classify `HOLD_ALREADY_SOURCE_RECONCILED_EXTERNAL_REPAIR` and exclude it from the next operator;
6. preserve the historical Book B/C finding as stale-but-valid provenance.

If the receipt is missing, ambiguous, or the live postimage does not close against Book A, hold instead of inferring a repair.

## Concurrent repair rebasing

Every Stage A and Stage C preflight is a fresh read, not a replay of an older candidate list.

If another lane repaired a candidate between stages:

- never overwrite merely to preserve the old tranche count;
- shrink/rebase the exact target set and freeze a new ordered hash/topology/packet if still in Stage A/B;
- if an already-frozen Stage B packet drifts before Stage C, HOLD and recertify rather than editing the frozen packet in place;
- record which external migration caused the rebase.

## Carrier identity

Some `UnifiedRule` nodes may not expose every convenience property consistently. A zero-row lookup using `rule`, citation-like text, or another optional property does not prove absence.

Use the frozen canonical UID/name path first. Treat carrier-shape mismatch as an identity lookup issue, not a substantive source result.

## Source-carrier defects

A first-hand OCR/TXT carrier can itself contain duplication or extraction artifacts. Do not automatically copy a known defective byte sequence into `UnifiedRule.text`.

Require an explicit discrepancy record and independently close the operative wording through the campaign's declared corroborating or official source. Preserve the distinction between:

- defective source carrier bytes;
- source-faithful operative Rule wording;
- current-law/version certification.

## Denominator closure

After Stage D verifies the final remainder:

- freeze the enacted/current-parent denominator independently from repealed, obsolete, or otherwise excluded negative controls;
- freeze each negative control's exact UID and exclusion reason without treating it as a repair candidate;
- freeze a denominator-closure statement and exact completed range;
- keep temporal/current-law/release/court-facing holds unchanged; negative-control exclusion is not current-law certification;
- do not pad the denominator or automatically start the next Rule family;
- follow the closeout's exact next nudge;
- if the campaign calls for a skill/workflow audit, invoke `skill-creator` before further Rule processing.
