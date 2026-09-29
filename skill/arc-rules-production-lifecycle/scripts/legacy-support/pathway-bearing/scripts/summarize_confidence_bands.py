#!/usr/bin/env python3
"""Summarize pathway-bearing counsel scoring confidence bands from a CSV."""
import argparse, csv, json
from collections import Counter

FIELDS = [
    "disposition_confidence_band",
    "legal_interpretation_confidence_band",
    "case_authority_confidence_band",
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    with open(args.csv_path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    result = {"row_count": len(rows), "bands": {}}
    for field in FIELDS:
        if rows and field in rows[0]:
            result["bands"][field] = dict(Counter(r.get(field, "") or "BLANK" for r in rows))
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    else:
        print(text)

if __name__ == "__main__":
    main()
