# Setup, Scripts, and Operational Checks

## Script checks

Before relying on local scripts, run:

```bash
python -m py_compile scripts/high_volume_neo4j_audit_runner.py
python -m py_compile scripts/summarize_high_volume_audit.py
python -m py_compile scripts/self_test.py
```

If those scripts are not present in the working repository, record them as unavailable and use MCP read-only queries instead.

## Dry run for high-volume runner

```bash
python scripts/high_volume_neo4j_audit_runner.py \
  --target-calls 3 \
  --dry-run \
  --out-dir out/manual_dry_run
```

## Timeout rejection test

This must fail because timeout values must be less than 80 seconds:

```bash
python scripts/high_volume_neo4j_audit_runner.py \
  --target-calls 1 \
  --query-timeout-seconds 80 \
  --dry-run \
  --out-dir out/timeout_reject
```

## Fixture summary tests

```bash
python scripts/summarize_high_volume_audit.py \
  --input references/sample_timeout_calls.jsonl \
  --summary-json references/sample_timeout_summary.json \
  --out-md out/sample_timeout_recommendations.md
```

```bash
python scripts/summarize_high_volume_audit.py \
  --input references/sample_mixed_failure_calls.jsonl \
  --summary-json references/sample_mixed_failure_summary.json \
  --out-md out/sample_mixed_failure_recommendations.md
```

## Self-test

```bash
python scripts/self_test.py
```

## Live Neo4j smoke test

```bash
export NEO4J_URI="bolt://..."
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="..."
python scripts/high_volume_neo4j_audit_runner.py \
  --target-calls 3 \
  --query-timeout-seconds 75 \
  --out-dir out/live_smoke
```

Confirm `summary.json` reports timeout enforcement and `call_count_satisfied` only if all requested calls succeeded.

## Local skill scripts in this package

This skill also includes:

```bash
python scripts/build_validation_plan.py --out-dir out/arc_pathway_validity_run
python scripts/unified_message_burst.py --dry-run --count 100 --interval-seconds 240 --message "ARC pathway validity unified setup test"
```

`build_validation_plan.py` creates a run folder with the manifest, query plan, artifact placeholders, and checklist files. It does not connect to Neo4j or perform writes.

`unified_message_burst.py` emits a uniform message cadence. Dry-run mode previews/logs all messages immediately. Real-time mode sleeps between messages.
