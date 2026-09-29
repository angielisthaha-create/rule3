# Interactive 100-Turn Manual Cadence Protocol

Use this protocol when the user will send one trigger message every 4 minutes for 100 turns and expects ChatGPT to perform the next database validation slice each time.

## Important limitation

The skill does not run in the background. The user supplies the cadence by sending each message. Each received trigger starts one bounded read-only validation slice. If the user pauses or stops, the test pauses or stops.

## Trigger message

Primary fixed-heartbeat trigger, repeated 100 times by the user:

```text
ARC_PATHWAY_VALIDITY_TEST seq=001/100 run_id=ARC_PATHWAY_VALIDITY_PARTS_2_11_13_14_SKIP_12
```

When this exact text is repeated, treat `seq=001/100` as a stable heartbeat token, not as an instruction to restart at sequence 1. Advance by the number of received triggers in the conversation ledger. Do not restart unless the user writes `reset`, `restart`, or gives a new `run_id`.

Optional changing-sequence trigger:

```text
ARC_PATHWAY_VALIDITY_TEST seq=<001-100>/100 run_id=<run_id>
```

Accept variants such as:

```text
next
continue test
turn 17
message 017
ARC pathway validity unified setup test
```

If the literal sequence number is fixed at `001/100`, missing, or ambiguous, infer the next number from conversation state and say that the count is inferred.

## Response format

Reply in this unified shape:

```text
ARC pathway validity test <actual_turn>/100 - <slice_name>

Trigger received: fixed heartbeat seq=001/100 or explicit seq=<seq>
Mode: read-only
Target: <part/global/special queue>
Database calls: successful=<n>; failed=<n>; timed_out=<n>; blocked_or_skipped=<n>
Result: <one concise finding>
Promotion impact: <none/red/amber/green/hold>
Ledger note: <what was recorded, including whether actual_turn was inferred by arrival count>
Next trigger: send the same heartbeat message again in about 4 minutes.
```

If a query times out or fails, include:

```text
Timeout/failure handling: not counted as successful; next query shape narrowed to <strategy>.
```

## 100-turn schedule

The schedule uses 5 cycles of 20 turns. Each cycle repeats the same validation categories while rotating focus parts and samples so the run becomes progressively thorough without using risky broad scans.

Target part rotation:

```text
Cycle 1: Parts 2, 3, 4
Cycle 2: Parts 5, 6, 7
Cycle 3: Parts 8, 9, 10
Cycle 4: Parts 11, 13, 14
Cycle 5: Cross-part reconciliation and resampling
```

### Per-cycle 20-turn pattern

1. Health/read-only posture and run ledger check.
2. Target `UnifiedRule` inventory.
3. Part 12 exclusion check.
4. Canonical ARC label inventory.
5. Canonical ARC relationship inventory.
6. Direct `UnifiedRule -> HAS_PATHWAY -> ARCProceduralPathway` traversal.
7. Same-rule anchor check using explicit rule properties.
8. Duplicate `UnifiedRule` anchor probe.
9. `RuleProvision`/`HubRule` fallback risk check.
10. Internal `UnifiedRule` text alignment sample.
11. Pathway field integrity sample.
12. Authority status / `A_rule_text` honesty check.
13. Phase-B leakage check.
14. Manual validation task classification.
15. Discard ledger review.
16. Companion-rule endpoint and necessity review.
17. Expected-count reconciliation checkpoint.
18. Special part rule checkpoint.
19. Manual sample queue generation.
20. Cycle summary and promotion matrix update.

## Special part routing

Apply these instructions whenever the focus includes the named part:

- Part 5: treat as partial; separately report blocker, pin-hold, conflict-signal, and Phase-B queues.
- Part 9: treat as partial if interpretive issues remain unformulated or holdings remain parked.
- Part 14: keep in QA quarantine until confidence bands, meta-wiring nodes, and anchor repairs are reviewed.
- Part 12: exclusion only; do not validate pathway coverage.
- Part 1: pending fallback only unless the user provides a separate Part 1 package.

## Call-count rule

Only successful returned database executions count. Do not count:

```text
blocked attempts
skipped checks
timeouts
queries rejected by read-only guard
queries that returned tool errors
```

## Safety rule

Use read-only database tools only. Do not write, delete, mutate schema, convert relationships, create embeddings, or run repair packets during this 100-turn test.
