#!/usr/bin/env python3
"""Check recommended relationships against the ARC pathway allowlist and reject executable write Cypher."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ALLOWLIST = {
    "HAS_INTERPRETIVE_ISSUE", "HAS_PATHWAY", "SUPPORTS_PATHWAY_HOLDING", "INTERPRETS_SUBRULE",
    "LIMITED_BY", "DISTINGUISHED_BY", "CONFIRMED_BY", "CONFLICTS_WITH", "ANALOGOUS_TO",
    "REQUIRES_ADMISSIBILITY_GATE", "REQUIRES_PRIVILEGE_SCREEN", "REQUIRES_PRIVACY_SCREEN",
    "NOT_GOVERNING_UNLESS_CONFIRMED_BY",
}
WRITE_KEYWORDS = re.compile(r"\b(CREATE|MERGE|SET|DELETE|DETACH|REMOVE|DROP|LOAD\s+CSV|CREATE\s+INDEX|CREATE\s+CONSTRAINT)\b", re.I)
RELTYPE = re.compile(r"\[:([A-Z0-9_]+)\]")


def reltypes_from_item(item: object) -> list[str]:
    if isinstance(item, dict):
        vals = []
        for key in ("relationship_type", "rel_type", "type"):
            if item.get(key):
                vals.append(str(item[key]))
        vals.extend(RELTYPE.findall(json.dumps(item)))
        return vals
    return RELTYPE.findall(str(item))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    errors: list[str] = []
    for i, rel in enumerate(packet.get("recommended_relationships", [])):
        text = rel if isinstance(rel, str) else json.dumps(rel)
        if WRITE_KEYWORDS.search(text):
            errors.append(f"relationship[{i}] appears to contain write cypher: {text[:160]}")
        found = reltypes_from_item(rel)
        if not found:
            errors.append(f"relationship[{i}] lacks a recognizable relationship type")
        for match in found:
            if match not in ALLOWLIST:
                errors.append(f"relationship[{i}] uses non-allowlisted relationship type {match}")
    report = {"valid": not errors, "errors": errors, "allowlist": sorted(ALLOWLIST)}
    print(json.dumps(report, indent=2))
    return 0 if not errors else 1

if __name__ == "__main__":
    sys.exit(main())
