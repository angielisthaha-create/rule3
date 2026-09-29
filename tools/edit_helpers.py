#!/usr/bin/env python3
"""TEXT-INSERTION helpers used to RECORD decisions already made by reading (they decide nothing).

Every function refuses to act unless its anchor text occurs exactly once, so a typo cannot edit the wrong place.

  python3 tools/edit_helpers.py see-also 2.21 "BOOK_A other Parts (8th pass): ..."
      Prepend an entry to MANUAL_SEE_ALSO["2.21"] in tools/build_rule2_reconciliation.py.
  python3 tools/edit_helpers.py replace FILE "old text" "new text"
      Replace text that occurs exactly once in FILE (builder, REVIEW_NOTES.txt, WORKFLOW.txt, README.txt).
  python3 tools/edit_helpers.py review-line 2.14 "[9th pass] ..."
      Insert "     <text>" into rule2_subrules/REVIEW_NOTES.txt as the last line of rule 2.14's block.
  python3 tools/edit_helpers.py status "Ninth pass: 2.1 - 2.10 (...)"
      Add a status line after the last "... pass:" line in WORKFLOW.txt section 5.

After any edit: python3 tools/build_rule2_reconciliation.py, then gate_all (tools/qa_display_helpers.sh),
then re-read the rebuilt JSON to confirm the decision landed.
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PART = os.environ.get("ARC_PART", "2")   # set ARC_PART=3 for Part 3
BUILDER = ROOT / "tools" / f"build_rule{PART}_reconciliation.py"
REVIEW = ROOT / f"rule{PART}_subrules" / "REVIEW_NOTES.txt"
WORKFLOW = ROOT / f"rule{PART}_subrules" / "WORKFLOW.txt"
PART_LEVEL = ("     Book C lists 2.11-2.21", "     Book C amendment notes")


def replace_once(path: Path, old: str, new: str) -> None:
    s = path.read_text(encoding="utf-8")
    n = s.count(old)
    if n != 1:
        sys.exit(f"refused: anchor occurs {n} times in {path.name}")
    path.write_text(s.replace(old, new), encoding="utf-8")


def add_see_also(rule: str, text: str) -> None:
    anchor = f'    "{rule}": ['
    s = BUILDER.read_text(encoding="utf-8")
    start = s.index("MANUAL_SEE_ALSO = {")
    end = s.index("\n}\n", start)
    block = s[start:end]
    esc = text.replace("\\", "\\\\").replace('"', '\\"')
    if block.count(anchor) == 0:
        # first entry for this rule: create the list
        block = block + f'\n    "{rule}": [\n        "{esc}",\n    ],'
    elif block.count(anchor) != 1:
        sys.exit(f"refused: {anchor!r} occurs {block.count(anchor)} times in MANUAL_SEE_ALSO")
    else:
        block = block.replace(anchor, anchor + '"' + esc + '",\n            ', 1)
    BUILDER.write_text(s[:start] + block + s[end:], encoding="utf-8")


def add_review_line(rule: str, text: str) -> None:
    lines = REVIEW.read_text(encoding="utf-8").split("\n")
    head = re.compile(rf"^{PART}\.(\d+)\b")
    target = int(rule.split(".")[1])
    starts = [k for k, l in enumerate(lines) if (m := head.match(l)) and int(m.group(1)) == target]
    if not starts:
        sys.exit(f"refused: no block for {rule}")
    k = starts[0] + 1
    while k < len(lines):
        m = head.match(lines[k])
        if m and int(m.group(1)) != target:
            break
        if lines[k] and not lines[k].startswith(" "):
            break
        k += 1
    while k > starts[0] + 1 and not lines[k - 1].strip():
        k -= 1
    # part-level notes that close the 2.20 and 2.32 blocks stay last (convention of earlier passes)
    while k > starts[0] + 1 and lines[k - 1].startswith(PART_LEVEL):
        k -= 1
    lines.insert(k, "     " + text)
    REVIEW.write_text("\n".join(lines), encoding="utf-8")


def add_status(text: str) -> None:
    lines = WORKFLOW.read_text(encoding="utf-8").split("\n")
    idx = [k for k, l in enumerate(lines) if re.match(r"^   \w+ pass", l)]
    if not idx:
        sys.exit("refused: no status lines found")
    lines.insert(idx[-1] + 1, "   " + text)
    WORKFLOW.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    cmd, rest = sys.argv[1], sys.argv[2:]
    if cmd == "see-also":
        add_see_also(rest[0], rest[1])
    elif cmd == "replace":
        replace_once(ROOT / rest[0] if not Path(rest[0]).is_absolute() else Path(rest[0]), rest[1], rest[2])
    elif cmd == "review-line":
        add_review_line(rest[0], rest[1])
    elif cmd == "status":
        add_status(rest[0])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
