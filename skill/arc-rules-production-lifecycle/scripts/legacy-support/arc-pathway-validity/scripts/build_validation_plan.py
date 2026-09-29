#!/usr/bin/env python3
"""Build a read-only ARC pathway validity run scaffold.

This script does not connect to Neo4j and does not perform writes. It creates a
manifest, query-plan skeleton, artifact placeholders, and a 100-turn manual
cadence plan for the ARC pathway validity workflow.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

TARGET_PARTS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "13", "14"]
EXCLUDED_PARTS = ["12"]
PENDING_PARTS = ["1"]
PARTS_REQUIRING_REPROBE = ["2", "3", "4", "6", "13", "14"]

ARC_LABELS = [
    "ARCRuleInterpretationIssue",
    "ARCProceduralPathway",
    "ARCAuthorityStatus",
    "ARCCasePathwayHolding",
    "ARCRuleConflictSignal",
    "ARCManualValidationTask",
    "ARCDiscardLedgerEntry",
]

ARC_RELS = [
    "HAS_INTERPRETIVE_ISSUE",
    "HAS_PATHWAY",
    "HAS_AUTHORITY_STATUS",
    "SUPPORTS_PATHWAY_HOLDING",
    "CITES_PATHWAY_HOLDING",
    "HAS_CONFLICT_SIGNAL",
    "HAS_MANUAL_VALIDATION_TASK",
    "HAS_DISCARD_LEDGER_ENTRY",
    "REFERENCES_COMPANION_RULE",
]

CYCLE_TARGETS = {
    1: "Parts 2, 3, 4",
    2: "Parts 5, 6, 7",
    3: "Parts 8, 9, 10",
    4: "Parts 11, 13, 14",
    5: "Cross-part reconciliation and resampling",
}

SLICE_NAMES = [
    "health_read_only_ledger_check",
    "target_unifiedrule_inventory",
    "part12_exclusion_check",
    "canonical_arc_label_inventory",
    "canonical_arc_relationship_inventory",
    "direct_pathway_traversal",
    "same_rule_anchor_check",
    "duplicate_unifiedrule_anchor_probe",
    "ruleprovision_hubrule_fallback_risk",
    "internal_unifiedrule_text_alignment_sample",
    "pathway_field_integrity_sample",
    "authority_status_and_a_rule_text_honesty",
    "phase_b_leakage_check",
    "manual_validation_task_classification",
    "discard_ledger_review",
    "companion_rule_quality_review",
    "expected_count_reconciliation_checkpoint",
    "special_part_rule_checkpoint",
    "manual_sample_queue_generation",
    "cycle_summary_promotion_matrix_update",
]

ARTIFACTS = [
    "query_ledger.jsonl",
    "scope_inventory.csv",
    "ontology_guard_result.json",
    "expected_count_reconciliation.csv",
    "duplicate_anchor_probe.csv",
    "stub_anchor_probe.csv",
    "part12_exclusion_check.json",
    "pathway_anchor_matrix.csv",
    "internal_unifiedrule_text_review.csv",
    "pathway_field_gaps.csv",
    "authority_status_gaps.csv",
    "phase_b_leakage_check.json",
    "manual_validation_task_matrix.csv",
    "discard_ledger_review.csv",
    "companion_rule_quality_review.csv",
    "part5_partial_queue.csv",
    "part9_partial_queue.csv",
    "part14_qa_quarantine.csv",
    "promotion_decisions.csv",
    "counsel_review_queue.csv",
    "summary.md",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_manifest(run_id: str) -> Dict[str, object]:
    return {
        "run_id": run_id,
        "created_utc": utc_now(),
        "mode": "read_only",
        "write_mode": "none",
        "source_of_truth": "Neo4j UnifiedRule corpus",
        "external_king_printer_check_required": False,
        "target_parts": TARGET_PARTS,
        "excluded_parts": EXCLUDED_PARTS,
        "pending_parts": PENDING_PARTS,
        "parts_requiring_duplicate_stub_reprobe": PARTS_REQUIRING_REPROBE,
        "phase": "Phase-A pathway validation; Phase-B holdings parked",
        "promotion_ceiling_without_phase_b": "Phase-A promoted candidate",
        "canonical_arc_labels": ARC_LABELS,
        "canonical_arc_relationships": ARC_RELS,
        "manual_cadence": {
            "count": 100,
            "interval_seconds": 240,
            "operator": "user_supplied_message_every_4_minutes",
        },
    }


def build_turn_plan(run_id: str) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for seq in range(1, 101):
        cycle = ((seq - 1) // 20) + 1
        position = ((seq - 1) % 20) + 1
        rows.append(
            {
                "run_id": run_id,
                "seq": seq,
                "count": 100,
                "cycle": cycle,
                "cycle_target": CYCLE_TARGETS[cycle],
                "position_in_cycle": position,
                "slice_name": SLICE_NAMES[position - 1],
                "mode": "read_only",
                "trigger_text": f"ARC_PATHWAY_VALIDITY_TEST seq={seq:03d}/100 run_id={run_id}",
            }
        )
    return rows


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an ARC pathway validity run scaffold.")
    parser.add_argument("--out-dir", default="out/arc_pathway_validity_run", help="Output directory")
    parser.add_argument("--run-id", default=None, help="Optional run id")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = args.run_id or "ARC_PATHWAY_VALIDITY_PARTS_2_11_13_14_SKIP_12"

    manifest = build_manifest(run_id)
    turn_plan = build_turn_plan(run_id)

    write_json(out_dir / "manifest.json", manifest)
    write_json(out_dir / "turn_plan.json", turn_plan)

    with (out_dir / "turn_plan.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(turn_plan[0].keys()))
        writer.writeheader()
        writer.writerows(turn_plan)

    for artifact in ARTIFACTS:
        path = out_dir / artifact
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            continue
        if artifact.endswith(".json"):
            path.write_text("{}\n", encoding="utf-8")
        elif artifact.endswith(".jsonl"):
            path.write_text("", encoding="utf-8")
        elif artifact.endswith(".csv"):
            path.write_text("status,notes\n", encoding="utf-8")
        elif artifact.endswith(".md"):
            path.write_text(f"# {artifact}\n\nRun ID: {run_id}\n", encoding="utf-8")

    print(json.dumps({"ok": True, "out_dir": str(out_dir), "run_id": run_id, "turns": 100}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
