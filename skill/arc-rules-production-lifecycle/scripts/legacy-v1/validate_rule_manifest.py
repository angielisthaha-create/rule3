#!/usr/bin/env python3
"""Validate a bounded ARC Rules 1-15 batch manifest and promotion-stage ledger.

This checks deterministic closure and governance fields only. It does not certify
legal meaning, authorize promotion, or verify Neo4j state.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
VALID_STAGE_STATUSES = {
    "PENDING",
    "ADMITTED",
    "IN_PROGRESS",
    "CLOSED",
    "CLOSED_WITH_LIMITATIONS",
    "BLOCKED",
    "ROLLED_BACK",
}
REQUIRED_STAGE_IDS = set(range(16))
REQUIRED_TOP = {
    "schema_version",
    "batch_id",
    "database",
    "rule_scope",
    "source_class",
    "authority",
    "source_files",
    "candidate_families",
    "stage_ledger",
    "authorization",
    "expected_graph_effects",
    "promotion_order",
    "migration",
    "recovery_protocol",
    "appendix",
    "limitations",
}


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_TOP - set(payload))
    add(errors, not missing, f"Missing top-level fields: {missing}")
    add(errors, payload.get("schema_version") == "arc-rule-batch-v2", "schema_version must be arc-rule-batch-v2")
    add(errors, nonempty_string(payload.get("batch_id")), "batch_id must be nonempty")
    add(errors, nonempty_string(payload.get("database")), "database must be nonempty")
    add(errors, isinstance(payload.get("rule_scope"), list) and bool(payload.get("rule_scope")), "rule_scope must be a nonempty list")
    for index, value in enumerate(payload.get("rule_scope", []) if isinstance(payload.get("rule_scope"), list) else []):
        add(errors, nonempty_string(value), f"rule_scope[{index}] must be nonempty")

    authority = payload.get("authority", {})
    required_authority = {
        "source_build",
        "candidate_write",
        "production_promotion",
        "current_law_certification",
        "court_facing_release",
    }
    add(errors, isinstance(authority, dict), "authority must be an object")
    if isinstance(authority, dict):
        add(errors, not (required_authority - set(authority)), f"authority missing fields: {sorted(required_authority - set(authority))}")
        for field in required_authority:
            add(errors, isinstance(authority.get(field), bool), f"authority.{field} must be boolean")

    source_files = payload.get("source_files", [])
    add(errors, isinstance(source_files, list) and bool(source_files), "source_files must be a nonempty list")
    source_paths: set[str] = set()
    for index, row in enumerate(source_files if isinstance(source_files, list) else []):
        prefix = f"source_files[{index}]"
        add(errors, isinstance(row, dict), f"{prefix} must be an object")
        if not isinstance(row, dict):
            continue
        path = row.get("path")
        add(errors, nonempty_string(path), f"{prefix}.path must be nonempty")
        if isinstance(path, str):
            add(errors, path not in source_paths, f"Duplicate source path: {path}")
            source_paths.add(path)
        add(errors, bool(SHA256_RE.match(str(row.get("sha256", "")))), f"{prefix}.sha256 must be 64 hex characters")
        for field in ("record_count", "segment_count", "span_count"):
            add(errors, isinstance(row.get(field), int) and row[field] >= 0, f"{prefix}.{field} must be a nonnegative integer")

    families = payload.get("candidate_families", [])
    add(errors, isinstance(families, list), "candidate_families must be a list")
    all_uids: set[str] = set()
    family_names: set[str] = set()
    total_candidates = 0
    for index, row in enumerate(families if isinstance(families, list) else []):
        prefix = f"candidate_families[{index}]"
        add(errors, isinstance(row, dict), f"{prefix} must be an object")
        if not isinstance(row, dict):
            continue
        family = row.get("family")
        add(errors, nonempty_string(family), f"{prefix}.family must be nonempty")
        if isinstance(family, str):
            add(errors, family not in family_names, f"Duplicate family: {family}")
            family_names.add(family)
        count = row.get("candidate_count")
        uids = row.get("uids")
        add(errors, isinstance(count, int) and count >= 0, f"{prefix}.candidate_count must be nonnegative")
        add(errors, isinstance(uids, list), f"{prefix}.uids must be a list")
        if isinstance(count, int):
            total_candidates += count
        if isinstance(count, int) and isinstance(uids, list):
            add(errors, count == len(uids), f"{prefix}.candidate_count does not match UID count")
        for uid in uids if isinstance(uids, list) else []:
            add(errors, nonempty_string(uid), f"{prefix} contains an empty/non-string UID")
            if isinstance(uid, str):
                add(errors, uid not in all_uids, f"Duplicate candidate UID across families: {uid}")
                all_uids.add(uid)
        add(errors, isinstance(row.get("evidence_span_count"), int) and row["evidence_span_count"] >= 0, f"{prefix}.evidence_span_count must be nonnegative")
        add(errors, nonempty_string(row.get("proposed_target_label")), f"{prefix}.proposed_target_label must be nonempty")
        add(errors, nonempty_string(row.get("promotion_contract")), f"{prefix}.promotion_contract must be nonempty")
        add(errors, isinstance(row.get("expected_metric_ids"), list), f"{prefix}.expected_metric_ids must be a list")
        add(errors, row.get("denominator_risk") in {"LOW", "MEDIUM", "HIGH", "NOT_APPLICABLE"}, f"{prefix}.denominator_risk is invalid")
        expected_complete = row.get("expected_complete_count")
        add(errors, isinstance(expected_complete, int) and expected_complete >= 0, f"{prefix}.expected_complete_count must be nonnegative")
        if isinstance(count, int) and isinstance(expected_complete, int):
            add(errors, expected_complete <= count, f"{prefix}.expected_complete_count exceeds candidate_count")

    stages = payload.get("stage_ledger", [])
    add(errors, isinstance(stages, list) and bool(stages), "stage_ledger must be a nonempty list")
    stage_ids: set[int] = set()
    for index, row in enumerate(stages if isinstance(stages, list) else []):
        prefix = f"stage_ledger[{index}]"
        add(errors, isinstance(row, dict), f"{prefix} must be an object")
        if not isinstance(row, dict):
            continue
        stage_id = row.get("stage_id")
        add(errors, isinstance(stage_id, int) and stage_id in REQUIRED_STAGE_IDS, f"{prefix}.stage_id must be 0..15")
        if isinstance(stage_id, int):
            add(errors, stage_id not in stage_ids, f"Duplicate stage_id: {stage_id}")
            stage_ids.add(stage_id)
        add(errors, nonempty_string(row.get("name")), f"{prefix}.name must be nonempty")
        add(errors, row.get("status") in VALID_STAGE_STATUSES, f"{prefix}.status is invalid")
        if row.get("status") in {"CLOSED", "CLOSED_WITH_LIMITATIONS", "ROLLED_BACK"}:
            add(errors, nonempty_string(row.get("verification_artifact")), f"{prefix}.verification_artifact required for terminal status")
    add(errors, stage_ids == REQUIRED_STAGE_IDS, f"stage_ledger must contain every stage 0..15; missing={sorted(REQUIRED_STAGE_IDS - stage_ids)} extra={sorted(stage_ids - REQUIRED_STAGE_IDS)}")

    authorization = payload.get("authorization", {})
    add(errors, isinstance(authorization, dict), "authorization must be an object")
    if isinstance(authorization, dict):
        add(errors, nonempty_string(authorization.get("authorization_id")), "authorization.authorization_id must be nonempty")
        add(errors, nonempty_string(authorization.get("allowed_action")), "authorization.allowed_action must be nonempty")
        add(errors, isinstance(authorization.get("candidate_uids"), list), "authorization.candidate_uids must be a list")
        if isinstance(authorization.get("candidate_uids"), list):
            auth_uids = authorization["candidate_uids"]
            add(errors, len(auth_uids) == len(set(auth_uids)), "authorization.candidate_uids contains duplicates")
            add(errors, set(auth_uids).issubset(all_uids), "authorization.candidate_uids must be a subset of candidate UIDs")
        add(errors, isinstance(authorization.get("issued"), bool), "authorization.issued must be boolean")
        add(errors, isinstance(authorization.get("consumed"), bool), "authorization.consumed must be boolean")
        add(errors, isinstance(authorization.get("prohibited_actions"), list), "authorization.prohibited_actions must be a list")

    graph_effects = payload.get("expected_graph_effects", {})
    add(errors, isinstance(graph_effects, dict), "expected_graph_effects must be an object")
    if isinstance(graph_effects, dict):
        for field in ("nodes_created", "relationships_created"):
            add(errors, isinstance(graph_effects.get(field), int) and graph_effects[field] >= 0, f"expected_graph_effects.{field} must be nonnegative")
        for field in ("production_labels", "prohibited_labels", "no_change_invariants"):
            add(errors, isinstance(graph_effects.get(field), list), f"expected_graph_effects.{field} must be a list")

    promotion_order = payload.get("promotion_order")
    add(errors, isinstance(promotion_order, list) and bool(promotion_order), "promotion_order must be a nonempty list")
    if isinstance(promotion_order, list):
        add(errors, all(nonempty_string(value) for value in promotion_order), "promotion_order values must be nonempty strings")
        add(errors, len(promotion_order) == len(set(promotion_order)), "promotion_order contains duplicates")

    migration = payload.get("migration", {})
    add(errors, isinstance(migration, dict), "migration must be an object")
    if isinstance(migration, dict):
        add(errors, nonempty_string(migration.get("migration_id")), "migration.migration_id must be nonempty")
        add(errors, nonempty_string(migration.get("canary_uid")), "migration.canary_uid must be nonempty")
        if nonempty_string(migration.get("canary_uid")) and all_uids:
            add(errors, migration.get("canary_uid") in all_uids, "migration.canary_uid must be one of the candidate UIDs")
        add(errors, migration.get("rollback_defined") is True, "migration.rollback_defined must be true")
        add(errors, nonempty_string(migration.get("rollback_path")), "migration.rollback_path must be nonempty")
        add(errors, isinstance(migration.get("expected_count"), int) and migration["expected_count"] >= 0, "migration.expected_count must be nonnegative")
        if isinstance(migration.get("expected_count"), int):
            add(errors, migration["expected_count"] <= total_candidates, "migration.expected_count cannot exceed total candidate count")

    recovery = payload.get("recovery_protocol", {})
    add(errors, isinstance(recovery, dict), "recovery_protocol must be an object")
    if isinstance(recovery, dict):
        add(errors, recovery.get("timeout_state") == "UNKNOWN_UNTIL_CHECKED", "recovery_protocol.timeout_state must be UNKNOWN_UNTIL_CHECKED")
        for field in ("label_scoped_checks", "exact_uid_rollback", "unlabeled_uid_scan_prohibited"):
            add(errors, recovery.get(field) is True, f"recovery_protocol.{field} must be true")

    appendix = payload.get("appendix", {})
    add(errors, isinstance(appendix, dict), "appendix must be an object")
    if isinstance(appendix, dict):
        for field in (
            "previous_revision",
            "current_revision",
            "previous_metadata_dir",
            "previous_conformance_dir",
            "current_metadata_dir",
            "current_conformance_dir",
        ):
            add(errors, nonempty_string(appendix.get(field)), f"appendix.{field} must be nonempty")
        add(errors, isinstance(appendix.get("expected_metric_deltas"), list), "appendix.expected_metric_deltas must be a list")
        add(errors, appendix.get("figure_verification_required") is True, "appendix.figure_verification_required must be true")

    add(errors, isinstance(payload.get("limitations"), list), "limitations must be a list")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Manifest root must be an object")
    errors = validate(payload)
    result = {
        "schema_version": "arc-rule-manifest-validation-v2",
        "manifest": str(args.manifest),
        "valid": not errors,
        "error_count": len(errors),
        "errors": errors,
    }
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
