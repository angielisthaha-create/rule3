# Rule batch manifest schema

Use `arc-rule-batch-v2` for every bounded ARC Rules 1-15 batch.

```json
{
  "schema_version": "arc-rule-batch-v2",
  "batch_id": "unique-id",
  "database": "neo4j",
  "rule_scope": ["7.1", "7.2"],
  "source_class": "secondary_commentary",
  "authority": {
    "source_build": true,
    "candidate_write": true,
    "production_promotion": false,
    "current_law_certification": false,
    "court_facing_release": false
  },
  "source_files": [
    {
      "path": "rule_7_1.txt",
      "sha256": "64-hex",
      "record_count": 1,
      "segment_count": 10,
      "span_count": 5
    }
  ],
  "candidate_families": [
    {
      "family": "deontic",
      "candidate_count": 2,
      "uids": ["uid-1", "uid-2"],
      "evidence_span_count": 2,
      "proposed_target_label": "DeonticOperator",
      "promotion_contract": "operator-plus-governed-proposition-plus-proof",
      "expected_metric_ids": ["GLOBAL-DEONTIC.DEONTIC_REASONING_WIRED"],
      "denominator_risk": "LOW",
      "expected_complete_count": 2
    }
  ],
  "stage_ledger": [
    {
      "stage_id": 0,
      "name": "scope_and_authority",
      "status": "CLOSED",
      "admission_artifact": "scope.json",
      "verification_artifact": "scope_verification.json"
    }
  ],
  "authorization": {
    "authorization_id": "one-time-id",
    "allowed_action": "create_promotion_packet",
    "candidate_uids": ["uid-1", "uid-2"],
    "issued": true,
    "consumed": false,
    "prohibited_actions": ["current_law_certification", "court_facing_release"]
  },
  "expected_graph_effects": {
    "nodes_created": 2,
    "relationships_created": 6,
    "production_labels": ["DeonticOperator"],
    "prohibited_labels": [],
    "no_change_invariants": []
  },
  "promotion_order": ["proofline", "proposition", "deontic"],
  "migration": {
    "migration_id": "unique-migration-id",
    "canary_uid": "uid-1",
    "rollback_defined": true,
    "rollback_path": "ROLLBACK.md",
    "expected_count": 2
  },
  "recovery_protocol": {
    "timeout_state": "UNKNOWN_UNTIL_CHECKED",
    "label_scoped_checks": true,
    "exact_uid_rollback": true,
    "unlabeled_uid_scan_prohibited": true
  },
  "appendix": {
    "previous_revision": "R4",
    "current_revision": "R5",
    "previous_metadata_dir": "path",
    "previous_conformance_dir": "path",
    "current_metadata_dir": "path",
    "current_conformance_dir": "path",
    "expected_metric_deltas": [],
    "figure_verification_required": true
  },
  "limitations": []
}
```

## Required stage IDs

The full lane uses stages 0 through 15 from `promotion-stage-playbook.md`. A manifest may show future stages as `PENDING`, but it must not omit them.

Valid status values:

- `PENDING`
- `ADMITTED`
- `IN_PROGRESS`
- `CLOSED`
- `CLOSED_WITH_LIMITATIONS`
- `BLOCKED`
- `ROLLED_BACK`

The validator checks deterministic closure facts only. It does not decide legal correctness or authorize promotion.
