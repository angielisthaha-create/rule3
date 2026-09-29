# ARC Rules 1-15 workflow knowledge

## Table of contents

1. Reusable lessons from Rule 7
2. Source construction
3. Candidate review
4. Promotion and verification
5. Appendix A discipline
6. Parallel-agent handover

## 1. Reusable lessons from Rule 7

### Local Appendix A is an operational control

Writing the Appendix to the local drive after every material batch provides:

- immutable before/after evidence;
- a reliable run-over-run delta;
- detection of concurrent or unauthorized graph changes;
- reproducible Markdown, DOCX, and PDF outputs;
- a durable handover for the next LLM.

Treat the Appendix directories as measurement inputs, not disposable reports.

### Candidate counts are not readiness

Rule 7 demonstrated that a candidate family can be extracted correctly while the global readiness numerator remains unchanged. This is expected when production contracts require additional evidence or topology.

Always report separately:

- source records;
- candidates;
- promoted production objects;
- complete production objects;
- metric numerator movement;
- denominator movement.

### Complete wiring can produce legitimate movement

Deontic semantics are a good example. A deontic object linked to its source proposition can legitimately increase both the total and the wired numerator. This is better than creating unlinked operators.

### Partial production objects can worsen ratios

Promoting an issue template into `LegalIssue`, a remedy condition into `RemedyGateway`, or secondary commentary into a version label can expand a denominator without satisfying the completion predicate. Use a candidate or template label until the full production contract is supported.

### Freshness and query correctness are different

A retrieval query may pass all fixed hashes and result checks while the overall release gate fails because persisted validation evidence is older than the permitted freshness window. Report:

- query execution result;
- baseline match;
- result hash match;
- evidence freshness;
- aggregate release readiness.

## 2. Source construction

Use deterministic IDs based on stable source identity, rule scope, segment type, and normalized text hash. Do not include machine-local paths in canonical IDs.

Recommended hierarchy:

```text
SourceDocument
  -> SourceFile
      -> TextChunk
          -> TextSpan
```

Preserve both:

- aggregate anchors such as Rule 7.3;
- exact provision spans such as Rule 7.3(2).

Do not substitute an aggregate rule anchor for an exact provision span when a candidate depends on the subrule text.

## 3. Candidate review

For every candidate, answer:

1. What exact text supports it?
2. Is the statement descriptive, normative, procedural, adjudicative, remedial, or temporal?
3. Is the source official law, secondary commentary, or case treatment?
4. What is explicitly stated and what would be inference?
5. What production contract would apply?
6. What evidence is missing?

Use closed verdicts:

- `PROMOTE_COMPLETE`
- `HOLD_MISSING_COMPONENT`
- `HOLD_SOURCE_AUTHORITY`
- `HOLD_IDENTITY`
- `REJECT_NOT_SUPPORTED`

Avoid vague `maybe` or `needs review` without naming the missing component.

## 4. Promotion and verification

Use one migration per family when rollback or completion predicates differ. A migration report must include:

- exact target IDs;
- expected created/updated nodes and relationships;
- pre-existing collisions;
- canary identity;
- canary rollback counts;
- full apply counters;
- separate read-pool verification;
- production-policy result;
- prohibited-member count;
- rollback packet path and hash.

Do not infer success from the write transaction alone.

## 5. Appendix A discipline

The reliable sequence is:

1. metadata audit;
2. conformance audit;
3. render Markdown;
4. build DOCX;
5. build PDF;
6. verify every figure;
7. diff prior and current machine-readable artifacts;
8. explain each changed metric.

Important implementation details:

- Metadata rows use `strict_count`, not `count`.
- The metadata row `status` compares against a frozen baseline, not necessarily the previous run.
- Run-over-run comparison must use the previous and current `COVERAGE_ROWS.json` files.
- Conformance readiness failure does not mean audit execution failure.
- Preserve the metric-definition version and schema fingerprint with every revision.

## 6. Parallel-agent handover

Every agent should receive:

- exact source package hash;
- exact rule range;
- prior completed families;
- pending families;
- exact database target;
- prior Appendix revision;
- immutable expected-count manifest;
- authority and promotion boundaries.

Every agent should return:

- exact completed IDs;
- exact pending IDs;
- complete-rule boundaries;
- artifact hashes;
- failure reasons;
- whether another nudge or agent is required.
