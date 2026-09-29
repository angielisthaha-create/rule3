# Legacy ARC Requalification

Use when existing ARC graph objects were created under a predecessor workflow and a changed source/semantic/retrieval rule may affect them.

Do not automatically grandfather or automatically rebuild.

For each exact object/cohort, freeze:

- producing migration/workflow/version where available;
- source/proof fingerprints;
- current labels/relationships/release/retrieval state;
- changed governing rule and compatibility disposition;
- dependency impact.

Classify:

- `PRESERVED` - new rule cannot affect the settled predicate and fingerprints remain valid;
- `REQUALIFICATION_REQUIRED` - material predicate may change and bounded re-review is possible;
- `QUARANTINED` - retrieval/use must be blocked pending evidence repair;
- `HOLD_IDENTITY_OR_PROVENANCE` - producing source/workflow cannot be responsibly resolved.

Every mutation remains bounded and reversible through `whitebox-neo4j-operator`.
