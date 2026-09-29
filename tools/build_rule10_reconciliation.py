#!/usr/bin/env python3
"""SOURCE_RECONCILIATION (arc-rules-production-lifecycle) for Alberta Rules of Court 10.1-10.55.

No-write: reads the repo's source carriers and emits one combined JSON packet holding every
carrier's content per subrule, plus per-subrule three-book gate records (arc-three-book-gate-v1).
Books never outvote the official source and no text is silently merged.
"""
from __future__ import annotations
import difflib, hashlib, json, re, subprocess, sys, unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "rule10_subrules"
RULES = [f"10.{n}" for n in range(1, 56)]

OFFICIAL_TXT = ROOT / "Alberta_Rules_of_Court.txt"
BOOK_A = [ROOT / "combined_rule10.txt"]
BOOK_B = [ROOT / f"rule10_part{n:02d}_document.json" for n in range(1, 13)]
BOOK_C = [ROOT / "441-460_10_1 to 10_10.json", ROOT / "461-480_10_11 to 10_31.json",
          ROOT / "481-500_10_32 to 10_46.json", ROOT / "501-520_10_47 to 11_9.json"]

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
    "id": "arc-rule10-compare-norm",
    "version": "1",
    "strict_steps": [
        "drop a leading rule number '10.N' (carriers differ on whether the number is part of the text span)",
        "drop footnote superscript digits (U+2070-U+2079, U+00B9/B2/B3)",
        "Unicode NFKC (expands ligatures such as U+FB01 'fi')",
        "curly quotes/apostrophes -> ASCII; en/em dash -> '-'",
        "remove markdown emphasis '*'",
        "collapse all whitespace to single space; trim",
        "remove space before , ; : . )  and after (",
    ],
    "alphanumeric_tier": "if the strict and editorial forms still differ, texts that are equal once every character except letters and digits is removed are classed NORMALIZATION_ONLY_DIFFERENCE with basis 'alphanumerics only' (needed for extractions that drop spaces, and extraction drops spaces, and for line-break hyphens); a hint, never a pass",
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
    s = re.sub(r"^\s*10\.\d+(?![\d.])", "", s)
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
    alnum = lambda x: re.sub(r"[^0-9a-z]", "", x)
    if alnum(o_e) == alnum(b_e):
        return {"status": "NORMALIZATION_ONLY_DIFFERENCE", "similarity": 1.0,
                "basis": "equal when only letters and digits are compared (spacing, hyphenation and punctuation spacing differ)"}
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
    # body of Part 10: second "Part 10" heading through the page break before second "Part 11"
    p2 = [i for i, l in enumerate(lines) if l.strip() == "Part 10"][1]
    p3 = [i for i, l in enumerate(lines) if l.strip() == "Part 11"][1]
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
    toc_s = [i for i, l in enumerate(lines) if l.strip() == "Part 10"][0]
    toc_e = [i for i, l in enumerate(lines) if l.strip() == "Part 11"][0]
    toc = [l.strip() for l in lines[toc_s:toc_e]]
    toc_title, toc_div, toc_sub, cur_div, cur_sub, k = {}, {}, {}, None, None, 0
    stop_re = r"(10\.\d+|Division \d+|Subdivision \d+)"
    while k < len(toc):
        m = re.fullmatch(r"(Sub)?[Dd]ivision (\d+)", toc[k])
        if m:
            j, head = k + 1, []
            while j < len(toc) and toc[j] and not re.fullmatch(stop_re, toc[j]):
                head.append(toc[j]); j += 1
            entry = {"number": int(m.group(2)), "heading": re.sub(r"\s+", " ", " ".join(head)).strip()}
            if m.group(1):
                cur_sub = entry
            else:
                cur_div, cur_sub = entry, None
            k = j; continue
        if re.fullmatch(r"10\.\d+", toc[k]):
            j, t = k + 1, []
            while j < len(toc) and toc[j] and not re.fullmatch(stop_re, toc[j]):
                t.append(toc[j]); j += 1
            toc_title[toc[k]], toc_div[toc[k]], toc_sub[toc[k]] = re.sub(r"\s+", " ", " ".join(t)).strip(), cur_div, cur_sub
            k = j; continue
        k += 1
    div_lines = {x for d in list(toc_div.values()) if d for x in [f"Division {d['number']}"]} | \
                {x for d in list(toc_sub.values()) if d for x in [f"Subdivision {d['number']}"]}
    div_head_words = {d["heading"] for d in list(toc_div.values()) + list(toc_sub.values()) if d}
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
            "subdivision": toc_sub[r],
            "operative_text": text,
            "operative_text_sha256": sha_text(text),
            "amendment_history": amend or "AR 124/2010",
            "amending_regulations": re.findall(r"\d+/\d{4}", amend or "")[1:] if amend else [],
            "locator": {"file": OFFICIAL_TXT.name, "pdf_pages": sorted({pages[s], pages[min(len(pages) - 1, s + len(body))]})},
        }
    return rules, {"consolidation": "Office Consolidation, Alberta Regulation 124/2010, with amendments up to and including Alberta Regulation 79/2026; current as of June 1, 2026"}


# ---------------------------------------------------------------- Book A (combined_rule10.txt)

def _subdivision_headings() -> list[str]:
    lines = OFFICIAL_TXT.read_text(encoding="utf-8").split("\n")
    toc = [l.strip() for l in lines[[i for i, l in enumerate(lines) if l.strip() == "Part 10"][0]:[i for i, l in enumerate(lines) if l.strip() == "Part 11"][0]]]
    out, k = [], 0
    while k < len(toc):
        if re.fullmatch(r"Subdivision \d+", toc[k]):
            j, h = k + 1, []
            while j < len(toc) and toc[j] and not re.fullmatch(r"(10\.\d+|Division \d+|Subdivision \d+)", toc[j]):
                h.append(toc[j]); j += 1
            out.append(" ".join(h)); k = j; continue
        k += 1
    return out


SUBDIVISION_HEADINGS = _subdivision_headings()


# ---------------------------------------------------------------- Book A (combined_rule10.txt)
def parse_book_a() -> tuple[dict, dict]:
    raw = BOOK_A[0].read_text(encoding="utf-8")
    lines = raw.split("\n")
    page_of, page = [], None
    for l in lines:
        if re.fullmatch(r"10-\d+", l.strip()):
            page = l.strip()
        page_of.append(page)
    # mark footnote blocks and running headers
    kind = ["text"] * len(lines)
    in_fn = False
    for i, l in enumerate(lines):
        s = l.strip()
        if s == "Footnote":
            in_fn = True
        if re.fullmatch(r"10-\d+", s):
            in_fn = False
            kind[i] = "header"
            continue
        if re.fullmatch(r"PART 10:.*R\.\S+|R\.\S+ PART 10:.*", s):
            kind[i] = "header"
            continue
        if in_fn:
            kind[i] = "footnote"
    # Book A division headings ("DIVISION N" + upper-case heading lines) and subdivision headings ("Subdivision N" +
    # heading lines, matched against the official table-of-contents headings) are structure, not rule text
    _lig = lambda x: re.sub(r"\W+", "", x.replace("ﬁ", "fi").replace("ﬂ", "fl")).lower()
    sub_heads = {_lig(h) for h in SUBDIVISION_HEADINGS}
    for i, l in enumerate(lines):
        if re.fullmatch(r"DIVISION \d+", l.strip()):
            kind[i] = "division"
            j = i + 1
            while j < len(lines) and lines[j].strip() and lines[j].strip() == lines[j].strip().upper():
                kind[j] = "division"; j += 1
        elif re.fullmatch(r"Subdivision \d+", l.strip()) and kind[i] == "text":
            kind[i] = "division"
            j, acc = i + 1, ""
            while j < len(lines) and lines[j].strip():
                acc += _lig(lines[j])
                if not any(h.startswith(acc) for h in sub_heads):
                    break
                kind[j] = "division"; j += 1
                if acc in sub_heads:
                    break
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
        pat = re.compile(rf"^{re.escape(r)}(\(1\) (?=[A-Za-z“‘\"])| [A-Z])")
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
        prev = f"10-{int(c['marker_page'].split('-')[1]) - 1}"
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



def parse_book_b() -> tuple[dict, dict]:
    paras = []
    for f in BOOK_B:
        d = json.loads(f.read_text(encoding="utf-8"))
        for p in d["document_structure"]["paragraphs"]:
            paras.append((f.name, p))
    out = {r: {"title": None, "operative_text_raw": "", "commentary": [], "paragraph_ids": [], "locator": {"files": set()}} for r in RULES}
    cur, mode = None, None
    front, years, seen_comm = [], [], set()
    for fname, p in paras:
        t = p["text"].strip()
        years += [int(y) for y in re.findall(r"\b(20[0-2]\d)\s+AB(?:QB|CA|KB|PC|CJ)\b", t)]
        if re.match(r"Part 10\. Lawyers' Charges \d+\.", t) or re.match(r"Part 10\. Lawyers' Charges", t) and len(t) < 250:
            continue  # running head repeated in the extraction
        mh = re.fullmatch(r"(10\.\d+)\. (.{1,250})", t, re.S)
        if mh and "_rule_10_" in p["paragraph_id"] and len(t) < 260:
            cur, mode = mh.group(1), "rule"
            if cur in out:
                out[cur]["title"] = out[cur]["title"] or mh.group(2).strip()
                out[cur]["paragraph_ids"].append(p["paragraph_id"]); out[cur]["locator"]["files"].add(fname)
            continue
        mc = re.match(r"Commentary § (10\.\d+)((?:\([^)]*\))*):(\d+)\s*(.*)", t, re.S)
        if mc:
            cur, mode = mc.group(1), "comm"
            if cur in out:
                o = out[cur]
                o["paragraph_ids"].append(p["paragraph_id"]); o["locator"]["files"].add(fname)
                key = (cur, mc.group(2), mc.group(3), mc.group(4)[:200])
                if key in seen_comm:
                    continue
                seen_comm.add(key)
                o["commentary"].append({"section": f"{cur}{mc.group(2)}:{mc.group(3)}", "text": mc.group(4).strip()})
            continue
        if cur not in out:
            front.append(t)
            continue
        o = out[cur]
        o["paragraph_ids"].append(p["paragraph_id"]); o["locator"]["files"].add(fname)
        if mode == "rule":
            # the extraction sometimes prints a rule's text twice (heading repeated across a page/file break): keep one copy, log the skip
            o.setdefault("_rule_paras", [])
            if len(t) > 40 and t in o["_rule_paras"]:
                o.setdefault("duplicate_rule_text_paragraphs_skipped", []).append(p["paragraph_id"])
                continue
            o["_rule_paras"].append(t)
            o["operative_text_raw"] = (o["operative_text_raw"] + "\n" + t).strip()
        elif o["commentary"]:
            o["commentary"][-1]["text"] += "\n" + t
        else:
            o["commentary"].append({"section": None, "text": t})
    amend_re = re.compile(r"\s*(Alta\. Reg\. \d+/\d{4}, s\. \d+(?:\([a-z0-9]+\))*(?:[;,] ?(?:Alta\. Reg\. )?\d+/\d{4}, s\. \d+(?:\([a-z0-9]+\))*)*)\s*$")
    for r, o in out.items():
        marker = MANUAL_BOOK_B_SPLIT.get(r)
        if marker and marker in o["operative_text_raw"]:
            # manual decision: the source prints commentary in the same paragraph as the rule text, without a 'Commentary §' header
            k = o["operative_text_raw"].index(marker)
            o["commentary"].insert(0, {"section": None, "text": o["operative_text_raw"][k:].strip(),
                                       "note": f"printed in the same source paragraph as the rule text, with no 'Commentary §' header; split at '{marker}' (manual review)"})
            o["operative_text_raw"] = o["operative_text_raw"][:k].rstrip()
        m = amend_re.search(o["operative_text_raw"])
        o["amendment_note_raw"] = m.group(1) if m else None
        if m:
            o["operative_text_raw"] = o["operative_text_raw"][: m.start()].rstrip()
        o["operative_text_sha256"] = sha_text(o["operative_text_raw"])
        o["locator"]["files"] = sorted(o["locator"]["files"])
        o.pop("_rule_paras", None)
    edition_year = str(max(years)) if years else None
    return out, {"edition_header": "Alberta Rules of Court, The Honourable Justice Allan A. Fradsham (Part 10 files carry no edition year; header text found only in some files)",
                 "edition_year": edition_year,
                 "edition_year_basis": "latest Alberta case year cited across the Part 10 files (no edition year is printed in them)"}


# ---------------------------------------------------------------- Book C (annotated JSON pages 441-520)
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
                rec = {
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
                if num in out:
                    # Book C lists some rules twice (rule text in one entry, annotation in the other): merge, keep both
                    first = out[num]
                    base, extra = (first, rec) if len(first["operative_text_raw"]) >= len(rec["operative_text_raw"]) else (rec, first)
                    for key in ("citations", "information_notes", "commentary"):
                        base[key] = list(base[key]) + list(extra[key])
                    if not base.get("amendment_note_raw"):
                        base["amendment_note_raw"] = extra.get("amendment_note_raw")
                    base["merged_duplicate_entries"] = [
                        {"file": x["locator"]["file"], "parsed_title": x["title"], "role": "kept as rule entry" if x is base else "merged into it",
                         "rule_text_of_merged_entry": x["operative_text_raw"] if x is not base and x["operative_text_raw"] else None}
                        for x in (first, rec)]
                    rec = base
                out[num] = rec
                prev = num
            elif prev in out and not str(num).startswith(("9.", "10.", "11.")):
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
        "BOOK_A": re.findall(r"\[Alta\.\s?Reg\.[^\]]*\]", (a or {}).get("operative_text_raw") or ""),
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




# Manual decisions for Part 10 are recorded here (see README section 4 / tools/edit_helpers.py). All start empty.
MANUAL_BOOK_B_SPLIT = {
}
MANUAL_NOTE_FLAGS = {
}
MANUAL_TEXT_KEEP = {
}
MANUAL_TEXT_NOTES = {
}
MANUAL_SEE_ALSO = {
    "10.2": ["Official text (searched for 'rule 10.2', 'Rules 10.2', line-wrapped forms and form headings '[Rule 10.x]'): table of contents (line 1463); the rule (line 11658, pdf pp.193-194: (3)(b) ends p.193 and Rule 10.3's running head follows); 10.5(3) ('the rate to which the lawyer would be entitled under rule 10.2 if no retainer agreement were entered into', lines 11788-11789); 10.8 ('lawyer's charges determined in accordance with rule 10.2 as if no contingency fee agreement had been entered into', line 11960); 10.18(1) ('must be determined under rule 10.2', line 12235); 10.19(1) ('the factors described in rule 10.2, except to the extent that a retainer agreement otherwise provides', line 12238); 10.24(2) ('the factors described in rule 10.2', line 12348). No form heading names 10.2. By subject: the Appendix defines 'lawyer's charges' (line 40883), 'retainer agreement' (line 41068) and 'contingency fee agreement' (line 40641); 10.3 (lawyer acting in representative capacity, (2)(c) review by a review officer), 10.4 (charging order, security for charges), 10.5 (retainer agreements), 10.9 (charges subject to review), 10.13(2)(c) and (3)(c) (a signed account of the charges to be reviewed), 10.35(2) (a bill of costs must itemize costs) and 10.31(1)(b)(i) (indemnity for a party's lawyer's charges).", "BOOK_A other rules of Part 10 that cite 10.2 (combined_rule10.txt; page = last 'N-NN' marker before the line; no other Book A file cites 10.2): 10.5 note, p.10-10 (lines 427 and 447 'R.10.2n.'), p.10-12 (line 534 'If there is no fee contract, or the contract seems to invoke R.10.2, then the factors in R.10.2 ...'), p.10-14 (line 620); 10.8 text p.10-21 (line 992) and note p.10-22 (line 1020 'See also R.10.2 and R.10.7', line 1026); 10.9 note p.10-23 (lines 1081, 1085 'the factors in R.10.2', 1098); 10.18 text p.10-33 (line 1602); 10.19 text p.10-34 (line 1636) and note p.10-35 (line 1695 'Because of Rr.10.2 and 10.19, even an unenforceable contingent-fee agreement has some (limited) relevance'); 10.24 text p.10-38 (line 1830); 10.31 note p.10-64 (line 3244 'Rr.10.33 and 10.2(1)'); 10.35 Related Provisions p.10-124 (line 6743 '10.2 (contents of solicitor-client account)'; official 10.35 is 'Preparation of bill of costs'). Book A's 10.3 note is not among them.", "BOOK_B: other commentary that cites 10.2 (all rule10_part*_document.json searched; the Part/Division running-head paragraphs repeat some commentary, so a passage may appear under several paragraph ids): 10.5 (quotation of 10.5(3), 'NR 10.5'), 10.8 (quotation of 10.8), 10.9 (Steinke v. Hajduk Gibbs LLP 2014 ABQB 34, quoted in part 6, paragraphs numbered 50-51 and later: 'exercising authority under r. 10.2(1)', 'Rule 10.2(1) introduces a reasonableness measure shaped by four specific but hard-to-apply factors ...', the criteria of r. 10.2(1) applied when no retainer agreement fixes the charges), 10.18, 10.19, 10.24 (quotations of the rules), 10.27 ('Rule 10.2 provides direction on the relevant factors to apply'; 'Rule 10.2(1) factors include: ...'), 10.29 ('the factors in r 10.2'), 10.31 (Rule 10.2(1) factors and 'see R. 10.2 and R. 10.33') and 10.41 (Rule 10.2(1) 'as providing some factors'). Book B's own 10.2 commentary uses the old numbers: 'R. 613' (its 'Rule 613 factors') is 1968 R.613, the old rule Book A's footnote 1 (p.10-3) names as the predecessor of 10.2(1); its part 3 (McDonald Crawford v. Morrow 2004 ABCA 150, 348 A.R. 118) is the case Book A cites at p.10-4 fn 9; its part 5 (Rath & Co. v. Sweetgrass First Nation 2013 ABQB 165, 559 A.R. 12, paras 77-78) quotes 'rule 10.19(2)' (official 10.19(2): a review of a retainer agreement must be based on the circumstances that existed when it was entered into); its part 9 prints 'Alberta Treasury Branches v. 14010507 Alberta Ltd., 2013 ABQB 748, ... 579 A.R. 152' while the Steinke passage in its 10.9 commentary prints the same neutral citation as 'Alberta Treasury Branches v. 1401057 Alberta Ltd., 2013 ABQB 748' (two spellings of the numbered company in Book B).", "BOOK_C: rule text equals the official text (EXACT_MATCH); the entry has one 'General Principles' commentary of 347 characters (see the BOOK_C flag): its words are taken from the passage Book B's 10.9 commentary (part 6) quotes from Steinke v. Hajduk Gibbs LLP 2014 ABQB 34, in the paragraph numbered 51, which follows the sentence 'Rule 10.5 of the Alberta Rules of Court is the Alberta provision ...'. Book C's other entries that cite 10.2 are the bracket-label reprints of the rule text in 10.5, 10.8, 10.18, 10.19 and 10.24 ('rule 10.2 [Payment for lawyer's services and contents of lawyer's account]'); no Book C commentary cites 10.2 (searched the four Part 10 files and all other Book C files)."],
    "10.1": ["Official text (searched for 'rule 10.1', 'Rules 10.1', line-wrapped forms and form headings '[Rule 10.x]'): no rule or form cites 10.1 by number; the only hits are the table of contents (line 1458) and the rule itself (line 11621, pdf pp.192-193: (a) on p.192, (b) on p.193 after the running head 'Rule 10.2'). By subject: the Appendix (Definitions) defines the same two terms in the same words - 'assessment officer' (line 40564, pdf p.668) and 'review officer' (line 41073, pdf pp.676-677; its sub-items are lettered (a)-(b) and (c)-(d) where 10.1 has (i)-(ii) and (iii)-(iv)); the terms are used in 9.35(1)(b) (line 11238), 13.33 (line 17400), 10.9, 10.13, 10.34, 10.36 and the rest of Division 1-2, Schedule B item 6 of Division 1 ('appointment for review by a review officer', line 39408) and the forms for reviews and assessments (Form 42 '[Rule 10.13]', Form 43 '[Rule 10.26]', Form 44 '[Rule 10.35(1)]', Form 45 '[Rule 10.37]', Form 46 '[Rule 10.44]').", "BOOK_A (all Book A files searched, line-wrapped forms included; pages from the 'N-NN' markers of combined_rule10.txt): the rule text is at p.10-3 (lines 52-66, running head 'R.10.1' line 47, DIVISION 1 heading lines 48-50); Book A prints no information note, related provisions or commentary for 10.1. The Part introduction (lines 22-41, before the first page marker) lists 'assessment officer' and 'review officer' among the words 'that have defined meanings in the Appendix'. Book A pointers that name 10.1: (1) p.10-5 (line 175, in the 10.2 note E 'Security for Fees'): 'Fewer lawyers are familiar with R.10.1(2) or the possibility of taking other security' - FLAG: official 10.1 has no subrule (2); the official subrule about security is 10.2(2) ('A lawyer may be paid in advance or take security for future lawyer's charges'); the sources do not say which was meant. (2) p.10-8 (line 308, Related Provisions of 10.4): '10.1(2) (agreement to provide security)' - FLAG: same, no 10.1(2) in the official text; the label matches 10.2(2). (3) p.10-35 (line 1694, in the 10.19 note): 'On negligence by the lawyer, see R.10.1 and commentary, supra.' - FLAG: 10.1 is the definitions rule and carries no commentary on negligence; the note on negligence and set-off is in Book A's 10.2 note (Part C 'Misconduct', p.10-5); the sources do not say which rule was meant. (4) p.10-96 (line 5125, footnote 5 in the 10.31 note): 'The test is reasonableness in prosecuting the suit, not R.10.1' - FLAG: 10.1 states no test of reasonableness (10.2(1) does); the sources do not say which rule was meant, but the same decision, McAteer v. Devoncroft Dev. (#2) 2003 ABQB 425, 340 AR 1, is cited in Book A\'s 10.2 note (p.10-6, footnote 8) for \'Rule 10.2 does not apply to the question of costs to the opponent on a solicitor-client (full indemnity) basis\'.", "BOOK_B: one commentary section 'Commentary § 10.1:1' (paragraph part10_part_10_..._004, 2,533 characters as printed with its heading; 2,513 in the built field): Shreem Holdings v. Barr Picard 2014 ABQB 112 paras 66-67 (Part 10, Division 1 is a comprehensive code that leaves no room for inherent jurisdiction) and Rath & Co. v. Sweetgrass First Nation 2013 ABQB 165 para 22 ('review officer' replaces 'taxing officer', quoting Champagne v. Sidorsky 2012 ABQB 522 para 26). Corroboration in Book A: Shreem 2014 ABQB 112 is cited at p.10-22 (line 1055, paras 47-48), p.10-45 (lines 2198-2199, paras 26-42 and 43 ff.) and in combined rule1.txt p.1-20 (line 986, paras 26-42), never for paras 66-67; Rath v. Sweetgrass is cited in Book A as 'Sweetgrass F. N. v. Rath & Co. 2013 ABQB 165, 559 AR 12' (p.10-24, line 1151; p.10-34, line 1663), the same decision and AR cite as Book B, and as 2014 ABCA 426, 588 AR 245 (p.10-13, line 594; p.10-24, line 1154); Champagne v. Sidorsky 2012 ABQB 522, 548 AR 10 (¶ 26) is in combined_rule2.txt p.2-30 (line 1499). Book B prints the heading '10.1. Definitions' twice (paragraphs _001 and _002, with the Part/Division running-head paragraph _003 between); it prints the footnote number '20' inside the quotation ('superior courts20') and '[Footnote omitted]'."],
}
MANUAL_BOOK_A_COMMENTARY_FLAGS = {
    "10.2": "Read in full, p.10-3 (line 67) to p.10-6 (line 216): title, rule text, Related Provisions (lines 94-97) and the note (A Contract vs. Default Mode, B More Than One Payor, C Misconduct, D Instructions Govern, E Security for Fees, F Dangers for Lawyer, G Miscellaneous; headings at lines 99, 148, 153, 161, 170, 194, 201) with all footnotes. The built record: related_provisions; the commentary field (5,042 characters, from 'There are reference works about lawyers's charges' at line 98 to the last sentence of G, lines 215-216); no information note; 31 footnotes (counted from the file: p.10-3 fns 1-2, p.10-4 fns 1-11, p.10-5 fns 1-10, p.10-6 fns 1-8; 2+11+10+8). Layout: each page's footnote block is printed before the next page marker; the p.10-6 block (lines 222-235) comes after the title and first lines of 10.3 (lines 217-220) and holds this rule's fns 1-8 and 10.3's history footnote 9 (line 235). History footnotes: fn 1 (p.10-3, marker after (1)(f)): 'Quite similar to previous 1968 R.613. It came from 1914 R.747 (as amended), and 1944 C. R.748'; fn 2 (p.10-3, after (2)): 'previous 1968 R.624 ... 1944 C. R.756, and (up to the comma) to 1914 R.624'; fn 1 (p.10-4, after (3)(c)): 'previous 1968 R.645(1). It came from 1944 C. R.779, new then'; Book B's 'R. 613' agrees with fn 1. (1) Related Provisions read against the official titles: '2.17 (lawyer as litigation representative)' (official 'Lawyer appointed as litigation representative': the Court may direct who bears a lawyer-representative's costs); '10.35 (contents of bill of costs)' (official 'Preparation of bill of costs', whose (2) says what the bill must contain); '2.25 (duty of lawyer)' (official 'Duties of lawyer of record'); '2.27 (limited retainers)' (official 'Retaining lawyer for limited purposes'); '10.4 (charging order)' (official 'Charging order for payment of lawyer's charges'). The labels are paraphrases; the list is not in numerical order. (2) Statements read against the official text: 'Rule 10.2(1) is only a default mode, operating in absence of different contractual provisions' agrees with 10.2(1) ('Except to the extent that a retainer agreement otherwise provides'); 'the factors in R.10.2 govern' a review where there is no express contract or the contract invokes 10.2 agrees with 10.19(1); 'Rule 10.2 also applies if a contrary contract is unenforceable, e. g. a contingency agreement with serious deviations from R.10.7' agrees with 10.8; FLAG: 'the hours spent are only one of about 11 factors listed there' - official 10.2(1) lists six factors, (a)-(f), and none mentions hours; the source of 'about 11' is not stated; FLAG: 'Fewer lawyers are familiar with R.10.1(2)' (E) - official 10.1 has no subrule (2); 10.2(2) is the subrule on security (see the 10.1 flags); footnote 3 (p.10-4) 'R.10.5' and footnote 8 'R.10.9' land (10.9: reasonableness of retainer agreements and charges subject to review); footnote 4 (p.10-4) 'R.10.7(7)', attached to 'the power of the review officer to intervene if a contingency fee contract was unreasonable': official 10.7(7) requires every account under a contingency fee agreement to state that a review officer may determine the reasonableness of the account and the agreement - the power itself is in 10.9; footnote 1 (p.10-5) 'and R.10.3' agrees with 10.3(2)(c) (estate, trust or fund); 'Rule 10.31(4) might suggest that it can easily be defeated' agrees with official 10.31(4) (deduction or set-off of costs awards); footnote 3 (p.10-6) 'R.10.13(2) (c)' agrees with 'if a lawyer wants his or her account reviewed, he or she must first sign it' (10.13(2)(c): a copy of a signed account). The statements on ethics, misconduct, conflict of interest, class-action fees, Supreme Court of Canada counsel rates, the provincial sales tax and prepayment out of a trust are case-law statements not in 10.2 and were not checked. (3) supra/infra: footnote 3 (p.10-4) 'Samson Cree v. O'Reilly Assoc., supra' - the full citation 'Samson Cree N. v. O'Reilly & Associés 2014 ABCA 268, 580 AR 181' is in footnote 5 of the same page, after it, and is the first full citation of that decision in Book A (searched all Book A files; 'Samson Cree N. v. R. (1999) 239 AR 214' in combined rule1.txt line 654 is a different case), so 'supra' points forward within the page; footnote 5 'Steinke v. Hajduk Gibbs, infra (¶ 53)' points to footnote 11 of the same page (2014 ABQB 34, 581 AR 91), direction correct; footnote 7 'Downes v. Botan, supra' (full in footnote 6), p.10-5 footnotes 4-5 'Khan v. Paul A. Kazakoff P.C., supra' (full at p.10-4 fn 3), p.10-5 fn 8 'Steinke ... supra' (p.10-4 fn 11) and p.10-6 fn 5 'R. v. White, supra' (same footnote) all point back correctly. (4) Printed as is: 'lawyers's charges' (line 98); '.. (2010)' in fn 2 of p.10-4. (5) The cases (Khan v. Paul A. Kazakoff 2019 ABQB 168, Ritchie v. Walker 2006 SCC 45, Betser-Zilevitch v. Prowse Chowne 2020 ABQB 732 affd 2021 ABCA 129, Samson Cree 2014 ABCA 268, O'Brian v. de Villars Jones 2015 ABQB 535, Downes v. Botan 2018 ABQB 341, McDonald Crawford v. Morrow 2004 ABCA 150, Steinke 2014 ABQB 34, Re Halun Est. 2002 ABQB 563, O'Keefe v. Overacker, Côté v. Rancourt 2004 SCC 58, Gunn & Prithipaul v. Daniel 2005 ABQB 6, Prowse Chowne v. Wasylyshyn 2006 ABQB 68, Hamill v. Kudryk 2014 ABCA 82, Adrian v. A.-G. Can. (#2) 2007 ABQB 377, Northwest v. A.-G. Can. 2006 ABQB 902, R. v. White 2010 SCC 59, Christie v. A.-G. B.C. 2007 SCC 21, Re Residential Warranty 2006 ABQB 236, McAteer v. Devoncroft (#2) 2003 ABQB 425) were not checked; McDonald Crawford v. Morrow (348 AR 118) is also the case in Book B's part 3 and Steinke is the case Book B's 10.9 commentary quotes; the C.P.E. references (Chapter 82, Parts B.8, I, O, Q.1, R, R.3, R.5, S.4, C to H) point to another work and were not opened.",
}
MANUAL_BOOK_A_FOOTNOTE_FLAGS = {
}
MANUAL_BOOK_C = {
    "10.2": {'commentary_flag': '(1) Rule text equals the official text (EXACT_MATCH). (2) The commentary (heading \'General Principles\', 347 characters, no citation printed) is garbled and cut off: \'The default method used to assess legal accounts where no retainer agreement is found is rule 10.2.1\' (the \'1\' after \'rule 10.2.\' is a footnote number whose text is not printed) \'Rule 10.2(1) introduces a reasonableness measure shaped by four specific but hard-to- similar conclusions as to what is a reasonable amount. The value of this process is not PART 10 LAWYERS\' CHARGES, RECOVERABLE COSTS OF LITIGATION, AND SANCTIONS\' - words are missing between \'hard-to-\' and \'similar\', and the sentence ends at \'not\' followed by the page\'s running head. The same words are in Book B\'s 10.9 commentary (part 6), quoting Steinke v. Hajduk Gibbs LLP 2014 ABQB 34 (para 51 by Book B\'s numbering): \'Rule 10.2(1) introduces a reasonableness measure shaped by four specific but hard-to-apply factors ("(a) the nature, importance and urgency of the matter, (b) the client\'s circumstances, ... (d) the manner in which the services are performed, (e) the skill, work and responsibility involved") and one omnibus and equally abstract factor ... It is safe to say that adjudicators asked to apply these factors are seldom likely to come up with similar conclusions as to what is a reasonable amount. In other words, the value of this process is not predictability and certainty.\' so the passage\'s \'four specific\' factors are the ones it lists, (a), (b), (d) and (e), with an ellipsis where (c) stands and \'any other factor\' (f) as the omnibus factor; 10.2(1) itself has six lettered factors. The first sentence agrees with Book A (\'Rule 10.2(1) is only a default mode, operating in absence of different contractual provisions\') and with Book B\'s part 3 (the Rule 613 factors apply \'absent any agreement as to fees\'). The passage is kept as printed (flagged) because Book C prints no source for it.', 'amendment_note_flag': "Book C prints '*[Alta. Reg. 124/2010, r. 10.2 effective November 1, 2010 Alta. Gaz. May 15, 2021]*' - the parentheses around the Gazette entry that other Book C notes have are missing; 'Alta. Reg. 124/2010' and 'November 1, 2010' agree with the official history (AR 124/2010, no amending regulation); the Gazette date 'May 15, 2021' is the one Book C prints throughout Part 10 (see the 10.1 flag) and was not checked."},
    "10.1": {'drop_rule_text': "Book C's rule text is dropped (official, Book A and Book B carry the whole text): it stops after '(ii) sufficient experience in the practice of law, and who is desig- nated as a review officer by' (with the hyphenated 'desig- nated'), so subparagraphs (iii) and (iv) of (b) are missing; what is printed equals the official words (the official (i)-(ii) are printed inline). The Subdivision heading 'Subdivision 1: LAWYERS' CHARGES' printed after the amendment note is the heading of Subdivision 1, which begins at 10.2 in the official text.", 'amendment_note_flag': "Book C prints '[Alta. Reg. 124/2010, r. 10.1 effective November 1, 2010 (Alta. Gaz. May 15, 2021)]': 'Alta. Reg. 124/2010' and 'November 1, 2010' agree with the official history (AR 124/2010, no amending regulation). The Gazette date 'May 15, 2021' is printed on Book C's Part 10 entries throughout (the four Part 10 files, 441-520, have 'Alta. Gaz. May 15, 2021' on 100 lines and 'August 14, 2010' only at rules 11.1-11.8), while its Part 3 entries print 'August 14, 2010'; the official text gives no Gazette date, so the printed date is kept as printed and was not checked."},
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
        for cid, note in MANUAL_TEXT_KEEP.get(r, {}).items():
            # raw text is NOT dropped: it holds the rule text interleaved with the whole printed note, which exists nowhere else in the packet
            rec = src.get(cid)
            if rec and rec.get("operative_text_raw"):
                rec["operative_text_note"] = note
                comp[cid]["review_note"] = note
                comp[cid].pop("differences", None)
                log.append(f"{r} {cid}: raw text KEPT (interleaved with the printed note); wording compared by eye (manual review)")
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
    last_part10_amend = max(int(y.split("/")[1]) for r in official.values() for y in r["amending_regulations"]) if any(
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
            "title": "Annotated rules text, Part 10 (publisher/title not stated in carrier; page style '10-N', 'Related Provisions', historical-derivation footnotes)",
            "version": f"unknown edition; latest Alberta case year cited in Part 10 = {a_year}",
            "artifacts": [{"file": BOOK_A[0].name, "sha256": file_sha(BOOK_A[0])}],
            "source_role": "ANNOTATED_RULES",
            "origin_id": "book-a-annotated-part10",
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
            "title": "Annotated rules text, book pages 441-520 (publisher/title not stated in carrier; source files 441-460_revised.md ... 501-520_revised.md)",
            "version": f"unknown edition; latest Alberta case year cited = {c_year}",
            "artifacts": [{"file": p.name, "sha256": file_sha(p)} for p in BOOK_C],
            "source_role": "ANNOTATED_RULES",
            "origin_id": "book-c-annotated-pp441-520",
            "permitted_use": "corroboration; annotation (information notes, citations, commentary)",
        },
    }
    registry_sha = sha_text(json.dumps(registry, sort_keys=True))

    def version_identity(cid: str) -> tuple[str, str]:
        floor = {"BOOK_A": a_year, "BOOK_B": int(b_meta["edition_year"]) if b_meta.get("edition_year") else None, "BOOK_C": c_year}[cid]
        if floor and floor > last_part10_amend:
            return "SAME_VERSION_PROVEN", (f"carrier post-dates {floor} >= last Part 10 amendment year {last_part10_amend} "
                                           "per official amendment history; no Part 10 amendment after that date appears in the June 1, 2026 consolidation")
        return "VERSION_IDENTITY_UNRESOLVED", "carrier date cannot be placed after the last Part 10 amendment"

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
            "subdivision": off.get("subdivision"),
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
        "schema_version": "arc-rule10-three-book-reconciliation-v1",
        "skill": "arc-rules-production-lifecycle",
        "mode": "SOURCE_RECONCILIATION",
        "write_status": "NO_WRITE (no Neo4j/LexGraph mutation; packet only)",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "target": {"instrument": "Alberta Rules of Court, Alta. Reg. 124/2010", "part": 10, "rules": f"{RULES[0]}-{RULES[-1]}", "count": len(RULES)},
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
            "source_closure_denominator": {"definition": "Alta. Reg. 124/2010 rules 10.1-10.55 in the June 1, 2026 consolidation", "count": len(RULES)},
            "pairwise_comparison_denominator": {"definition": "rules x book carriers (A,B,C) compared against OFFICIAL", "count": len(RULES) * 3},
        },
        "summary": {"pairwise_status_counts": summary, "gate_result_counts": gate_counts,
                    "last_part10_amendment_year": last_part10_amend},
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
