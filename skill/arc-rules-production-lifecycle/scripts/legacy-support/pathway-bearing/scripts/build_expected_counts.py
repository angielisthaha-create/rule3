#!/usr/bin/env python3
"""Build expected_counts.json from canonical handoff JSON.

Usage:
  build_expected_counts.py <canonical.json> <output.json>
"""
import json
import sys
from collections import Counter
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        print("usage: build_expected_counts.py <canonical.json> <output.json>", file=sys.stderr)
        return 2
    canonical_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    data = json.loads(canonical_path.read_text(encoding="utf-8"))
    label_counts = Counter()
    rel_counts = Counter()
    for node in data.get("nodes", []):
        labels = node.get("labels", [])
        if isinstance(labels, str):
            labels = [labels]
        for label in labels:
            label_counts[label] += 1
    for rel in data.get("relationships", []):
        rel_counts[rel.get("type", "UNKNOWN")] += 1
    out = {
        "migration_id": data.get("migration_id", ""),
        "rule_slug": data.get("rule_slug", ""),
        "node_counts_by_label": dict(sorted(label_counts.items())),
        "relationship_counts_by_type": dict(sorted(rel_counts.items())),
        "phase_b_parked_count": len(data.get("phase_b_parked", [])),
        "manual_validation_count": len(data.get("manual_validation", [])),
        "skipped_count": len(data.get("skipped", [])),
    }
    output_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
