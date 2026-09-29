# Three-Book Source Gate

## Scope

Use this gate only when `three_book_mode` is `REQUIRED` or `OPTIONAL_CORROBORATION`.

- `REQUIRED`: all campaign-declared required carriers must close or the dependent source/text gate holds.
- `OPTIONAL_CORROBORATION`: use available carriers adversarially; absence alone does not block independently sufficient source closure.
- `NOT_APPLICABLE`: do not invent three-book requirements.

## Do not assume the books' evidentiary roles

Before assigning Book A/B/C weight, freeze a source registry for each actual artifact:

- `book_id` / carrier ID;
- title/edition/version/date where known;
- file/artifact identity and SHA-256;
- `source_role`: `FIRST_HAND_RULE_CARRIER`, `OFFICIAL_REPRODUCTION`, `ANNOTATED_RULES`, `SECONDARY_COMMENTARY`, `DERIVED_COPY`, or `UNKNOWN`;
- `origin_id` and `derived_from` lineage where known;
- extraction/OCR/transcription method and version where material;
- permitted use: operative-text reconciliation, corroboration, interpretation seed, or commentary only.

If a required carrier's role or identity is materially unknown, hold rather than guessing.

## Book roles inside a declared campaign

- **Book A** is the campaign's declared first-hand reconciliation anchor only when its registry entry supports that role.
- **Book B/C** are corroborating/adversarial carriers according to their registry roles.
- **Official Alberta source** is a separate authority for official version/current-to closure when required.

Book B/C do not outvote Book A. Book A does not override a proved extraction defect. Three carriers derived from one origin are not three independent corroborators.

## Required gate record

For every Rule/subrule/version under a required gate, freeze:

- exact Rule/subrule target identity;
- `three_book_mode`;
- required carrier IDs;
- source-registry SHA-256;
- normalization profile ID/version/SHA-256;
- for A/B/C: artifact SHA-256, exact locator/span, extracted text SHA-256, version/consolidation evidence, origin/derivation identity, source role;
- version-identity result;
- pairwise wording comparison result;
- discrepancy class and resolution evidence;
- exact gate result and gate artifact SHA-256.

## Version identity precedes wording comparison

Use only:

- `SAME_VERSION_PROVEN`
- `LEGITIMATE_VERSION_DIFFERENCE`
- `VERSION_IDENTITY_UNRESOLVED`

Do not close a substantive wording comparison when version identity is unresolved. `VERSION_IDENTITY_UNRESOLVED` is a hold.

## Reconciliation order

1. Bind carrier identities, roles, origins, hashes, and required/optional status.
2. Establish Rule/subrule identity and version identity.
3. Apply only the frozen normalization profile for comparison; preserve raw bytes/text separately.
4. Compare A/B/C pairwise only when legally comparable.
5. Classify exact match, permitted normalization-only difference, extraction/OCR defect, provision-boundary bleed, commentary/UI contamination, stale snapshot, legitimate version difference, or unresolved conflict.
6. Re-read current live Neo4j state before freezing a text-repair candidate.
7. Reconcile external repairs using exact migration/receipt evidence and current postimage.
8. If Book A is defective, independently close operative wording through the campaign's allowed corroborating/official source; preserve the defective carrier as provenance.
9. If a required carrier is missing, materially incomplete, unverifiable, or version-incomparable, hold.

## Prohibited shortcuts

- majority vote;
- silent text merge/concatenation;
- treating cleaner wording as authoritative without source closure;
- using an undocumented normalization;
- counting copies/derived carriers as independent corroboration;
- treating version differences as corruption;
- replaying stale corroborator findings after a verified external repair;
- treating three-book agreement as current-law certification.

Validate gate artifacts with `scripts/validate_three_book_gate.py` before using their result downstream.
