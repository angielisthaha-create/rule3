# ARC Phase-A Worker Handoff Phase Checklists

Use these phases for any ARC rule or part. Replace `<RULE_OR_PART>` with the user-supplied target and `<rule_slug>` with a file-safe slug such as `rule5`, `rule14`, or `rule6_37`.

The full cadence is 15 same-prompt turns: five counsel-scoring insert turns followed by ten handoff-phase turns. The user may manually space these prompts about 5 minutes apart. On each turn, run only the next incomplete step and stop.

If the package includes counsel rows or confidence scores that are not final, run the five-prompt counsel-scoring insert in `counsel_scoring.md` before Phase 3. Treat its final scored row-decision CSV as the canonical row-level counsel package.

## Phase 1 - Source-of-truth setup

Build the source-of-truth setup for a Pane-A Phase-A worker handoff.

Tasks:

1. Identify the canonical source packet.
2. Identify the canonical row-level counsel package.
3. Identify supplemental sources that may inform scoring but do not replace the canonical source unless expressly adopted.
4. Confirm the target rule or part scope.
5. Confirm candidate-only/no-write status.
6. Confirm no new labels or relationship types are introduced outside the frozen ARC ontology.
7. Emit `<rule_slug>_source_of_truth_ledger.json`.

Required output:

- `<rule_slug>_source_of_truth_ledger.json`
- `<rule_slug>_source_of_truth_summary.md`

## Phase 2 - Authoritative rule-text verification

Verify target rule numbers against authoritative rule text when available. Do not treat LexGraph `UnifiedRule` text as public rule-text verification.

Tasks:

1. Verify each target rule number.
2. Record whether each rule exists.
3. Record title/body verification status.
4. Record discrepancies, repeal, stale-text, or unresolved status.
5. Do not fabricate missing rule text.
6. Keep the package candidate-only.

Required output:

- `<rule_slug>_rule_text_verification.tsv`
- `<rule_slug>_rule_text_verification.json`

## Phase 3 - Counsel normalization

Normalize the row-level review surface into canonical ARC classes.

Tasks:

1. Build a single row-level review surface.
2. Normalize every substantive row into one canonical class.
3. Keep meta rows separate.
4. Preserve original row IDs and provenance.
5. Flatten nested maps/list-of-maps to primitives or JSON strings.
6. Drop `None` values from executable candidate properties.
7. Mark case-holding rows as Phase B unless public paragraph pin and citator/current-status verification are complete.

Required output:

- `<rule_slug>_normalized_rows.csv`
- `<rule_slug>_normalized_rows.json`
- `<rule_slug>_normalization_issues.csv`

## Phase 4 - Phase A / Phase B split

Tasks:

1. Identify substantive Phase A rows.
2. Identify parked Phase B case-holding rows.
3. Identify skipped or unrecoverable rows.
4. Identify blocker/manual-validation rows.
5. Confirm no Phase B case-holding rows appear in Phase-A write artifacts.
6. Emit counts by class and decision.

Required output:

- `<rule_slug>_phase_a_rows.csv`
- `<rule_slug>_phase_b_parked_case_holdings.csv`
- `<rule_slug>_skipped_or_unrecoverable_rows.csv`
- `<rule_slug>_phase_split_summary.json`

## Phase 5 - Source repair and anchor resolution

Tasks:

1. Repair malformed rule numbers.
2. Recover real rule numbers from source key, raw hit id, anchor info, packet metadata, or row provenance.
3. Resolve placeholder or missing anchor UIDs to live `UnifiedRule` nodes.
4. Preserve original broken values in provenance fields.
5. Do not leave placeholder anchors in executable MATCH endpoints.
6. Park rows if no live anchor can be resolved safely.
7. Produce repair and skip ledgers.

Required output:

- `<rule_slug>_anchor_repair_ledger.csv`
- `<rule_slug>_anchor_skip_ledger.csv`
- `<rule_slug>_resolved_anchor_map.json`

## Phase 6 - Live graph verification

Run read-only live graph verification.

Tasks:

1. Verify each target `UnifiedRule` anchor exists live.
2. Verify companion-rule anchors exist live where companion links will be emitted.
3. Confirm no dangling source anchors, dangling target anchors, or unlabeled endpoints.
4. Confirm duplicate/stub risk.
5. Do not perform graph writes.

Required output:

- `<rule_slug>_live_anchor_verification.csv`
- `<rule_slug>_companion_anchor_verification.csv`
- `<rule_slug>_dangling_endpoint_check.json`
- `<rule_slug>_live_graph_verification_summary.json`

## Phase 7 - Canonical ARC wiring

Generate canonical ARC relationship wiring.

Tasks:

1. Use packet `recommended_relationships` where valid and endpoint-safe.
2. Infer only the minimum missing safe relationships.
3. Prefer explicit `pathway_uid` linkage where available.
4. Use same-rule fallback only where clearly intended.
5. Record wiring basis on each generated relationship.
6. Exclude Phase B case-holding rows from Phase-A writes.
7. Emit relationship counts by type.

Required output:

- `<rule_slug>_canonical_relationships.csv`
- `<rule_slug>_relationship_counts.json`
- `<rule_slug>_wiring_basis_ledger.csv`

## Phase 8 - Canonical JSON and reversible Cypher generation

Generate Pane-A Phase-A handoff artifacts.

Required output:

- `<rule_slug>_canonical.json`
- `<rule_slug>_write_nodes.cypher`
- `<rule_slug>_write_rels.cypher`
- `<rule_slug>_readback.cypher`
- `<rule_slug>_rollback.cypher`

Cypher rules:

1. Use `MERGE` on `uid`.
2. Set a rule-scoped `migration_id`.
3. Use label-scoped endpoint `MATCH`.
4. Use only Neo4j-safe primitive properties or JSON strings.
5. Exclude Phase B case-holding rows.
6. Exclude dangling anchors.
7. Scope rollback strictly by `migration_id`.

## Phase 9 - Expected counts, worker ledger, and self-checks

Tasks:

1. Generate `expected_counts.json`.
2. Generate `WORKER_RUN_LEDGER.json`.
3. Confirm no-write status, property safety, endpoint safety, rollback scope, readback expectations, and Phase-B exclusion.
4. Record source paths, rules processed, counts, anchor repairs, skips, self-checks, and generated files.

Required output:

- `expected_counts.json`
- `WORKER_RUN_LEDGER.json`
- `<rule_slug>_self_check_report.json`

## Phase 10 - Final handoff package and PromptBus summary

Tasks:

1. Assemble final handoff folder.
2. Create `<rule_slug>_paneA_promptbus_summary.md`.
3. Include artifact path, counts, anchor skip result, self-check result, Phase B parked count, caveats, and no-write confirmation.
4. Zip the package.
5. Do not perform graph writes.

Required output:

- `<rule_slug>_PHASE_A_WORKER_HANDOFF_PACKAGE.zip`
- `<rule_slug>_paneA_promptbus_summary.md`

## Unified scoring insertion prompt

```text
Run the pathway-bearing counsel-scoring insert for <RULE_OR_PART>. Use the uploaded counsel package and any already-generated scoring artifacts. Process only the next incomplete scoring prompt, preserve candidate-only/no-write status, update the scoring ledger, stop after producing that prompt's artifacts, and tell me the next required scoring or handoff phase. No graph writes.
```

## Unified continuation prompt

```text
Continue the ARC Phase-A worker handoff for <RULE_OR_PART>. Run the next incomplete phase only, update the worker ledger, preserve no-write status, and stop after producing that phase's artifacts.
```
