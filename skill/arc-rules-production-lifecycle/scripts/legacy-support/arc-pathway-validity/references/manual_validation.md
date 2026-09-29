# Manual Validation Protocol

Automated graph checks are necessary but not sufficient. Use this protocol after structural and source-alignment checks.

## Sampling plan

For each target part, sample:

```text
5 high-confidence pathways
5 low-confidence pathways
5 pathways with manual validation tasks
5 pathways with conflict signals
5 pathways with companion-rule dependencies
5 pathways with anchor repairs, if any
```

## Review questions

For each sampled row, answer:

1. What rule or subrule is this pathway anchored to?
2. Does the internal `UnifiedRule` text support the pathway?
3. Does the pathway identify the trigger?
4. Does it identify the actor?
5. Does it identify timing or deadline, if any?
6. Does it identify the condition or threshold?
7. Does it identify whether the consequence is mandatory or discretionary?
8. Does it identify the remedy or procedural result?
9. Does it identify exceptions or caveats?
10. Is any part of the formulation broader than the internal rule text?
11. Is the authority grade honest?
12. Is counsel review required before promotion?

## Manual task categories

Classify `ARCManualValidationTask` rows as:

```text
BLOCKER - prevents pathway promotion
PIN_HOLD - blocks Phase-B authority linkage
SOURCE_REVIEW - check against internal UnifiedRule text
COUNSEL_REVIEW - legal formulation requires human approval
ANCHOR_REPAIR_REVIEW - repaired anchor must be confirmed
CONFIDENCE_REVIEW - low/medium confidence row
META_WIRING_REVIEW - possible non-substantive wiring node
```

Any unresolved `BLOCKER` prevents promotion beyond structural Phase-A validity.

## Safe finding labels

Use:

```text
accurate
accurate but incomplete
overbroad
under-specified
wrong anchor
source-text mismatch
candidate-only
manual blocker
Phase-B pending
discard or hold
```

Avoid using “false” unless the internal rule text directly contradicts the pathway. Prefer “unsupported,” “overbroad,” “incomplete,” or “requires counsel review.”

## Counsel review queue fields

Recommended fields:

```text
part
rule_number
pathway_uid
pathway_formulation
internal_unifiedrule_excerpt
authority_status
confidence_band
manual_task_type
conflict_signal_present
companion_rule_dependency
review_question
recommended_status
reviewer_notes
```
