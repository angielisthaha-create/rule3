#!/usr/bin/env python3
"""DISPLAY ONLY. Print a subrule's see_also entries and every flag/note field, for manual reading.

Usage: python3 tools/show_rule_notes.py 9 10          (rules 2.9 and 2.10)
       python3 tools/show_rule_notes.py --full 24     (do not cut long values; footnote lists included)
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PART = os.environ.get("ARC_PART", "2")   # set ARC_PART=3 for Part 3


def main() -> int:
    args = sys.argv[1:]
    full = "--full" in args
    rules = [a for a in args if a != "--full"]
    for i in rules:
        d = json.loads((ROOT / f"rule{PART}_subrules" / f"{PART}.{i}.json").read_text(encoding="utf-8"))
        print(f"######## {PART}.{i}", d["title"]["official"], d["title"].get("variants"))
        for x in d.get("see_also", []):
            print(" SA:", x if isinstance(x, str) else json.dumps(x, ensure_ascii=False))

        def walk(o, path=""):
            if isinstance(o, dict):
                for k, v in o.items():
                    hit = any(t in k for t in ("flag", "note", "dropped", "why"))
                    if hit and k != "information_notes" and "operative_text_note" not in k:
                        txt = json.dumps(v, ensure_ascii=False)
                        print(" ", path + "/" + k, ":", txt if full else txt[:1500])
                    elif k == "footnotes" and not full:
                        continue
                    else:
                        walk(v, path + "/" + k)
            elif isinstance(o, list):
                for v in o:
                    walk(v, path)

        walk(d["sources"])
        walk(d.get("comparison_vs_official", {}), "/cmp")
    return 0


if __name__ == "__main__":
    sys.exit(main())
