# Text Remediation Control Plane

Use this reference with the preserved remediation packet/state-machine/failure-mode references.

## Scope

Text remediation corrects exact `UnifiedRule.text`, stale vector/embedding metadata, or receipt metadata. It does not authorize semantic promotion, current-law certification, retrieval release, or embedding regeneration.

## A/B/C/D separation

- A: source reconcile and freeze exact candidates/holds.
- B: build and falsify exact-N operator; no domain write.
- C: exact bounded APPLY plus immediate safety readback only.
- D: later independent verification.

Stage C and D are separate nudges. If executable bytes, wrapper, verifier, rollback logic, authorization logic, or registry binding changes after B, recertify B.

## Mandatory G4 safeguards

- **G4F footprint equality**: APPLY and rollback cover the same exact target identities/properties.
- **G4H payload binding**: executed payload hash equals the reviewed payload hash.
- **G4L operation-enforced batch bound**: the operation itself rejects N+1.
- **G4D verifier discrimination**: the same guard path accepts a known-good packet and rejects known-bad controls.

## Additional hardening

Require exact preimage, null-safe equality for nullable properties, mirrored atomic-preimage eligibility, topology hash plus canonicalizer ID/version, source-reconciliation binding, rollback preimage, exact receipt identity, and independent no-write readback after authorization-gate probes.

Standing owner/tool authority is not evidence that a particular packet is correct. Preserve the exact operation-bound authorization/receipt artifact required by the campaign contract without asking for redundant conversational permission.
