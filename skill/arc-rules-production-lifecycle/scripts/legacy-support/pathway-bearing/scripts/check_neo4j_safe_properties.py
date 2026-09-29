#!/usr/bin/env python3
"""Validate that canonical JSON uses Neo4j-safe executable properties.

Usage:
  check_neo4j_safe_properties.py <canonical.json>
"""
import json
import sys
from pathlib import Path

PRIMITIVE = (str, int, float, bool)


def is_safe_value(value):
    if value is None:
        return False
    if isinstance(value, PRIMITIVE):
        return True
    if isinstance(value, list):
        return all(isinstance(v, PRIMITIVE) and v is not None for v in value)
    return False


def iter_items(data):
    for section in ("nodes", "relationships"):
        for idx, item in enumerate(data.get(section, [])):
            yield section, idx, item


def main():
    if len(sys.argv) != 2:
        print("usage: check_neo4j_safe_properties.py <canonical.json>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = []
    for section, idx, item in iter_items(data):
        props = item.get("properties", {})
        if not isinstance(props, dict):
            errors.append(f"{section}[{idx}].properties is not an object")
            continue
        for key, value in props.items():
            if not is_safe_value(value):
                errors.append(f"{section}[{idx}].properties.{key} is not Neo4j-safe: {type(value).__name__}")
    if errors:
        print("FAIL: non-safe properties found")
        for err in errors:
            print(err)
        return 1
    print("PASS: executable properties are Neo4j-safe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
