#!/usr/bin/env python3
"""Offline replay of frozen Rule-7 hardening failures.

No graph access. Each fixture encodes a historical failure mode or a positive
control. A release candidate passes only when every fixture produces its frozen
expected disposition.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def receipt_identity(c, o):
    return "ACCEPT" if all(o.get(k) == c.get(k) for k in ("phase", "stage", "campaign")) else "REJECT"


def topology_fingerprint(c, o):
    if o.get("canonicalizer_id") != c.get("canonicalizer_id"):
        return "REJECT"
    return "ACCEPT" if o.get("sha256") == c.get("sha256") else "REJECT"


def null_safe_equality(c, o):
    expected, live = c.get("value"), o.get("value")
    return "ACCEPT" if (expected is None and live is None) or (expected is not None and live is not None and expected == live) else "REJECT"


def atomic_eligibility(c, o):
    return "ACCEPT" if int(o.get("eligible_count", -1)) == int(c.get("expected_count", -2)) else "REJECT"


def authorization_reuse(c, o):
    if c.get("one_time") and o.get("apply_started") and o.get("reuse_requested"):
        return "REJECT_REUSE"
    return "ACCEPT"


def invalidation_footprint(c, o):
    permitted = set(c.get("permitted", []))
    footprint = set(o.get("mutation_footprint", []))
    forbidden = {"text", "source", "full_text", "labels", "relationships", "topology"}
    return "ACCEPT" if footprint <= permitted and not (footprint & forbidden) else "REJECT"


def denominator_disjoint(c, o):
    current = set(c.get("current_parent_uids", []))
    negative = set(o.get("negative_control_uids", []))
    return "ACCEPT" if current.isdisjoint(negative) else "REJECT"


def stage_separation(c, o):
    actions = set(o.get("same_nudge_actions", []))
    if c.get("separate_stage_d", True) and "APPLY" in actions and "INDEPENDENT_STAGE_D" in actions:
        return "REJECT"
    return "ACCEPT"


def wrapper_receipt_identity(c, o):
    keys = (("phase", "delegated_apply_phase"), ("operation", "delegated_apply_operation"), ("version", "delegated_apply_version"))
    return "ACCEPT" if all(c.get(ck) == o.get(ok) for ck, ok in keys) else "REJECT"


def registry_required_args(c, o):
    return "ACCEPT" if set(c.get("required_args", [])) <= set(o.get("provided_args", [])) else "REJECT"


def executable_identity(c, o):
    if o.get("requested_action") == "APPLY" and o.get("current_module_sha256") != c.get("stage_b_module_sha256"):
        return "REJECT"
    return "ACCEPT"


def release_rebase(c, o):
    return "ACCEPT" if o.get("edit_base_package_sha256") == c.get("release_qualified_package_sha256") else "REJECT"


def integrated_positive(c, o):
    checks = [
        receipt_identity(c["receipt"], o["receipt"]),
        topology_fingerprint(c["topology"], o["topology"]),
        atomic_eligibility({"expected_count": c["expected_count"]}, {"eligible_count": o["eligible_count"]}),
        invalidation_footprint({"permitted": c["permitted_invalidation"]}, {"mutation_footprint": o["mutation_footprint"]}),
        denominator_disjoint({"current_parent_uids": c["current_parent_uids"]}, {"negative_control_uids": o["negative_control_uids"]}),
        stage_separation({"separate_stage_d": True}, {"same_nudge_actions": o["same_nudge_actions"]}),
        registry_required_args({"required_args": c["required_args"]}, {"provided_args": o["provided_args"]}),
        executable_identity({"stage_b_module_sha256": c["stage_b_module_sha256"]}, {"current_module_sha256": o["current_module_sha256"], "requested_action": "APPLY"}),
        release_rebase({"release_qualified_package_sha256": c["release_qualified_package_sha256"]}, {"edit_base_package_sha256": o["edit_base_package_sha256"]}),
    ]
    return "ACCEPT" if all(x == "ACCEPT" for x in checks) else "REJECT"


CHECKS = {
    "receipt_identity": receipt_identity,
    "topology_fingerprint": topology_fingerprint,
    "null_safe_equality": null_safe_equality,
    "atomic_eligibility": atomic_eligibility,
    "authorization_reuse": authorization_reuse,
    "invalidation_footprint": invalidation_footprint,
    "denominator_disjoint": denominator_disjoint,
    "stage_separation": stage_separation,
    "wrapper_receipt_identity": wrapper_receipt_identity,
    "registry_required_args": registry_required_args,
    "executable_identity": executable_identity,
    "release_rebase": release_rebase,
    "integrated_positive": integrated_positive,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixtures", nargs="?", type=Path, default=Path(__file__).with_name("adversarial_replay_fixtures.json"))
    args = parser.parse_args()
    data = json.loads(args.fixtures.read_text(encoding="utf-8"))
    results = []
    ok = True
    seen = set()
    for fixture in data.get("fixtures", []):
        fid = fixture.get("id")
        check = fixture.get("check")
        expected = fixture.get("expected")
        if not fid or fid in seen or check not in CHECKS or not expected:
            results.append({"id": fid, "ok": False, "reason": "INVALID_FIXTURE"})
            ok = False
            continue
        seen.add(fid)
        observed = CHECKS[check](fixture.get("contract", {}), fixture.get("observed", {}))
        passed = observed == expected
        ok = ok and passed
        results.append({"id": fid, "check": check, "expected": expected, "observed": observed, "ok": passed})
    if len(results) != 14:
        ok = False
    payload = {"ok": ok, "schema": data.get("schema"), "fixture_count": len(results), "passed_count": sum(1 for r in results if r.get("ok")), "results": results}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
