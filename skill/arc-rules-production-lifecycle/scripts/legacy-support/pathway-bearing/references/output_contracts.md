# Output Contracts

## Canonical JSON shape

A canonical handoff JSON should include:

```json
{
  "artifact_type": "arc_phase_a_worker_handoff",
  "rule_slug": "rule5",
  "target_scope": "Rule 5 / Part 5",
  "migration_id": "ARC_RULE5_PHASE_A_<date>",
  "safety": {
    "candidate_only": true,
    "graph_writes_performed": false,
    "filing_ready": false
  },
  "source_artifacts": [],
  "nodes": [],
  "relationships": [],
  "phase_b_parked": [],
  "manual_validation": []
}
```

Each node should include `uid`, `labels`, and `properties`. Each relationship should include `type`, `source_label`, `source_uid`, `target_label`, `target_uid`, and `properties`.

## Expected counts

`expected_counts.json` should include:

```json
{
  "migration_id": "...",
  "node_counts_by_label": {},
  "relationship_counts_by_type": {},
  "phase_b_parked_count": 0,
  "skipped_count": 0,
  "manual_validation_count": 0
}
```

## Worker run ledger

`WORKER_RUN_LEDGER.json` should include source paths, target scope, phases complete, counts, anchor repairs, anchor skips, self-check results, generated files, and no-write confirmation.

## PromptBus summary

Keep summaries short:

```markdown
# Pane A PromptBus Summary - <rule_slug>

Artifact path: `<path>`
Migration ID: `<migration_id>`
No-write confirmation: true
Phase A nodes: <n>
Phase A relationships: <n>
Phase B parked case holdings: <n>
Anchor skips: <n>
Self-check: pass/fail
Caveats: ...
```
