# Unified 15-Prompt Cadence

Use this reference when the user asks how to run pathway-bearing repeatedly.

## Total prompts

Run 15 same-prompt turns unless the user explicitly skips scoring:

1. Scoring Prompt 1 - counsel scoring source setup
2. Scoring Prompt 2 - confidence split normalization
3. Scoring Prompt 3 - case and authority scoring
4. Scoring Prompt 4 - enhancement pass
5. Scoring Prompt 5 - final scored counsel package
6. Handoff Phase 1 - source-of-truth setup
7. Handoff Phase 2 - authoritative rule-text verification
8. Handoff Phase 3 - counsel normalization
9. Handoff Phase 4 - Phase A / Phase B split
10. Handoff Phase 5 - source repair and anchor resolution
11. Handoff Phase 6 - live graph verification
12. Handoff Phase 7 - canonical ARC wiring
13. Handoff Phase 8 - canonical JSON and reversible Cypher draft generation
14. Handoff Phase 9 - expected counts, worker ledger, and self-checks
15. Handoff Phase 10 - final Pane A handoff package and PromptBus summary

## Same prompt to paste

```text
Run the pathway-bearing workflow for <RULE_OR_PART>. Use the uploaded consolidated source packet, counsel package, scoring artifacts, source-of-truth ledger, and any already-generated phase artifacts. Process only the next incomplete step in the 15-step sequence: first the five counsel-scoring prompts if scoring is not complete, then the ten Phase-A worker-handoff phases. Preserve candidate-only/no-write status, update the scoring or worker ledger, produce this step's required artifacts, stop after completing this step, and tell me the next required step. No graph writes.
```

The user may manually wait about 5 minutes between prompts. Do not create or promise sub-hour recurring automations.
