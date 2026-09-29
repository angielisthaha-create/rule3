#!/usr/bin/env python3
"""Generate or emit unified ARC pathway validity trigger messages.

Dry-run mode creates all messages immediately. Real-time mode sleeps between
messages and is intended only for local runner setups; it does not send SMS,
email, Slack, or ChatGPT messages by itself.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def build_record(run_id: str, seq: int, count: int, interval_seconds: int, scheduled: datetime, message: str, dry_run: bool, fixed_seq: bool) -> Dict[str, object]:
    if fixed_seq:
        trigger = f"ARC_PATHWAY_VALIDITY_TEST seq=001/{count:03d} run_id={run_id}"
    else:
        trigger = f"ARC_PATHWAY_VALIDITY_TEST seq={seq:03d}/{count:03d} run_id={run_id} message=\"{message}\""
    return {
        "run_id": run_id,
        "sequence": seq,
        "count": count,
        "interval_seconds": interval_seconds,
        "scheduled_utc": iso(scheduled),
        "emitted_utc": iso(utc_now()),
        "dry_run": dry_run,
        "message": message,
        "fixed_seq": fixed_seq,
        "trigger_text": trigger,
    }


def write_outputs(records: List[Dict[str, object]], out_jsonl: Optional[str], out_text: Optional[str]) -> None:
    if out_jsonl:
        path = Path(out_jsonl)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, sort_keys=True) + "\n")
    if out_text:
        path = Path(out_text)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(str(record["trigger_text"]) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate or emit unified manual trigger messages.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Generate all records immediately without sleeping")
    mode.add_argument("--real-time", action="store_true", help="Sleep between emissions")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--interval-seconds", type=int, default=240)
    parser.add_argument("--message", default="ARC pathway validity unified setup test")
    parser.add_argument("--run-id", default="ARC_PATHWAY_VALIDITY_PARTS_2_11_13_14_SKIP_12")
    parser.add_argument("--fixed-seq", action="store_true", help="Emit the same heartbeat trigger each time with seq=001/count")
    parser.add_argument("--out-jsonl", default=None)
    parser.add_argument("--out-text", default=None)
    args = parser.parse_args()

    if args.count < 1:
        raise SystemExit("--count must be >= 1")
    if args.interval_seconds < 1:
        raise SystemExit("--interval-seconds must be >= 1")

    start = utc_now()
    records: List[Dict[str, object]] = []

    for seq in range(1, args.count + 1):
        scheduled = start + timedelta(seconds=args.interval_seconds * (seq - 1))
        if args.real_time and seq > 1:
            time.sleep(args.interval_seconds)
        record = build_record(args.run_id, seq, args.count, args.interval_seconds, scheduled, args.message, args.dry_run, args.fixed_seq)
        records.append(record)
        print(record["trigger_text"], flush=True)

    write_outputs(records, args.out_jsonl, args.out_text)
    summary = {
        "ok": True,
        "run_id": args.run_id,
        "count": args.count,
        "interval_seconds": args.interval_seconds,
        "dry_run": args.dry_run,
        "fixed_seq": args.fixed_seq,
        "out_jsonl": args.out_jsonl,
        "out_text": args.out_text,
    }
    print(json.dumps(summary, indent=2), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
