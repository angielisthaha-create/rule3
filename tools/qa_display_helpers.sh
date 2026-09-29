#!/usr/bin/env bash
# DISPLAY helpers used in the manual passes. They only find and show text; every decision is made by
# reading the output and the sources (see README.txt section 5). Usage: source tools/qa_display_helpers.sh
# Run from the repository root.

# Validate every subrule's gate record. Usage: gate_all [first] [last]   (default 1 32)
gate_all() {
  local g; g=$(mktemp)
  for i in $(seq "${1:-1}" "${2:-32}"); do
    python3 -c "import json;json.dump(json.load(open('rule2_subrules/2.$i.json'))['three_book_gate'],open('$g','w'))"
    printf '2.%s ' "$i"; python3 tools/validate_three_book_gate.py "$g" | grep -o '"valid": [a-z]*'
  done
  rm -f "$g"
}

# Page of each line matching a regex in a Book A file that uses "N-NN" page markers (all Parts except 3).
# Usage: pg combined_rule9.txt '2\.11 \(litigation'
pg() {
  awk -v p="$2" '/^[0-9]+-[0-9]+$/{m=$0} $0 ~ p {print FILENAME": line "NR" page "m": "substr($0,1,90)}' "$1"
}

# Same for the Part 3 file, which opens each page with "**PAGE N". Usage: pg3 'Rr\.2\.11 to 2\.16'
pg3() {
  awk -v p="$1" '/^\*\*PAGE [0-9]+$/{m=$2} $0 ~ p {print "line "NR" p.3-"m": "substr($0,1,90)}' "combined rule3.txt"
}

# Rule whose text/notes a line falls in (last rule heading before it). Usage: rule_at combined_rule9.txt 3274 9
rule_at() {
  awk -v n="$2" -v P="$3" 'NR<=n && $0 ~ "^"P"\\.[0-9]+[ (]" {l=NR": "$0} NR==n{print l}' "$1"
}

# Every reference to a Part 2 rule in the other Parts of Book A (R.2.x, Rr.2.x, Rule 2.x, "2.x (label)").
# Line-wrapped forms are NOT caught; also read around each hit. Usage: reverse_refs [regex-for-rule-number]
reverse_refs() {
  local n="${1:-(1[1-9]|2[0-9]|3[0-2]|[1-9]|10)}"
  for f in combined*.txt; do
    [ "$f" = combined_rule2.txt ] && continue
    grep -E -o ".{0,60}(R\. ?2\.$n\b|Rr\. ?2\.$n\b|[Rr]ules? 2\.$n\b|(^|[ ;])2\.$n(\([0-9a-z]+\))* ?\([a-z][^)]*\)).{0,40}" "$f" | sed "s/^/[$f] /"
  done
}

# Pages of other Parts that carry any Part 2 reference, per file (to spot pages no note has cited yet).
ref_pages() {
  for f in combined*.txt; do
    [ "$f" = combined_rule2.txt ] && continue
    [ "$f" = "combined rule3.txt" ] && continue
    awk '/^[0-9]+-[0-9]+$/{m=$0} /R\. ?2\.[0-9]|Rr\. ?2\.|[Rr]ules? 2\.[0-9]|(^|[ ;])2\.[0-9]+(\([0-9a-z]+\))* ?\(/{printf "%s ", m}' "$f" \
      | tr ' ' '\n' | sort -u -V | paste -sd' ' | sed "s/^/$f: /"
  done
}

# Official rule text by number. Usage: official 2.20
official() {
  local n; n=$(grep -n "^$1[ (]" Alberta_Rules_of_Court.txt | tail -1 | cut -d: -f1)
  sed -n "$((n-3)),$((n+25))p" Alberta_Rules_of_Court.txt
}

# ---- added after the 8th pass ------------------------------------------------------------------------------

# Footnotes of Book A Part 2 by page, with footnote number and line. Usage: fn_pages 30 47  (pages 2-30..2-47)
# A line numbered like "fn2005" is a wrapped continuation line, not a footnote. "[Footnote N from prior page]"
# means footnote N's reference mark is on the previous page.
fn_pages() {
  awk -v a="$1" -v b="$2" '/^[0-9]+-[0-9]+$/{m=$0; inf=0} /^Footnote$/{inf=1; next}
    inf && /^[0-9]+ /{split(m,x,"-"); if (x[2]>=a && x[2]<=b) print m" fn"substr($0,1,index($0," ")-1)" L"NR": "substr($0,index($0," ")+1,75)}' combined_rule2.txt
}

# References to Part 2 rules split over two lines in the other Parts ("See R." / "2.30"). Usage: wrapped_refs
wrapped_refs() {
  for f in combined*.txt; do
    [ "$f" = combined_rule2.txt ] && continue
    awk -v F="$f" '/^[0-9]+-[0-9]+$/{m=$0} /^\*\*PAGE [0-9]+$/{m="3-"$2}
      {if (prev ~ /(R\.|Rr\.|[Rr]ules?|see|See|and|under|;|,|to) *$/ && $0 ~ /^ *\*?2\.([1-9]|[12][0-9]|3[0-2])([^0-9]|$)/)
         print F" "m" L"NR": "substr(prev,length(prev)-45)" | "substr($0,1,70); prev=$0}' "$f"
  done
}

# Book A Part 2 "Related Provisions" lists with the rule each belongs to. Usage: related_labels
related_labels() {
  awk '/^2\.[0-9]+(\([0-9]+\))? [A-Z]/{r=substr($0,1,index($0," ")-1)}
       /^Related Provisions/{f=3; next} f>0 && NF{print "["r"] L"NR": "$0; f--; next} f>0{f--}' combined_rule2.txt
}

# Official title of rules. Usage: official_title 3.36 12.6 14.82
official_title() {
  for r in "$@"; do
    local n; n=$(grep -n "^$r *$" Alberta_Rules_of_Court.txt | head -1 | cut -d: -f1)
    [ -n "$n" ] && echo "$r: $(sed -n "$((n+1))p" Alberta_Rules_of_Court.txt)" || echo "$r: (no title line found)"
  done
}

# How often a string occurs in each Book A file - use before calling something a defect (e.g. '(#_)' is a
# book-wide convention, 448 uses). Usage: book_count '(#_'
book_count() { grep -c -F -- "$1" combined*.txt | grep -v ":0$"; }

# Pretty-printed reading copies of Books B and C (identical content; only indentation differs).
# Usage: pretty_sources [outdir]   (default scratch/reading_copies)
pretty_sources() {
  local out="${1:-scratch/reading_copies}"; mkdir -p "$out"
  for f in rule2_part01_document.json rule2_part02_document.json "81-100_2_1 to 2_27.json" "101-120_2_28 to 3_18.json"; do
    python3 -c "import json,sys;json.dump(json.load(open(sys.argv[1])),open(sys.argv[2],'w'),indent=4,ensure_ascii=False)" "$f" "$out/${f%.json}.pretty.json"
  done
}

# ---- Part 3 -------------------------------------------------------------------------------------------------
# Validate every Part 3 subrule's gate record. Usage: gate_all3 [first] [last]   (default 1 77)
gate_all3() {
  local g; g=$(mktemp)
  for i in $(seq "${1:-1}" "${2:-77}"); do
    python3 -c "import json;json.dump(json.load(open('rule3_subrules/3.$i.json'))['three_book_gate'],open('$g','w'))"
    printf '3.%s ' "$i"; python3 tools/validate_three_book_gate.py "$g" | grep -o '"valid": [a-z]*'
  done
  rm -f "$g"
}
# Python helpers take the Part from the environment: ARC_PART=3 python3 tools/show_rule_notes.py 2
