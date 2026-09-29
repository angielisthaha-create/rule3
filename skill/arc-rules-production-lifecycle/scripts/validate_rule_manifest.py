#!/usr/bin/env python3
"""Validate a bounded ARC Rules 1-15 batch manifest and Stage 0-15 ledger.

The validator checks deterministic closure and governance fields only. It does
not certify legal meaning, current law, production identity, or Neo4j state.
New manifests should use arc-rule-batch-v3. Legacy v2 remains accepted.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
VALID_SCHEMA_VERSIONS = {"arc-rule-batch-v2", "arc-rule-batch-v3"}
VALID_STAGE_STATUSES = {
    "PENDING",
    "ADMITTED",
    "IN_PROGRESS",
    "CLOSED",
    "CLOSED_WITH_LIMITATIONS",
    "BLOCKED",
    "NOT_APPLICABLE",
    "ROLLED_BACK",
}
REQUIRED_STAGE_IDS = set(range(16))
EXPECTED_STAGE_NAMES = {
    0: "scope_and_authority",
    1: "manual_txt_source_build",
    2: "source_evidence_closure",
    3: "review_candidate_materialization",
    4: "stage1_cumulative_closure",
    5: "official_source_comparison",
    6: "amended_manifest_admission",
    7: "semantic_metadata_correction",
    8: "appendix_baseline_metric_design",
    9: "promotion_packet_rollback",
    10: "production_canary",
    11: "family_promotion",
    12: "independent_production_closure",
    13: "post_promotion_appendix",
    14: "policy_retrieval_validation",
    15: "lane_closure",
}
CLOSED_LIKE = {"CLOSED", "CLOSED_WITH_LIMITATIONS"}
LANE_REQUIRED_CLOSED_STAGES = {
    "SOURCE_BUILD": {0, 1, 2},
    "CANDIDATE_ENVELOPE_INGEST": {0, 1, 2, 3, 4},
    "SOURCE_GRAPH_MATERIALIZATION": {0, 1, 2},
    "OFFICIAL_SOURCE_CLOSURE": {0, 1, 2, 5},
    "PRODUCTION_PROMOTION": {0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12},
    "RETRIEVAL_RELEASE": {0, 2, 12, 14},
}
PROVISIONAL_REQUIRED_LEDGER_FIELDS = {
    "source_package_sha256",
    "source_record_sha256",
    "artifact_hash_ledger_sha256",
    "span_hash_ledger_sha256",
    "embedded_candidate_uid_ledger_sha256",
}
WORKFLOW_LANES = {
    "SOURCE_BUILD",
    "CANDIDATE_ENVELOPE_INGEST",
    "SOURCE_GRAPH_MATERIALIZATION",
    "OFFICIAL_SOURCE_CLOSURE",
    "PRODUCTION_PROMOTION",
    "RETRIEVAL_RELEASE",
}
SOURCE_MODES = {"GRAPH_MATERIALIZED", "PROVISIONAL_ENVELOPE_ONLY"}
APPENDIX_MODES = {"REQUIRED", "DEFERRED_NONPRODUCTION", "NOT_APPLICABLE"}
REQUIRED_TOP_V2 = {
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
REQUIRED_TOP_V3 = REQUIRED_TOP_V2 | {"workflow_lane", "source_materialization"}


def add(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_sha256(value: Any) -> bool:
    return bool(SHA256_RE.match(str(value or "")))


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    schema_version = payload.get("schema_version")
    add(errors, schema_version in VALID_SCHEMA_VERSIONS, "schema_version must be arc-rule-batch-v2 or arc-rule-batch-v3")
    is_v3 = schema_version == "arc-rule-batch-v3"
    required_top = REQUIRED_TOP_V3 if is_v3 else REQUIRED_TOP_V2
    missing = sorted(required_top - set(payload))
    add(errors, not missing, f"Missing top-level fields: {missing}")

    add(errors, nonempty_string(payload.get("batch_id")), "batch_id must be nonempty")
    add(errors, nonempty_string(payload.get("database")), "database must be nonempty")
    add(errors, isinstance(payload.get("rule_scope"), list) and bool(payload.get("rule_scope")), "rule_scope must be a nonempty list")
    for index, value in enumerate(payload.get("rule_scope", []) if isinstance(payload.get("rule_scope"), list) else []):
        add(errors, nonempty_string(value), f"rule_scope[{index}] must be nonempty")

    workflow_lane = payload.get("workflow_lane") if is_v3 else "PRODUCTION_PROMOTION"
    if is_v3:
        add(errors, workflow_lane in WORKFLOW_LANES, f"workflow_lane must be one of {sorted(WORKFLOW_LANES)}")

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
        missing_authority = sorted(required_authority - set(authority))
        add(errors, not missing_authority, f"authority missing fields: {missing_authority}")
        for field in required_authority:
            add(errors, isinstance(authority.get(field), bool), f"authority.{field} must be boolean")

    source_mode = None
    source_materialization = payload.get("source_materialization", {})
    if is_v3:
        add(errors, isinstance(source_materialization, dict), "source_materialization must be an object")
        if isinstance(source_materialization, dict):
            source_mode = source_materialization.get("mode")
            add(errors, source_mode in SOURCE_MODES, f"source_materialization.mode must be one of {sorted(SOURCE_MODES)}")
            for field in (
                "source_graph_materialized",
                "envelope_only",
                "production_promotion_blocked",
                "proposed_anchor_relationship_created",
            ):
                add(errors, isinstance(source_materialization.get(field), bool), f"source_materialization.{field} must be boolean")
            ledger_fields = source_materialization.get("required_ledger_fields")
            add(errors, isinstance(ledger_fields, list), "source_materialization.required_ledger_fields must be a list")
            if isinstance(ledger_fields, list):
                add(errors, all(nonempty_string(x) for x in ledger_fields), "source_materialization.required_ledger_fields values must be nonempty strings")
                add(errors, len(ledger_fields) == len(set(ledger_fields)), "source_materialization.required_ledger_fields contains duplicates")
            if source_mode == "GRAPH_MATERIALIZED":
                add(errors, source_materialization.get("source_graph_materialized") is True, "GRAPH_MATERIALIZED requires source_graph_materialized=true")
                add(errors, source_materialization.get("envelope_only") is False, "GRAPH_MATERIALIZED requires envelope_only=false")
            if source_mode == "PROVISIONAL_ENVELOPE_ONLY":
                add(errors, source_materialization.get("source_graph_materialized") is False, "PROVISIONAL_ENVELOPE_ONLY requires source_graph_materialized=false")
                add(errors, source_materialization.get("envelope_only") is True, "PROVISIONAL_ENVELOPE_ONLY requires envelope_only=true")
                add(errors, source_materialization.get("production_promotion_blocked") is True, "PROVISIONAL_ENVELOPE_ONLY requires production_promotion_blocked=true")
                add(errors, source_materialization.get("proposed_anchor_relationship_created") is False, "PROVISIONAL_ENVELOPE_ONLY prohibits a proposed-anchor relationship")
                if isinstance(authority, dict):
                    add(errors, authority.get("production_promotion") is False, "PROVISIONAL_ENVELOPE_ONLY requires authority.production_promotion=false")
                if isinstance(ledger_fields, list):
                    add(errors, PROVISIONAL_REQUIRED_LEDGER_FIELDS.issubset(set(ledger_fields)),
                        "PROVISIONAL_ENVELOPE_ONLY required_ledger_fields must include all governed hash-ledger fields")

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
        add(errors, is_sha256(row.get("sha256")), f"{prefix}.sha256 must be 64 hex characters")
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
    stage_status: dict[int, str] = {}
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
            if isinstance(row.get("status"), str):
                stage_status[stage_id] = row["status"]
        add(errors, nonempty_string(row.get("name")), f"{prefix}.name must be nonempty")
        if isinstance(stage_id, int) and stage_id in EXPECTED_STAGE_NAMES:
            add(errors, row.get("name") == EXPECTED_STAGE_NAMES[stage_id],
                f"{prefix}.name must be {EXPECTED_STAGE_NAMES[stage_id]!r} for stage_id={stage_id}")
        add(errors, row.get("status") in VALID_STAGE_STATUSES, f"{prefix}.status is invalid")
        if row.get("status") in {"CLOSED", "CLOSED_WITH_LIMITATIONS", "ROLLED_BACK"}:
            add(errors, nonempty_string(row.get("verification_artifact")), f"{prefix}.verification_artifact required for terminal status")
        if row.get("status") == "CLOSED_WITH_LIMITATIONS":
            add(errors, nonempty_string(row.get("limitation")), f"{prefix}.limitation required for CLOSED_WITH_LIMITATIONS")
    add(errors, stage_ids == REQUIRED_STAGE_IDS, f"stage_ledger must contain every stage 0..15; missing={sorted(REQUIRED_STAGE_IDS - stage_ids)} extra={sorted(stage_ids - REQUIRED_STAGE_IDS)}")
    if is_v3 and source_mode == "PROVISIONAL_ENVELOPE_ONLY":
        add(errors, stage_status.get(2) in {"CLOSED_WITH_LIMITATIONS", "BLOCKED"}, "Stage 2 must be CLOSED_WITH_LIMITATIONS or BLOCKED for PROVISIONAL_ENVELOPE_ONLY")

    # Validate lane closure as a state machine, not merely a populated ledger.
    terminal15 = stage_status.get(15) in {"CLOSED", "CLOSED_WITH_LIMITATIONS"}
    if terminal15:
        add(errors, stage_status.get(0) in CLOSED_LIKE, "Stage 15 cannot close before Stage 0 closes")
        active = sorted(i for i, st in stage_status.items() if i != 15 and st in {"ADMITTED", "IN_PROGRESS"})
        add(errors, not active, f"Stage 15 cannot close while stages are active: {active}")
        required = LANE_REQUIRED_CLOSED_STAGES.get(workflow_lane, set())
        for sid in sorted(required):
            add(errors, stage_status.get(sid) in CLOSED_LIKE,
                f"{workflow_lane} lane closure requires Stage {sid} ({EXPECTED_STAGE_NAMES[sid]}) to be CLOSED/CLOSED_WITH_LIMITATIONS")
        if workflow_lane == "CANDIDATE_ENVELOPE_INGEST":
            add(errors, stage_status.get(15) == "CLOSED_WITH_LIMITATIONS",
                "CANDIDATE_ENVELOPE_INGEST terminal closure must be CLOSED_WITH_LIMITATIONS")
        if workflow_lane == "PRODUCTION_PROMOTION":
            if payload.get("appendix", {}).get("mode") == "REQUIRED":
                add(errors, stage_status.get(13) in CLOSED_LIKE, "Appendix REQUIRED requires Stage 13 closed before lane closure")
            else:
                add(errors, stage_status.get(13) in CLOSED_LIKE | {"NOT_APPLICABLE"}, "Stage 13 must be closed or NOT_APPLICABLE before production lane closure")

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
        if isinstance(authorization.get("issued"), bool) and isinstance(authorization.get("consumed"), bool):
            add(errors, not authorization.get("consumed") or authorization.get("issued"),
                "authorization.consumed=true requires issued=true")
            if authorization.get("issued") is False:
                add(errors, authorization.get("consumed") is False, "authorization issued=false requires consumed=false")
        add(errors, isinstance(authorization.get("prohibited_actions"), list), "authorization.prohibited_actions must be a list")

    graph_effects = payload.get("expected_graph_effects", {})
    add(errors, isinstance(graph_effects, dict), "expected_graph_effects must be an object")
    if isinstance(graph_effects, dict):
        for field in ("nodes_created", "relationships_created"):
            add(errors, isinstance(graph_effects.get(field), int) and graph_effects[field] >= 0, f"expected_graph_effects.{field} must be nonnegative")
        for field in ("production_labels", "prohibited_labels", "no_change_invariants"):
            add(errors, isinstance(graph_effects.get(field), list), f"expected_graph_effects.{field} must be a list")
        if is_v3 and workflow_lane == "CANDIDATE_ENVELOPE_INGEST":
            add(errors, graph_effects.get("production_labels") == [], "CANDIDATE_ENVELOPE_INGEST requires expected_graph_effects.production_labels=[]")

    promotion_order = payload.get("promotion_order")
    add(errors, isinstance(promotion_order, list), "promotion_order must be a list")
    if isinstance(promotion_order, list):
        add(errors, all(nonempty_string(value) for value in promotion_order), "promotion_order values must be nonempty strings")
        add(errors, len(promotion_order) == len(set(promotion_order)), "promotion_order contains duplicates")
        if not is_v3 or workflow_lane == "PRODUCTION_PROMOTION":
            add(errors, bool(promotion_order), "promotion_order must be nonempty for production promotion")

    migration = payload.get("migration", {})
    add(errors, isinstance(migration, dict), "migration must be an object")
    if isinstance(migration, dict):
        add(errors, nonempty_string(migration.get("migration_id")), "migration.migration_id must be nonempty")
        canary_required = migration.get("canary_required", True if not is_v3 else workflow_lane == "PRODUCTION_PROMOTION")
        add(errors, isinstance(canary_required, bool), "migration.canary_required must be boolean")
        canary_uid = migration.get("canary_uid")
        if canary_required:
            add(errors, nonempty_string(canary_uid), "migration.canary_uid must be nonempty when canary_required=true")
            if nonempty_string(canary_uid) and all_uids:
                add(errors, canary_uid in all_uids, "migration.canary_uid must be one of the candidate UIDs")
        else:
            add(errors, canary_uid is None or canary_uid == "", "migration.canary_uid must be null/empty when canary_required=false")
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
        if is_v3:
            mode = appendix.get("mode")
            add(errors, mode in APPENDIX_MODES, f"appendix.mode must be one of {sorted(APPENDIX_MODES)}")
            add(errors, isinstance(appendix.get("generation_required"), bool), "appendix.generation_required must be boolean")
            add(errors, nonempty_string(appendix.get("trigger_reason")), "appendix.trigger_reason must be nonempty")
            for field in (
                "metric_surface_changed",
                "production_topology_changed",
                "release_status_changed",
                "schema_or_metric_definition_changed",
                "figure_verification_required",
            ):
                add(errors, isinstance(appendix.get(field), bool), f"appendix.{field} must be boolean")
            add(errors, isinstance(appendix.get("expected_metric_deltas"), list), "appendix.expected_metric_deltas must be a list")
            if mode == "REQUIRED":
                add(errors, appendix.get("generation_required") is True, "appendix REQUIRED mode requires generation_required=true")
                add(errors, appendix.get("figure_verification_required") is True, "appendix REQUIRED mode requires figure_verification_required=true")
                for field in (
                    "previous_revision",
                    "current_revision",
                    "previous_metadata_dir",
                    "previous_conformance_dir",
                    "current_metadata_dir",
                    "current_conformance_dir",
                ):
                    add(errors, nonempty_string(appendix.get(field)), f"appendix.{field} must be nonempty in REQUIRED mode")
            elif mode == "DEFERRED_NONPRODUCTION":
                add(errors, appendix.get("generation_required") is False, "DEFERRED_NONPRODUCTION requires generation_required=false")
                add(errors, appendix.get("figure_verification_required") is False, "DEFERRED_NONPRODUCTION requires figure_verification_required=false")
                add(errors, nonempty_string(appendix.get("baseline_fingerprint")), "DEFERRED_NONPRODUCTION requires appendix.baseline_fingerprint")
                add(errors, nonempty_string(appendix.get("audit_run_id")), "DEFERRED_NONPRODUCTION requires appendix.audit_run_id")
                add(errors, workflow_lane == "CANDIDATE_ENVELOPE_INGEST", "DEFERRED_NONPRODUCTION is allowed only for CANDIDATE_ENVELOPE_INGEST")
                change_flags = (
                    appendix.get("metric_surface_changed"),
                    appendix.get("production_topology_changed"),
                    appendix.get("release_status_changed"),
                    appendix.get("schema_or_metric_definition_changed"),
                )
                add(errors, not any(change_flags), "DEFERRED_NONPRODUCTION requires all Appendix change flags=false")
            elif mode == "NOT_APPLICABLE":
                add(errors, appendix.get("generation_required") is False, "NOT_APPLICABLE requires generation_required=false")
                add(errors, appendix.get("figure_verification_required") is False, "NOT_APPLICABLE requires figure_verification_required=false")
        else:
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

    if is_v3 and workflow_lane == "CANDIDATE_ENVELOPE_INGEST":
        if isinstance(authority, dict):
            add(errors, authority.get("candidate_write") is True, "CANDIDATE_ENVELOPE_INGEST requires authority.candidate_write=true")
            add(errors, authority.get("production_promotion") is False, "CANDIDATE_ENVELOPE_INGEST requires authority.production_promotion=false")
        add(errors, source_mode == "PROVISIONAL_ENVELOPE_ONLY", "CANDIDATE_ENVELOPE_INGEST requires PROVISIONAL_ENVELOPE_ONLY")
        if isinstance(appendix, dict):
            add(errors, appendix.get("mode") == "DEFERRED_NONPRODUCTION", "CANDIDATE_ENVELOPE_INGEST requires appendix.mode=DEFERRED_NONPRODUCTION")

    add(errors, isinstance(payload.get("limitations"), list), "limitations must be a list")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Manifest root must be an object")
    errors = validate(payload)
    result = {
        "schema_version": "arc-rule-manifest-validation-v3",
        "manifest": str(args.manifest),
        "input_schema_version": payload.get("schema_version"),
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
