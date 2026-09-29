# Generic ARC Rule Processing Process

This reference defines the generic governed process for taking any Alberta Rules of Court rule or part package from consolidated candidate material to a Pane-A-reviewable Phase-A worker handoff.

## Purpose

The process is candidate-first, reversible, and write-governed.

- Pane A is the sole live graph writer unless the user expressly authorizes another lane.
- Worker panes may prepare, normalize, validate, and hand off.
- Case-holding authority rows are Phase B unless paragraph pin plus citator/current-status verification is complete.

## Required inputs

Prefer these artifacts when available:

1. consolidated source packet with candidate nodes, pathways, recommended relationships, and rule anchors;
2. row-level counsel package with one substantive row per issue, pathway, conflict, discard, and case-holding candidate;
3. authoritative rule-text verification ledger;
4. supplemental review packages such as conflict-enhanced reviews, evidence ledgers, and case-signal ledgers.

Supplemental review packages may inform scoring or notes but do not replace the canonical counsel source unless expressly adopted.

## Completion standard

A rule package is ready for Pane A review only when:

- rule text is verified or explicitly marked pending;
- ontology is canonical;
- Phase A and Phase B are separated;
- live anchors are verified;
- executable Cypher is reversible and label-scoped;
- all executable properties are Neo4j-safe;
- no dangling rows remain;
- counts are explicit;
- the package is still candidate-only.

## Required self-checks

Before handoff, confirm:

1. `graph_writes_performed = false`;
2. no executable non-primitive properties;
3. no dangling relationship endpoints;
4. no placeholder anchor UIDs in executable MATCH clauses;
5. rollback is scoped strictly by `migration_id`;
6. readback counts match expected counts;
7. Phase B case-holding rows are excluded from Phase-A write artifacts.

## Worker ledger content

The worker ledger must record:

1. source artifact paths;
2. rules processed;
3. substantive row counts;
4. parked Phase-B counts;
5. meta node counts;
6. relationship counts by type;
7. anchor repairs;
8. anchor skip list;
9. self-check results;
10. generated file list.

## Handoff protocol

1. Write all artifacts to disk.
2. Send Pane A a short PromptBus summary with artifact path, counts, anchor skip result, self-check result, and caveats.
3. Mirror the summary to another pane only if requested or operationally necessary.
