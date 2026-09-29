#!/usr/bin/env python3
"""Compare two immutable Appendix A metadata/conformance audit runs.

The script compares metadata by metric_id_strict + strict_count and conformance
by exact metric IDs. It intentionally ignores metadata row status because that
field may refer to a frozen baseline rather than the immediately previous run.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_file(path: Path, candidates: list[str]) -> Path:
    if path.is_file():
        return path
    for name in candidates:
        candidate = path / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"No supported artifact in {path}: {candidates}")


def metadata_map(path: Path) -> dict[str, dict[str, Any]]:
    file_path = resolve_file(path, ["COVERAGE_ROWS.json", "result.json"])
    payload = load_json(file_path)
    rows = payload.get("rows", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError(f"Metadata rows are not a list in {file_path}")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        metric_id = row.get("metric_id_strict")
        if not metric_id:
            continue
        result[metric_id] = {
            "count": row.get("strict_count"),
            "total": row.get("total"),
            "percent": row.get("strict_percent"),
            "label": row.get("label"),
            "measure": row.get("measure"),
        }
    return result


def conformance_map(path: Path) -> dict[str, dict[str, Any]]:
    file_path = resolve_file(path, ["CONFORMANCE_CHECKS.json", "result.json"])
    payload = load_json(file_path)
    checks = payload.get("checks", payload) if isinstance(payload, dict) else payload
    if not isinstance(checks, dict):
        raise ValueError(f"Conformance checks are not an object in {file_path}")
    result: dict[str, dict[str, Any]] = {}
    for check_name, check in checks.items():
        if not isinstance(check, dict):
            continue
        values = check.get("values", {})
        metric_ids = check.get("metric_ids", {})
        population = check.get("population")
        for measure, value in values.items():
            metric_id = metric_ids.get(measure, f"{check_name}.{measure}")
            result[metric_id] = {
                "count": value,
                "population": population,
                "check": check_name,
                "measure": measure,
            }
    return result


def numeric_delta(previous: Any, current: Any) -> Any:
    if isinstance(previous, (int, float)) and isinstance(current, (int, float)):
        return current - previous
    return None


def compare_maps(previous: dict[str, dict[str, Any]], current: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for metric_id in sorted(set(previous) | set(current)):
        old = previous.get(metric_id, {})
        new = current.get(metric_id, {})
        old_count = old.get("count")
        new_count = new.get("count")
        delta = numeric_delta(old_count, new_count)
        if metric_id not in previous:
            classification = "NEW_METRIC"
        elif metric_id not in current:
            classification = "REMOVED_METRIC"
        elif old_count == 0 and isinstance(new_count, (int, float)) and new_count > 0:
            classification = "ZERO_TO_POSITIVE"
        elif isinstance(old_count, (int, float)) and old_count > 0 and new_count == 0:
            classification = "POSITIVE_TO_ZERO"
        elif delta is not None and delta > 0:
            classification = "INCREASED"
        elif delta is not None and delta < 0:
            classification = "DECREASED"
        else:
            classification = "UNCHANGED"
        rows.append(
            {
                "metric_id": metric_id,
                "previous": old_count,
                "current": new_count,
                "delta": delta,
                "classification": classification,
                "previous_context": old,
                "current_context": new,
            }
        )
    return rows


def markdown_report(metadata_rows: list[dict[str, Any]], conformance_rows: list[dict[str, Any]]) -> str:
    changed_meta = [row for row in metadata_rows if row["classification"] != "UNCHANGED"]
    changed_conf = [row for row in conformance_rows if row["classification"] != "UNCHANGED"]
    zero_moves = [row for row in conformance_rows if row["classification"] == "ZERO_TO_POSITIVE"]
    lines = [
        "# Appendix A Run-over-Run Delta",
        "",
        "This report compares exact metric identifiers. Metadata uses `strict_count`; row `status` is ignored.",
        "",
        "## Summary",
        "",
        f"- Metadata metrics changed: {len(changed_meta)}",
        f"- Conformance metrics changed: {len(changed_conf)}",
        f"- Conformance zero-to-positive movements: {len(zero_moves)}",
        "",
    ]
    for title, rows in (("Metadata changes", changed_meta), ("Conformance changes", changed_conf)):
        lines.extend([f"## {title}", "", "| Metric | Previous | Current | Delta | Classification |", "|---|---:|---:|---:|---|"])
        if not rows:
            lines.append("| _None_ |  |  |  |  |")
        for row in rows:
            lines.append(
                f"| `{row['metric_id']}` | {row['previous']} | {row['current']} | {row['delta']} | {row['classification']} |"
            )
        lines.append("")
    lines.extend(
        [
            "## Interpretation requirement",
            "",
            "Classify each change as migration-attributable, substrate-only, denominator regression, unrelated drift, definition mismatch, or unresolved. Raw growth is not proof of improvement.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous-metadata", required=True, type=Path)
    parser.add_argument("--current-metadata", required=True, type=Path)
    parser.add_argument("--previous-conformance", required=True, type=Path)
    parser.add_argument("--current-conformance", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    metadata_rows = compare_maps(metadata_map(args.previous_metadata), metadata_map(args.current_metadata))
    conformance_rows = compare_maps(conformance_map(args.previous_conformance), conformance_map(args.current_conformance))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "appendix-run-delta-v1",
        "previous_metadata": str(args.previous_metadata),
        "current_metadata": str(args.current_metadata),
        "previous_conformance": str(args.previous_conformance),
        "current_conformance": str(args.current_conformance),
        "metadata": metadata_rows,
        "conformance": conformance_rows,
    }
    (args.out_dir / "appendix_delta.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    (args.out_dir / "appendix_delta.md").write_text(markdown_report(metadata_rows, conformance_rows), encoding="utf-8")
    print(args.out_dir / "appendix_delta.json")
    print(args.out_dir / "appendix_delta.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
