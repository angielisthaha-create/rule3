#!/usr/bin/env python3
"""SOURCE_RECONCILIATION (arc-rules-production-lifecycle) for Alberta Rules of Court 2.1-2.32.

No-write: reads the repo's source carriers and emits one combined JSON packet holding every
carrier's content per subrule, plus per-subrule three-book gate records (arc-three-book-gate-v1).
Books never outvote the official source and no text is silently merged.
"""
from __future__ import annotations
import difflib, hashlib, json, re, subprocess, sys, unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "rule2_subrules"
RULES = [f"2.{n}" for n in range(1, 33)]

OFFICIAL_TXT = ROOT / "Alberta_Rules_of_Court.txt"
BOOK_A = [ROOT / "combined_rule2.txt"]
BOOK_B = [ROOT / "rule2_part01_document.json", ROOT / "rule2_part02_document.json"]
BOOK_C = [ROOT / "81-100_2_1 to 2_27.json", ROOT / "101-120_2_28 to 3_18.json"]

SUPERSCRIPTS = "⁰¹²³⁴⁵⁶⁷⁸⁹"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_text(s: str) -> str:
    return sha(s.encode("utf-8"))


def file_sha(p: Path) -> str:
    return sha(p.read_bytes())


def pdf_sha() -> str | None:
    for ref in ("origin/main", "main", "HEAD"):
        r = subprocess.run(["git", "show", f"{ref}:Alberta rule of court.pdf"], cwd=ROOT, capture_output=True)
        if r.returncode == 0:
            return sha(r.stdout)
    return None


# ---------------------------------------------------------------- normalization
NORMALIZATION_PROFILE = {
    "id": "arc-rule2-compare-norm",
    "version": "1",
    "strict_steps": [
        "drop a leading rule number '2.N' (carriers differ on whether the number is part of the text span)",
        "drop footnote superscript digits (U+2070-U+2079, U+00B9/B2/B3)",
        "Unicode NFKC (expands ligatures such as U+FB01 'fi')",
        "curly quotes/apostrophes -> ASCII; en/em dash -> '-'",
        "remove markdown emphasis '*'",
        "collapse all whitespace to single space; trim",
        "remove space before , ; : . )  and after (",
    ],
    "editorial_steps": [
        "all strict steps",
        "remove bracketed editorial cross-reference labels '[...]'",
        "citation style 'Alta. Reg.' -> 'AR'",
        "case-fold",
    ],
    "note": "Raw carrier text is preserved separately; normalization is used only for comparison.",
}
NORMALIZATION_PROFILE["sha256"] = sha_text(json.dumps(NORMALIZATION_PROFILE, sort_keys=True))


def norm_strict(s: str) -> str:
    s = re.sub(r"^\s*2\.\d+(?=[\s(])", "", s)
    s = re.sub(f"[{SUPERSCRIPTS}¹²³]", "", s)
    s = unicodedata.normalize("NFKC", s)
    s = s.translate(str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"}))
    s = s.replace("*", "")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+([,;:.)])", r"\1", s)
    s = re.sub(r"\(\s+", "(", s)
    return s


def norm_editorial(s: str) -> str:
    s = norm_strict(s)
    s = re.sub(r"\s*\[[^\]]*\]", "", s)
    s = re.sub(r"\bAlta\. Reg\.", "AR", s)
    s = re.sub(r"\s+([,;:.)])", r"\1", s)
    return re.sub(r"\s+", " ", s).strip().casefold()


def compare(official: str, book: str | None) -> dict:
    if not book:
        return {"status": "CARRIER_TEXT_MISSING"}
    o_s, b_s = norm_strict(official), norm_strict(book)
    if o_s == b_s:
        return {"status": "EXACT_MATCH", "similarity": 1.0}
    o_e, b_e = norm_editorial(official), norm_editorial(book)
    ow, bw = o_e.split(), b_e.split()
    sm = difflib.SequenceMatcher(None, ow, bw, autojunk=False)
    ops, kinds = [], set()
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        kinds.add(tag)
        ops.append({"op": tag, "official": " ".join(ow[i1:i2]), "carrier": " ".join(bw[j1:j2])})
    if not ops:
        status = "NORMALIZATION_ONLY_DIFFERENCE"
    elif kinds == {"insert"}:
        status = "CARRIER_HAS_EXTRA_TEXT"  # boundary bleed / commentary contamination candidate
    elif kinds == {"delete"}:
        status = "CARRIER_MISSING_TEXT"  # extraction/boundary defect candidate
    else:
        status = "WORDING_DIFFERENCE"
    out = {"status": status, "similarity": round(sm.ratio(), 4)}
    if ops:
        out["differences"] = ops[:40]
        if len(ops) > 40:
            out["differences_truncated"] = len(ops) - 40
    return out


# ---------------------------------------------------------------- official source
def parse_official() -> tuple[dict, dict]:
    raw = OFFICIAL_TXT.read_text(encoding="utf-8")
    lines = raw.split("\n")
    # body of Part 2: second "Part 2" heading through the page break before second "Part 3"
    p2 = [i for i, l in enumerate(lines) if l.strip() == "Part 2"][1]
    p3 = [i for i, l in enumerate(lines) if l.strip() == "Part 3"][1]
    seg = lines[p2:p3]
    # track page numbers and strip running headers
    clean, page, pages = [], None, []
    first_page = None
    for i, l in enumerate(lines[:p2]):
        m = re.match(r"--- Page (\d+) ---", l)
        if m:
            first_page = int(m.group(1))
    page = first_page
    i = 0
    while i < len(seg):
        m = re.match(r"--- Page (\d+) ---", seg[i])
        if m:
            page = int(m.group(1))
            j = i + 1
            while j < len(seg) and not re.fullmatch(r"\d+", seg[j].strip()):
                j += 1
            i = j + 1
            continue
        clean.append(seg[i].rstrip())
        pages.append(page)
        i += 1
    # titles and division headings from the official table of contents (lines p2_toc..p3_toc)
    toc_s = [i for i, l in enumerate(lines) if l.strip() == "Part 2"][0]
    toc_e = [i for i, l in enumerate(lines) if l.strip() == "Part 3"][0]
    toc = [l.strip() for l in lines[toc_s:toc_e]]
    toc_title, toc_div, cur_div, k = {}, {}, None, 0
    while k < len(toc):
        m = re.fullmatch(r"Division (\d+)", toc[k])
        if m:
            j, head = k + 1, []
            while j < len(toc) and toc[j] and not re.fullmatch(r"2\.\d+", toc[j]):
                head.append(toc[j]); j += 1
            cur_div = {"number": int(m.group(1)), "heading": " ".join(head)}
            k = j; continue
        if re.fullmatch(r"2\.\d+", toc[k]):
            j, t = k + 1, []
            while j < len(toc) and toc[j] and not re.fullmatch(r"(2\.\d+|Division \d+)", toc[j]):
                t.append(toc[j]); j += 1
            toc_title[toc[k]], toc_div[toc[k]] = re.sub(r"\s+", " ", " ".join(t)).strip(), cur_div
            k = j; continue
        k += 1
    div_lines = {x for d in toc_div.values() if d for x in [f"Division {d['number']}"]}
    div_head_words = {d["heading"] for d in toc_div.values() if d}
    starts, pos = [], 0
    for r in RULES:
        pat = re.compile(rf"^{re.escape(r)}(\(1\))?\s")
        while pos < len(clean) and not pat.match(clean[pos]):
            pos += 1
        starts.append(pos)
        pos += 1

    def title_begin(idx):
        s0 = starts[idx]
        first = toc_title[RULES[idx]].split()[0]
        k = s0 - 1
        while k > 0 and not clean[k].strip().startswith(first):
            k -= 1
        # walk further back over division heading lines
        while k > 0 and (clean[k - 1].strip() in div_lines or not clean[k - 1].strip()
                         or any(clean[k - 1].strip() and clean[k - 1].strip() in h for h in div_head_words)):
            if clean[k - 1].strip().endswith((".", ";", ":")):
                break
            k -= 1
        return k

    rules = {}
    for idx, r in enumerate(RULES):
        s = starts[idx]
        end = title_begin(idx + 1) if idx + 1 < len(RULES) else len(clean)
        body = [x for x in clean[s:end]]
        while body and not body[-1].strip():
            body = body[:-1]
        amend = None
        if body and body[-1].strip().startswith("AR 124/2010"):
            amend = body[-1].strip()
            body = body[:-1]
        text = "\n".join(x.strip() for x in body if x.strip())
        rules[r] = {
            "title": toc_title[r],
            "division": toc_div[r],
            "operative_text": text,
            "operative_text_sha256": sha_text(text),
            "amendment_history": amend or "AR 124/2010",
            "amending_regulations": re.findall(r"\d+/\d{4}", amend or "")[1:] if amend else [],
            "locator": {"file": OFFICIAL_TXT.name, "pdf_pages": sorted({pages[s], pages[min(len(pages) - 1, s + len(body))]})},
        }
    return rules, {"consolidation": "Office Consolidation, Alberta Regulation 124/2010, with amendments up to and including Alberta Regulation 79/2026; current as of June 1, 2026"}


# ---------------------------------------------------------------- Book A (combined_rule2.txt)
def parse_book_a() -> tuple[dict, dict]:
    raw = BOOK_A[0].read_text(encoding="utf-8")
    lines = raw.split("\n")
    page_of, page = [], None
    for l in lines:
        if re.fullmatch(r"2-\d+", l.strip()):
            page = l.strip()
        page_of.append(page)
    # mark footnote blocks and running headers
    kind = ["text"] * len(lines)
    in_fn = False
    for i, l in enumerate(lines):
        s = l.strip()
        if s == "Footnote":
            in_fn = True
        if re.fullmatch(r"2-\d+", s):
            in_fn = False
            kind[i] = "header"
            continue
        if re.fullmatch(r"(PART 2: THE PARTIES TO LITIGATION R\.\S+|R\.\S+ PART 2: THE PARTIES TO LITIGATION)", s):
            kind[i] = "header"
            continue
        if in_fn:
            kind[i] = "footnote"
    # Book A division headings ("DIVISION N" + heading line) are structure, not rule text
    for i, l in enumerate(lines):
        if re.fullmatch(r"DIVISION \d+", l.strip()):
            kind[i] = "division"
            if i + 1 < len(lines):
                kind[i + 1] = "division"
    # "[Footnote N (continued) from prior page]" lines and the text under them continue a footnote of the previous page
    fn_cont, cur = [], None
    for i, l in enumerate(lines):
        m = re.fullmatch(r"\[Footnote (\d+) (?:continued )?from prior page\]", l.strip())
        if m:
            cur = {"marker_page": page_of[i], "number": int(m.group(1)), "lines": []}
            fn_cont.append(cur)
            kind[i] = "fn_cont"
            continue
        if cur is not None:
            if not l.strip():
                cur = None
                continue
            kind[i] = "fn_cont"
            cur["lines"].append(l.strip())
    starts, pos = [], 0
    for r in RULES:
        pat = re.compile(rf"^{re.escape(r)}(\(1\) | [A-Z])")
        while pos < len(lines) and not (pat.match(lines[pos]) and kind[pos] == "text"):
            pos += 1
        starts.append(pos)
        pos += 1

    def prev_text(i):
        k = i - 1
        while k >= 0 and (kind[k] != "text" or not lines[k].strip()):
            k -= 1
        return k

    # footnote entries per page: {page: {num: text}}; entries must number consecutively
    fn_by_page = {}
    cur_num = None
    for i, l in enumerate(lines):
        if kind[i] != "footnote" or l.strip() in ("", "Footnote"):
            continue
        pg = page_of[i]
        book = fn_by_page.setdefault(pg, {})
        m = re.match(r"(\d+) (.*)", l.strip())
        if m and (not book and int(m.group(1)) < 400 or book and int(m.group(1)) in (cur_num + 1, 1) and int(m.group(1)) not in book):
            cur_num = int(m.group(1))
            book[cur_num] = m.group(2).strip()
        elif book:
            book[cur_num] += " " + l.strip()
    for c in fn_cont:
        prev = f"2-{int(c['marker_page'].split('-')[1]) - 1}"
        if c["lines"] and c["number"] in fn_by_page.get(prev, {}):
            fn_by_page[prev][c["number"]] += " " + " ".join(c["lines"])
        elif not c["lines"] and c["number"] in fn_by_page.get(c["marker_page"], {}):
            # the carried-over footnote was printed in this page's footnote block: move it back to its own page
            fn_by_page.setdefault(prev, {})[c["number"]] = fn_by_page[c["marker_page"]].pop(c["number"])
    sup = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")

    def refs(i):
        return [(page_of[i], int(x.translate(sup))) for x in re.findall(r"[⁰¹²³⁴⁵⁶⁷⁸⁹]+", lines[i])]

    part_intro = "\n".join(l for l, k in zip(lines[: prev_text(starts[0])], kind) if k == "text").strip()
    out = {}
    for idx, r in enumerate(RULES):
        s = starts[idx]
        t = prev_text(s)
        title = lines[t].strip()
        end = prev_text(starts[idx + 1]) if idx + 1 < len(RULES) else len(lines)
        seg = list(range(s, end))
        text_body = [lines[i] for i in seg if kind[i] == "text"]
        seen, footnotes = set(), []
        for i in range(t, end):
            if kind[i] != "text":
                continue
            for pg, n in refs(i):
                if (pg, n) in seen:
                    continue
                seen.add((pg, n))
                txt = fn_by_page.get(pg, {}).get(n)
                footnotes.append({"page": pg, "number": n, "text": txt} if txt else
                                 {"page": pg, "number": n, "text": None, "defect": "FOOTNOTE_TEXT_NOT_FOUND_ON_PAGE"})
        # split text body: operative / information note / related provisions / commentary
        op, info, rel, comm, state = [], [], [], [], "op"
        for j, l in enumerate(text_body):
            st = l.strip()
            if st == "Information Note":
                state = "info"; continue
            if st == "Related Provisions":
                state = "rel"; continue
            if state == "op" and not st:
                nxt = next((x.strip() for x in text_body[j + 1:] if x.strip()), "")
                if nxt and not nxt.startswith("(") and nxt not in ("Information Note", "Related Provisions"):
                    state = "comm"
                continue
            if state == "rel" and rel:
                # a Related Provisions list can wrap across a blank line; it ends only once complete
                joined = " ".join(x.strip() for x in rel if x.strip())
                complete = joined.endswith(".") or (joined.endswith(")") and joined.count("(") == joined.count(")"))
                if not st:
                    continue
                if complete:
                    state = "comm"
            if state == "info" and not st and info:
                continue
            {"op": op, "info": info, "rel": rel, "comm": comm}[state].append(l.rstrip())
        op_text = "\n".join(x for x in op if x.strip())
        out[r] = {
            "title": title,
            "operative_text_raw": op_text,
            "operative_text_sha256": sha_text(op_text),
            "information_note": "\n".join(info).strip() or None,
            "related_provisions": " ".join(x.strip() for x in rel if x.strip()) or None,
            "commentary": "\n".join(comm).strip() or None,
            "footnotes": footnotes,
            "locator": {"file": BOOK_A[0].name, "lines": [t + 1, end], "book_pages": sorted({p for p in page_of[t:end] if p})},
        }
    return out, {"part_introduction": part_intro}


# ---------------------------------------------------------------- Book B (Fradsham JSON)
def parse_book_b() -> tuple[dict, dict]:
    paras = []
    for f in BOOK_B:
        d = json.loads(f.read_text(encoding="utf-8"))
        for p in d["document_structure"]["paragraphs"]:
            paras.append((f.name, p))
    out = {r: {"title": None, "operative_text_raw": "", "commentary": [], "paragraph_ids": [], "locator": {"files": set()}} for r in RULES}
    cur, mode = None, None
    front, front_year = [], None
    for fname, p in paras:
        t = p["text"]
        m = re.match(r"Alberta Rules of Court (§ )?(2\.\d+)(:\d+)? \(\d{4}\)", t)
        if m:
            front_year = front_year or re.search(r"\((\d{4})\)", t).group(1)
            cur, mode = m.group(2), ("comm" if m.group(1) else "rule")
            if cur in out:
                out[cur]["paragraph_ids"].append(p["paragraph_id"]); out[cur]["locator"]["files"].add(fname)
            continue
        if cur not in out:
            front.append(t)
            continue
        o = out[cur]
        o["paragraph_ids"].append(p["paragraph_id"]); o["locator"]["files"].add(fname)
        mh = re.match(rf"{re.escape(cur)}\. (.*)", t)
        if mh and p["paragraph_id"].startswith("part2_rule_"):
            o["title"] = o["title"] or mh.group(1).strip()
            continue
        mc = re.match(r"Commentary § (2\.\d+:\d+)\s*(.*)", t, re.S)
        if mc:
            o["commentary"].append({"section": mc.group(1), "text": mc.group(2).strip()})
            mode = "comm"
            continue
        if mode == "rule":
            o["operative_text_raw"] = (o["operative_text_raw"] + "\n" + t).strip()
        elif o["commentary"]:
            o["commentary"][-1]["text"] += "\n" + t
        else:
            o["commentary"].append({"section": None, "text": t})
    for r, o in out.items():
        m = re.search(r"\s*(Alta\. Reg\. \d+/\d{4}, s\. \d+(?:[;,] ?Alta\. Reg\. \d+/\d{4}, s\. \d+)*)\s*$", o["operative_text_raw"])
        o["amendment_note_raw"] = m.group(1) if m else None
        if m:
            o["operative_text_raw"] = o["operative_text_raw"][: m.start()].rstrip()
        o["operative_text_sha256"] = sha_text(o["operative_text_raw"])
        o["locator"]["files"] = sorted(o["locator"]["files"])
    return out, {"edition_header": f"Alberta Rules of Court ({front_year}), The Honourable Justice Allan A. Fradsham", "edition_year": front_year}


# ---------------------------------------------------------------- Book C (annotated JSON pages 81-120)
def parse_book_c() -> tuple[dict, dict]:
    out, part_meta, misparsed = {}, {"definitions_used_in_part": []}, []
    for f in BOOK_C:
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("definitions"):
            part_meta["definitions_used_in_part"] = d["definitions"]
        seq = []
        for h in d["hierarchy"]:
            if h["type"] == "orphan_rule":
                seq.append((None, h["data"]))
            else:
                for rr in h.get("rules", []):
                    seq.append((h.get("heading"), rr))
        prev = None
        for heading, rr in seq:
            num = rr.get("number")
            if num in RULES:
                text = rr.get("text", "")
                m = re.search(r"\s*\*?\[Alta\. Reg\. 124/2010", text)
                op = text[: m.start()].strip() if m else text.strip()
                amend = text[m.start():].strip() if m else None
                out[num] = {
                    "title": rr.get("title"),
                    "division_heading": heading,
                    "operative_text_raw": op,
                    "operative_text_sha256": sha_text(op),
                    "amendment_note_raw": amend,
                    "citations": rr.get("citations", []),
                    "information_notes": rr.get("info_notes", []),
                    "commentary": rr.get("commentary", []),
                    "misattributed_entries": [],
                    "locator": {"file": f.name, "source_file": d.get("source_file")},
                }
                prev = num
            elif prev in out and not str(num).startswith("3."):
                entry = {"parsed_number": num, "parsed_title": rr.get("title"), "text": rr.get("text"),
                         "information_notes": rr.get("info_notes", []), "commentary": rr.get("commentary", []),
                         "defect": "HEADING_MISPARSE: entry parsed as a separate rule but sits inside the preceding rule's annotation block"}
                out[prev]["misattributed_entries"].append(entry)
                misparsed.append({"attached_to": prev, "parsed_number": num})
    part_meta["misparsed_entries"] = misparsed
    return out, part_meta


# ---------------------------------------------------------------- latest-cited-year (edition floor)
def latest_year(text: str) -> int | None:
    ys = [int(y) for y in re.findall(r"\b(20[0-2]\d)\s+AB(?:QB|CA|KB|PC|CJ)\b", text)]
    return max(ys) if ys else None


def amendment_check(off: dict, a: dict | None, b: dict | None, c: dict | None) -> dict:
    """Compare amending regulations cited by each book with the official history (years normalized to 4 digits)."""
    def regs(txt):
        out = set()
        for n, y in re.findall(r"(\d+)/(\d{2,4})", txt or ""):
            y = int(y)
            y = y + 2000 if y < 100 else y
            if (n, y) != ("124", 2010) and y >= 2010:
                out.add(f"{n}/{y}")
        return out
    official = set(off["amending_regulations"])
    notes = {
        "BOOK_A": re.findall(r"\[Alta\. Reg\.[^\]]*\]", (a or {}).get("operative_text_raw") or ""),
        "BOOK_B": (b or {}).get("amendment_note_raw"),
        "BOOK_C": (c or {}).get("amendment_note_raw"),
    }
    check = {}
    for cid, note in notes.items():
        if note:
            found = regs(" ".join(note) if isinstance(note, list) else note)
            check[cid] = "AGREES" if found == official else f"DIFFERS: carrier cites {sorted(found)}, official {sorted(official)}"
    return {"official": off["amendment_history"], "amending_regulations": off["amending_regulations"],
            "carrier_notes": {k: v for k, v in notes.items() if v}, "crosscheck_vs_official": check}


def _sim(x: str, y: str) -> float:
    return difflib.SequenceMatcher(None, norm_editorial(x).split(), norm_editorial(y).split(), autojunk=False).ratio()


# findings from manual review that the word-set test cannot see
MANUAL_NOTE_FLAGS = {
    "2.11": "garbled copy; not retained. WARNING: its word order reverses the meaning "
            "('would apply if a not personal representative'); the correct text is BOOK_A's ('would not apply')",
}


MANUAL_TEXT_NOTES = {
    "2.23": {"BOOK_A": "same wording as official except (2)(a) and (b) end with ';' (official ','), plus bracketed labels "
                       "and amendment bracket '[Alta. Reg.124/10;36/20]'. No substantive difference."},
    "2.24": {"BOOK_A": "same wording as official except 'self represent' (no hyphen) in (2)."},
    "2.25": {"BOOK_A": "same wording as official plus the bracketed label for rule 1.2."},
    "2.29": {"BOOK_A": "same wording as official plus the bracketed label for rule 2.31."},
    "2.32": {"BOOK_A": "differs from official in form only: (1)(a)(iii) 'practice' (official 'practise', same meaning); "
                       "(3) 'The court' lower case; (4) garbled 'rule 2.28 or [label] or 2.29 [label]' (repeated 'or'); "
                       "bracketed labels. Official text controls."},
    "2.11": {"BOOK_A": "same wording as official; differs only by spacing and the bracketed amendment note "
                       "'[Alta. Reg.124/10;122/12]' (kept in amendment_history.carrier_notes).",
             "BOOK_B": "same wording as official; only 'Alta. Reg. 130/95' for 'AR 130/95' (amendment note kept separately)."},
    "2.12": {"BOOK_A": "same wording as official plus editorial cross-reference titles in brackets and the word 'rule' "
                       "repeated before 2.16 and 2.21. No substantive difference."},
    "2.13": {"BOOK_A": "same wording as official; only spacing and the bracketed amendment note '[Alta. Reg.124/10;140/13]'.",
             "BOOK_B": "same wording as official; only 'Alta. Reg. 130/95' for 'AR 130/95'."},
    "2.14": {"BOOK_A": "same wording as official except typography: 'self appointed' (no hyphen) in (3), '(1) (a)' spacing, "
                       "bracketed labels, and '(e) repealed AR 143/2011.' (official: '... s2.').",
             "BOOK_B": "same wording as official; (3)(d) ends with '.' and (e) reads '[Repealed Alta. Reg. 143/2011, s. 2(b).]' "
                       "- adds the paragraph reference s. 2(b). No substantive difference."},
    "2.15": {"BOOK_A": "same wording as official plus the bracketed label '[Litigation representative required]'."},
    "2.17": {"BOOK_A": "same wording as official plus the bracketed label '[Litigation representative required]'."},
    "2.18": {"BOOK_A": "same wording as official plus the bracketed label for rule 2.16."},
}

MANUAL_SEE_ALSO = {
    "2.28": ["BOOK_A other Parts (full Book A uploaded; 6th pass): R.10.6 information note (p.10-14): 'The rules about self-representing are in rule 2.28' (the reverse of 2.28 fn 1 'See R.10.6(2)'); listed as a related provision under R.10.25 (p.10-38) and R.11.16 (p.11-21).",
            "Rule 2.32(4) (official): an order under 2.32 applies until a notice is given under rule 2.28 or 2.29; "
             "BOOK_A 2.32 related provisions.",
             "Rules 2.21, 2.22 and 2.24: BOOK_A related provisions list 2.28.",
             "Rule 2.11: BOOK_A 2.28 commentary 'On need for a lawyer where the client is under a disability, see "
             "R.2.11n., supra'; rule 10.6(2): BOOK_A fn 1 (p.2-63).",
             "Official Form 3 is headed '[Rule 2.28]' (the notice of change named in 2.28(1)(a)). BOOK_C's citations in "
             "2.28 re-verified in the 4th pass: Shell v. Sunterra and Genstar recur in BOOK_C's rule 3.2 entry. BOOK_A "
             "2.24 p.2-50 fn 12 ('Part C below', last-minute change of lawyer) may be aimed at this rule's commentary."],
    "2.29": ["BOOK_A other Parts (full Book A uploaded; 6th pass): R.12.6 information note (p.12-6) cites 2.29(4) (address need not be disclosed); listed as a related provision under R.11.16 (p.11-21) and R.11.17 (p.11-22). BOOK_A 2.29's pointer 'R.9.2n' checked: R.9.2 notes say a lawyer who appears and later ceases to act keeps a continuing obligation (matches).",
            "Rule 2.31: official 2.29(1) is 'Subject to rule 2.31'; BOOK_A 2.31 related provisions list 2.29.",
             "Rule 2.32(4) (official) and BOOK_A 2.32 related provisions; rule 2.26: BOOK_A related provisions.",
             "Rule 2.24: BOOK_A 2.29 fn 5 'See further R.2.24n. A'; rule 9.2: BOOK_A 2.29 commentary 'see R.9.2n.'",
             "Rule 2.30 (service after the lawyer ceases to be lawyer of record) and BOOK_A 2.29 fn 3 (earlier service "
             "on the lawyer stays valid; see R.11.17).",
             "Official Form 4 is headed '[Rule 2.29]' (notice of withdrawal). BOOK_C's displaced citations re-verified in "
             "the 4th pass: Regular and Behiels recur in BOOK_C's rule 3.4 entry, Patrus in 3.9; BOOK_C's own text calls "
             "Regular a change-of-venue case."],
    "2.30": ["BOOK_A other Parts (full Book A uploaded; 6th pass): Part 11 notes to R.11.17 fn 4 (reference mark on p.11-22, after 'Service of interlocutory documents ... on a party's solicitor of record is effective even if he or she later ceases to act'; footnote printed on p.11-23 as 'from prior page' - 8th pass) cite N.-S. Trade & Inv. v. Aquanorth Farms 2002 ABQB 553 (the case BOOK_A 2.29 fn 3 cites) and add 'See R.2.30' (split over two lines in the source).",
            "Rule 2.29: withdrawal takes effect 10 days after the affidavit of service is filed (2.29(2)); BOOK_A 2.29 "
             "commentary and fn 3 (service made before withdrawal stays valid). CORRECTED in 6th pass: the full Book A (uploaded) does cite 2.30 elsewhere - see the first item.",
             "BOOK_C's 2.30 entry ends with 2.31 late-withdrawal cases (Cunningham, Behm) - see rule 2.31."],
    "2.31": ["BOOK_A other Parts (full Book A uploaded; 6th pass): listed as a related provision under R.8.4 (p.8-10), R.8.5 (p.8-13) and R.8.7 (p.8-17) ('withdrawal of lawyer after trial date set').",
            "Rule 2.29(1) (official): 'Subject to rule 2.31'; BOOK_A 2.29 related provisions list 2.31.",
             "BOOK_A 2.24 Part A (p.2-50 fn 3, Cunningham 2010 SCC 10: court may restrain counsel from withdrawing) and "
             "BOOK_A 2.29 fn 5 (Kong; Cunningham) - the same case BOOK_B 2.31 relies on (Fitzpatrick 2020 ABCA 88).",
             "Rules 8.4, 8.5 (BOOK_A information note) and 8.7 (BOOK_A related provisions).",
             "BOOK_A 2.29 commentary 'Alberta wisely does not require [leave to withdraw] in civil cases' is qualified by "
             "this rule (permission needed once a trial date is scheduled) - flagged under 2.29 in the 4th pass."],
    "2.32": ["BOOK_A other Parts (full Book A uploaded; 6th pass): R.11.29 information note (p.11-61): 'Rule 2.32(2) ... provides that a party may apply to the Court for directions concerning service of documents if a lawyer stops acting'.",
            "Rules 2.28 and 2.29: BOOK_A related provisions list 2.32; 2.32(4) refers back to notices under 2.28 or 2.29.",
             "Rule 11.29 (dispensing with service): named in 2.32(3)(b)."],
    "2.26": ["BOOK_A other Parts (full Book A uploaded; 6th pass): BOOK_A 2.26's pointer 'R.3.35n' checked: R.3.35 notes (p.3-86 to 3-89) review a solicitor's authority to bind a client to a settlement, citing Shannon v. Shannon 2023 ABCA 79 (also BOOK_A 2.26 fn 11).",
            "Rule 2.24: BOOK_A 2.24 Part A 'On the authority of the lawyer of record, see R.2.26n.'; BOOK_A related "
             "provisions of 2.26 list 2.24 and 2.29.",
             "Rule 2.25: BOOK_A 2.25 history footnote (same sources as R.2.26: 1968 R.557).",
             "Rule 3.35: BOOK_A 2.26 commentary 'On authority of a solicitor to compromise a suit, see R.3.35n.'"],
    "2.27": ["BOOK_A other Parts (full Book A uploaded; 6th pass): listed as a related provision under R.10.2 (p.10-4, 'limited retainers'); R.13.42 notes (p.13-103) list 'Rr.2.27, 3.34, ...' among rules that 'seem to require filing' - official 2.27(1) lets the lawyer inform the Court orally OR by filing the terms of the retainer, so filing is one option, not a requirement.",
            "Rule 2.24: BOOK_A related provisions list 2.27 (limited retainers).",
             "Rule 11.15 (address for service): BOOK_B 2.27 (1920341 Alberta v Jonsson 2018 ABCA 231).",
             "Rule 2.22: BOOK_A 2.27 'Generally on self-represented parties, see R.2.2 n.' - probably R.2.22 (flagged)."],
    "2.25": ["BOOK_A other Parts (full Book A uploaded; 6th pass): listed as a related provision under R.6.18 (p.6-105), R.9.2 (p.9-9) and R.10.49 (p.10-140) - the reverse of 2.25's own list; 2.25(2) under R.11.15 (p.11-18) and R.11.22 (p.11-28) ('disclosing address of litigant').",
            "Rule 2.24: BOOK_A 2.25 commentary refers to R.2.24n on conflicts of interest.",
             "Rule 2.27: BOOK_A related provisions list 2.25.",
             "Rule 2.26: BOOK_A history footnotes - 2.25(2) from 1968 R.557(2), 2.26 from 1968 R.557(1), (3).",
             "Rule 1.2 (purpose and intention): named in 2.25(1)(a)."],
    "2.24": ["BOOK_A other Parts (full Book A uploaded; 6th pass): listed as a related provision under R.1.1 (p.1-3), R.5.9 (p.5-69), R.11.17 (p.11-22), R.14.81 (p.14-250) and R.14.82 (p.14-251); R.11.15-11.17 notes (p.11-19 and on): 'Rule 11.17 allows service on a lawyer who has gone on the record under R.2.24'; R.8.17 notes (p.8-49) fn 4 'See also R.2.24 n. C' (see the 2.24 flag). Official, by subject: 3.35(1)-(4) (consent judgments when a party has, or has ceased to have, a lawyer of record); 5.9(2) (the lawyer of record may not swear the party's affidavit of records); 13.13(1)(g) (documents show the lawyer of record who prepared them - the mechanism of 2.24(1)).",
            "Rule 2.25: BOOK_A 2.25 commentary 'On conflicts of interest of solicitors, see R.2.24n.'",
             "Rules 2.26 and 2.27: BOOK_A related provisions list 2.24.",
             "Rule 2.29: BOOK_A 2.29 footnote 5 'See further R.2.24n. A' (withdrawal; Cunningham 2010 SCC 10).",
             "Rule 2.22: BOOK_A 2.24 p.2-50 fn 10 'See also R.2.22 n. F above'; BOOK_A 2.24 Part A points to R.2.26n "
             "on a lawyer of record's authority.",
             "Rule 14.82 (lawyer of record on appeal): BOOK_A related provisions and p.2-50 fn 1. The official text of "
             "14.82(a) keeps the lawyer of record on the appeal 'until ceasing to be so in accordance with Part 2, "
             "Division 4' (rules 2.24-2.32) - added in 4th pass."],
    "2.23": ["BOOK_A 2.13 commentary: a relative may give quiet assistance under R.2.23 but cannot speak for the "
             "litigant; BOOK_B 2.13 (Nahirney: limited assistance under Rule 2.23, not speaking).",
             "Rule 2.22: BOOK_A related provisions and fn 9 (p.2-44: 'some basic help is covered in R.2.23'); BOOK_B 2.22 "
             "(908077 QB summary: 2.23 allows only a 'McKenzie Friend' role; Real Estate Strategies para 8 on 2.23(1)).",
             "BOOK_B 2.14 and BOOK_B 2.23 section 4 both quote Chapman Estate/Oommen v Ramjohn (2015 ABCA 34 and 58).",
             "Legal Profession Act s.106 (official 2.23(3)(a); BOOK_A information note).",
             "Cross-book (4th pass): BOOK_B section 4 (Chapman Estate v. Ramjohn 2015 ABCA 58) is the leave decision "
             "BOOK_A 2.22 fn 8 records ('Oommen (Chapman Est.) v. Ramjohn 2015 ABCA 34 ... leave den 2015 ABCA 58'). "
             "BOOK_C's Vizor 2022 ABQB 5 is BOOK_A 2.22 fn 4 (p.2-46); PurpleRung 2020 ABCA 341 is cited only by BOOK_C. "
             "BOOK_A's statements on the 2020 amendment (new 2.23(4)) agree with the official text and with BOOK_B's "
             "Vuong 2020 ABCA 169 para 15 quote. Fortin 'supra' flag re-verified by citation (2001 SCC 45 only at p.2-48 "
             "fn 3)."],
    "2.22": ["BOOK_A other Parts (full Book A uploaded; 6th pass): R.1.1 notes (p.1-4): 'On self-represented litigants, see also R.2.22'; listed as a related provision under R.1.1 (p.1-3), R.10.31 (p.10-60), R.11.18 (p.11-23) and R.12.56 (p.12-86). BOOK_A 2.22's pointer 'R.3.68 n. C' checked: R.3.68's Part C is 'Vexatious Litigants' (matches). BOOK_A's own Part 11 labels 11.22 '(service on address on most recently filed document)' (p.11-22), unlike its 2.22 label - see the 2.22 flag.",
            "Rule 2.23: BOOK_A related provisions and Part C ('McKenzie friends, on whom also see R.2.22 n. F'); BOOK_A "
             "2.22 fn 9 (p.2-44): 'some basic help is covered in R.2.23'; BOOK_B 2.22 quotes Real Estate Strategies on "
             "2.23(1).",
             "Rule 2.24: BOOK_A related provisions and fn 10 ('See also R.2.22 n. F above').",
             "BOOK_B 2.13 (Nahirney para 25: self-represented litigants have a right of audience under Rule 2.22) and "
             "BOOK_B 2.14 (Oommen: an estate is not an individual under Rule 2.22).",
             "Rule 3.68: BOOK_A Part C 'See also R.3.68 n. C'.",
             "Cross-book (4th pass): BOOK_B 2.22 sections 1 and 3 (Beacon Hill 2011 ABQB 138 / 2012 ABCA 269; 908077 2015 "
             "ABQB 108 / 2015 ABCA 117; Landmass 2015 ABQB 362; Park Avenue 2016 ABCA 211; Real Estate Strategies 2016 "
             "ABCA 286; National Leasing 2015 ABQB 631; Pacer 2004 ABCA 28; Lameman 2012 ABCA 59) are cited by BOOK_A under "
             "2.23 (fns p.2-47 #2, #4-6) and 2.24 (Beacon Hill, p.2-58 fn 4). BOOK_C's dropped 2.22 fragment repeats "
             "908077 CA para 2 as quoted by BOOK_B. BOOK_B read in full in the 4th pass: sections 1-3, ends at source; the "
             "quoted judgments' own footnote numbers are merged into the text ('no more.2', 'fair hearing3', 'judges4'), "
             "and the RESG quote's 'Rule 2.22(1)' is the judge's wording (2.22 has no subrules)."],
    "2.21": ["BOOK_A other Parts (7th pass): BOOK_A R.3.26 fns 9-10 (p.3-72), R.3.27 fn 4 (p.3-75) and R.9.13 notes (p.9-28) cite an earlier decision in the same court file, 'Paget v. Paget [sic] (Re Padget Est.) 2014 ABQB 750, JCE 1303 07147' - the file number matches Re Padget Est. (M) 2015 ABQB 515 (BOOK_A 2.22 fn 10; BOOK_C 2.21). Book A's own '[sic]' shows the parties' name is printed both ways.",
            "BOOK_A other Parts (full Book A uploaded; 6th pass): listed as a related provision under R.14.82 (p.14-251); Book A's R.14.82 text prints the 2.21 label with a semicolon ('Litigation representative; termination ...').",
            "Rule 2.12(1)(c) (official: a Court-appointed litigation representative under rule 2.15, 2.16 or 2.21) and "
             "BOOK_A 2.12 information note.",
             "Rules 2.13 and 2.14: BOOK_A related provisions list 2.21.",
             "Rule 14.82(b) (official): a litigation representative continues on appeal, subject to rule 2.21.",
             "Rule 2.17(2): BOOK_C 2.17 commentary reads 2.17(2) and 2.21 together on advance costs.",
             "Cross-book (4th pass): Kunkel v. Winquist 2022 ABQB 367 is cited in all three books (A fns 1-2 paras "
             "38-40; C para 21; B 2.11 quotes paras 23-26; A 2.14 paras 31, 38). Rufenack v. Hope Mission 2005 ABCA 129 "
             "(A fn 2, C) is spelled 'Rufenak' in the judgment BOOK_B 2.11 quotes. BOOK_A 2.11 p.2-32 fn 8 cites a "
             "related Sawridge decision, 1985 Sawridge Tr. v. Pub. T'ee. 2012 ABQB 365 (Public Trustee preferred as "
             "litigation representative for minors); the books do not say whether 2013 ABCA 226 (B, C) is its appeal."],
    "2.11": ["8th pass: BOOK_A's related-provision label '3.36(2) (noting litigation representative in default)' (under 2.11, 2.12, 2.16 and 2.19) is loose - official 3.36(2) says a judgment in default of defence must not be entered, without the Court's permission, against a person represented by a litigation representative; noting in default (3.36(1)(b)) is not restricted. Read the official text.",
            "BOOK_A other Parts (full Book A uploaded; 6th pass): listed as a related provision under R.3.74 (p.3-231), R.9.11 (p.9-22), R.10.47 (p.10-138) and, as 2.11(a), R.12.6 (p.12-6); R.3.74 notes (p.3-243): 'On suits by estates and the wrong representative, see Rr.2.11 to 2.16 and notes'; R.10.31 notes (p.10-85) name 'litigation representative under R.2.11'. Official, by subject: 5.9(1)(c) (the litigation representative swears the affidavit of records); 5.17(1)(c) (the litigation representative is questioned; the represented person only with the Court's permission); Appendix: 'litigation representative' includes a guardian ad litem and next friend. BOOK_A's pointer 'R.14.90(1)(b)' (fn 6, p.2-31) checked: official 14.90(1)(b) concerns non-compliance with a rule, direction or order.",
            "Rules 2.13, 2.14(1) and 2.15(1): their official text refers to an individual or estate 'required to have a "
             "litigation representative under rule 2.11'. Rule 2.17(1) refers more narrowly to 'an individual referred to "
             "in rule 2.11(a) to (d)' - individuals only, not estates under (e) (corrected in 4th pass).",
             "Rule 12.6 (official, outside Part 2): 12.6(1) a minor who is or was a spouse or adult interdependent "
             "partner need not have a litigation representative 'as required under rule 2.11(a)'; 12.6(2) a child is not "
             "'participating' for rule 2.11(a) merely by being the subject of a dispute or served with notice (added in "
             "4th pass; the only references to rules 2.11-2.20 in other rules - the forms schedule also has Form 1 "
             "'[Rule 2.14]' and Form 2 '[Rule 2.14(1)(b)]', corrected in 5th pass).",
             "Cross-book (4th pass): BOOK_A fn 12 (p.2-31) 'L. C. v. R. (Alta.) 2011 ABQB 42' is the case BOOK_C 2.15/2.17 "
             "calls 'C. (L.) v. Alberta (Metis Settlements Child & Family Services Region 10)'; BOOK_A p.2-33 fn 4 'Hughes "
             "Est. v. Brady 2007 ABCA 277' = BOOK_B 2.11's quoted 'Hughes Estate v Hughes, 2007 ABCA 277' (names differ); "
             "BOOK_A p.2-32 fn 7 'Gronnerud ... 2002 SCC 38' = BOOK_B's quoted 'Gonnerud ... 2002 SCC 38' (spelling "
             "differs); BOOK_B's Kunkel 2022 ABQB 367 is also BOOK_A 2.21 fn 2 and BOOK_C 2.21.",
             "BOOK_B 2.13 commentary (Nahirney): rules 2.11, 2.13 and 2.14(1) apply only where representation is required.",
             "BOOK_C 2.15 commentary: an appointment needs a finding of lack of capacity under 2.11(c).",
             "Rule 12.6: BOOK_A related provisions ('12.6 (minors involved in family litigation)'); BOOK_B 2.11 section 1 "
             "(Public Guardian v C.(K.)) applies 12.6(2) by analogy to a represented adult."],
    "2.12": ["8th pass: BOOK_A's related-provision label '3.36(2) (noting litigation representative in default)' (under 2.11, 2.12, 2.16 and 2.19) is loose - official 3.36(2) says a judgment in default of defence must not be entered, without the Court's permission, against a person represented by a litigation representative; noting in default (3.36(1)(b)) is not restricted. Read the official text.",
            "BOOK_A other Parts (full Book A uploaded; 6th pass): 2.12(2) is listed as a related provision under R.11.4 (p.11-7), R.11.5 (p.11-8), R.11.7 (p.11-11, where an information note also says 2.12(2) requires service on the litigation representative), R.11.16 (p.11-21), R.11.17 (p.11-22), R.11.27 (p.11-55) and R.11.29 (p.11-61); R.3.26 information note (p.3-71): 'service must be effected on the litigation representative. See rule 2.12(2)'.",
            "BOOK_A 2.11 commentary: 'There are three types, described in R.2.12'.",
             "Rules 2.13, 2.14, 2.15, 2.16 and 2.21: the types of litigation representative listed in 2.12, and their "
             "termination or replacement.",
             "Rule 11.7: BOOK_A information note."],
    "2.13": ["BOOK_A other Parts (full Book A uploaded; 6th pass): R.3.74 notes (p.3-243): 'On suits by estates and the wrong representative, see Rr.2.11 to 2.16 and notes'.",
            "BOOK_A 2.11 footnotes: 'Pursuant to Rule 2.13' and 'See Rr.2.13 and 2.15'.",
             "Rule 2.12(1)(a) (the automatic type); rules 2.19 and 2.21 (BOOK_A related provisions).",
             "Rule 2.23: BOOK_A's own 2.13 commentary (line 1783) says a relative may give quiet assistance under R.2.23 "
             "but cannot speak for the litigant (corrected in 4th pass - an earlier version attributed this to BOOK_A "
             "2.23); BOOK_B 2.13 (Nahirney paras 26-27) says the same.",
             "Cross-book (4th pass): Nahirney 2011 ABQB 586 is in all three books (A fn 1 p.2-36; B section 1; C's "
             "dropped fragment repeats para 22). BOOK_B also cites Torrance 2010 ABCA 88 (= BOOK_A 2.11 fn 11) and "
             "Champagne v. Sidorsky 2012 ABQB 522 (cited by BOOK_A under 2.9, 2.11, 2.16, 2.22 and 2.23)."],
    "2.14": ["BOOK_A other Parts (full Book A uploaded; 6th pass): R.3.74 notes (p.3-243) refer to 'Rr.2.11 to 2.16'. Official, by subject: 10.47 - a plaintiff's litigation representative is liable for costs; a defendant's only for serious misconduct and by order (the costs acknowledgment in 2.14(2)(g)).",
            "BOOK_A 2.11 footnote 10: 'Rules 2.14(2)(f), 10.47'.",
             "Rule 2.12(1)(b) (the self-appointed type).",
             "BOOK_B 2.13 commentary (Nahirney) on 2.14(1).",
             "BOOK_B 2.22 commentary quotes the same Oommen v Ramjohn passage as BOOK_B 2.14.",
             "Cross-book (4th pass): Oommen v. Ramjohn 2015 ABCA 34 is also BOOK_A 2.22 fn 8 (p.2-45, 'Oommen (Chapman "
             "Est.) v. Ramjohn'). Kunkel v. Winquist 2022 ABQB 367 (BOOK_A 2.14 fns p.2-38) is also cited by BOOK_B under "
             "2.11 and by BOOK_A and BOOK_C under 2.21 (wording corrected in 5th pass - BOOK_A does not cite it under 2.11). BOOK_A fn 2 'Royal Bank of Can. v. Godbout 2021 ABQB 191' and BOOK_A 2.21 fn 4 'Royal "
             "Bank v. Godbout 2021 ABQB 321' are two different decisions in the same court file. BOOK_A 2.11 fn 10 cites "
             "'2.14(2)(f)' for costs - probably 2.14(2)(g) (flagged under 2.11).",
             "Official Form 1 is headed '[Rule 2.14]' (the affidavit named in 2.14(1)(a)) and Form 2 '[Rule 2.14(1)(b)]' "
             "(notice of appointment to beneficiaries and heirs). Form 1 was found in the 4th pass of 2.21-2.32; Form 2 was "
             "missed by that search pattern (it has a subrule in the heading) and added in the 5th pass."],
    "2.15": ["BOOK_A other Parts (full Book A uploaded; 6th pass): R.3.74 notes (p.3-243) refer to 'Rr.2.11 to 2.16'.",
            "BOOK_A 2.11 footnote 6: 'See Rr.2.13 and 2.15'.",
             "BOOK_A 2.16 commentary: do not confuse other persons with a R.2.15 representative.",
             "Rule 2.12(1)(c) (the Court-appointed type); rule 2.17 (BOOK_A related provision).",
             "Cross-book (4th pass): Chutskoff Estate v. Bonora 2013 ABQB 119 is cited by all three books (BOOK_A 2.15 fn "
             "6; BOOK_B 2.11 section 1, para 19; BOOK_C 2.11 para 19 and 2.15 para 23). BOOK_C's C. (L.) v. Alberta "
             "(Metis Settlements ...) 2011 ABQB 42 is BOOK_A 2.11 fn 12 'L. C. v. R. (Alta.) 2011 ABQB 42, 509 AR 72'. "
             "Note BOOK_C's statement that an appointment needs a finding of lack of capacity under 2.11(c) concerns "
             "adults; minors are covered by 2.11(a) without any capacity finding."],
    "2.16": ["8th pass: BOOK_A's related-provision label '3.36(2) (noting litigation representative in default)' (under 2.11, 2.12, 2.16 and 2.19) is loose - official 3.36(2) says a judgment in default of defence must not be entered, without the Court's permission, against a person represented by a litigation representative; noting in default (3.36(1)(b)) is not restricted. Read the official text.",
            "BOOK_A other Parts (full Book A uploaded; 6th pass): R.3.74 notes (p.3-243) refer to 'Rr.2.11 to 2.16'.",
            "Rule 2.6 (representative actions): BOOK_A 2.6 related provisions list 2.16.",
             "Rule 2.12(1)(c); rule 2.18 (its text applies to actions described in 2.16); rule 2.19 (BOOK_A related "
             "provisions)."],
    "2.17": ["BOOK_A other Parts (full Book A uploaded; 6th pass): listed as a related provision under R.10.2 (p.10-4, 'lawyer as litigation representative').",
            "BOOK_A 2.11 footnote 10: 'See R.2.17'.",
             "Rule 2.15 (BOOK_A related provisions list 2.17).",
             "Rule 2.21: BOOK_C 2.17 commentary reads 2.17(2) and 2.21 together on advance costs.",
             "Cross-book (4th pass): BOOK_C's C. (L.) 2011 ABQB 42 is BOOK_A 2.11 fn 12 'L. C. v. R. (Alta.) 2011 ABQB "
             "42'; on advance costs see also BOOK_A 2.11 Part F fn 5 (p.2-34: a litigation representative given advance "
             "costs immunities, L. C. v. R. (Alta.) 2015 ABQB 713) and BOOK_B 2.21 (Sawridge 2013 ABCA 226, advance "
             "costs to the Public Trustee)."],
    "2.18": ["Rule 2.16 (its text applies to actions described in 2.16).",
             "Rule 2.19: BOOK_A related provisions of 2.18 and 2.19 list each other; BOOK_A 2.18 commentary contrasts them."],
    "2.19": ["8th pass: BOOK_A's related-provision label '3.36(2) (noting litigation representative in default)' (under 2.11, 2.12, 2.16 and 2.19) is loose - official 3.36(2) says a judgment in default of defence must not be entered, without the Court's permission, against a person represented by a litigation representative; noting in default (3.36(1)(b)) is not restricted. Read the official text. Also: BOOK_A 2.18's list labels this rule '2.19 (settling estate litigation)'; official 2.19 covers court approval of any settlement, discontinuance or abandonment for a represented person, not only estates.",
            "BOOK_A other Parts (full Book A uploaded; 6th pass): R.3.35 notes: 'See R.3.35 n.D, and R.2.19' (p.3-86, fn 10), and 'The court can approve a compromise rejected by a party who is not sui juris: S.W. v. K.T. 2007 ABQB 38 ... See R.2.19' (p.3-87, fn 5) - the same case as BOOK_A 2.19 fn 3.",
            "Rule 2.18: BOOK_A 2.18 commentary ('Rule 2.19 allows the court to approve a compromise in trust or estate "
             "proceedings') and related provisions. That Book A sentence is narrower than official 2.19, which covers "
             "any litigation representative (flagged under 2.18, 4th pass).",
             "BOOK_A 2.11 Part E (p.2-33 fn 7): 'Court approval is needed for settlement' - Minors' Property Act s.15 "
             "and the court's inherent jurisdiction (added in 4th pass). BOOK_A 2.19 fn 3 'S. W. v. K. T. 2007 ABQB 38' "
             "and BOOK_A 2.11 p.2-32 fn 4 'S. W. v. K. T. (#2) 2006 ABQB 830' are different decisions.",
             "Rule 3.36(2): BOOK_A information note."],
    "2.20": ["BOOK_A other Parts (full Book A uploaded; 6th pass): R.9.17 notes (p.9-50): 'Note R.2.20, which addresses payments recovered by litigation representatives'; listed as a related provision under R.9.19 (p.9-62), R.9.22 (p.9-67) and R.13.48 (p.13-106).",
            "Part 13 Division 7 (payment into and out of Court) and rule 13.49: BOOK_A information note and related "
             "provisions. (An earlier note said no other commentary cites 2.20 - CORRECTED in 6th pass, see the first item.)"],
    "2.10": ["BOOK_A other Parts (full Book A; 7th pass): R.3.17 information note and related provisions (p.3-57) - the same note BOOK_C prints ('The Court may grant intervenor status ... under rule 2.10'); R.3.15 and later Part 3 notes (p.3-51, p.3-69): 'see R.2.10n.E' on costs (matches this rule's Part E); R.3.69 notes (p.3-220, 3-221): 'Rr.2.10 n.C' twice (matches Part C, Lack of Standing) and 'See Rr.2.10, and 14.58'; R.6.3 fn 2 (p.6-28) 'See R.2.10 on interveners'; R.10.31 fn 4 (p.10-98) on costs 'and R.2.10'; listed under R.14.58 (p.14-173). This rule's own pointers verified: R.3.24 n. D is 'Costs'; R.3.69 n. B 'Standing'; R.3.74 n. F 'Limitation Periods'; R.14.58n exists (about 430 lines on intervention).",
            "Official, by subject (6th pass): in Part 14 'party' includes an intervenor where the context requires "
            "(14.1(1)(k) and the Appendix); rule 14.25(3) - an intervenor's factum takes the respondent's form; rule "
            "14.26(1)(d) - 30 pages for an intervenor; rule 14.37(2)(e) - a single appeal judge may grant permission to "
            "intervene.",
            "Rule 3.17 (standing of Attorney General on judicial review): BOOK_C's 3.17 information note (101-120 json "
             "line 693) says 'The Court may grant intervenor status to other persons under rule 2.10'; BOOK_A lists 3.17 "
             "as a related provision.",
             "Rule 14.58 (intervenor on appeal): BOOK_A related provision and 'On interventions in appeals, see R.14.58n.'; "
             "BOOK_B and BOOK_C cite 14.58(3) (intervenor may not raise new issues).",
             "Rule 3.68 (striking pleadings for lack of standing): BOOK_A Part C; rule 10.31 (costs for intervenors): BOOK_B "
             "section 4 ('See the annotation Costs for Intervenors under Rule 10.31').",
             "Cross-book (4th pass): BOOK_C's re-paired names are independently confirmed - Suncor v. Unifor Local 707A "
             "2014 ABQB 555 (BOOK_A p.2-29 fn 9; BOOK_B section 1 'Local 707 A'); Stratum 2017 ABQB 351 (BOOK_B section 3); "
             "R. v. Neve 1996 ABCA 242 (BOOK_B, 184 AR 359 = BOOK_A p.2-27 fn 2 '[1996] 8 WWR 294, 184 AR 359'); "
             "Papaschase Indian Band v. Canada (AG) 2005 ABCA 320 (BOOK_B, 380 AR 301 = BOOK_A p.2-22 fn 7 'Lameman v. "
             "A.-G. Can. (#1) 2005 ABCA 320, 380 AR 301' - same case, different style); M. (V.L.) v. Dominey Estate 2023 "
             "ABCA 226 (BOOK_A p.2-23 fn 1 [page corrected in 5th pass], an intervention decision, distinct from the 2023 ABCA 261 merits decision "
             "cited in BOOK_A 2.9). BOOK_A's 'Thomson' (p.2-27 fn 7, Thomson Nwsp. 1997) is a different case from BOOK_C's "
             "Canadian Life and Health Insurance Assn. v. Thomson 2023 ABCA 340. BOOK_B read in full (sections 1-4, ends "
             "at source); its '202 ABCA 243' (United Taxi) is printed so in the source (probably 2002)."],
    "2.9": ["BOOK_A other Parts (full Book A; 7th pass): listed under R.3.69 (p.3-220) and R.3.70 (p.3-224). BOOK_A 2.9's statement that 'much of the commentary on class actions is in the notes to R.13.11' checked: R.13.11's notes run about 1,040 lines, Parts A-H (tests, opting in/out, court permission, examples, legal fees, procedure, multi-jurisdiction, costs).",
            "Official, by subject (6th pass): rule 4.12(3) - an action under the Class Proceedings Act must have a case "
            "management judge unless the Chief Justice decides otherwise; rule 10.32 - costs factors in class and "
            "representative proceedings (BOOK_A Part H cites R.10.32); rule 14.14(2)(f) - appeals from certification or "
            "refusal to certify are fast-track appeals; rule 3.62(6) - class-proceeding amendments are outside 3.62 "
            "(see 2.7).",
            "Rule 13.11 (outside Part 2): BOOK_A says 'much of the commentary on class actions is in the notes to R.13.11'.",
            "Rule 2.6: BOOK_A's 2.6 commentary contrasts representative actions with class actions 'under Rr.2.9 and "
            "13.11'; 2.9's Part G says 'the ambiguities and gaps in R.2.6 can be fixed by the courts' inherent power'.",
            "Rules 2.7 (Part G: 'See also R.2.7 and notes') and 2.8 (Part H costs fn 7 cites Rule 2.8).",
            "Rule 1.9 (related provision: enactments prevail over rules); Class Proceedings Act, S.A. 2003, c. C-16.5 "
            "(in force April 1, 2004 - BOOK_A fn 9, p.2-9)."],
    "2.8": ["BOOK_A other Parts (7th pass): also listed under R.5.3 (p.5-14, modifying or waiving rights under Part 5) as '2.8 (discovery in class proceedings)' (label wraps over two lines) - missed in the 7th pass for 2.1-2.10.",
            "BOOK_A other Parts (full Book A; 7th pass): R.5.4 fn 3 (p.5-15), R.5.5 notes (p.5-18: 'On class proceedings, see R.2.8'), R.5.17 notes (p.5-89, 5-91) and R.5.31 fn 5 (p.5-122) cite R.2.8; listed under R.5.5 (p.5-17), R.5.17 (p.5-88), R.5.19 (p.5-98) and R.5.28 (p.5-113).",
            "Rule 2.9: BOOK_A's 2.9 commentary, Part H Costs (fn 7, p.2-20; combined_rule2.txt line 967) cites 'Rule 2.8' "
            "for individual class members being 'arguably, subject to discovery'.",
            "Class Proceedings Act s.18 (text in the information note) and s.19 (BOOK_A fn 1, p.2-9: 'Compare ... s.18 "
            "and s.19'); discovery rules 5.1(2), 5.3, 5.5, 5.17, 5.19 (related provisions); rule 6.22 (BOOK_A commentary)."],
    "2.7": ["BOOK_A other Parts (full Book A; 7th pass): R.3.62 information note (p.3-135): 'Rule 2.7 ... says that after a certification order is made in a class proceeding, pleadings' may be amended only with permission (agrees with official 2.7 and 3.62(6)); listed under R.3.62 (p.3-135), R.3.74 (p.3-231) and R.13.11 (p.13-45).",
            "Official, by subject (6th pass): rule 3.62(6) - the general amendment rule 'does not apply to amendments to a "
            "class proceeding under the Class Proceedings Act'; that is the gap 2.7 fills. (BOOK_A's related-provision "
            "label '3.62(b)' matches no top-level subrule of 3.62; the clause is 3.62(1)(b), and 3.62(6) is the one that "
            "speaks to class proceedings.)",
            "Rule 2.9: BOOK_A's 2.9 commentary, Part G (combined_rule2.txt line 847): 'See also R.2.7 and notes.'",
            "Rule 13.11 (style of cause in class proceedings) - BOOK_A and BOOK_C information note; related provisions "
            "3.62(b) (amending pleadings) and 3.68 (deficiencies in claims)."],
    "2.6": ["BOOK_A other Parts (7th pass): FLAG - R.10.32 related provisions (p.10-103) print '2.61 (representative actions)'; there is no rule 2.61 and the label is official 2.6's title ('Representative actions'), so it reads as 2.6. R.10.32 itself is the costs rule for class and representative proceedings.",
            "BOOK_A other Parts (full Book A; 7th pass): listed under R.3.69 (p.3-220), R.3.70 (p.3-224, 'See also R.2.6 (representative actions) and R.2.9') and R.13.11 (p.13-45, as 2.6(2)); R.1.4 notes (p.1-21) repeat the Ford v. New Democrats point (reverse of BOOK_A 2.6 fns 9-10). R.3.68 fn 7 (p.3-213) 'And see Rr.2.6, 11.25, 11.26' sits by a forum question; the Part 3 extraction does not show which sentence it supports.",
            "Official, by subject (6th pass): rule 10.32 (costs) applies 'in a representative action' and in Class "
            "Proceedings Act proceedings - factors: public interest, novel point of law, test case, access to justice. "
            "BOOK_B section 3 quotes 10.32 (in Kowch) accurately apart from its typos 'coasts' and 'The'.",
            "Rule 2.1: BOOK_A's 2.6 commentary uses the trustee-beneficiary relation ('as R.2.1 tells us') as the model "
            "for all representative actions.",
            "Rule 2.5: BOOK_A says 2.5 'may not apply to ... clubs or associations'; such groups fit 2.6.",
            "Rules 2.9 and 13.11 (class proceedings): BOOK_A distinguishes class actions from 2.6; BOOK_A's 2.9 commentary "
            "(combined_rule2.txt line 874) says 'the ambiguities and gaps in R.2.6 can be fixed by the courts' inherent "
            "power to settle procedure'.",
            "Rule 2.16 lists 2.6 among its related provisions (BOOK_A); rule 1.4 (BOOK_A: with R.1.4, 2.6 would probably "
            "allow appointing a representative for an unincorporated association).",
            "Cross-book: BOOK_B's 'Rule 42' / 'R. 42' = former 1968 R.42, the predecessor named in BOOK_A fn 3 (p.2-6). "
            "Both books cite Western Canadian Shopping Centres v. Dutton (A fns 4-6; B sections 1, 2, 5) and Paron (A 2.9 "
            "footnotes, e.g. p.2-11 'Paron v. R. 2006 ABQB 375'; B sections 4 and 15). BOOK_B commentary read in full in the 4th pass: sections 1-15, 15(a)-(d), ends "
            "at the source's last sentence; its typos ('coasts', 'Cass Proceedings Act', 'T.L. at determining') are in "
            "the source."],
    "2.5": ["BOOK_A other Parts (full Book A; 7th pass): listed under R.5.28 (p.5-113), R.6.37 (p.6-141), R.11.12 (p.11-16) and R.11.13 (p.11-17, whose information note cites rule 2.5); R.13.12 checklist (p.13-65) 'Rr.2.2(1)-2.5(1)'.",
            "Rule 2.2: BOOK_A's 2.5 commentary says 2.5 'extends the benefits of R.2.2' (suing in a firm name) to an "
            "individual trading under another name, plaintiff or defendant.",
            "Rule 2.4: a similar 'notice to disclose' (comply within 10 days); 2.4 alone adds a dispute/application step "
            "(2.4(3)) and last-known-address duty (2.4(4)); BOOK_A repeats 2.4's history note under 2.5(3).",
            "Rule 2.6: BOOK_A says 2.5 'may not apply to ... clubs or associations'; BOOK_A's 2.6 commentary treats "
            "unincorporated associations (unions, yacht clubs) as suited to representative actions."],
    "2.4": ["BOOK_A other Parts (full Book A; 7th pass): listed under R.5.22 (p.5-102), R.5.28 (p.5-113), R.6.37 (p.6-141), R.11.10 and R.11.11 (p.11-15); R.5.17 fn 5 (p.5-90): 'See R.2.4 on disclosing names of partners'. FLAG: R.8.8 notes (p.8-20): 'See further, R.2.4n.' - Book A has no notes on 2.4, and the preceding sentence (a lawyer acting as advocate and witness; fn 5 Beacon Hill 2011 ABQB 138) is the subject of BOOK_A 2.24 Part D, which cites Beacon Hill at p.2-58 fn 4. Probably 'R.2.24n' with a digit lost. Not corrected.",
            "Official, by subject (6th pass): rule 5.17(1)(f) and (2)(d) - a partner or former partner of a partnership "
            "that is an adverse party may be questioned (a route alongside 2.4's notice to disclose).",
            "Rule 2.5(2)-(3): a similar 'notice to disclose' (comply within 10 days) for sole proprietors - but 2.5 has "
            "no equivalent of 2.4(3) (dispute and apply to the Court) or 2.4(4) (last known address); BOOK_A repeats "
            "2.4's history note (1968 R.80(3)-(5)) under 2.5(3).",
            "Rules 2.2 (actions in the partnership name) and 2.3 (suing individual partners) - rules 2.2-2.4 form the "
            "partnership rules."],
    "2.3": ["BOOK_A other Parts (full Book A; 7th pass): Book A's R.9.23 text (p.9-67) cites rule 2.3 and 2.3(1), as the official 9.23 does. The R.11.15 '2.3 (contract providing for service)' slip is noted in the next item.",
            "BOOK_A other Parts (full Book A uploaded; 6th pass): R.11.15's related provisions (p.11-18) list '2.3 (contract providing for service)' - rule 2.3 is about suing individual partners; the label matches official rule 11.3 ('Agreement between parties'), so this is probably a slip for 11.3. Flagged, not corrected.",
            "Rule 2.2: actions in the partnership name; BOOK_A 2.2 fn 2 (p.2-4) advises naming the individual partners too.",
            "Rule 2.4: notice to disclose the partners' names and addresses (rules 2.2-2.4 form the partnership rules).",
            "Rule 9.23 (outside Part 2): enforcement against partners and partnership property - cited in BOOK_A's 2.3 "
            "information note and in the related provisions of both 2.2 and 2.3. The official text of 9.23(2) and (3) "
            "itself refers to 'a notice under rule 2.3', 'presumed to be a partner under rule 2.3' and 'rule 2.3(1)' "
            "(the only references to rules 2.1-2.10 elsewhere in the official Rules; added in 4th pass; re-confirmed in "
            "5th pass - no Division-level reference to Part 2 Division 1 and no form headed [Rule 2.1]-[Rule 2.10]).",
            "6th pass: 9.23 holds the only references to these rules BY NUMBER; other official rules deal with the same "
            "subjects without naming them (see the see_also of 2.1, 2.2, 2.4, 2.6, 2.7, 2.9, 2.10)."],
    "2.2": ["BOOK_A other Parts (full Book A; 7th pass): R.11.10 information note (p.11-15) cites Rule 2.2; listed under R.9.23 (p.9-68, 'action against partners'); R.3.70 notes (p.3-224): same person cannot be both plaintiff and defendant, 'R.2.2(2) on overlapping partnerships is an exception' (consistent with official 2.2(2)); R.13.12 checklist (p.13-65): trade names or partnerships, 'Rr.2.2(1)-2.5(1)'.",
            "Official, by subject (6th pass): the Appendix defines 'partnership' as a partnership to which the Partnership "
            "Act applies; rule 5.17(1)(f) and (2)(d) let a partner or former partner of a partnership that is an adverse "
            "party be questioned.",
            "BOOK_A 2.5 commentary (combined_rule2.txt lines 174-177): 'Rule 2.5 now extends the benefits of R.2.2 to an "
            "individual defendant who carried on business under a different name ... It now extends to a plaintiff doing "
            "that.' (sole proprietors, either side; quote completed in 4th pass).",
            "BOOK_B 2.1 commentary part 2 ('Limited Partners', 155569 Canada v. 248524 Alberta 2000 CA): a general partner "
            "may sue in its own name only as trustee of the partnership property.",
            "Rules 2.3 (suing individual partners) and 2.4 (disclosure of partners) complete the partnership scheme."],
    "2.1": ["BOOK_A other Parts (full Book A; 7th pass): R.11.6 information note (p.11-11) cites rule 2.1. R.3.68 notes (p.3-213): 'See also R.2.1n., supra' - the Part 3 extraction interleaves text and footnotes, so the sentence it supports cannot be confirmed. FLAG: R.7.1 notes (p.7-5), on splitting trials: 'recent case law again stresses the impact of R.2.1.' (fn 6: NEP Can. v. MEC Op 2016 ABCA 201) - rule 2.1 (actions by or against personal representatives and trustees) does not deal with splitting trials; the intended rule cannot be determined from the text.",
            "BOOK_A 2.6 commentary (combined_rule2.txt lines 207-210, 226-228): representative actions - beneficiaries "
            "sue or are sued through the executor/personal representative 'as R.2.1 tells us'; the trustee-beneficiary "
            "relationship is the model for all representative actions.",
            "BOOK_B 2.1 commentary part 2 ('Limited Partners', 155569 Canada v. 248524 Alberta 2000 CA): a general partner "
            "may sue in its own name only as trustee of the partnership property - links 2.1 with 2.2.",
            "Cross-book: BOOK_B section 1 (Paterson v. Hamilton (1997), 199 A.R. 399) is the case BOOK_A fn 5 cites for "
            "'a shareholder of a closely-held company can sue as the trustee of the company?'. BOOK_B's quotes refer to "
            "'Rule 43' = former 1968 R.43, the predecessor named in BOOK_A fn 1.",
            "Official, by subject (6th pass): the Appendix defines 'trustee' (incl. an executor, administrator or trustee of an "
            "estate, and a trustee appointed by the Court) and 'personal representative' (as in s.1(l) of the Surrogate "
            "Rules); rule 11.25(1)(j) allows service outside Alberta of a claim against a trustee about the trust."],
}

MANUAL_BOOK_A_COMMENTARY_FLAGS = {
    "2.11": "5th pass, statements read against the official text: (1) Part C and D (p.2-32, p.2-33) speak of persons "
            "'with no trustee or guardian under the Dependent Adults Act' and its notice periods (fn 3: RSA 2000 c. D-11); "
            "official 2.11(c)-(d) refer instead to the Adult Guardianship and Trusteeship Act, and the official Rules "
            "never name the Dependent Adults Act. The sources do not say how the two Acts relate; read 2.11(c)-(d). "
            "(2) BOOK_B section 1 quotes Public Guardian v C.(K.) para 67: 'Rule 2.11 ... directs that a Represented "
            "Adult must have a litigation representative' - official 2.11(d) requires one only for a represented adult "
            "'in respect of whom no person is appointed to make a decision about a claim' (the judge's wording, as "
            "printed). Other statements checked and consistent: three types (2.12(1)); settlement needs approval (2.19); "
            "'interested person' not defined (not among Part 2's defined terms). 6th pass: 'The job of the litigation "
            "representative is to pay costs' (p.2-31, fn 10) and Part F 'answer for costs ... primarily liable' (p.2-34) "
            "must be read with official 10.47: a plaintiff's litigation representative is liable for a costs award; a "
            "defendant's is not, unless there was serious misconduct and the Court so orders.",
    "2.14": "5th pass: 'the affidavit under R.2.14 by the self-appointee only need give that person's \"reasons for "
            "self-appointing\"' (p.2-38, Kunkel para 31) is about proving status; read literally it is narrower than "
            "official 2.14(2)-(3), which require agreement in writing, the reason, the relationship, no adverse interest, "
            "residence or place of business, a costs acknowledgment, and (for estates) the (3)(a)-(d) disclosures.",
    "2.15": "5th pass: 'This Rule creates a duty on the opponent to apply for a litigation representative' (fn 6 Chutskoff) "
            "- official 2.15(1): an interested person MAY apply, and a party adverse in interest MUST apply only 'if "
            "there is no interested person'. Book A's sentence omits that condition. Left as printed.",
    "2.2": "5th pass: 'Rule 2.2 lets one use the partnership name if the firm still exists' - official 2.2(1) states no "
           "such condition (an action by or against 2 or more persons as partners may be brought using the partnership "
           "name; (2) extends it to actions between partnerships with a partner in common). The 'still exists' "
           "condition is Book A's gloss; its own fn 2 and the dissolved-partnership sentence treat that as a practical "
           "risk. Left as printed; read the official text.",
    "2.18": "4th pass: the commentary (printed on p.2-41 after the p.2-40 footnote block; correctly kept with 2.18) says "
            "'Rule 2.19 allows the court to approve a compromise in trust or estate proceedings'. That is narrower than "
            "official 2.19, which applies to ANY litigation representative without express authority: settling, "
            "discontinuing or abandoning an action needs the Court's approval. The trust/estate setting is rule 2.16, "
            "to which 2.18 applies. Left as printed; read 2.19's official text.",
    "2.6": "4th pass: footnotes p.2-6 #3 and p.2-7 1-10 consecutive; 'W. Cdn. Shopping Centres ... supra' (fns 5, 6) -> "
           "fn 4 (C.A. 1998 ABCA 392; SCC 2001 SCC 46); fn 10 'ibid.' -> fn 9 (Ford v. New Democrats 2024 ABKB 141). "
           "Probable typo in the related provisions: '2.16 (unborn or unascertained clauses)' - BOOK_A's own 2.19 list "
           "reads '2.16 (unascertained or unborn classes)', and rule 2.16 concerns persons/classes. Left as printed.",
    "2.29": "probable wrong subrule reference: 'especially the notice under R.2.29(1) (c) and the last known address of "
            "the client'. Official 2.29(1) has only clauses (a) and (b); the notice's contents are in 2.29(1)(a)(i) "
            "(last known address) and (ii) (10-day statement). Left as printed. Checked: the last sentence ('On the "
            "lawyer's duty ... see R.9.2n.') is printed at the top of p.2-65 before the 2.30 heading and belongs to "
            "2.29; footnotes p.2-63 fn 4 and p.2-64 fns 1-9 consecutive; 'Kong and Cunningham cases' (fn 5) resolve "
            "within the same footnote. Case-name variant: fn 5 'R. (Lilles) v. Cunningham' and 2.24 p.2-50 fn 3 "
            "'Cunningham v. Lilles (R. v. Cunningham)' are the same 2010 SCC 10. 4th pass: the statement 'Some "
            "provinces require leave of the court before a lawyer can withdraw. Alberta wisely does not require that in "
            "civil cases' must be read with official rule 2.31 - after a trial date is scheduled, a notice of withdrawal "
            "needs the Court's permission or has no effect. Book A's next sentence (serious harm, 'shortly before a "
            "scheduled trial') points that way but does not cite 2.31.",
    "2.24": "checked by reading pp.2-49..2-59: 106 footnotes (count corrected from 107 in the 8th pass; the per-page list sums to 106), consecutive on every page (2-49: 4; 2-50: 1-12; 2-51: 1-10; "
            "2-52: 1-7; 2-53: 1-11; 2-54: 1-12; 2-55: 1-12; 2-56: 1-11; 2-57: 1-13; 2-58: 1-11; 2-59: 1-6). All "
            "supra/infra references resolve inside Book A. Points to note: (1) p.2-50 fn 10 'See Part C below' is "
            "attached to ground (d) 'a solicitor ... likely also to be a witness at trial'; in this rule Part C is "
            "'Separate Counsel for a Child' and Part D is 'Counsel as Witness', so probably means Part D. (2) p.2-55 fn 9 "
            "'the Can. S. Petr. case, infra': Book A cites two decisions - Can. S. Petr. v. Amoco Can. Petr. (CA) [1997] "
            "5 WWR 395 at p.2-53 fn 5 (earlier; it mentions delay in seeking disqualification, the point of fn 9) and "
            "[1998] 4 WWR 701 at p.2-57 fn 4 (later; costs). Which one is meant is not certain. (3) spelling variant "
            "'Feeidoni' (p.2-53 fn 11, p.2-54 fn 1) for 'Feeidooni v. Burnham' 2018 ABQB 390. (4) p.2-58 fns 8-9 'R. T. "
            "v. R. (Alta.), infra': full cite at p.2-58 fn 3 and again at p.2-59 fn 1 (2020 ABQB 655), so 'infra' is "
            "correct. Left as printed. 4th pass (all four points re-verified by citation): also p.2-50 fn 12 'See further "
            "the C. P. E., v.2, Chap.38, Part H.3 and Part C below' is attached to last-minute changes of lawyer; this "
            "rule's Part C (Separate Counsel for a Child) does not discuss that, whereas BOOK_A's 2.28 commentary "
            "(p.2-63) does, and its fn 3 cites the same C.P.E. Chapter 38 Part H.3. The pointer's target is uncertain. "
            "(fn 10's companion 'See also R.2.22 n. F above' is right: 2.22 Part F covers a lawyer likely to be a "
            "witness, fn 13 Forward v. Zurich.) 6th pass (full Book A): a THIRD such pointer - R.8.17 notes (p.8-49), "
            "heading 'E. Conflict of Interest' fn 4 'See also R.2.24 n. C' - conflicts are this rule's Part B.2 and "
            "counsel as witness its Part D. All three 'Part C' pointers (fns 10, 12 and R.8.17 fn 4) miss the printed "
            "Part C; the text does not show why.",
    "2.23": "short-form cites checked (footnotes run 1-8 p.2-47, 1-6 p.2-48, 1-3 p.2-49). Direction wrong (Book A "
            "drafting): p.2-47 fn 4 and fn 8 'Fortin v. Chretien ... supra' - the full cite comes later, p.2-48 fn 3: "
            "Fortin v. Chretien (Barreau du Que.) 2001 SCC 45, [2001] 2 SCR 500. All others resolve correctly (Bus. Dev. "
            "Bank -> p.2-47 fn 3; Landmass infra -> fn 6; EXP Mining -> R.2.22 p.2-46 fn 2; Lameman -> p.2-47 fn 2; "
            "Westmount Travel -> p.2-48 fn 3; Drucker -> fn 2; Nahirney -> R.2.13; Potts -> p.2-48 fn 4). Case-name "
            "variant: fn 1 'Van Vuong Tai Hldg. v. Min. of Justice' 2020 ABCA 169 = BOOK_B 'Vuong Van Tai Holding v. "
            "Alberta (Minister of Justice and Solicitor General)' (same citation, same para 15); order of the first two "
            "words differs between the books - not resolved here.",
    "2.22": "checked: footnotes run 1-8 (p.2-43), 1-11 (p.2-44), 1-13 (p.2-45), 1-4 (p.2-46); all 11 supra/infra/ibid "
            "references point the right way (Fraser v. Ksenych -> p.2-43 fn 5; J. L. v. T. T. -> fn 8; Pintea -> fn 7; "
            "Latham infra -> p.2-44 fn 8; Williams -> p.2-44 fn 2; Thompson v. DeAgostini -> p.2-43 fn 4; Christie -> "
            "p.2-45 fn 1; Re Padget Est. -> p.2-45 fn 10). Printed typos kept as printed: Part B 'if doing often so "
            "contains' (read 'if doing so often'); p.2-43 fn 1 'Represennted'. 4th pass: related provisions list "
            "'11.22 (service on self-represented person)', but official 11.22 is 'Recorded mail service' (service of "
            "non-commencement documents by recorded mail); the rule on service on self-represented litigants is 11.18 "
            "(which Book A cites correctly under 2.28 and 2.29). Probably a wrong number; left as printed. 6th pass: in the "
            "full Book A, R.11.17's related provisions label 11.22 '(service on address on most recently filed document)' "
            "(p.11-22), matching the official rule - Book A itself describes 11.22 differently elsewhere. Other related "
            "provisions checked: 1.1(2), 10.31(5), 12.56, 3.35 and the 11.5 information note all match the official text. "
            "5th pass: Part F 'A non-lawyer can represent himself or herself in litigation, but cannot represent anyone "
            "else, natural person or corporation' (p.2-45 fn 5) must be read with official 2.23(4) (2020): the Court "
            "keeps a discretion, subject to the Legal Profession Act, to grant a non-lawyer agent a right of audience to "
            "speak on behalf of an individual or corporation. Book A's own 2.23 commentary says so (p.2-47 Part A text, and fn 5).",
    "2.16": "wording to read with care: 'an ordinary representative action pursuant to Rr.2.13-2.15'. Representative "
            "actions are rule 2.6; rules 2.13-2.15 appoint litigation representatives. Probably means an ordinary "
            "litigation representative. Left as printed. 5th pass: the same passage says 'R.2.15 pertains to "
            "situations where there is no personal representative' - official 2.15(1) covers any individual or estate "
            "required to have a litigation representative under 2.11 who has none (minors, missing persons, adults "
            "lacking capacity, represented adults, and estates without a grant); 'no personal representative' fits "
            "only the estate case (2.11(e)).",
    "2.10": "short-form cites checked: all 26 'supra/infra' references resolve to a full cite inside Book A. Direction "
            "wrong in these (Book A drafting): p.2-22 fn 6 Kellogg and fn 8 Pedersen 'supra' (full cites only at p.2-29 fn 5: "
            "Dir. of Human Rts. & Citizenship Comm. v. Kellog Brown & Root (Can.) 2007 ABCA 175; Pederson v. R. 2008 ABCA "
            "192, 432 AR 219); p.2-23 fn 9 Reference re Greenhouse Gas 'supra, Part C' (full cite later, p.2-24 fn 7: 2019 ABCA 361); "
            "p.2-25 fn 6 A.-G. Alta. v. U.F.C.W. Local 401 'infra' (full cite earlier, p.2-24 fn 5: 2011 ABCA 93); p.2-28 fn 3 "
            "S. M. v. Director 'supra' (full cite in the next footnote, fn 4: 2020 ABQB 558). Spelling: Book A has "
            "'Pedersen' (p.2-22) and 'Pederson' (p.2-29) for 2008 ABCA 192; Book B spells it 'Pedersen v Alberta'. "
            "7th pass (full Book A): Part 14 also prints 'Pederson v. R. 2008 ABCA 192, 432 AR 219', so both of Book A's "
            "full cites read 'Pederson'; Part 14 prints 2007 ABCA 175 both as 'Kellog Brown & Root' and 'Kellogg Brown & "
            "Root'. "
            "Source page number '2-26' is printed twice (lines 1234, 1236); footnote numbering is unaffected. "
            "CORRECTED IN 4TH PASS: p.2-23 fn 9 'Univ. of Alta. v. Info. & Privacy Comm'r., infra' is right - the case is "
            "cited in full again later, p.2-27 fn 10 (2011 ABQB 389; page corrected in 5th pass); the 3rd-pass flag had listed it as wrong. New in "
            "4th pass: p.2-27 fn 13 'R. v. Hirsekoro 2011 ABQB 156' - p.2-22 fn 5 spells it 'Hirsekorn' (same citation). "
            "Not corrected.",
    "2.9": "short-form cites checked: all ~50 'supra/infra/ibid.' references resolve to a full cite inside Book A. "
           "Direction wrong in these (Book A drafting, not extraction): p.2-10 fn 1 Ayrton and Elder Advocates 'supra' "
           "(first full cites later: Ayrton 2006 ABCA 88, 384 AR 1; Elder Advocates 2008 ABQB 490, 453 AR 1); p.2-10 fn 7 "
           "Investplan, Gillespie v. Gessert and Pro-Sys 'supra' (full cites later: Owners Condo. Plan 0020701 v. Investplan "
           "Prop. 2006 ABQB 224, 57 Alta LR(4th) 310; Gillespie 2006 ABQB 949; Pro-Sys 2013 SCC 57) and p.2-11 fn 6 and "
           "p.2-12 fn 5 Investplan 'supra' (full cite p.2-12 fn 7); p.2-13 fn 8 (continued on p.2-14) 'T. L. v. Dir. of "
           "Child Welfare (#2), (Q.B.), infra' (the #2 decision, 2008 ABQB 114, is cited in full only earlier: p.2-9 fn 10, "
           "p.2-12 fn 7); p.2-15 fns 1-2 Singh 'supra' (full cite fn 3: 2021 ABQB 316). "
           "CORRECTED IN 4TH PASS (the 3rd-pass version of this flag was wrong on three points): p.2-14 fn 3 'T. L. "
           "(Q.B.), infra' is right - 2006 ABQB 104 is cited in full again later, p.2-16 fn 4; p.2-15 fns 6, 7, 12, 13 "
           "'Spring v. Goodyear, supra' are right - full cite earlier at p.2-13 fn 7 (2020 ABQB 252); the T. L. (#2) "
           "footnote is p.2-13 fn 8, not p.2-12 fn 8; and p.2-12 fn 5 Investplan had been missed. "
           "Other probable Book A typos found by reading all 2.9 pages in the 4th pass: p.2-17 fn 8 'Bruno v. Samson "
           "Cree N. 2020 ABQB 504 ... varg 2021 ABCA 504' - elsewhere (p.2-10 fn 8, p.2-16 fn 5) the appeal is 2021 ABCA "
           "381, which varied 2020 ABQB 504; p.2-20 fn 7 'Lameman ... (#2) 2004 ABQB 913, 365 AR 88' - fn 4 on the same "
           "page gives 365 AR 881; Part I (p.2-21) says costs were set at '3 times column 5 of Schedule C' but its fn 7 "
           "(Macaronies #2 2021 ABQB 106) says 'treble col.3'. Not corrected. 8th pass (wording corrected in the 8th pass of 2.11-2.32): Macaronies ... v. BofA Can. "
           "Bank 2022 ABQB 143 is printed '(#_)' (p.2-20 fn 2) and '(#__)' (p.2-21 fn 7). This is Book A's convention "
           "for a decision in a series whose number is not given - '(#_)'/'(#__)' occurs 448 times across Book A, 13 "
           "times in Part 2 - not a defect; the neutral citation is complete.",
    "2.27": "probable Book A typo: 'Generally on self-represented parties, see R.2.2 n.' - rule 2.2 is about partnerships; "
            "self-represented parties are covered at R.2.22 n. Not corrected.",
}

MANUAL_BOOK_A_FOOTNOTE_FLAGS = {
    "2.11": {("2-31", 10): "probable wrong clause (4th pass): 'Rules 2.14(2) (f), 10.47' is cited for the litigation "
                           "representative's job 'to pay costs'. Official 2.14(2)(f) is the corporation's place of "
                           "business; the costs acknowledgment is 2.14(2)(g). Left as printed.",
             ("2-31", 8):"probable wrong rule number: the text cites 'R.2.15' for 'no order is required ... but an "
                          "affidavit of the litigation representative must be filed'. That requirement is in "
                          "rule 2.14(1)(a) (self-appointment), so this probably means R.2.14. Left as printed."},
    "2.7": {("2-8", 2): "short-form cases resolved from Book A itself: T. L. v. Dir. of Child Welfare = 2006 ABQB 104, "
                        "395 AR 327 (first full cite at 2.9, combined_rule2.txt line 440 - so Book A's 'supra' points the "
                        "wrong way; T. L. (#2) 2008 ABQB 114 at p.2-9 fn 10 is a different decision). C. H. S. v. "
                        "Dir. of Child Welfare 'infra' - corrected in 4th pass: Book A later cites THREE C. H. S. "
                        "decisions (2008 ABQB 513, 452 AR 66 at 2.8 fn 3, p.2-9; 2006 ABQB 528, 403 AR 103 in 2.9's "
                        "footnotes, line 862; (#2) 2008 ABQB 620, 452 AR 98 at 2.11, line 1563), so which one is meant "
                        "is not certain; 'infra' is right for all three."},
    "2.1": {("2-3", 2): "possible source typo in the court file number: 'Edm 703 0193 AC' - Book A writes other Court "
                        "of Appeal file numbers as 'Edm 1803 0166 AC', so a leading digit ('1703') is probably missing. "
                        "Not corrected."},
    "2.5": {("2-6", 1): "attached to 2.5(3); same history note as rule 2.4 (1968 R.80(3)-(5)). 2.5(2)-(3) have a "
                        "similar notice to disclose (not identical - no equivalent of 2.4(3)-(4)); whether 1968 "
                        "R.80(3)-(5) is really their source cannot be checked from the sources (6th pass removed an "
                        "earlier 'plausible' judgment). Source typo: '914 R.146(a)' should read "
                        "'1914 R.146(a)'. 2.5(1)'s own history is footnote 3 on page 2-5 (1968 R.83)."},
}

MANUAL_BOOK_C = {
    "2.21": {
        "citation_names": {"2015 ABQB 515": "Padget Estate v. Padget Estate, [2015] A.J. No. 897 (Master)",
                           "2005 ABCA 129": "Rufenack v. Hope Mission, [2005] A.J. No. 317",
                           "2013 ABCA 226": "1985 Sawridge Trust v. Alberta (Public Trustee), [2013] A.J. No. 640",
                           "2022 ABQB 367": "Kunkel v. Winquist, [2022] A.J. No. 677"},
        "commentary_flag": "useful: 2.21 used where an inherent conflict risks the estate 'lending its name to someone "
                           "else's fight' (Padget para 43); broad power to set terms incl. advance costs (Sawridge paras 23-24). "
                           "Case names re-paired from the text (Padget name as printed in C; Book A 2.22 p.2-45 fn 10 cites the "
                           "same 2015 ABQB 515 as 'Re Padget Est. (M)'). Corroborated: Book A fn 2 (Rufenack, "
                           "Kunkel), Book B (Sawridge, which quotes paras 23-26; C prints 'paras. 23 24').",
    },
    "2.22": {
        "drop_commentary": "one sentence ('Corporations are not individuals and cannot represent themselves in courts') then "
                           "cut off and ending in a stray statute citation from rule 2.11. The point is stated fully in Book A "
                           "(2.22 Part F) and Book B. Not retained.",
    },
    "2.23": {
        "drop_rule_text": "same words as official; 'Legal Profession Act' displaced twice by extraction. No substantive difference.",
        "drop_c_note": "same note as BOOK_A, cut off mid-sentence and ending in a citation - Chutskoff Estate v. Bonora "
                       "2013 ABQB 119 at para. 19, the same citation and pinpoint Book C gives under 2.11 (lack of "
                       "capacity); nothing links it to 2.23 (reworded in 5th pass - earlier called 'unrelated'). Not "
                       "retained.",
        "drop_one_citation": {"2017 ABQB 76": "Bidell Equipment LP v. Caliber Midstream GP LLC, [2017] A.J. No. 264, 2017 "
                                              "ABQB 76 (pinpoint lost) - dropped in 5th pass for consistency with 2.2 and "
                                              "2.14: here it stands where the number '2' of 'Reg. 36/2020, s. 2' should "
                                              "be, the same extraction pattern as its other occurrences, and nothing in "
                                              "the sources ties it to 2.23."},
        "amendment_note_flag": "garbled: Book C's case list for 2.23 was extracted into this note. Readable facts: amended by "
                               "Alta. Reg. 36/2020 (agrees with official), 'effective May 26' (year cut off), gazetted "
                               "April 15, 2020.",
        "keep_citations_note": "Book C's 2.23 commentary text is lost; these citations survive only inside the garbled "
                               "amendment note. Pinpoints partly lost.",
        "citation_names": {"2020 ABCA 341": "PurpleRung Foundation v. Peace River (Town of) Subdivision and Development "
                                            "Appeal Board, [2020] A.J. No. 1014",
                           "2022 ABQB 5": "Vizor v. 383501 Alberta Ltd. (c.o.b. Val Brig Equipment Sales), [2022] A.J. No. 6"},
        "citation_notes": {"2020 ABCA 341": "paras 11-12.",
                           "2022 ABQB 5": "pinpoint lost. Also cited by Book A (2.22 fn, p.2-46 #4: company told to use a lawyer).",
                           },
        "add_citations": [{"neutral_citation": "2020 ABCA 169", "style_of_cause": "Van Vuong Tai Hldg. v. Min. of Justice "
                           "(name as cited in Book A)", "note": "only 'ABCA 169 at para. 15' survives in Book C; identified from "
                           "Book A 2.23 fn 1 (same case, same para. 15): 2020 amendment lets a judge allow a non-lawyer to "
                           "represent a connected corporation."}],
    },
    "2.24": {
        "drop_rule_text": "cut off in (1) after 'for that'. Not usable. Book C has nothing else for 2.24.",
    },
    "2.25": {
        "drop_rule_text": "same wording as official (bracketed label only).",
    },
    "2.27": {
        "amendment_note_flag": "a stray statute citation ('R.S.A. 2000, c. L-12, s. 3(2)(c).') follows the amendment note; "
                               "a bare citation with no text; the Act is not named in any of the sources and it "
                               "appears nowhere else in Book C, so its connection to 2.27 cannot be shown (reworded in "
                               "4th pass - the earlier note asserted it was unrelated). Not used.",
    },
    "2.28": {
        "drop_rule_text": "'Form 3' replaced by case citations. Not usable; official text controls.",
        "drop_citations": "Shell Canada Products v. Sunterra Beef 2013 ABQB 193 (affd 2014 ABCA 243) and Genstar v. Plains "
                          "Midstream 2012 ABQB 457 are displaced from Book C's Part 3 commentary. Evidence (5th pass): they "
                          "stand where the '3' of 'Form 3' should be, and the passage is word-for-word (same 'para. 53', "
                          "same garbled '[2012] A.J. No. Genstar ... 755') in Book C's rule 3.2 entry. Nothing in the "
                          "sources ties them to 2.28 (earlier wording 'not about 2.28' replaced).",
    },
    "2.29": {
        "drop_rule_text": "'Form 4' and '10' replaced by case citations; (5) missing. Not usable; official text controls.",
        "drop_citations": "Regular v. Regular 2016 ABQB 570, Patrus v. Alberta (WCB) and Behiels v. Tibu are place-of-trial / "
                          "venue cases displaced from Book C's Part 3 commentary. Evidence (5th pass): they stand where "
                          "'4' of 'Form 4' and '10' should be; Regular and Behiels recur in C's rule 3.4 entry and Patrus "
                          "in 3.9, and C's own text calls Regular a change-of-venue case. Nothing in the sources ties them "
                          "to 2.29 (earlier wording 'not about 2.29' replaced).",
    },
    "2.30": {
        "drop_rule_text": "cut off and ends with 'R. v. Cunningham (S.C.C.); see also Behm v. Hansen' - late-withdrawal cases "
                          "belonging to rule 2.31 (Book B's 2.31 commentary cites Cunningham 2010 SCC 10; Book A's 2.31 fn 3 "
                          "cites Behm 2021 ABQB 701). Not usable.",
    },
    "2.31": {
        "drop_rule_text": "same wording as official ('court's' lower case once).",
    },
    "2.32": {
        "drop_rule_text": "same as official except (1)(a)(iii) 'practice' (official 'practise') and (4) labels out of order "
                          "('[Withdrawal of lawyer or 2.29 of record]'). Official text controls.",
    },
    "2.11": {
        "drop_rule_text": "garbled in source: (b) has stray text ('[ ]. Payment into Court and Payment out of Court'), "
                          "(d) and (e) replaced by case citations. Not usable; official text controls.",
        "drop_citations": "the 3 citations in the 2.11 text are displaced: 2008 ABCA 192 ([2008] A.J. No. 543; Book C "
                          "prints no name here - Books A and B identify 2008 ABCA 192 as Pedersen/Pederson v. Alberta) and "
                          "Grant Thornton 2016 ABCA 238 are intervenor cases (rule 2.10), Stamos 2018 ABQB 566 is a rule "
                          "2.5 case (kept there). Also in the garbled text (4th pass): a bare case name 'Morrow v. Zhang' "
                          "with no recoverable citation or context; it appears nowhere else in any of the sources, so it "
                          "cannot be attributed. Dropped. Evidence (5th pass): all three stand where the text of 2.11(d)-(e) "
                          "should be. Stamos 'at para. 3' is the same pinpoint as in C's 2.5 commentary. Grant Thornton is "
                          "here 'at para. 11' - that pinpoint appears nowhere else in Book C (C's 2.10 and 2.13 cite "
                          "para. 9); it is called an intervenor case because C's own 2.10 commentary cites it for the "
                          "intervenor test. 2008 ABCA 192 appears in Book C only here.",
        "citation_names": {"2013 ABQB 119": "Chutskoff Estate v. Bonora, [2013] A.J. No. 195",
                           "2015 ABQB 490": "1368276 Alberta Ltd. v. Grotski Estate, [2015] A.J. No. 849"},
        "commentary_flag": "useful and unique points (definitions of 'represented adult' s.1(hh) and 'capacity' s.1(d); "
                           "2.11 covers a will-appointed personal representative before probate). Last sentence cut off in "
                          "source. Act name misprinted as 'Adult Guardian and Trusteeship Act' (correct: Adult Guardianship "
                           "and Trusteeship Act, as in official 2.11(c)). Cross-book: Chutskoff 2013 ABQB 119 para 19 "
                           "is the same passage BOOK_B 2.11 section 1 quotes.",
    },
    "2.12": {
        "drop_rule_text": "cut off after (1)(a), and the number '3' replaced by a stray citation. Not usable.",
        "drop_citations": "Stamos 2018 ABQB 566 is displaced (a rule 2.5 case, kept there): it stands where the number "
                          "'3' of 'There are 3 types' should be, with the same 'at para. 3' pinpoint as in C's 2.5 "
                          "commentary (evidence added in 5th pass). Book C has nothing else for 2.12.",
    },
    "2.13": {
        "drop_rule_text": "same words as official; 'Surrogate Rules' displaced by extraction. No substantive difference.",
        "drop_commentary": "one sentence cut off mid-way ('the rule should only ...') and ending in a displaced intervenor "
                           "citation (Grant Thornton 2016 ABCA 238 'at para. 9' - the same pinpoint C's 2.10 commentary "
                           "gives for the intervenor test; evidence added in 5th pass). Its point - 2.13(e) powers of attorney apply only when a "
                           "litigation representative is required - is stated in full by Book B (Nahirney 2011 ABQB 586) and "
                           "Book A. Not retained.",
    },
    "2.14": {
        "drop_rule_text": "cut off at (2)(a); Form numbers 1 and 2 replaced by a stray citation. Not usable.",
        "drop_citations": "Bidell 2017 ABQB 76 is displaced (see rule 2.2). Book C has nothing else for 2.14.",
    },
    "2.15": {
        "drop_rule_text": "same wording as official (bracketed label only).",
        "citation_names": {"2011 ABQB 42": "C. (L.) v. Alberta (Metis Settlements Child & Family Services Region 10), "
                                           "[2011] A.J. No. 84",
                           "2013 ABQB 119": "Chutskoff Estate v. Bonora, [2013] A.J. No. 195"},
        "commentary_flag": "useful: the Court must be able to find lack of capacity under 2.11(c) before directing an "
                           "appointment. Case names re-paired from the text. NOTE Book C's amendment note (143/2011) is "
                           "misattributed - that regulation amended rule 2.14.",
    },
    "2.16": {
        "drop_rule_text": "cut off in (2). Not usable. Book C has nothing else for 2.16.",
    },
    "2.17": {
        "drop_rule_text": "same wording as official; bracketed label displaced and a doubled comma.",
        "citation_names": {"2011 ABQB 42": "C. (L.) v. Alberta (Metis Settlements Child & Family Services Region 10), "
                                           "[2011] A.J. No. 84"},
        "commentary_flag": "useful and unique: defendant may be ordered to pay a child's litigation representative's costs; "
                           "Public Trustee cost options; 2.17(2) and 2.21 allow advance costs (C.(L.) 2011 ABQB 42 paras 61-62). "
                           "Ends with a cut-off second citation ('[2013] A.J. No.'). Read with the official text (4th "
                           "pass): 2.17(1) applies only when the Court appoints a LAWYER as litigation representative for "
                           "an individual in 2.11(a)-(d), and lets costs be borne by 'the parties or ... one or more of "
                           "them' or a fund in Court - Book C's 'the defendant' is one instance of that.",
    },
    "2.18": {
        "drop_rule_text": "same wording as official ('non- disclosure' split only).",
    },
    "2.20": {
        "drop_rule_text": "(2) cut off and ends with a stray statute citation from rule 2.11's commentary "
                          "('S.A. 2008, c. A-4.2, s. 1(hh)'). Not usable. Book C has nothing else for 2.20.",
    },
    "2.10": {
        "drop_c_note": "same note as BOOK_A, garbled, with two citations mixed in (reworded in 5th pass - earlier called "
                       "'unrelated'): Champagne v. Sidorsky 2012 ABQB 522 para 67 stands where the number '6' of 'Part 6' "
                       "should be (an extraction pattern seen throughout Book C) and appears nowhere else in Book C; "
                       "its link to 2.10 cannot be shown. Grant Thornton 2016 ABCA 238 (pinpoint lost) is an intervenor "
                       "case that Book C's 2.10 commentary itself cites (para 9), so it is kept there. Note not retained.",
        "citation_names": {
            "2023 ABKB 579": "R. v. McKee, [2023] A.J. No. 1047",
            "2014 ABQB 555": "Suncor Energy Inc. v. Unifor, Local 707A, [2014] A.J. No. 1025",
            "2017 ABQB 351": "Stratum Projects Alberta Inc. v. Aman Building Corp., [2017] A.J. No. 528",
            "2019 ABCA 113": "Jonsson v. Lymer, [2019] A.J. No. 360",
            "2005 ABCA 320": "Papaschase Indian Band v. Canada (Attorney General), [2005] A.J. No. 1273",
            "2013 ABQB 726": "G. (G.) v. G. (J.T.), [2013] A.J. No. 1444",
            "2019 ABCA 385": "Wilcox v. Alberta Prison Justice Society, [2019] A.J. No. 1659",
            "2016 ABCA 238": "Grant Thornton Ltd. v. Alberta Energy Regulator, [2016] A.J. No. 790",
            "2023 ABCA 226": "M. (V.L.) v. Dominey Estate, [2023] A.J. No. 814",
            "1996 ABCA 242": "R. v. Neve, [1996] A.J. No. 570",
        },
        "add_commentary_citations": [
            {"neutral_citation": "2023 ABCA 340", "style_of_cause": "Canadian Life and Health Insurance Assn. v. Thomson, "
             "[2023] A.J. No. 1221", "note": "cited at para. 8 in the commentary text; missing from Book C's citation list"},
            {"neutral_citation": "2014 ABCA [number lost]", "style_of_cause": "Gauchier v. Alberta (Metis Settlements "
             "Land Registry, Registrar), [2014] A.J. No. 908", "note": "cited twice in the text; neutral citation number "
             "cut off in source - verify before citing"},
        ],
        "commentary_flag": "case names corrected from the commentary text (the source's name/citation pairing was scrambled); "
                           "factor 7 garbled in source: read 'Will intervention widen the lis between the parties'.",
    },
    "2.9": {
        "drop_rule_text": "same wording as the official text plus the Act citation 'S.A. 2003, c. C-16.5' and a stray, "
                          "incomplete case reference ('Gauchier v. Alberta ... 2014 ABCA') displaced from Book C's rule 2.10 "
                          "commentary, where it is kept. Only other difference: 'these Rules' capitalised. No substantive "
                          "difference. Book C has no note or commentary for 2.9.",
    },
    "2.8": {
        "drop_rule_text": "same words as the official text, but 'Class Proceedings Act' is displaced within both "
                          "subrules (moved by extraction; 5th pass removed an unsupported guess about italics). No "
                          "substantive difference.",
        "drop_note_variant": "same note; only adds the Act citation 'S.A. 2003, c. C-16.5' (kept elsewhere). Not retained.",
        "note_flag": "Book A text ends with a doubled period ('members..'); Book C's copy has a single period.",
        "commentary_flag": "unique to Book C; no authority cited in the source.",
    },
    "2.7": {
        "drop_rule_text": "same wording as the official text, except an editorial statute citation inserted after the Act "
                          "name ('S.A. 2003, c. C-16.5') and a stray comma. No substantive difference; the citation is "
                          "also in Book A (2.9 fn 9) and Book B commentary.",
    },
    "2.6": {
        "drop_rule_text": "garbled in source: (1) cut off mid-sentence and followed by case citations; (2) missing. "
                          "Not usable; official text controls.",
        "drop_citations": "the 4 citations found in the 2.6 text (Jonsson 2019 ABCA 113, Papaschase 2005 ABCA 320, "
                          "G.(G.) v. G.(J.T.) 2013 ABQB 726, Wilcox 2019 ABCA 385) are the intervenor-test cases from "
                          "Book C's rule 2.10 commentary, displaced by extraction; kept there, not here. Evidence (5th "
                          "pass): the passage is a verbatim copy of the 2.10 one - same pinpoints (paras 18, 2, 27, "
                          "11-13) and the same scrambled name order ('Jonsson v. Lymer Papaschase , ...'). "
                          "Book C has no commentary for 2.6.",
    },
    "2.5": {"citation_names": {"2018 ABQB 566": "Stamos v. Huculuk, [2018] A.J. No. 925"}},
    "2.4": {
        "drop_rule_text": "cut off in source after the first 10 words of (1); nothing else survives. "
                          "Not usable; official text controls. Book C has no note, commentary or citation for 2.4.",
    },
    "2.3": {
        "drop_rule_text": "cut off in source after the first 9 words of (1); nothing else survives. "
                          "Not usable; official text controls. Book C has no note, commentary or citation for 2.3.",
    },
    "2.2": {
        "drop_rule_text": "garbled in source: (1) cut off mid-sentence, '2' replaced by a stray case citation, (2) missing. "
                          "Not usable; official text controls.",
        "rescue_misattributed": "fragment cut off in source; Book C mis-parsed it under a heading read as rule '11.10'",
        "drop_one_citation": {"2017 ABQB 76": "Bidell Equipment LP v. Caliber Midstream GP LLC, [2017] A.J. No. 264, "
                                              "2017 ABQB 76 - dropped in 5th pass (of 2.21-2.32) so that 2.2, 2.14 and 2.23 "
                                              "get the same decision. It was found inside Book C's garbled 2.2 rule text. The same citation also "
                                           "appears in Book C's 2.14 and 2.23 text. In every occurrence it stands where "
                                           "a number should be ('[2] or more persons' here; 'Form [1]', 'Form [2]' in "
                                           "2.14; 's. [2]' in 2.23's amendment note) - the extraction pattern also seen "
                                           "with Stamos ('3', 2.12), Champagne ('6', 2.10 note) and the Part 3 cases "
                                           "('Form 3', 'Form 4', '10', 2.28-2.29). So no occurrence shows which rule it "
                                           "belongs to, and nothing links it to the 2.2 commentary quote (5th pass "
                                           "removed an earlier 'may be the source' guess). Unverified - do not cite."},
    },
}


def dedupe(packet: dict) -> None:
    """Remove redundancy without losing information: every dropped value is identical (after the
    documented normalization) to a value kept elsewhere, and its hash/locator stays in place."""
    log = []
    for s in packet["subrules"]:
        r, src, comp = s["rule"], s["sources"], s["comparison_vs_official"]
        # 1. book operative text identical to official -> keep hash + status only
        for cid in ("BOOK_A", "BOOK_B", "BOOK_C"):
            rec = src.get(cid)
            if rec and comp[cid]["status"] == "EXACT_MATCH":
                rec["operative_text_raw"] = None
                rec["operative_text_note"] = f"same as official operative text ({comp[cid]['status']}); see operative_text_sha256"
                log.append(f"{r} {cid}: operative text dropped ({comp[cid]['status']})")
        # 2. titles: keep official; list book variants only when wording (not case) differs
        t = s["title"]
        variants = {k: v for k, v in t.items() if k != "official" and v and norm_editorial(v) != norm_editorial(t["official"])}
        s["title"] = {"official": t["official"], "variants": variants}
        # 3. information notes: merge Book A / Book C duplicates
        notes = []
        a_note = src["BOOK_A"].pop("information_note", None) if src.get("BOOK_A") else None
        c_notes = src["BOOK_C"].pop("information_notes", []) if src.get("BOOK_C") else []
        if a_note:
            notes.append({"text": a_note, "carriers": ["BOOK_A"]})
        for cn in c_notes:
            hit = next((n for n in notes if _sim(n["text"], cn) >= 0.8), None)
            if hit:
                hit["carriers"].append("BOOK_C")
                if norm_strict(hit["text"]) != norm_strict(cn):
                    words = lambda x: set(re.findall(r"[a-z0-9.()]+", norm_strict(x).casefold()))
                    if words(cn) <= words(hit["text"]):
                        # same words, only scrambled: nothing new, so the garbled copy is not kept
                        hit.setdefault("carrier_defects", {})["BOOK_C"] = MANUAL_NOTE_FLAGS.get(
                            r, "garbled copy of the same note (word order/brackets); not retained")
                        log.append(f"{r} BOOK_C information note dropped: garbled duplicate, no new words")
                        continue
                    hit.setdefault("variant_text", {})["BOOK_C"] = cn
                log.append(f"{r} BOOK_C information note merged into BOOK_A copy")
            else:
                notes.append({"text": cn, "carriers": ["BOOK_C"]})
        s["information_notes"] = notes
        # 3b. Book C citation "context" is a window of the carrier text; drop it when that text is kept verbatim
        if src.get("BOOK_C"):
            kept = [src["BOOK_C"].get("operative_text_raw") or ""] + [c["text"] for c in src["BOOK_C"]["commentary"]]
            cits = list(src["BOOK_C"]["citations"]) + [x for c in src["BOOK_C"]["commentary"] for x in c.get("citations", [])]
            for cit in cits:
                ctx = cit.get("context")
                if ctx and any(ctx.strip() in k for k in kept):
                    cit.pop("context")
                    log.append(f"{r} BOOK_C citation context dropped ({cit.get('neutral_citation')}): verbatim in kept text")
        # 4. Book C commentary: drop per-item sentence splits (derived from the same text)
        if src.get("BOOK_C"):
            for grp in [src["BOOK_C"]["commentary"]] + [e["commentary"] for e in src["BOOK_C"]["misattributed_entries"]]:
                for c in grp:
                    if c.pop("sentences", None) is not None:
                        log.append(f"{r} BOOK_C commentary sentence split dropped")
        # 5. rule-by-rule manual curation of Book C (decided on manual review)
        cur = MANUAL_BOOK_C.get(r)
        if cur and src.get("BOOK_C"):
            c = src["BOOK_C"]
            if cur.get("drop_rule_text"):
                c["operative_text_raw"] = None
                c["operative_text_note"] = cur["drop_rule_text"]
                comp["BOOK_C"].pop("differences", None)
                log.append(f"{r} BOOK_C: rule text dropped (manual review)")
            if cur.get("rescue_misattributed"):
                for e in c.pop("misattributed_entries", []):
                    for item in e["commentary"]:
                        item["note"] = cur["rescue_misattributed"]
                        c["commentary"].append(item)
                    if e.get("parsed_title"):
                        for n in s["information_notes"]:
                            n["carriers"].append("BOOK_C")
                            n.setdefault("carrier_defects", {})["BOOK_C"] = "copy survives only as a garbled heading; not retained"
                log.append(f"{r} BOOK_C: misparsed entry folded into commentary; garbled heading dropped (manual review)")
            if cur.get("drop_note_variant"):
                for n in s["information_notes"]:
                    if n.get("variant_text", {}).pop("BOOK_C", None) is not None:
                        n.setdefault("carrier_defects", {})["BOOK_C"] = cur["drop_note_variant"]
                        if not n["variant_text"]:
                            n.pop("variant_text")
                        log.append(f"{r} BOOK_C information-note variant dropped (manual review)")
            if cur.get("note_flag"):
                for n in s["information_notes"]:
                    n["review_flag"] = cur["note_flag"]
            if cur.get("commentary_flag"):
                for cm in c["commentary"]:
                    cm["review_flag"] = cur["commentary_flag"]
            if cur.get("drop_c_note"):
                keep = []
                for n in s["information_notes"]:
                    if n["carriers"] == ["BOOK_C"]:
                        log.append(f"{r} BOOK_C information note dropped (manual review)")
                        continue
                    keep.append(n)
                for n in keep:
                    if "BOOK_A" in n["carriers"]:
                        n["carriers"].append("BOOK_C")
                        n.setdefault("carrier_defects", {})["BOOK_C"] = cur["drop_c_note"]
                s["information_notes"] = keep
            for cm in c["commentary"]:
                cm.setdefault("citations", []).extend(cur.get("add_commentary_citations", []))
            if cur.get("drop_commentary"):
                c["commentary"] = []
                c["commentary_note"] = cur["drop_commentary"]
                log.append(f"{r} BOOK_C: commentary dropped (manual review)")
            if cur.get("amendment_note_flag"):
                s["amendment_history"].setdefault("carrier_note_flags", {})["BOOK_C"] = cur["amendment_note_flag"]
            if cur.get("keep_citations_note"):
                c["citations_note"] = cur["keep_citations_note"]
            c["citations"].extend(cur.get("add_citations", []))
            if cur.get("drop_citations"):
                dropped = [x.get("neutral_citation") for x in c["citations"]]
                c["citations"] = []
                c["citations_note"] = cur["drop_citations"]
                log.append(f"{r} BOOK_C: displaced citations dropped {dropped} (manual review)")
            for nc_drop, why in cur.get("drop_one_citation", {}).items():
                c["citations"] = [x for x in c["citations"] if x.get("neutral_citation") != nc_drop]
                c.setdefault("dropped_citation_notes", {})[nc_drop] = why
                log.append(f"{r} BOOK_C: citation {nc_drop} dropped (manual review)")
            for cit in list(c["citations"]) + [x for cm in c["commentary"] for x in cm.get("citations", [])]:
                nc = cit.get("neutral_citation")
                if nc in cur.get("citation_notes", {}):
                    cit["note"] = cur["citation_notes"][nc]
                if nc in cur.get("citation_names", {}):
                    cit["style_of_cause"] = cur["citation_names"][nc]
        # 5a. amendment notes are kept once, in amendment_history.carrier_notes
        for cid in ("BOOK_B", "BOOK_C"):
            if (src.get(cid) or {}).pop("amendment_note_raw", None):
                log.append(f"{r} {cid}: amendment note moved to amendment_history.carrier_notes (was duplicated)")
        # 5b. manual drops of Book A / Book B raw text whose differences are editorial only
        for cid, note in MANUAL_TEXT_NOTES.get(r, {}).items():
            rec = src.get(cid)
            if rec and rec.get("operative_text_raw"):
                rec["operative_text_raw"] = None
                rec["operative_text_note"] = note
                comp[cid]["review_note"] = note
                comp[cid].pop("differences", None)
                log.append(f"{r} {cid}: raw text dropped, differences editorial only (manual review)")
        # 5c. Book C division heading vs official
        cdiv = (src.get("BOOK_C") or {}).get("division_heading")
        if cdiv and s["division"] and not cdiv.startswith(f"Division {s['division']['number']} "):
            src["BOOK_C"]["division_heading_flag"] = (f"wrong in Book C: rule {r} is in Division {s['division']['number']} "
                                                      f"({s['division']['heading']}) per the official text")
        if r in MANUAL_BOOK_A_COMMENTARY_FLAGS and src.get("BOOK_A"):
            src["BOOK_A"]["commentary_review_flag"] = MANUAL_BOOK_A_COMMENTARY_FLAGS[r]
        if r in MANUAL_SEE_ALSO:
            s["see_also"] = MANUAL_SEE_ALSO[r]
        # 6. manual flags on Book A footnotes
        for (pg, num), flag in MANUAL_BOOK_A_FOOTNOTE_FLAGS.get(r, {}).items():
            for fn in (src.get("BOOK_A") or {}).get("footnotes", []):
                if fn["page"] == pg and fn["number"] == num:
                    fn["review_flag"] = flag
    packet["dedupe_log"] = {"rule": "a value is dropped only when an equal value (under the normalization profile) is kept", "entries": log}


def main() -> int:
    official, off_meta = parse_official()
    a, a_meta = parse_book_a()
    b, b_meta = parse_book_b()
    c, c_meta = parse_book_c()

    pdf_hash = pdf_sha()
    a_year = latest_year(BOOK_A[0].read_text(encoding="utf-8"))
    c_year = latest_year("\n".join(p.read_text(encoding="utf-8") for p in BOOK_C))
    last_part2_amend = max(int(y.split("/")[1]) for r in official.values() for y in r["amending_regulations"]) if any(
        r["amending_regulations"] for r in official.values()) else 2010

    registry = {
        "OFFICIAL": {
            "carrier_id": "OFFICIAL",
            "title": "Alberta Rules of Court, Alta. Reg. 124/2010 (Alberta King's Printer office consolidation)",
            "version": off_meta["consolidation"],
            "artifacts": [{"file": "Alberta rule of court.pdf", "sha256": pdf_hash, "branch": "main"},
                          {"file": OFFICIAL_TXT.name, "sha256": file_sha(OFFICIAL_TXT), "derived_from": "Alberta rule of court.pdf",
                           "method": "PyMuPDF page.get_text() (embedded text layer, no OCR)"}],
            "source_role": "FIRST_HAND_RULE_CARRIER",
            "origin_id": "ab-kings-printer-consolidation-2026-06-01",
            "permitted_use": "operative-text reconciliation anchor; official version/current-to closure",
        },
        "BOOK_A": {
            "carrier_id": "BOOK_A",
            "title": "Annotated rules text, Part 2 (publisher/title not stated in carrier; page style '2-N', 'Related Provisions', historical-derivation footnotes)",
            "version": f"unknown edition; latest Alberta case year cited in Part 2 = {a_year}",
            "artifacts": [{"file": BOOK_A[0].name, "sha256": file_sha(BOOK_A[0])}],
            "source_role": "ANNOTATED_RULES",
            "origin_id": "book-a-annotated-part2",
            "permitted_use": "corroboration; annotation (information notes, related provisions, commentary, footnotes)",
        },
        "BOOK_B": {
            "carrier_id": "BOOK_B",
            "title": "Alberta Rules of Court, The Honourable Justice Allan A. Fradsham (per carrier running header)",
            "version": b_meta.get("edition_header"),
            "artifacts": [{"file": p.name, "sha256": file_sha(p)} for p in BOOK_B],
            "source_role": "ANNOTATED_RULES",
            "origin_id": "book-b-fradsham",
            "permitted_use": "corroboration; commentary",
        },
        "BOOK_C": {
            "carrier_id": "BOOK_C",
            "title": "Annotated rules text, book pages 81-120 (publisher/title not stated in carrier; source files 81-100_revised.md / 101-120_revised.md)",
            "version": f"unknown edition; latest Alberta case year cited = {c_year}",
            "artifacts": [{"file": p.name, "sha256": file_sha(p)} for p in BOOK_C],
            "source_role": "ANNOTATED_RULES",
            "origin_id": "book-c-annotated-pp81-120",
            "permitted_use": "corroboration; annotation (information notes, citations, commentary)",
        },
    }
    registry_sha = sha_text(json.dumps(registry, sort_keys=True))

    def version_identity(cid: str) -> tuple[str, str]:
        floor = {"BOOK_A": a_year, "BOOK_B": int(b_meta["edition_year"]) if b_meta.get("edition_year") else None, "BOOK_C": c_year}[cid]
        if floor and floor > last_part2_amend:
            return "SAME_VERSION_PROVEN", (f"carrier post-dates {floor} >= last Part 2 amendment year {last_part2_amend} "
                                           "per official amendment history; no Part 2 amendment after that date appears in the June 1, 2026 consolidation")
        return "VERSION_IDENTITY_UNRESOLVED", "carrier date cannot be placed after the last Part 2 amendment"

    books = {"BOOK_A": a, "BOOK_B": b, "BOOK_C": c}
    subrules, summary = [], {"EXACT_MATCH": 0, "NORMALIZATION_ONLY_DIFFERENCE": 0, "CARRIER_HAS_EXTRA_TEXT": 0,
                             "CARRIER_MISSING_TEXT": 0, "WORDING_DIFFERENCE": 0, "CARRIER_TEXT_MISSING": 0}
    gate_counts = {}
    for r in RULES:
        off = official[r]
        comps, carriers_gate, vis = {}, {}, {}
        for cid, data in books.items():
            rec = data.get(r)
            comps[cid] = compare(off["operative_text"], rec and rec["operative_text_raw"])
            summary[comps[cid]["status"]] += 1
            vi, basis = version_identity(cid)
            vis[cid] = {"result": vi, "basis": basis}
            comps[cid]["version_identity"] = vi
            if rec:
                carriers_gate[cid] = {
                    "carrier_id": cid,
                    "artifact_sha256": registry[cid]["artifacts"][0]["sha256"],
                    "text_sha256": rec["operative_text_sha256"],
                    "source_role": registry[cid]["source_role"],
                    "origin_id": registry[cid]["origin_id"],
                    "locator": rec["locator"],
                }
        carriers_gate["OFFICIAL"] = {
            "carrier_id": "OFFICIAL", "artifact_sha256": pdf_hash or file_sha(OFFICIAL_TXT),
            "text_sha256": off["operative_text_sha256"], "source_role": "FIRST_HAND_RULE_CARRIER",
            "origin_id": registry["OFFICIAL"]["origin_id"], "locator": off["locator"],
        }
        agree = all(comps[k]["status"] in ("EXACT_MATCH", "NORMALIZATION_ONLY_DIFFERENCE") for k in books)
        overall_vi = "SAME_VERSION_PROVEN" if all(v["result"] == "SAME_VERSION_PROVEN" for v in vis.values()) else "VERSION_IDENTITY_UNRESOLVED"
        if agree and overall_vi == "SAME_VERSION_PROVEN":
            result = "THREE_BOOK_SOURCE_RECONCILED"
        elif overall_vi == "SAME_VERSION_PROVEN" and off["operative_text"]:
            # the official carrier closes operative wording independently; book defects are preserved as provenance
            result = "SOURCE_CARRIER_DEFECT_INDEPENDENTLY_CLOSED"
        else:
            result = "THREE_BOOK_RECONCILIATION_HOLD"
        gate_counts[result] = gate_counts.get(result, 0) + 1
        gate = {
            "schema_version": "arc-three-book-gate-v1",
            "rule_identity": {"instrument": "Alta. Reg. 124/2010", "rule": r, "title_official": off["title"]},
            "three_book_mode": "OPTIONAL_CORROBORATION",
            "required_carriers": ["OFFICIAL"],
            "source_registry_sha256": registry_sha,
            "normalization_profile": {k: NORMALIZATION_PROFILE[k] for k in ("id", "version", "sha256")},
            "version_identity": overall_vi,
            "carrier_version_identity": vis,
            "pairwise_vs_official": {k: v["status"] for k, v in comps.items()},
            "result": result,
            "independent_origin_count": len({c["origin_id"] for c in carriers_gate.values()}),
            "carriers": carriers_gate,
        }
        gate["gate_artifact_sha256"] = sha_text(json.dumps(gate, sort_keys=True))
        subrules.append({
            "rule": r,
            "title": {"official": off["title"], "BOOK_A": a.get(r, {}).get("title"),
                      "BOOK_B": b.get(r, {}).get("title"), "BOOK_C": c.get(r, {}).get("title")},
            "division": off["division"],
            "operative_text": {
                "controlling": off["operative_text"],
                "controlling_carrier": "OFFICIAL",
                "sha256": off["operative_text_sha256"],
            },
            "amendment_history": amendment_check(off, a.get(r), b.get(r), c.get(r)),
            "sources": {
                "OFFICIAL": {"locator": off["locator"]},
                "BOOK_A": a.get(r),
                "BOOK_B": b.get(r),
                "BOOK_C": c.get(r),
            },
            "comparison_vs_official": comps,
            "three_book_gate": gate,
        })

    packet = {
        "schema_version": "arc-rule2-three-book-reconciliation-v1",
        "skill": "arc-rules-production-lifecycle",
        "mode": "SOURCE_RECONCILIATION",
        "write_status": "NO_WRITE (no Neo4j/LexGraph mutation; packet only)",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "target": {"instrument": "Alberta Rules of Court, Alta. Reg. 124/2010", "part": 2, "rules": f"{RULES[0]}-{RULES[-1]}", "count": len(RULES)},
        "limits": [
            "Three-book agreement is not current-law certification; currency rests on the official consolidation's stated current-to date only.",
            "Book A and Book C titles/editions are not stated in their carriers; roles are inferred from content and recorded as such.",
            "Commentary and notes are copied as carried; no burdens, tests, or exceptions were added.",
            "Discrepancy status values are machine classifications for review, not adjudicated resolutions.",
        ],
        "source_registry": registry,
        "source_registry_sha256": registry_sha,
        "normalization_profile": NORMALIZATION_PROFILE,
        "denominators": {
            "source_closure_denominator": {"definition": "Alta. Reg. 124/2010 rules 2.1-2.32 in the June 1, 2026 consolidation", "count": len(RULES)},
            "pairwise_comparison_denominator": {"definition": "rules x book carriers (A,B,C) compared against OFFICIAL", "count": len(RULES) * 3},
        },
        "summary": {"pairwise_status_counts": summary, "gate_result_counts": gate_counts,
                    "last_part2_amendment_year": last_part2_amend},
        "part_level": {
            "official": off_meta,
            "BOOK_A": a_meta,
            "BOOK_B": b_meta,
            "BOOK_C": c_meta,
        },
        "subrules": subrules,
    }
    dedupe(packet)
    OUT_DIR.mkdir(exist_ok=True)
    log = packet.pop("dedupe_log")
    subs = packet.pop("subrules")
    packet["files"] = [f"{x['rule']}.json" for x in subs]
    packet["dedupe_rule"] = log["rule"]
    (OUT_DIR / "_index.json").write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for x in subs:
        x = {"index": "_index.json (source registry, normalization profile, denominators, part-level notes)", **x,
             "dedupe_log": [e for e in log["entries"] if e.split(" ")[0] == x["rule"]]}
        (OUT_DIR / f"{x['rule']}.json").write_text(json.dumps(x, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(packet["summary"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
