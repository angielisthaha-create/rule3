#!/usr/bin/env python3
"""Validate a candidate-only ARC Phase-A worker handoff folder.

Usage:
  validate_worker_handoff.py <handoff_dir> [rule_slug]
"""
import json
import re
import sys
from pathlib import Path

REQUIRED_GLOBAL = ["expected_counts.json", "WORKER_RUN_LEDGER.json"]
REQUIRED_SUFFIXES = [
    "_canonical.json",
    "_write_nodes.cypher",
    "_write_rels.cypher",
    "_readback.cypher",
    "_rollback.cypher",
    "_self_check_report.json",
    "_paneA_promptbus_summary.md",
]
WRITE_KEYWORDS = re.compile(r"\b(CREATE|DELETE|DETACH|SET\s+[^\n]*=|MERGE)\b", re.I)


def load_json(path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def main():
    if len(sys.argv) < 2:
        print("usage: validate_worker_handoff.py <handoff_dir> [rule_slug]", file=sys.stderr)
        return 2
    root = Path(sys.argv[1])
    slug = sys.argv[2] if len(sys.argv) > 2 else None
    if not root.is_dir():
        print(f"FAIL: not a directory: {root}")
        return 1

    errors = []
    for name in REQUIRED_GLOBAL:
        if not (root / name).exists():
            errors.append(f"missing {name}")

    if slug:
        for suffix in REQUIRED_SUFFIXES:
            if not (root / f"{slug}{suffix}").exists():
                errors.append(f"missing {slug}{suffix}")
    else:
        for suffix in REQUIRED_SUFFIXES:
            if not list(root.glob(f"*{suffix}")):
                errors.append(f"missing file ending {suffix}")

    ledger_path = root / "WORKER_RUN_LEDGER.json"
    if ledger_path.exists():
        ledger = load_json(ledger_path)
        if ledger.get("graph_writes_performed") is not False:
            errors.append("WORKER_RUN_LEDGER graph_writes_performed is not false")
        checks = ledger.get("self_check_results", {})
        for key in [
            "no_executable_nonprimitive_properties",
            "no_dangling_relationship_endpoints",
            "no_placeholder_anchor_uids_in_match_clauses",
            "rollback_scoped_by_migration_id",
            "phase_b_excluded_from_phase_a_write_artifacts",
        ]:
            if checks.get(key) is not True:
                errors.append(f"self check not true: {key}")

    canonical_files = list(root.glob("*_canonical.json"))
    for path in canonical_files:
        data = load_json(path)
        safety = data.get("safety", {})
        if safety.get("graph_writes_performed") is not False:
            errors.append(f"{path.name} safety.graph_writes_performed is not false")
        if not data.get("migration_id"):
            errors.append(f"{path.name} missing migration_id")
        for rel in data.get("relationships", []):
            for key in ["source_label", "source_uid", "target_label", "target_uid", "type"]:
                if not rel.get(key):
                    errors.append(f"{path.name} relationship missing {key}")

    rollback_files = list(root.glob("*_rollback.cypher"))
    for path in rollback_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        if "migration_id" not in text:
            errors.append(f"{path.name} rollback lacks migration_id scope")

    if errors:
        print("FAIL: handoff validation errors")
        for err in errors:
            print(f"- {err}")
        return 1
    print("PASS: handoff folder meets structural no-write validation checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
