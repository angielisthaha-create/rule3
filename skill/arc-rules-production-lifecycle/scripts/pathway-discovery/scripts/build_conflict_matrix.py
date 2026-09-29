#!/usr/bin/env python3
"""Build a starter conflict matrix TSV from a candidate packet."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

FIELDS = ["holding_a", "holding_b", "relationship_type", "reason", "authority_level_a", "authority_level_b", "manual_status"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    rows = []
    for p in packet.get("candidate_pathways", []):
        uid = p.get("pathway_uid", "")
        for rel_key in ("confirmed_by", "limited_by", "distinguished_by", "conflicts_with", "analogue_only"):
            for target in p.get(rel_key, []) if isinstance(p.get(rel_key, []), list) else []:
                rows.append({"holding_a": uid, "holding_b": target, "relationship_type": rel_key.upper(), "reason": "candidate_signal", "manual_status": "needs_review"})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, delimiter="	")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})
    print(f"wrote {len(rows)} rows to {args.out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
