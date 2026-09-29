#!/usr/bin/env python3
"""DISPLAY ONLY. List every page ("p.2-NN", "pp.2-NN"), line ("line NNN") and other-Part page ("p.3-NN",
"p.11-NN") reference written in the notes of the given subrules, so each can be checked BY HAND against the
page markers (see README section 2 and tools/qa_display_helpers.sh: pg, pg3, fn_pages).

Usage: python3 tools/extract_note_refs.py 1 10     (rules 2.1 to 2.10; ARC_PART=3 for Part 3)
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PART = os.environ.get("ARC_PART", "2")   # set ARC_PART=3 for Part 3
LAST = {"3": 77, "10": 55}.get(PART, 32)
PAT = re.compile(r"[^\"]{0,120}(?:pp?\.\s?\d{1,2}-\d+|lines? \d+)[^\"]{0,60}")


def main() -> int:
    first, last = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) == 3 else (1, LAST)
    for i in range(first, last + 1):
        d = json.loads((ROOT / f"rule{PART}_subrules" / f"{PART}.{i}.json").read_text(encoding="utf-8"))
        s = json.dumps(d, ensure_ascii=False)
        for m in PAT.finditer(s):
            print(f"{PART}.{i} ::", m.group(0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
