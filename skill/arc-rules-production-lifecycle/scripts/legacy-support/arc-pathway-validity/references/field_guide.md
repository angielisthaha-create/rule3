# ARC Procedural Pathway Validity Field Guide

## Purpose

Validate the LexGraph ARC Procedural Pathway layer for Alberta Rules of Court Parts 2-11, 13, and 14 while excluding Part 12. The workflow classifies each pathway by present reliability level; it does not certify matter-specific legal use.

## Source of truth

Use the current Neo4j `UnifiedRule` corpus as the rule-text source of truth. Do not require external King's Printer verification during this workflow when the latest rules are already in Neo4j.

Required trace:

```text
ARCProceduralPathway
-> resolved_rule_number / rule_number / rule / subrule
-> canonical UnifiedRule
-> current internal UnifiedRule text
-> pathway trigger / condition / answer / remedy
```

Historical sources such as King's Printer verification outputs, ARC.txt, markdown packages, write ledgers, and worker handoffs remain provenance records, not the acceptance authority for this run.

## Scope

In scope: Parts 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, and 14.

Excluded: Part 12. Part 12 may have `UnifiedRule` nodes; it should not be validated or promoted as pathway coverage.

Pending: Part 1. Foundational dependencies such as Rules 1.2, 1.5, and 1.7 fall back to internal `UnifiedRule` text unless Part 1 has separately landed.

## Key distinctions

- Say “Parts 2-11, 13, and 14,” not “rules 2-14,” unless quoting a user.
- A graph-valid candidate is not filing-ready law.
- `A_rule_text` means rule-text support only, not case authority.
- Phase-B case holdings require public paragraph pins, citator/current-status clearance, and counsel validation.

## Validation levels

| Level | Label | Meaning |
|---|---|---|
| 0 | Inventory-only | Node exists, but correct anchor and source alignment are not proven. |
| 1 | Structurally valid | Canonical label, relationship, migration, candidate-only status, and correct `UnifiedRule` anchor are proven. |
| 2 | Source-valid against Neo4j | Pathway aligns with current internal `UnifiedRule` text. |
| 3 | Counsel-review ready | Formulation is clear, no blocker tasks remain, confidence is adequate. |
| 4 | Phase-A promoted candidate | Human-approved as a candidate pathway, still not case-backed. |
| 5 | Phase-B authority-backed | Public paragraph pin, citator/current-status check, and case holding are complete. |
| 6 | Matter-use ready | A lawyer applies the pathway to specific facts. |

Without Phase B, the promotion ceiling is Level 4.

## Special part rules

### Part 5

Treat Part 5 as partial. Report separately on structural pathway coverage, conflict-signal coverage, blocker queue, pin-hold queue, and Phase-B holding queue.

### Part 9

Treat Part 9 as partial if interpretive issues remain unformulated or holdings remain parked. Pathway rows may be structurally valid while issue coverage remains incomplete.

### Part 14

Quarantine Part 14 for QA until low/medium confidence rows, meta-wiring nodes, and anchor repairs are reviewed. Do not promote Part 14 on traversal counts alone.

## Required ontology guard

Confirm:

```text
7 ARC content labels + ARCWriteCandidate marker = label_count 8
9 canonical ARC relationship types = relationship_count 9
LegalConcept collision count = 0
```

Canonical content labels:

```text
ARCRuleInterpretationIssue
ARCProceduralPathway
ARCAuthorityStatus
ARCCasePathwayHolding
ARCRuleConflictSignal
ARCManualValidationTask
ARCDiscardLedgerEntry
```

Canonical relationship types:

```text
HAS_INTERPRETIVE_ISSUE
HAS_PATHWAY
HAS_AUTHORITY_STATUS
SUPPORTS_PATHWAY_HOLDING
CITES_PATHWAY_HOLDING
HAS_CONFLICT_SIGNAL
HAS_MANUAL_VALIDATION_TASK
HAS_DISCARD_LEDGER_ENTRY
REFERENCES_COMPANION_RULE
```

Run or reproduce `scripts/validate_arc_shared_ontology_registry_guard.py` when available.

## Required artifact reconciliation

Do not rely on graph counts alone. Reconcile live graph against worker/governance artifacts, including:

```text
paneA_part2_canonical_ontology_crosswalk_20260622.json
config/arc_shared_ontology_schema_registry_20260622.json
scripts/validate_arc_shared_ontology_registry_guard.py
arc_part2_rule_level_run/paneA_prewrite/ARC_WRITE_EXECUTOR_HANDOFF_to_PaneD.md
paneA_write_part.py
per-part WORKER_HANDOFF_RULE<n>_PHASE_A/
*_write_result*.json
rollback artifacts
WORKER_RUN_LEDGER.json
deep/rule_*/*_neo4j_grounded_authorities.tsv
```

For each part, reconcile expected node count, expected relationship count, actual live ARCWriteCandidate count, actual live canonical relationship count, anchored-to-UnifiedRule count, discrepancy reason, and promotion status.

Accept discrepancies only if documented as parked, held, rejected, partial, manual-validation pending, or Phase-B pending.

## Safety warnings

Default mode is read-only. Do not perform writes, deletes, schema changes, embedding writes, relationship conversions, domain remediation, or repair execution.

Prohibited query operations include:

```text
CREATE
MERGE
SET
DELETE
DETACH DELETE
REMOVE
DROP
LOAD CSV
CALL dbms
CALL apoc.periodic
CALL apoc.create
CREATE INDEX
CREATE CONSTRAINT
```

If a write-capable owner session exists, it does not itself authorize this validation run to write.

## Timeout and high-volume rules

Every query plan must target less than 80 seconds. Use 75 seconds for local runner calls where configurable.

After a timeout: record query shape, mark failed/timed out, do not count it, do not retry the same shape, and narrow to exact labels, exact UIDs, aggregate counts, saved suites, or smaller batches.

Default timeout attribution:

```text
timeout_due_to_query_planning_or_payload_size
```

High-call-count completion requires:

```text
target_calls == successful_calls
failed_calls == 0
timeout_calls == 0
call_count_satisfied == true
```

## Run manifest template

```json
{
  "run_id": "ARC_PATHWAY_VALIDITY_PARTS_2_11_13_14_SKIP_12",
  "mode": "read_only",
  "write_mode": "none",
  "source_of_truth": "Neo4j UnifiedRule corpus",
  "external_king_printer_check_required": false,
  "target_parts": ["2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "13", "14"],
  "excluded_parts": ["12"],
  "pending_parts": ["1"],
  "phase": "Phase-A pathway validation; Phase-B holdings parked",
  "promotion_ceiling_without_phase_b": "Phase-A promoted candidate"
}
```

## Output artifacts

Each run should produce:

```text
manifest.json
query_ledger.jsonl
scope_inventory.csv
ontology_guard_result.json
expected_count_reconciliation.csv
duplicate_anchor_probe.csv
stub_anchor_probe.csv
part12_exclusion_check.json
pathway_anchor_matrix.csv
internal_unifiedrule_text_review.csv
pathway_field_gaps.csv
authority_status_gaps.csv
phase_b_leakage_check.json
manual_validation_task_matrix.csv
discard_ledger_review.csv
companion_rule_quality_review.csv
part5_partial_queue.csv
part9_partial_queue.csv
part14_qa_quarantine.csv
promotion_decisions.csv
counsel_review_queue.csv
summary.md
```

## Promotion labels

### Red

Use Red for no canonical `UnifiedRule` anchor, wrong rule/part anchor, unresolved duplicate/stub, noncanonical label or relationship, missing UID, missing migration ID, non-candidate write status, unsupported case-authority implication, contradiction with internal `UnifiedRule` text, or unresolved blocker.

### Amber

Use Amber for missing but honestly pending authority status, low/medium confidence, unresolved non-blocker manual validation task, conflict signal, companion-rule dependency requiring review, plausible but unconfirmed internal text alignment, partial Part 5/Part 9 status, or Part 14 QA quarantine.

### Green

Use Green for structurally valid Phase-A candidates: in-scope, not Part 12, correct canonical `UnifiedRule` anchor, no duplicate/stub issue, canonical labels/relationships, candidate-only status, migration/rollback metadata, internal rule-text alignment, substantive pathway formulation, honest authority status, no unresolved blocker, and reconciled expected counts.

### Blue

Use Blue only after Phase-B authority backing exists: `ARCCasePathwayHolding`, public paragraph pin, citator/current-status pass, and counsel validation. Blue should normally be unavailable in the current Phase-A state.

## Summary rule

Do not merely ask whether a pathway node exists. Ask whether it is correctly anchored to the current internal `UnifiedRule`, expressed through the canonical ARC ontology, consistent with internal rule text, honestly graded as Phase-A or Phase-B, free of unresolved blocker tasks, reconciled against expected counts, and safe to promote only to the level actually supported.
