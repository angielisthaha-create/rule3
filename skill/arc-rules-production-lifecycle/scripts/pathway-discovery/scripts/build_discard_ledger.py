#!/usr/bin/env python3
"""Create a starter discard-ledger TSV for ARC pathway runs."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

FIELDS = ["raw_hit_id", "term", "source_type", "discard_reason", "disposition", "source", "notes"]
DEFAULT_ROWS = [
    ("", "generic rule citation", "case", "rule mentioned but not interpreted", "discard", "", ""),
    ("", "commentary-only", "commentary", "no underlying case paragraph verified", "manual_review", "", ""),
    ("", "reform proposal", "commentary", "not current law unless confirmed", "separate_reform_signal", "", ""),
    ("", "generic Case node", "graph", "placeholder or poor metadata", "discard_until_verified", "", ""),
    ("", "duplicate RuleProvision stub", "graph", "not canonical rule anchor", "quarantine", "", ""),
    ("", "out-of-jurisdiction case", "case", "not binding; use only if analogue", "analogue_only", "", ""),
    ("", "privileged material", "record", "privilege unresolved", "stop_escalate", "", ""),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(FIELDS)
        writer.writerows(DEFAULT_ROWS)
    print(f"wrote discard ledger template to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
