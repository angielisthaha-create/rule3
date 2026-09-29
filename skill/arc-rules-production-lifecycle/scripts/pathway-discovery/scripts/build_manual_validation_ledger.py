#!/usr/bin/env python3
"""Create a manual-validation TSV from an ARC candidate packet."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

FIELDS = [
    "candidate_id",
    "pathway_uid",
    "case_name",
    "neutral_citation",
    "canlii_url",
    "official_source_url",
    "case_exists_publicly",
    "paragraphs_confirmed",
    "quoted_text_confirmed",
    "case_status_checked",
    "appeal_history_checked",
    "negative_treatment_checked",
    "authority_level_confirmed",
    "current_rule_text_confirmed",
    "source_material_classified",
    "use_purpose_classified",
    "same_or_related_action_classified",
    "privilege_screen_complete",
    "non_party_privacy_screen_complete",
    "sealed_or_restricted_access_checked",
    "verified_by",
    "verified_date",
    "notes",
]


def iter_pathways(packet: dict):
    for key in ("candidate_pathways", "pathways"):
        if isinstance(packet.get(key), list):
            yield from packet[key]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    rows = []
    for pathway in iter_pathways(packet):
        pathway_uid = pathway.get("pathway_uid") or pathway.get("key") or ""
        candidate_id = pathway.get("candidate_id") or pathway_uid
        ladder = pathway.get("case_ladder") or []
        if not ladder:
            rows.append({"candidate_id": candidate_id, "pathway_uid": pathway_uid, "notes": "no case ladder yet"})
        for item in ladder:
            rows.append({
                "candidate_id": candidate_id,
                "pathway_uid": pathway_uid,
                "case_name": item.get("case_name", ""),
                "neutral_citation": item.get("neutral_citation", item.get("citation", "")),
                "paragraphs_confirmed": "no",
                "quoted_text_confirmed": "no",
                "case_status_checked": "no",
                "appeal_history_checked": "no",
                "negative_treatment_checked": "no",
                "authority_level_confirmed": "no",
                "current_rule_text_confirmed": "no",
                "source_material_classified": "no",
                "use_purpose_classified": "no",
                "same_or_related_action_classified": "no",
                "privilege_screen_complete": "no",
                "non_party_privacy_screen_complete": "no",
                "sealed_or_restricted_access_checked": "no",
                "notes": item.get("manual_status", "needs_validation"),
            })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})
    print(f"wrote {len(rows)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
