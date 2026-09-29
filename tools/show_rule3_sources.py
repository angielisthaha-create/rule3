#!/usr/bin/env python3
"""DISPLAY ONLY (Part 3). Print, for one rule, everything a reviewer reads by eye:
  official text; Book A lines (numbered, with page markers); Book B paragraphs; Book C entry; the built statuses;
  and every reference to the rule in the official text, all Book A files, all Book B files and all Book C files.
It finds text; the reviewer decides. Usage: python3 tools/show_rule3_sources.py 9 [--noxref] [--xref-only]
"""
import glob
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("b3", ROOT / "tools" / "build_rule3_reconciliation.py")
b3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b3)


def book_a_raw_range(n):
    """Raw line numbers [first, last] of rule 3.n in combined rule3.txt (same start markers as the builder)."""
    raw = b3.BOOK_A[0].read_text(encoding="utf-8")
    starts, pos = {}, 0
    for r in b3.RULES:
        pat = re.compile(rf"\*(?:(?P<t>[A-Z][^*]{{1,150}})\*\s?)?(?P<n>{re.escape(r)})(?=\(1\)|\s|[A-Z(])")
        m = pat.search(raw, pos)
        if m:
            starts[r] = m.start("n")
            pos = m.end()
    r = f"3.{n}"
    if r not in starts:
        return None, None, raw
    found = [x for x in b3.RULES if x in starts]
    k = found.index(r)
    end = starts[found[k + 1]] if k + 1 < len(found) else len(raw)
    first = raw.count("\n", 0, starts[r]) + 1
    last = raw.count("\n", 0, end) + 1
    return first, last, raw


def show_book_a(n):
    first, last, raw = book_a_raw_range(n)
    print("\n================ BOOK A (combined rule3.txt) ================")
    if first is None:
        print("(rule marker not found in Book A)")
        return
    lines = raw.split("\n")
    # go back to the previous non-empty lines that may hold the title / footnotes printed before the marker
    print(f"rule text marker on line {first}; segment lines {first}-{last} (title/footnotes printed before the marker are at lines {max(1, first - 4)}-{first - 1})")
    page = None
    for i in range(0, first - 1):
        m = re.fullmatch(r"\*\*PAGE (\d+)", lines[i].strip())
        if m:
            page = m.group(1)
    for i in range(max(1, first - 4) - 1, min(len(lines), last + 1)):
        m = re.fullmatch(r"\*\*PAGE (\d+)", lines[i].strip())
        if m:
            page = m.group(1)
        if lines[i].strip() == "" or lines[i].strip() == "--- PAGE BREAK ---":
            continue
        print(f"[{i + 1}|p.3-{page}] {lines[i]}")


def show_book_b(n):
    print("\n================ BOOK B (rule3_part01..10) ================")
    r = f"3.{n}"
    on = False
    for f in b3.BOOK_B:
        d = json.loads(f.read_text(encoding="utf-8"))
        for p in d["document_structure"]["paragraphs"]:
            t = p["text"].strip()
            mh = re.fullmatch(r"(3\.\d+)\. (.{1,250})", t, re.S)
            mc = re.match(r"Commentary § (3\.\d+)", t)
            if mh and "_rule_3_" in p["paragraph_id"] and len(t) < 260:
                on = mh.group(1) == r
            elif mc:
                on = mc.group(1) == r
            if on:
                print(f"--- {f.name[:17]} {p['paragraph_id']} ({len(t)} chars)")
                print(t)


def show_book_c(n):
    print("\n================ BOOK C ================")
    r = f"3.{n}"
    hit = False
    for f in b3.BOOK_C:
        d = json.loads(f.read_text(encoding="utf-8"))
        for h in d["hierarchy"]:
            items = [(None, h["data"])] if h["type"] == "orphan_rule" else [(h.get("heading"), x) for x in h.get("rules", [])]
            for heading, x in items:
                if x.get("number") == r:
                    hit = True
                    print(f"--- {f.name} (division heading: {heading!r})")
                    print("TITLE:", x.get("title"))
                    print("TEXT:\n" + x.get("text", ""))
                    print("INFO NOTES:", json.dumps(x.get("info_notes"), ensure_ascii=False))
                    print("CITATIONS:", [(c.get("neutral_citation"), c.get("style_of_cause")) for c in x.get("citations", [])])
                    for c in x.get("commentary", []):
                        print(f"COMMENTARY [{c.get('topic')}] ({len(c['text'])} chars):\n{c['text']}")
                        print("  citations:", [(y.get("neutral_citation"), y.get("style_of_cause")) for y in c.get("citations", [])])
    if not hit:
        print("(rule not found in Book C files)")


def show_official_and_built(n):
    r = f"3.{n}"
    d = json.loads((ROOT / "rule3_subrules" / f"{r}.json").read_text(encoding="utf-8"))
    print("================ OFFICIAL ================")
    print(r, d["title"]["official"], "| division", d["division"], "| subdivision", d.get("subdivision"))
    print(d["operative_text"]["controlling"])
    print("official amendment line:", d["amendment_history"]["official"], d["amendment_history"]["amending_regulations"])
    print("\nBUILT STATUSES:", {k: v["status"] for k, v in d["comparison_vs_official"].items()})
    print("amendment cross-check:", d["amendment_history"]["crosscheck_vs_official"])


def strings(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("sentences", "context", "sentence_id", "section_heading"):
                continue
            yield from strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from strings(v)
    elif isinstance(o, str):
        yield o


def xrefs(n):
    r = f"3.{n}"
    e = re.escape(r)
    pat = re.compile(
        rf"(?:[Rr]ules?|Rr\.|R\.)\s?{e}(?![\d])(?:\([0-9a-z]+\))*"
        rf"|(?:and|to|or|,|;)\s?{e}(?![\d.])(?:\([0-9a-z]+\))*"
        rf"|(?:^|[ ;(\"]){e}(?![\d.])(?:\([0-9a-z]+\))* ?\([a-z]"
        rf"|\[Rule {e}[\]\(]")
    print("\n================ CROSS-REFERENCES TO", r, "================")
    text = (ROOT / "Alberta_Rules_of_Court.txt").read_text(encoding="utf-8")
    J = re.sub(r"\s*\n\s*", " ", text)
    print("--- OFFICIAL")
    own = None
    for m in pat.finditer(J):
        print("   ...", J[max(0, m.start() - 110):m.end() + 90])
    print("--- BOOK A (file line, page, context)")
    first, last, _ = book_a_raw_range(n)
    for f in sorted(glob.glob(str(ROOT / "combined*.txt"))):
        name = Path(f).name
        Ls = Path(f).read_text(encoding="utf-8").split("\n")
        page = None
        for i in range(len(Ls)):
            m0 = re.fullmatch(r"\*\*PAGE (\d+)", Ls[i].strip())
            if m0:
                page = "3-" + m0.group(1)
            m1 = re.fullmatch(r"\d+-\d+", Ls[i].strip())
            if m1:
                page = Ls[i].strip()
            if name == "combined rule3.txt" and first and first - 4 <= i + 1 <= last:
                continue
            two = Ls[i] + " " + (Ls[i + 1].strip() if i + 1 < len(Ls) else "")
            for m in pat.finditer(two):
                if m.start() >= len(Ls[i]) + 1:
                    continue
                ctx = two[max(0, m.start() - 80):m.end() + 70]
                if name == "combined rule3.txt" and re.search(rf"R\.{e}(?:\(\d\))?PART|PART 3:COURT ACTIONSR\.{e}", two[max(0, m.start() - 25):m.end() + 25]):
                    continue
                print(f"   {name} l.{i + 1} p.{page} ...{ctx}")
    for tag, files in (("BOOK B", sorted(glob.glob(str(ROOT / "rule*_part*.json")) + [str(ROOT / "rule1_split_document.json")] + glob.glob(str(ROOT / "rule9_p*.json")))),
                       ("BOOK C", sorted(glob.glob(str(ROOT / "[0-9]*_*.json"))))):
        print(f"--- {tag} (all files; the rule's own paragraphs are skipped)")
        for f in files:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
            for t in strings(d):
                t = re.sub(r"\s+", " ", t)
                for m in pat.finditer(t):
                    ctx = t[max(0, m.start() - 90):m.end() + 70]
                    print(f"   {Path(f).name[:24]} ...{ctx}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    n = int(args[0])
    if "--xref-only" not in sys.argv:
        show_official_and_built(n)
        show_book_a(n)
        show_book_b(n)
        show_book_c(n)
    if "--noxref" not in sys.argv:
        xrefs(n)


if __name__ == "__main__":
    main()
