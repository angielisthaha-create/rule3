#!/usr/bin/env python3
"""Create a standard ARC pathway workspace for one rule."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

FILES = [
    "pathway_report.md", "graph_candidate_packet.json", "manual_validation.tsv",
    "discard_ledger.tsv", "no_write_run_ledger.json", "case_ladder.tsv",
    "source_material_classifier.tsv", "use_purpose_classifier.tsv", "README.md",
]

def slug(rule: str) -> str:
    return "rule_" + re.sub(r"[^0-9a-zA-Z]+", "_", rule).strip("_").lower()

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rule", required=True)
    parser.add_argument("--base-dir", type=Path, default=Path("arc_pathway_pilot"))
    args = parser.parse_args()
    d = args.base_dir / slug(args.rule)
    d.mkdir(parents=True, exist_ok=True)
    prefix = slug(args.rule)
    for name in FILES:
        p = d / f"{prefix}_{name}" if name != "README.md" else d / name
        if not p.exists():
            if p.suffix == ".tsv":
                p.write_text("status\tnotes\n", encoding="utf-8")
            elif p.suffix == ".json":
                p.write_text("{}\n", encoding="utf-8")
            else:
                p.write_text(f"# {prefix} {name}\n\nstatus: draft\n", encoding="utf-8")
    print(d)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
