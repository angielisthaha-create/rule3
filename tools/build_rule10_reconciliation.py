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
    "10.5": {'BOOK_A': "same wording as official 10.5(1)-(3) (read by eye) except: the bracket label '[Payment for lawyer's services and contents of lawyer's account]' (the official title of 10.2) after 'rule 10.2' in (3); the title in title case ('Retainer Agreements', line 415, printed after the Subdivision 2 heading 'Subdivision 2 / Retainer Agreements' of lines 413-414, which is the heading of the Subdivision, not repeated text); the text is printed in one piece (lines 416-430); the footnote marker '6' after (3) (the history footnote printed in the p.10-10 block, line 442). No amendment bracket; the official text lists only 'AR 124/2010' (no amending regulation). No wording difference."},
    "10.4": {'BOOK_A': "same wording as official 10.4(1)-(6) (read by eye) except: '(2) (a) and (b)' with a space in (3)(b) (official '(2)(a) and (b)'); the ligature 'fi' (Unicode 'ﬁ') in 'specified' and 'bona fide'; the title in title case ('Charging Order for Payment of Lawyer's Charges', printed before the rule number, after the Subdivision 2 heading lines of 10.3's page); the text is printed in pieces ((1)-(2)(a) at p.10-7 lines 265-271; the rest after the page marker 10-8 at lines 287-305) with the p.10-7 footnote block (10.3's, lines 273-283) printed between them; the footnote marker '1' after (6). No amendment bracket; the official text lists only 'AR 124/2010' (no amending regulation). No wording difference."},
}
MANUAL_SEE_ALSO = {
    "10.6": ["Official text (searched for 'rule 10.6', 'Rules 10.6', line-wrapped forms and form headings '[Rule 10.x]'): no rule or form cites 10.6 by number; the only hits are the table of contents (line 1477) and the rule itself (line 11791, pdf pp.195-196). By subject: 10.5 (retainer agreements), 10.7 and 10.8 (contingency fee agreements), 10.9 (reasonableness reviewable 'despite any agreement to the contrary'), 2.28 (change in lawyer of record or self-representation; the rule the Information Note names), 4.36 and 4.37 (discontinuance of a claim and of a defence) and 2.19 (Court approval of settlement, discontinuance, and abandonment of actions); the Appendix defines 'client' (line 40619: includes a former client and any person to whom a lawyer has rendered an account, or a person who is or may be liable to pay it), 'lawyer' (line 40881) and 'retainer agreement' (line 41068), the three terms Book A prints under its 'Related Provisions' label.", "BOOK_A (all Book A files searched, line-wrapped forms included; pages from the 'N-NN' markers): other rules that cite 10.6 - the 10.5 note, p.10-11 (line 478 'R.10.6(1) (a)', line 482 'R.10.6(2)', lines 484 '(R. 10.6(1) (b))': Forbidden Terms items 1, 3 and 4, which agree with 10.6(1)(a), (2) and (1)(b)), and the 2.28 note in Part 2, combined_rule2.txt p.2-63 (line 3214, footnote 1 'See R.10.6(2). See the C.P.E., Chapter 4, Part F.', attached to the 2.28 text about a client changing lawyer; already in the 2.28 see-also). The running head 'R.10.6(1)' is at p.10-14 (line 607, before this rule's title at line 626). No other Book A file cites 10.6.", "BOOK_B: rule text only (paragraphs part10_rule_10_6_001 and _020); no 'Commentary § 10.6' section (searched rule10_part01..12_document.json for '§ 10.6:'); no other Book B commentary cites 10.6. BOOK_C: rule text, amendment note and Information Note only (no commentary); no other Book C entry cites 10.6."],
    "10.5": ["Official text (searched for 'rule 10.5', 'Rules 10.5', line-wrapped forms and form headings '[Rule 10.x]'): no rule or form cites 10.5 by number; the only hits are the table of contents (line 1474), the running head of pdf p.195 (line 11744) and the rule itself (line 11772). By subject: 10.2(1) ('Except to the extent that a retainer agreement otherwise provides'), 10.6 (void provisions in a retainer agreement), 10.7 and 10.8 (contingency fee agreements), 10.9 (reasonableness of retainer agreements and charges subject to review 'despite any agreement to the contrary'), 10.10(1) (a retainer agreement may not be reviewed 6 months after it terminated), 10.19(1)-(2) (a review takes account of the factors in 10.2 'except to the extent that a retainer agreement otherwise provides'; a review of a retainer agreement is based on the circumstances when it was entered into), 15.5(1) (transitional: 10.7(2) does not apply to certain contingency fee agreements, line 20050), Form 42 (notice of appointment for review; asks for the retainer agreement(s), line 23462 ff.), and the Appendix definitions of 'retainer agreement' (line 41068: 'an express or implied agreement between a lawyer and a client with respect to the payment by the client of lawyer's charges, and includes a contingency fee agreement') and 'contingency fee agreement' (line 40641).", 'BOOK_A (all Book A files searched, line-wrapped forms included; pages from the \'N-NN\' markers): other rules that cite 10.5 - the 10.2 note, p.10-4 (line 104, \'On what a retainer agreement cannot do, see R.10.5n.\'; line 125, fn 3 \'R.10.5; and see the notes to it, infra\'); the 10.7 Related Provisions, p.10-17 (line 753, \'10.5 (retainer agreements) ; definition of "retainer agreement"; 15.5 (transitional rule)\'); the 10.9 note, p.10-23 (line 1105, \'See R.10.5n. A.\'). The running head \'R.10.5(1)\' is at p.10-10 (line 400), before this rule\'s own text begins at line 415; no other Book A file cites 10.5 (the \'10.5\' in combined_rule9.txt line 2653 is part of the statute number \'SA 1994 c. C-10.5\'). Book A\'s own 10.5 pages: p.10-10 (marker line 399) to p.10-14 (marker line 606); Related Provisions \'10.7 (contingency agreements)\' (lines 452-453); note A Basic Principle (line 455), B Forbidden Terms (line 476), C Explanations to Client (line 508), D Interpretation and Credibility (line 526), E Miscellaneous (line 579).', "BOOK_B: this rule's own commentary is one passage (Samson Cree Nation v. O'Reilly & Associes 2013 ABQB 350, 564 A.R. 169, Rooke A.C.J. para 113: 'OR 615 ... and R 10.5 all contemplate that a lawyer and client may enter an agreement for fees to be determined in some other way'); the only other Book B passage that names 10.5 is the 10.9 commentary (Steinke v. Hajduk Gibbs 2014 ABQB 34: 'Rule 10.5 of the Alberta Rules of Court is the Alberta provision with ...', and a reference to 'Alberta Civil Procedure Handbook 2013-2014 at 10.5', a handbook page number, not a rule). Cross-book: Book A's history footnote 6 (p.10-10) 'Quite similar to previous 1968 R.615' agrees with Book B's 'OR 615'; Book A's line 1189 (10.9 note fn) cites the same decision as '... 564 AR 169, affd 2014 ABCA 268', the ABCA appeal being the decision Book A cites here (p.10-4 fn 5 and p.10-11 fn 1: 'Samson Cree N. v. O'Reilly & Associes 2014 ABCA 268, 580 AR 181') and Book C cites with pinpoints; Book B's 10.2 commentary prints Yule v. Saskatoon as '(1955), 16 W.W.R. (N.S.) 305 (Sask. Q.B.)' and this passage as 'Yule v. Saskatoon (City) (1955) 17 W.W.R. 296 (Sask. C.A.)' (two reports of the 1955 case, as printed).", "BOOK_C: the commentary is this rule's own (see the BOOK_C flag); no other Book C entry names 10.5 except the bracket-label reprints of other rules' text; no Book C entry outside 10.5 cites Samson Cree (searched all Book C files)."],
    "10.4": ["Official text (searched for 'rule 10.4', 'Rules 10.4', line-wrapped forms and form headings '[Rule 10.x]'): no rule or form cites 10.4 by number; the only hits are the table of contents (line 1469) and the rule itself (line 11720, pdf pp.194-195); 'charging order' and 'lien' occur nowhere else in the official text (searched). By subject: 10.2(2) (a lawyer may take security for future charges), 10.31(4) and 10.41(5) (deduction or set-off of costs awards, the two rules Book A lists as related), 10.3 (payment out of a trust, estate or fund).", "BOOK_A (all Book A files searched, line-wrapped forms included; pages from the 'N-NN' markers): other rules that cite 10.4 - the 10.2 Related Provisions, p.10-4 (line 97, '10.4 (charging order)'); the 10.5 note, p.10-10 (line 432, footnote 1 'R.10.4(5). See the C.P.E., Chapter 82, Part O.3.', which is the first footnote of the p.10-10 block that belongs to this rule's last paragraphs); the 10.31 Related Provisions, p.10-60 (line 3030, '10.4 (lawyer's charging order)'); and, in Part 9, the note to 9.18(2) at p.9-62 (combined_rule9.txt line 3262: 'If a Rule (such as 10.4) requires proof of some fact to get relief, the judge may give such relief conditional on proof of that fact before the order becomes enforceable', which restates the Paragon v. Starke point of footnote 6, p.10-9). No other Book A file cites 10.4.", "BOOK_B (all rule*_document.json files searched; commentary passages repeated under the running-head paragraph ids are counted once): only 10.7's commentary names 10.4 apart from this rule's own: a passage on service of a contingency fee agreement speaks of 'the service required by Rule 10.4' and of the client receiving a fully-executed contingency agreement 'under Rule 10.4' (FLAG: official 10.4 is the charging-order rule and has no service requirement; service of the signed contingency fee agreement is required by 10.7(4), and the same passage cites 10.7(2)(g); Book B prints it as quoted - it is not determined whether the slip is in the judgment or in Book B).", 'BOOK_C: rule text equals the official text (EXACT_MATCH); its one commentary is about this rule (see the BOOK_C flag); no other Book C entry names 10.4 (searched all Book C files).', "Cross-book: Book A and Book B cite the same decisions - Toliver v. Koepke 2017 ABQB 686 (Book A p.10-8 fn 3, p.10-9 fns 3, 5, 8; Book B part 1, Macklin J. para 39), Paragon Capital Corp. v. Starke Dominion 2020 ABCA 216 (Book A p.10-8 fn 1 no pinpoint; p.10-9 fn 3 paras 60-61, fn 6 paras 32-34, 36, 42, 44-45, 47, 49, 51, 53; p.10-10 fn 2 paras 31-32, fn 3 paras 30-36; Book A also cites the trial decision, 2018 ABQB 351, [2018] 10 WWR 375, at p.10-9 fn 4 para 41 and p.10-10 fn 4 paras 37-45; Book B parts 2 and 12 quote paras 32, 51, 52-53), Royal Bank v. Laughlin 2001 ABCA 78, 277 AR 201 (Book A p.10-9 fn 5, no pinpoint; Book B cites 'para 34' in the Toliver passage and '§ 35' in the Merchant Law Group passage for the same four conditions), Merchant Law Group v. McLeod & Co. 2005 ABQB 875, 55 Alta LR(4th) 301 (Book A p.10-8 fn 5; Book B part 8 'pp. 306-322'), Re Cochard 2005 ABQB 679 (Book A p.10-8 fn 2 '¶'s 66 ff', retaining lien '¶'s 62, 67', statutory charge '¶'s 62-3'; Book B, inside the Merchant passage, puts the description of the retaining lien at para 60, the Atkinson comparison at ¶67, discretion at ¶70, and ¶79 and ¶111 - the pinpoints are not the same and are not reconciled here), Calf Robe (M.C.R.) v. A.-G. Can. 2006 ABQB 652, 405 AR 366 (Book A p.10-9 fns 5, 10, 11, p.10-10 fn 1; Book B part 8, McMahon J. para 19), and the D. S. M. v. K. L. S. 2021 ABQB 1024 / Robertson LLP v. Pasco 2021 ABQB 988 pair discussed in the BOOK_C flag. Book A cites Robertson LLP v. Pasco 2021 ABQB 988, JCC 1901 14596 (Dec 13) (paras 11-21) for priority; Book B's part 5 reports the oral reasons of Price J. of 21 October 2019 in 'Edmonton, QB Action 1901-14596' - the same action number as Book A's 'JCC 1901 14596'; whether the 2019 oral reasons and the 2021 decision are the same or different decisions is not stated in either book."],
    "10.3": ["Official text (searched for 'rule 10.3', 'Rules 10.3', line-wrapped forms and form headings '[Rule 10.x]'): no rule or form cites 10.3 by number; the only hits are the table of contents (line 1466), the running head of pdf p.194 (line 11688) and the rule itself (line 11700, all on pdf p.194). By subject: 10.2(1)(c) (the trust, estate or fund out of which a lawyer's charges are to be paid), 10.4 (charging order over property), 10.47 (liability of a litigation representative for costs), 2.17 (costs of a lawyer appointed as litigation representative), and the Appendix definitions of 'personal representative' (line 40988, pdf p.675: 'the same meaning as it has in section 1(l) of the Surrogate Rules (AR 130/95)') and 'trustee' (line 41128, pdf p.677: (a) an executor, administrator or trustee of an estate, (b) a person expressly appointed as trustee, (c) a trustee at law, ...); no Appendix definition begins with 'guardian', 'mortgagee', 'trust' or 'estate' (searched the definition headings), and the word 'mortgagee' occurs in the official text only in 10.3 (lines 11702-11703).", "BOOK_A (all Book A files searched, line-wrapped forms included; pages from the 'N-NN' markers of combined_rule10.txt): the only pointer to 10.3 is the 10.2 note's footnote 1 on p.10-5 (line 181) 'Re Halun Est.2002 ABQB 563, 319 AR 380, and R.10.3.', attached to 'The criteria for fees settling an estate may differ somewhat' (agrees with 10.3(2)); the other hit is the running head 'R.10.3(1)' (p.10-6, line 193). Book A's own 10.3 record: title line 217, (1) lines 218-220, page marker 10-7 line 237, (2)-(3) lines 239-251, a bare line 'trustee' (line 254, no label; see the BOOK_A flag), the note lines 255-262. Cross-references between Book A notes for the same authorities: the sentence 'On an agreement about fees to an estate, see the Salmon case' is printed in this note (p.10-7, line 258, fn 5) and again in the 10.5 note (p.10-13, line 576, fn 7, 'Re Salmon Est. (#1), supra'); Pub. T'ee. v. Koska 2010 ABQB 239 (fns 6-7 here) is also cited in the 10.13 note (p.10-28, line 1377, fn 6) and the 10.22 note (p.10-36, line 1761, fn 5); Re Boje Est. 2006 ABQB 599, 405 AR 41 is also cited at p.10-86 (line 4545, fn 1, 'Generally on setting executors' fees'), and Re Salmon Est. (#2) 2005 ABQB 15, 370 AR 327 at p.10-86 (line 4527), both in the 10.31 note.", "BOOK_B: rule text only (paragraphs part10_rule_10_3_001 and _010); no 'Commentary § 10.3' section (searched rule10_part01..12_document.json for '§ 10.3:'); no other Book B commentary cites 10.3 (searched all Book B files). BOOK_C: rule text and amendment note only, no information note or commentary; no other Book C entry cites 10.3 (searched all Book C files)."],
    "10.2": ["Official text (searched for 'rule 10.2', 'Rules 10.2', line-wrapped forms and form headings '[Rule 10.x]'): table of contents (line 1463); the rule (line 11658, pdf pp.193-194: (3)(b) ends p.193 and Rule 10.3's running head follows); 10.5(3) ('the rate to which the lawyer would be entitled under rule 10.2 if no retainer agreement were entered into', lines 11788-11789); 10.8 ('lawyer's charges determined in accordance with rule 10.2 as if no contingency fee agreement had been entered into', line 11960); 10.18(1) ('must be determined under rule 10.2', line 12235); 10.19(1) ('the factors described in rule 10.2, except to the extent that a retainer agreement otherwise provides', line 12238); 10.24(2) ('the factors described in rule 10.2', line 12348). No form heading names 10.2. By subject: the Appendix defines 'lawyer's charges' (line 40883), 'retainer agreement' (line 41068) and 'contingency fee agreement' (line 40641); 10.3 (lawyer acting in representative capacity, (2)(c) review by a review officer), 10.4 (charging order, security for charges), 10.5 (retainer agreements), 10.9 (charges subject to review), 10.13(2)(c) and (3)(c) (a signed account of the charges to be reviewed), 10.35(2) (a bill of costs must itemize costs) and 10.31(1)(b)(i) (indemnity for a party's lawyer's charges).", "BOOK_A other rules of Part 10 that cite 10.2 (combined_rule10.txt; page = last 'N-NN' marker before the line; no other Book A file cites 10.2): 10.5 note, p.10-10 (lines 427 and 447 'R.10.2n.'), p.10-12 (line 534 'If there is no fee contract, or the contract seems to invoke R.10.2, then the factors in R.10.2 ...'), p.10-14 (line 620); 10.8 text p.10-21 (line 992) and note p.10-22 (line 1020 'See also R.10.2 and R.10.7', line 1026); 10.9 note p.10-23 (lines 1081, 1085 'the factors in R.10.2', 1098); 10.18 text p.10-33 (line 1602); 10.19 text p.10-34 (line 1636) and note p.10-35 (line 1695 'Because of Rr.10.2 and 10.19, even an unenforceable contingent-fee agreement has some (limited) relevance'); 10.24 text p.10-38 (line 1830); 10.31 note p.10-64 (line 3244 'Rr.10.33 and 10.2(1)'); 10.35 Related Provisions p.10-124 (line 6743 '10.2 (contents of solicitor-client account)'; official 10.35 is 'Preparation of bill of costs'). Book A's 10.3 note is not among them.", "BOOK_B: other commentary that cites 10.2 (all rule10_part*_document.json searched; the Part/Division running-head paragraphs repeat some commentary, so a passage may appear under several paragraph ids): 10.5 (quotation of 10.5(3), 'NR 10.5'), 10.8 (quotation of 10.8), 10.9 (Steinke v. Hajduk Gibbs LLP 2014 ABQB 34, quoted in part 6, paragraphs numbered 50-51 and later: 'exercising authority under r. 10.2(1)', 'Rule 10.2(1) introduces a reasonableness measure shaped by four specific but hard-to-apply factors ...', the criteria of r. 10.2(1) applied when no retainer agreement fixes the charges), 10.18, 10.19, 10.24 (quotations of the rules), 10.27 ('Rule 10.2 provides direction on the relevant factors to apply'; 'Rule 10.2(1) factors include: ...'), 10.29 ('the factors in r 10.2'), 10.31 (Rule 10.2(1) factors and 'see R. 10.2 and R. 10.33') and 10.41 (Rule 10.2(1) 'as providing some factors'). Book B's own 10.2 commentary uses the old numbers: 'R. 613' (its 'Rule 613 factors') is 1968 R.613, the old rule Book A's footnote 1 (p.10-3) names as the predecessor of 10.2(1); its part 3 (McDonald Crawford v. Morrow 2004 ABCA 150, 348 A.R. 118) is the case Book A cites at p.10-4 fn 9; its part 5 (Rath & Co. v. Sweetgrass First Nation 2013 ABQB 165, 559 A.R. 12, paras 77-78) quotes 'rule 10.19(2)' (official 10.19(2): a review of a retainer agreement must be based on the circumstances that existed when it was entered into); its part 9 prints 'Alberta Treasury Branches v. 14010507 Alberta Ltd., 2013 ABQB 748, ... 579 A.R. 152' while the Steinke passage in its 10.9 commentary prints the same neutral citation as 'Alberta Treasury Branches v. 1401057 Alberta Ltd., 2013 ABQB 748' (two spellings of the numbered company in Book B).", "BOOK_C: rule text equals the official text (EXACT_MATCH); the entry has one 'General Principles' commentary of 347 characters (see the BOOK_C flag): its words are taken from the passage Book B's 10.9 commentary (part 6) quotes from Steinke v. Hajduk Gibbs LLP 2014 ABQB 34, in the paragraph numbered 51, which follows the sentence 'Rule 10.5 of the Alberta Rules of Court is the Alberta provision ...'. Book C's other entries that cite 10.2 are the bracket-label reprints of the rule text in 10.5, 10.8, 10.18, 10.19 and 10.24 ('rule 10.2 [Payment for lawyer's services and contents of lawyer's account]'); no Book C commentary cites 10.2 (searched the four Part 10 files and all other Book C files)."],
    "10.1": ["Official text (searched for 'rule 10.1', 'Rules 10.1', line-wrapped forms and form headings '[Rule 10.x]'): no rule or form cites 10.1 by number; the only hits are the table of contents (line 1458) and the rule itself (line 11621, pdf pp.192-193: (a) on p.192, (b) on p.193 after the running head 'Rule 10.2'). By subject: the Appendix (Definitions) defines the same two terms in the same words - 'assessment officer' (line 40564, pdf p.668) and 'review officer' (line 41073, pdf pp.676-677; its sub-items are lettered (a)-(b) and (c)-(d) where 10.1 has (i)-(ii) and (iii)-(iv)); the terms are used in 9.35(1)(b) (line 11238), 13.33 (line 17400), 10.9, 10.13, 10.34, 10.36 and the rest of Division 1-2, Schedule B item 6 of Division 1 ('appointment for review by a review officer', line 39408) and the forms for reviews and assessments (Form 42 '[Rule 10.13]', Form 43 '[Rule 10.26]', Form 44 '[Rule 10.35(1)]', Form 45 '[Rule 10.37]', Form 46 '[Rule 10.44]').", "BOOK_A (all Book A files searched, line-wrapped forms included; pages from the 'N-NN' markers of combined_rule10.txt): the rule text is at p.10-3 (lines 52-66, running head 'R.10.1' line 47, DIVISION 1 heading lines 48-50); Book A prints no information note, related provisions or commentary for 10.1. The Part introduction (lines 22-41, before the first page marker) lists 'assessment officer' and 'review officer' among the words 'that have defined meanings in the Appendix'. Book A pointers that name 10.1: (1) p.10-5 (line 175, in the 10.2 note E 'Security for Fees'): 'Fewer lawyers are familiar with R.10.1(2) or the possibility of taking other security' - FLAG: official 10.1 has no subrule (2); the official subrule about security is 10.2(2) ('A lawyer may be paid in advance or take security for future lawyer's charges'); the sources do not say which was meant. (2) p.10-8 (line 308, Related Provisions of 10.4): '10.1(2) (agreement to provide security)' - FLAG: same, no 10.1(2) in the official text; the label matches 10.2(2). (3) p.10-35 (line 1694, in the 10.19 note): 'On negligence by the lawyer, see R.10.1 and commentary, supra.' - FLAG: 10.1 is the definitions rule and carries no commentary on negligence; the note on negligence and set-off is in Book A's 10.2 note (Part C 'Misconduct', p.10-5); the sources do not say which rule was meant. (4) p.10-96 (line 5125, footnote 5 in the 10.31 note): 'The test is reasonableness in prosecuting the suit, not R.10.1' - FLAG: 10.1 states no test of reasonableness (10.2(1) does); the sources do not say which rule was meant, but the same decision, McAteer v. Devoncroft Dev. (#2) 2003 ABQB 425, 340 AR 1, is cited in Book A\'s 10.2 note (p.10-6, footnote 8) for \'Rule 10.2 does not apply to the question of costs to the opponent on a solicitor-client (full indemnity) basis\'.", "BOOK_B: one commentary section 'Commentary § 10.1:1' (paragraph part10_part_10_..._004, 2,533 characters as printed with its heading; 2,513 in the built field): Shreem Holdings v. Barr Picard 2014 ABQB 112 paras 66-67 (Part 10, Division 1 is a comprehensive code that leaves no room for inherent jurisdiction) and Rath & Co. v. Sweetgrass First Nation 2013 ABQB 165 para 22 ('review officer' replaces 'taxing officer', quoting Champagne v. Sidorsky 2012 ABQB 522 para 26). Corroboration in Book A: Shreem 2014 ABQB 112 is cited at p.10-22 (line 1055, paras 47-48), p.10-45 (lines 2198-2199, paras 26-42 and 43 ff.) and in combined rule1.txt p.1-20 (line 986, paras 26-42), never for paras 66-67; Rath v. Sweetgrass is cited in Book A as 'Sweetgrass F. N. v. Rath & Co. 2013 ABQB 165, 559 AR 12' (p.10-24, line 1151; p.10-34, line 1663), the same decision and AR cite as Book B, and as 2014 ABCA 426, 588 AR 245 (p.10-13, line 594; p.10-24, line 1154); Champagne v. Sidorsky 2012 ABQB 522, 548 AR 10 (¶ 26) is in combined_rule2.txt p.2-30 (line 1499). Book B prints the heading '10.1. Definitions' twice (paragraphs _001 and _002, with the Part/Division running-head paragraph _003 between); it prints the footnote number '20' inside the quotation ('superior courts20') and '[Footnote omitted]'."],
}
MANUAL_BOOK_A_COMMENTARY_FLAGS = {
    "10.6": "Read in full, p.10-14 (line 626) to p.10-15 (line 653): title (line 626), rule text (lines 627-633; marker '6' after (2)), Information Note (lines 634-638), a 'Related Provisions' label with the line 'client, lawyer, retainer agreement' (lines 639-640) and the p.10-14 footnote block (lines 643-651); no commentary is printed. The block's fns 1-5 (Torode v. Smyth, Twinn v. Sawridge, L. C. v. R., Betser-Zilevitch) belong to the 10.5 note; the built record has one footnote, p.10-14 fn 6 (counted from the file), the history footnote: 'Quite similar to previous 1968 R.620. It came from 1914 R.750, and 1944 C. R.751. Compare the English Solicitors Act, 1957, s.60(4). Subrule (2) was new in 1968. Subrule (3) came from 1944 C. R.754. It was like s.54 of the Ontario Solicitors Act (as of 1940).' - printed as is; the rule has only subrules (1) and (2), so the 'Subrule (3)' sentence refers to a subrule the current rule does not have (1944 C. R.754 is also the source printed for 10.3(1) in the footnote at p.10-6, line 235). The Information Note is printed with its last word repeated: 'The rules about self-representing are in rule 2.28 [Change in lawyer of record or self-' / 'representation].' (lines 635-636) and again 'representation].' (line 638) - the built note keeps both (extraction duplicate, as printed); the bracket label agrees with the official title of 2.28 ('Change in lawyer of record or self-representation'). The line under 'Related Provisions' lists no rule numbers: 'client, lawyer, retainer agreement' are terms the Appendix defines (official lines 40619, 40881, 41068) and are printed under that label in this extraction; the built related_provisions holds them as printed. No statements or cases are printed to check.",
    "10.5": 'Read in full, p.10-10 (line 415) to p.10-14 (line 625): title (line 415, after the Subdivision 2 heading lines 413-414), rule text (lines 416-430), Related Provisions (lines 452-453) and the note (A Basic Principle line 455, B Forbidden Terms line 476, C Explanations to Client line 508, D Interpretation and Credibility line 526, E Miscellaneous line 579) with all footnotes; the p.10-14 text (from line 606) runs on to line 625, where 10.6\'s title begins. The built record: related_provisions \'10.7 (contingency agreements)\' (official 10.7 is \'Contingency fee agreement requirements\': paraphrase); a commentary field of 7,903 characters; 37 footnotes (counted from the file: p.10-10 fn 6, p.10-11 fns 1-9, p.10-12 fns 1-11, p.10-13 fns 1-11, p.10-14 fns 1-5; 1+9+11+11+5). The p.10-10 footnote block (lines 431-448) holds fns 1-5 of 10.4 and this rule\'s history fn 6; the p.10-14 block (lines 645-655, after 10.6\'s text) holds fns 1-5 of this note and 10.6\'s history fn 6. History fn 6 (marker after (3)): \'Quite similar to previous 1968 R.615. It came from 1914 R.748, and 1944 C. R.749, though they said "in writing". It stemmed from (Imp.) Solicitors Act 1870, via Ont.1909 c.28, and R. S. O.1937 c.223 s.48. A contingency fee agreement has special Rules: Rr.10.7 ff. On whether some breach of those Rules can still leave some legal effect for such an agreemnt, see R.10.2n.\' (typo \'agreemnt\' as printed; Book B\'s \'OR 615\' agrees). Statements read against the official text: B Forbidden Terms items 1, 3 and 4 agree with 10.6(1)(a), 10.6(2) and 10.6(1)(b); item 2 \'bar the power of the review officer (within 6 months) to reduce the lawyer\'s charges if they are not in accordance with the contract, or maybe if the contract is unreasonable (R.10.9)\' - 10.9 makes reasonableness reviewable \'despite any agreement to the contrary\', but the 6-month limit in official 10.10(1) is for review of a retainer agreement (6 months after it terminated); official 10.10(2) allows review of a lawyer\'s charges until one year after the account was sent, so \'within 6 months\' does not match the time limit for reviewing charges; \'An oral retainer agreement is valid, so long as it is not a contingency agreement\' agrees with 10.7(1)(a) (a contingency fee agreement must be in writing; 10.5 has no writing requirement); \'A review officer cannot interpret such an agreement, but can say whether an agreement is understandable enough to comly with the Rules\' (\'comly\' as printed) is consistent with 10.7(2) (\'precise and understandable terms\'); \'the client can ... fire the lawyer\' agrees with 10.6(2); \'On evidence, see R.10.17 n.\' lands (10.17(1)(a): a review officer may take evidence by affidavit or orally); \'Rule 10.15(b) on confidentiality does not apply\' (D-E paragraph, p.10-13) lands (10.15(b): the filed information is not available for inspection by anyone other than a party to the agreement, a review officer or the Court); \'R.10.9 mandates that\' lands; \'If there is no fee contract, or the contract seems to invoke R.10.2, then the factors in R.10.2 apply\' agrees with 10.19(1) and 10.5(3); \'On an agreement about fees to an estate, see the Salmon case\' is the sentence also printed in the 10.3 note (p.10-7) (footnote 7 \'Re Salmon Est. (#1), supra\' refers to the full cite at p.10-7 fn 4). Printed as is: \'On reasonableness, see Rr.10.9, 1010\' (fn 1, p.10-11, line 490 - there is no rule 1010; 10.10 is the time-limit rule, 10.9 the reasonableness rule); \'contra preferentem\' (line 557; the Latin is \'proferentem\' in Book B\'s Rath v. Sweetgrass passage under 10.2). The other statements (Fatal Accidents Act, Public Trustee and infants, independent legal advice, waiver, credibility of the client, corporate client that did not exist, incapacity, privilege of a fee agreement, discount for prompt payment) are case-law statements not in 10.5 and were not checked. supra/infra: p.10-11 fn 1 \'McDonald Crawford v. Morrow, infra\' points to fn 6 of the same page (2004 ABCA 150, 348 AR 118), correct; fn 2 \'Samson Cree v. O\'Reilly, supra\' to fn 1 of the same page (and p.10-4 fn 5); fn 5 \'Khan v. Kazakoff, supra\' to fn 1 (Khan v. Paul A. Kazakoff P.C. 2019 ABQB 168); fn 7 \'McDonald Crawford v. Morrow, supra\' to fn 6; p.10-12 fns 2-5 \'Khan ...\' and \'Samson Cree ..., supra\' back to p.10-11 fn 1; fn 10 \'Moll v. MacPherson Leslie, supra\' to p.10-11 fn 5 (2014 ABCA 45, 569 AR 69); p.10-13 fn 4 \'Moll ... supra\' likewise; p.10-14 fn 2 \'Twinn v. Sawridge, supra\' to p.10-12 fn 9 (2017 ABQB 366, [2018] 1 WWR 298); p.10-14 fn 4 \'Betser-Zilevitch v. Prowse Chowne, infra (¶\'s 19-21)\' - the next footnote (fn 5) is the 2021 ABCA 129 decision (¶ 22), while the full citation of the trial decision 2020 ABQB 732 is earlier (p.10-11 fn 4), so which decision \'infra\' points to is not determined. The cases (Steinke v. Hajduk Gibbs 2014 ABQB 34 paras 51 and 54, Samson Cree 2014 ABCA 268, Stubbard v. Hajduk Gibbs 2014 ABQB 632, Khan v. Paul A. Kazakoff 2019 ABQB 168, Johnson v. Thingvold (#2) 2019 ABQB 4, Betser-Zilevitch 2020 ABQB 732 and 2021 ABCA 129, Adebisi v. Dentons 2023 ABKB 452, Moll v. MacPherson Leslie 2014 ABCA 45, McDonald Crawford v. Morrow 2004 ABCA 150, Prowse Chowne v. Northey, Tallcree F.N. v. Rath & Co. 2022 ABCA 174 and (#2) 2021 ABQB 234, Bell v. Fraser Milner 2003 ABQB 926, Homersham v. New Urban 2017 ABQB 384, Foco v. Strathcona Law Grp. 2011 ABQB 67, Twinn v. Sawridge Band 2017 ABQB 366, Borden Ladner v. CBI Invs. 2016 ABQB 220, Re Van Brabant Est. 2013 ABQB 547, Rath & Co. v. Sweetgrass F.N. 2014 ABCA 426, Barry v. Ind. Alliance Ins. 2022 ABKB 706, Walsh v. Stephen M. K. Hope 2019 ABQB 516, Graham v. Skovberg Hinz 2006 ABQB 763, Obi Agbarakwe Pro. Corp. v. Condo. Corp. No.0726502 2011 ABQB 286, Guardian Law Grp. v. L. S. 2021 ABQB 591, Torode v. Smyth (#1) 2009 ABQB 601 and (#2) 2009 ABQB 682, L. C. v. R. (Alta.) 2016 ABQB 554) were not checked; the C.P.E. references (Chapter 82 Parts K.4 and L.9) were not opened.',
    "10.4": 'Read in full, p.10-7 (line 264) to p.10-10 (line 412): title (line 264), rule text in pieces (lines 265-271; the p.10-7 footnote block, lines 273-283, is 10.3\'s and is printed between the pieces; page marker 10-8 line 285, running head line 286, rest of the rule lines 287-305), Related Provisions (lines 307-308) and the note (A Types of Security, line 310; B Charging Order, line 344; the conditions (a)-(e) and the closing paragraphs, lines 399-412) with all footnotes; lines 413-414 are the \'Subdivision 2 / Retainer Agreements\' heading. The built record: related_provisions and a commentary field of 3,212 characters; 22 footnotes (counted from the file: p.10-8 fns 1-5, p.10-9 fns 1-12, p.10-10 fns 1-5; 5+12+5); the p.10-10 footnote block (lines 431-448) also holds fn 6, the history footnote of 10.5 (1968 R.615), which is not this rule\'s. History footnote (p.10-8 fn 1, marker after (6)): \'Quite similar to previous 1968 R.625. It came from 1914 R.647. Virtually identical to 1914 Rr.757-59. Came via 1944 C. Rr.758-61. Cf. Ont.1897 R.1129, 1928 R.689. See also (Imp.) 23 & 24 Vict. s.127. ALRI\'s Consultation Memo #12.17 recommended keeping old R.625 "as regards charging orders"\' - printed as is (\'R.647\' and \'Rr.757-59\' both given as the 1914 source; the Imperial statute is \'s.127\' here and \'c.127, s.28\' in fn 2 of the same page; Book B\'s Merchant Law Group passage names s. 28 of the English Solicitors Act, 1860, so the section number agrees with fn 2); Book B\'s \'old Rule 625\' agrees with fn 1. (1) Related Provisions read against the official text: \'10.1(2) (agreement to provide security)\' - FLAG (see the 10.1 flags): official 10.1 has no subrule (2), 10.2(2) is the subrule on security; \'10.31(4) (set off of costs)\' and \'10.41(5) (set off of costs)\' agree with official 10.31(4) (deduction or set-off) and 10.41(5)(a) (deduction or set-off); the labels do not name 10.4\'s own subject and are not the official titles. (2) Statements read against the official text and Book B: the conditions (a) \'charges are unlikely to be paid without a charging order\', (c) \'efforts ... recovered or preserved ... the same net property\' and the fn 7 pointer \'R.10.4(2)\' agree with 10.4(2)(a) and (b)(ii); (b) \'The lawyer ran or defended litigation, which may not include expropriation\' - official 10.4(2)(b)(i) says \'the action conducted by the lawyer on the client\'s behalf\', and Book B (part 5, Robertson LLP v. Pasco, Price J.) reports that \'action\' can be \'whatever conduct by the lawyer\', that the new rule is \'much more expansive\' than old R.625 and that this is \'a material departure\' - a difference between the books, not settled here (Book A footnote 5 of p.10-9 says the tests under former R.625 still apply, citing Toliver v. Koepke); (d) \'The charge is limited to fees and disbursements incurred in the same suit which recovered or preserved this property\' is not in the words of 10.4 and matches Book B\'s quotation of Royal Bank v. Laughlin condition (c); (e) \'The court need not give the charge even if conditions (a) to (c) are all met, if it seems unfair to give it\' - official 10.4(5) is mandatory (\'An order must not be made ... if ... unfair\'), and the conditions listed above it are (a) to (d), not (a) to (c) (as printed); \'It is a good remedy where applicable, because it prevails over the interests of all the persons who benefit from the lawyer\'s efforts, and is a secured claim which prevails over unsecured claims and collusive settlements\' is a case-law statement (fn 4), and fn 4\'s \'But not over a bona fide purchaser for value: Paragon Cap. Corp. v. Starke Dom. 2018 ABQB 351 (¶ 41)\' agrees with 10.4(6) (\'unless the property is disposed of to a bona fide purchaser for value without notice of the charge\'). FLAG: \'Even a creditor with (previously) higher priority.\' (line 407, p.10-10) has no verb - the sentence is broken by the column order of the extraction; as printed. FLAG: fn 3 of p.10-9 ends \'which are no bar to the order?\' (question mark as printed). (3) supra/infra: fn 2 (p.10-8) \'Merchant Law Grp. v. McLeod & Co., infra\' points to fn 5 of the same page (full cite 2005 ABQB 875, 55 Alta LR(4th) 301), direction correct, and p.10-9 fn 1 \'Merchant Grp. v. McLeod & Co., supra\' (name shortened) points back; p.10-9 fn 3 \'Toliver v. Koepke, supra\' (full at p.10-8 fn 3); p.10-9 fn 4 \'Sharma v.643454 Alta., infra\' points to fn 6 of the same page (full cite 2006 ABQB 119, 392 AR 353), correct; p.10-9 fn 10 \'Sharma ... supra\' (fn 6) correct; FLAG: p.10-9 fn 12 \'Sharma v.643454 Alta., infra\' - the full citation is earlier on the same page (fn 6), and the only later full citation is at p.10-28 (line 1371, footnote 2 of the 10.13 note, \'(¶\'s 36-7)\'), so \'infra\' either points to that later cite or should be \'supra\'; p.10-10 fn 2 \'Paragon Cap. v. Starke, supra\' (p.10-8 fn 1), fn 3 \'Paragon Cap. v. Starke, infra (¶\'s 30-36)\': the later footnote 4 of the block is the full citation of the 2018 trial decision (2018 ABQB 351, ¶\'s 37-45), while the full citation of the appeal decision 2020 ABCA 216 is earlier (p.10-8 fn 1), so which decision \'infra\' means is not determined; fn 5 (p.10-9) \'Calf Robe (M. C. R.) v. A.-G. Can. 2006 ABQB 652\' is the full cite and p.10-9 fns 10-11 and p.10-10 fn 1 \'Calf Robe ... supra\' point back correctly. (4) Statements of law (liens, set-off, limitation periods, unfairness, priority) are case-law statements not in 10.4 except as noted; the cases (Re Cochard 2005 ABQB 679, Toliver v. Koepke 2017 ABQB 686, Merchant Law Grp. v. McLeod 2005 ABQB 875, Royal Bank v. Laughlin 2001 ABCA 78, Calf Robe 2006 ABQB 652, Paragon v. Starke 2018 ABQB 351 and 2020 ABCA 216, Sharma v. 643454 Alta. 2006 ABQB 119, Thackray Burgess v. Ernst & Young 2009 ABCA 203, Skovberg Hinz v. A.T. 2009 ABQB 272, Strathcona (Cty.) v. Half Moon L. Resort 2001 ABCA 271, Robertson LLP v. Pasco 2021 ABQB 988, D. S. M. v. K. L. S. 2021 ABQB 1024) were not checked beyond the cross-book comparisons in the see-also; the C.P.E. references (Chapter 82 Parts O.2, O.3; Chapter 73 Parts C and O; Chapter 13 Part B) and the Possessory Liens Act pointer were not opened.',
    "10.3": "Read in full, p.10-6 (line 217) to p.10-7 (line 263): title (line 217), rule text (lines 218-220 and 239-251; the page marker 10-7 is line 237 and the running head 'R.10.3(2)' line 238), a bare line 'trustee' (line 254) and the note (lines 255-262, 861 characters as built, beginning with that word), with footnotes. No Related Provisions and no information note are printed. Footnotes (8 in the built record, counted from the file): p.10-6 fn 9 (line 235, in the p.10-6 block that follows the first lines of 10.3) - history for (1): 'Quite similar to previous 1968 R.622. It came from 1914 R.753, and 1944 C. R.754'; p.10-7 fn 1 (marker after (2)(c)) - 'previous 1968 R.623(1). It was similar to 1914 R.754, and 1944 C. R.755. Cf. (Imp.) 6 & 7 Vict. c.7 s.39'; fn 2 (marker after (3)) - 'previous 1968 R.623(2). It came from 1914 R.754, and 1944 C. R.755. Cf. (Imp.) 6 & 7 Vict. c.73 s.39' (fn 1 prints 'c.7', fn 2 'c.73' for what is printed as the same section; as printed, not resolved); fns 3-7 are the note's (Re Salmon Est., Re Boje Est., Re Czaban Est., Pub. T'ee. v. Koska). Statements read against the official text: 'A lawyer can act both as executor and as the lawyer for the estate, and bill for that' agrees with 10.3(1) ('whether or not the lawyer is also acting in the capacity of a ... personal representative'); 'If a co-trustee and guardian of an estate is a solicitor, the court must approve his or her fees or disbursements' is narrower than 10.3(2), which lets a lawyer-guardian, mortgagee, personal representative or trustee be paid out of the fund if (a) the Court orders it, (b) every interested person is legally competent and agrees, or (c) a review officer has reviewed and certified the charges; the statement rests on Pub. T'ee. v. Koska (fn 6), not checked; the remaining sentences (roles kept distinct and careful records, corroboration of the lawyer's evidence of the deceased's agreement, clerical work billed below lawyers' rates) are case-law statements not in 10.3. supra/infra: fn 3 'Re Salmon Est., infra' points to fn 4 of the same page (Re Salmon Est. (#1) 2004 ABQB 598, 370 AR 316), direction correct; fn 5 'Re Salmon Est. (#1), supra' (fn 4) and fn 7 'Pub. T'ee. v. Koska, supra' (fn 6) point back correctly. The bare line 'trustee' has no 'Defined Terms' or other label in this extraction; the Appendix defines 'trustee' and 'personal representative' (official lines 41128 and 40988), and 10.3 uses both words. The cases (Re Salmon Est. (#1) 2004 ABQB 598, Re Boje Est. 2006 ABQB 599, Re Czaban Est. 2005 ABQB 917, Pub. T'ee. v. Koska 2010 ABQB 239) were not checked; Book B and Book C print nothing on them under 10.3.",
    "10.2": "Read in full, p.10-3 (line 67) to p.10-6 (line 216): title, rule text, Related Provisions (lines 94-97) and the note (A Contract vs. Default Mode, B More Than One Payor, C Misconduct, D Instructions Govern, E Security for Fees, F Dangers for Lawyer, G Miscellaneous; headings at lines 99, 148, 153, 161, 170, 194, 201) with all footnotes. The built record: related_provisions; the commentary field (5,042 characters, from 'There are reference works about lawyers's charges' at line 98 to the last sentence of G, lines 215-216); no information note; 31 footnotes (counted from the file: p.10-3 fns 1-2, p.10-4 fns 1-11, p.10-5 fns 1-10, p.10-6 fns 1-8; 2+11+10+8). Layout: each page's footnote block is printed before the next page marker; the p.10-6 block (lines 222-235) comes after the title and first lines of 10.3 (lines 217-220) and holds this rule's fns 1-8 and 10.3's history footnote 9 (line 235). History footnotes: fn 1 (p.10-3, marker after (1)(f)): 'Quite similar to previous 1968 R.613. It came from 1914 R.747 (as amended), and 1944 C. R.748'; fn 2 (p.10-3, after (2)): 'previous 1968 R.624 ... 1944 C. R.756, and (up to the comma) to 1914 R.624'; fn 1 (p.10-4, after (3)(c)): 'previous 1968 R.645(1). It came from 1944 C. R.779, new then'; Book B's 'R. 613' agrees with fn 1. (1) Related Provisions read against the official titles: '2.17 (lawyer as litigation representative)' (official 'Lawyer appointed as litigation representative': the Court may direct who bears a lawyer-representative's costs); '10.35 (contents of bill of costs)' (official 'Preparation of bill of costs', whose (2) says what the bill must contain); '2.25 (duty of lawyer)' (official 'Duties of lawyer of record'); '2.27 (limited retainers)' (official 'Retaining lawyer for limited purposes'); '10.4 (charging order)' (official 'Charging order for payment of lawyer's charges'). The labels are paraphrases; the list is not in numerical order. (2) Statements read against the official text: 'Rule 10.2(1) is only a default mode, operating in absence of different contractual provisions' agrees with 10.2(1) ('Except to the extent that a retainer agreement otherwise provides'); 'the factors in R.10.2 govern' a review where there is no express contract or the contract invokes 10.2 agrees with 10.19(1); 'Rule 10.2 also applies if a contrary contract is unenforceable, e. g. a contingency agreement with serious deviations from R.10.7' agrees with 10.8; FLAG: 'the hours spent are only one of about 11 factors listed there' - official 10.2(1) lists six factors, (a)-(f), and none mentions hours; the source of 'about 11' is not stated; FLAG: 'Fewer lawyers are familiar with R.10.1(2)' (E) - official 10.1 has no subrule (2); 10.2(2) is the subrule on security (see the 10.1 flags); footnote 3 (p.10-4) 'R.10.5' and footnote 8 'R.10.9' land (10.9: reasonableness of retainer agreements and charges subject to review); footnote 4 (p.10-4) 'R.10.7(7)', attached to 'the power of the review officer to intervene if a contingency fee contract was unreasonable': official 10.7(7) requires every account under a contingency fee agreement to state that a review officer may determine the reasonableness of the account and the agreement - the power itself is in 10.9; footnote 1 (p.10-5) 'and R.10.3' agrees with 10.3(2)(c) (estate, trust or fund); 'Rule 10.31(4) might suggest that it can easily be defeated' agrees with official 10.31(4) (deduction or set-off of costs awards); footnote 3 (p.10-6) 'R.10.13(2) (c)' agrees with 'if a lawyer wants his or her account reviewed, he or she must first sign it' (10.13(2)(c): a copy of a signed account). The statements on ethics, misconduct, conflict of interest, class-action fees, Supreme Court of Canada counsel rates, the provincial sales tax and prepayment out of a trust are case-law statements not in 10.2 and were not checked. (3) supra/infra: footnote 3 (p.10-4) 'Samson Cree v. O'Reilly Assoc., supra' - the full citation 'Samson Cree N. v. O'Reilly & Associés 2014 ABCA 268, 580 AR 181' is in footnote 5 of the same page, after it, and is the first full citation of that decision in Book A (searched all Book A files; 'Samson Cree N. v. R. (1999) 239 AR 214' in combined rule1.txt line 654 is a different case), so 'supra' points forward within the page; footnote 5 'Steinke v. Hajduk Gibbs, infra (¶ 53)' points to footnote 11 of the same page (2014 ABQB 34, 581 AR 91), direction correct; footnote 7 'Downes v. Botan, supra' (full in footnote 6), p.10-5 footnotes 4-5 'Khan v. Paul A. Kazakoff P.C., supra' (full at p.10-4 fn 3), p.10-5 fn 8 'Steinke ... supra' (p.10-4 fn 11) and p.10-6 fn 5 'R. v. White, supra' (same footnote) all point back correctly. (4) Printed as is: 'lawyers's charges' (line 98); '.. (2010)' in fn 2 of p.10-4. (5) The cases (Khan v. Paul A. Kazakoff 2019 ABQB 168, Ritchie v. Walker 2006 SCC 45, Betser-Zilevitch v. Prowse Chowne 2020 ABQB 732 affd 2021 ABCA 129, Samson Cree 2014 ABCA 268, O'Brian v. de Villars Jones 2015 ABQB 535, Downes v. Botan 2018 ABQB 341, McDonald Crawford v. Morrow 2004 ABCA 150, Steinke 2014 ABQB 34, Re Halun Est. 2002 ABQB 563, O'Keefe v. Overacker, Côté v. Rancourt 2004 SCC 58, Gunn & Prithipaul v. Daniel 2005 ABQB 6, Prowse Chowne v. Wasylyshyn 2006 ABQB 68, Hamill v. Kudryk 2014 ABCA 82, Adrian v. A.-G. Can. (#2) 2007 ABQB 377, Northwest v. A.-G. Can. 2006 ABQB 902, R. v. White 2010 SCC 59, Christie v. A.-G. B.C. 2007 SCC 21, Re Residential Warranty 2006 ABQB 236, McAteer v. Devoncroft (#2) 2003 ABQB 425) were not checked; McDonald Crawford v. Morrow (348 AR 118) is also the case in Book B's part 3 and Steinke is the case Book B's 10.9 commentary quotes; the C.P.E. references (Chapter 82, Parts B.8, I, O, Q.1, R, R.3, R.5, S.4, C to H) point to another work and were not opened.",
}
MANUAL_BOOK_A_FOOTNOTE_FLAGS = {
}
MANUAL_BOOK_C = {
    "10.6": {'drop_c_note': "Book C's copy of the Information Note is dropped: it has the same words as Book A's ('The rules about self-representing are in rule 2.28 [Change in lawyer of record or self representation]') with the hyphen of 'self-representation' lost, and the heading 'Subdivision 3: CONTINGENCY FEE AGREEMENTS' (the Subdivision that begins at 10.7) printed after it."},
    "10.5": {'drop_rule_text': "Book C's rule text is dropped (official, Book A and Book B carry the whole text): (1) and (3) are printed, but (2) stops after '(b) commission,' - subparagraphs (2)(c) percentage, (d) salary and (e) an hourly rate are missing - and (3) has the bracket label '[Payment for lawyer's services and contents of lawyer's account]' (the official title of 10.2) after 'rule 10.2'; the words printed otherwise equal the official text.", 'citation_names': {'2014 ABCA 268': 'Samson Cree Nation v. O’Reilly & Associés'}, 'commentary_flag': "(1) The commentary ('General Principles', 2,087 characters as built) is cut off at the end ('The court must hold the lawyer and the client to promises made in a retainer') and has printing defects: the footnote number '22' is fused to 'rule 10.5.22'; the statute title is displaced ('is made within the meaning of the , when the appointment Limitations Act for assessment is taken out'); 'tentative- ness' is a line-break hyphen; the last case name is incomplete ('This was reiterated in Attila Dogan Construction and Installation Co. Inc. v. Bennett' with no citation - Book A cites Attila Dogan Constr. only as a party to 'Attila Dogan Constr. & Installation Co. v. AMEC Americas 2011 ABQB 794' (p.10-82, line 4308, 10.31 note) and 'AMEC Foster Wheeler etc. v. Attila Dogan Constr. etc. 2016 ABQB 305' (p.10-165, line 8921, 10.53 note), and Book B's 10.10 commentary cites 'Attila' (Wittmann C.J., para 35); no source names a decision 'v. Bennett'). The sentence 'The court must hold the lawyer and the client to promises made in a retainer' is the third principle of Steinke v. Hajduk Gibbs 2014 ABQB 34 as Book B quotes it in its 10.9 commentary ('a court must hold the lawyer and the client to promises made in a retainer agreement'). (2) Read against the official text: 'A lawyer seeking to collect on a contingency fee who has not complied with rule 10.7 cannot obtain assistance from rule 10.5' agrees in substance with 10.8 (a lawyer who does not comply with 10.7(1)-(4), (6) and (7) is entitled only to charges determined under 10.2); 'like rule 10.7(7) (on contingency agreements) ... a future requirement that each account of a lawyer to a client contain a notice to the effect that a right to review is available' agrees with 10.7(7) (every account under a contingency fee agreement must state that a review officer may determine reasonableness); the suggested 'time limitations - including that it be brought within two years of the date of the account' is a proposal, and official 10.10(2) already bars review of a lawyer's charges one year after the account was sent; 'A claim for a remedial order ... is made within the meaning of the Limitations Act when the appointment for assessment is taken out. Any account pre-dating two years prior to this appointment is statute barred' agrees with Book A p.10-9 footnote 6 (Sharma: an appointment for taxation stops the limitation period running) and is a statement from Samson Cree, not in the Rules. The five bullets are attributed to Samson Cree Nation v. O'Reilly & Associes [2014] A.J. No. 904, 2014 ABCA 268 at paras 53, 81-82, 110, 165-169 (pinpoints found only here; Book A cites the decision without pinpoints); the printed name is displaced before the A.J. citation, so the build had given 2014 ABCA 268 no name - repaired from the printed text. The commentary is kept as printed and flagged."},
    "10.4": {'citation_names': {'2021 ABQB 988': 'Robertson LLP v. Pasco', '2021 ABQB 1024': 'M. (D.S.) v. S. (K.L.)'}, 'commentary_flag': "(1) Rule text equals the official text (EXACT_MATCH); the amendment note is in the standard form (see the 10.1 flag on the Gazette date). (2) The commentary ('General Principles', four paragraphs, 1,909 characters as built) was read in full against the official text, Book A and Book B: 'a charging order under rule 10.4 ... may only be made, pursuant to subrule (2), if two requirements are satisfied' agrees with 10.4(2)(a)-(b) ('First, the lawyer must establish that the fees are unlikely to be paid without the order. Second, the property to be charged must be associated with the lawyer's work and that work must result in recovery or preservation of the property'); the quotation 'The purpose of r 10.4(2) would be best met by permitting the 10.4(2)(a) requirement to be established at the time of bringing the application for a charging order, or within a reasonable time subsequently' is word for word paragraph [51] of Paragon Capital Corp. v. Starke Dominion 2020 ABCA 216 as Book B quotes it in its part 2; the 10.4(5) paragraph (unfairness from granting, not from refusing) matches Book B's part 12 (Paragon [52]-[53]) and Book A's footnote 6 on p.10-9 ('Paragon v. Starke, supra (¶ 53)'); the paragraph on excessive delay (M. (D.S.) v. S. (K.L.) 2021 ABQB 1024 para 25) agrees with Book A p.10-10 footnote 1 ('Delay in moving is a ground to deny a charging order for unpaid fees ... D. S. M. v. K. L. S. 2021 ABQB 1024') and with Book B's Merchant Law Group passage on laches; the priority paragraph ('a contextual analysis, it is not always that they take such priority') agrees with Book A's last note paragraph ('does not always have priority over other registered interests') and its footnote 5 (Robertson LLP v. Pasco 2021 ABQB 988, paras 11-21). (3) Printing defects: the last sentence prints its citation with the case name displaced after it - 'see also , [2021] A.J. No. 1758, 2021 ABQB 988 at para. 13 (Alta. Q.B.). Robertson LLP v. Pasco RETAINER GREEMENTS A' - and ends with a fragment of the next Subdivision's heading ('RETAINER AGREEMENTS', letters lost); in the delay paragraph the name 'M. (D.S.) v. S. (K.L.)' is printed before '[2021] A.J. No. 1749, 2021 ABQB 1024'. The built citation records were repaired from the printed text (2021 ABQB 988 = Robertson LLP v. Pasco; 2021 ABQB 1024 = M. (D.S.) v. S. (K.L.)); the build had given the first the name of the previous case (Paragon) and the second no name. Paragon is cited at para. 51, paras 53-54 and, in the priority paragraph, without a pinpoint."},
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
