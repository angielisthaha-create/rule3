# Generic ARC Counsel Scoring Insert

Use this insert when a rule package includes a counsel review package, row-decision CSV, case-signal ledger, blocker/discard ledger, DB evidence ledger, or any prior confidence scoring that must be normalized before Phase-A handoff. Run these five scoring prompts before Phase 3 counsel normalization unless the user explicitly says the counsel package is already final and no scoring revision is needed. In the full workflow, these five prompts are the first five turns of the 15 same-prompt cadence; the ten Phase-A handoff phases follow afterward.

## Scoring posture

Keep scoring separate from write eligibility:

- high disposition confidence is not high legal confidence;
- high rejection confidence is not high case authority confidence;
- LexGraph evidence is a retrieval signal, not current-law or public paragraph verification;
- case-holding rows stay Phase B unless public paragraph pin and citator/current-status verification are complete;
- no graph writes are authorized by scoring.

Always produce or preserve these fields when row-level material exists:

```text
disposition_confidence_0_100
legal_interpretation_confidence_0_100
case_authority_confidence_0_100
disposition_confidence_band
legal_interpretation_confidence_band
case_authority_confidence_band
write_eligibility_status
manual_validation_required
manual_validation_reason
public_verification_status
current_status_check
```

## Band thresholds

Use these default bands unless a package defines stricter thresholds:

```text
HIGH: 90-100
MEDIUM_HIGH: 80-89
MEDIUM: 60-79
LOW: 0-59
```

## Score axes

### disposition confidence

Score whether the workflow decision is correct.

Examples:

- reject unsafe CasePathwayHolding write because paragraph/citator evidence is missing: 95-98;
- approve blocker/discard ledger entry with clear source basis: 94-98;
- retain public-pin-pending case signal with exact citation and target paragraph: 90-95;
- retain research-ready pathway with live rule anchor and no public filing verification: 90-96.

### legal interpretation confidence

Score whether the legal/procedural proposition is substantively reliable.

Examples:

- exact official rule text verified and proposition tracks it: 94-98;
- exact live UnifiedRule anchor plus clear rule-text/candidate pathway fit but public text not checked: 88-93;
- exact case identity plus target paragraph but public pin/citator pending: 80-89;
- graph signal or placeholder row only: 20-59.

### case authority confidence

Score only case support for the proposition.

Examples:

- public paragraph pin and citator/current-status verified: 90-100;
- exact case identity, citation, target paragraph, and LexGraph match, but public pin/citator pending: 65-79;
- exact case identity and citation but paragraph missing: 45-64;
- placeholder case name only: 10-40;
- no case basis: 0.

## Write eligibility statuses

Use these exact statuses when possible:

```text
write_candidate_after_governed_approval
hold_for_manual_validation
parking_phase_b_case_holding
reject_as_current_casepathwayholding
discard_ledger_only
blocker_ledger_only
graph_signal_discard
case_signal_only
research_ready_pathway_only
no_write_candidate_only
```

## Five scoring prompts

### Scoring Prompt 1 - Counsel scoring source setup

Use when a rule has a counsel package or row-level review artifacts.

```text
Run the pathway-bearing counsel-scoring insert for <RULE_OR_PART>, Scoring Prompt 1.

Identify the canonical counsel scoring source and supporting ledgers from the uploaded package. Select the canonical row-decision surface, list adopted supplemental scoring inputs, list excluded/stale scoring inputs, preserve candidate-only/no-write status, and emit <rule_slug>_counsel_scoring_source_ledger.json plus <rule_slug>_counsel_scoring_source_summary.md.

Do not perform graph writes.
```

Required outputs:

- `<rule_slug>_counsel_scoring_source_ledger.json`
- `<rule_slug>_counsel_scoring_source_summary.md`

### Scoring Prompt 2 - Confidence split normalization

Use to split any single score or source confidence into the three required axes.

```text
Run the pathway-bearing counsel-scoring insert for <RULE_OR_PART>, Scoring Prompt 2.

Normalize the counsel row surface so each row has disposition, legal-interpretation, and case-authority confidence scores and bands. Preserve source confidence fields in provenance. Do not treat high rejection confidence as high legal or case authority confidence. Emit <rule_slug>_confidence_split_rows.csv, <rule_slug>_confidence_split_rows.json, and <rule_slug>_confidence_split_summary.json.

Do not perform graph writes.
```

Required outputs:

- `<rule_slug>_confidence_split_rows.csv`
- `<rule_slug>_confidence_split_rows.json`
- `<rule_slug>_confidence_split_summary.json`

### Scoring Prompt 3 - Case and authority scoring

Use to classify case rows, authority rows, and public-pin/citator gaps.

```text
Run the pathway-bearing counsel-scoring insert for <RULE_OR_PART>, Scoring Prompt 3.

Review case-signal, case-holding, and authority-status rows. Assign case_authority_confidence_0_100 using exact case identity, citation, paragraph-pin status, public verification status, citator/current-status status, and whether the case changes the rule pathway. Park all case-holding authority rows in Phase B unless public paragraph pin and citator/current-status verification are both complete. Emit <rule_slug>_case_authority_scoring_ledger.csv and <rule_slug>_phase_b_case_scoring_parking.csv.

Do not perform graph writes.
```

Required outputs:

- `<rule_slug>_case_authority_scoring_ledger.csv`
- `<rule_slug>_phase_b_case_scoring_parking.csv`

### Scoring Prompt 4 - Enhancement pass

Use to safely promote medium or medium-high rows without inflating unsupported authority.

```text
Run the pathway-bearing counsel-scoring insert for <RULE_OR_PART>, Scoring Prompt 4.

Enhance eligible MEDIUM or MEDIUM_HIGH rows only on the scoring axis supported by evidence. Promote conflict/pathway rows only where live rule-anchor fit, rule-text fit, companion-rule fit, blocker/discard basis, or exact case-signal identity supports the change. Do not raise case_authority_confidence without public paragraph-pin and citator/current-status support. Emit <rule_slug>_scoring_enhancement_ledger.csv and <rule_slug>_remaining_subhigh_rows.csv.

Do not perform graph writes.
```

Required outputs:

- `<rule_slug>_scoring_enhancement_ledger.csv`
- `<rule_slug>_remaining_subhigh_rows.csv`

### Scoring Prompt 5 - Final scored counsel package

Use to freeze the scored counsel package that later phases will normalize and split into Phase A/B.

```text
Run the pathway-bearing counsel-scoring insert for <RULE_OR_PART>, Scoring Prompt 5.

Build the final scored counsel package for downstream Phase-A handoff. Emit a final scored row-decision CSV, final scored analysis JSON, scoring README with counts and hashes, manual-validation scoring ledger, and no-write scoring ledger. Confirm graph_writes_performed=false, filing_ready=false, and graph_write_ready=false unless separately verified and approved. Tell me the next required handoff phase.

Do not perform graph writes.
```

Required outputs:

- `<rule_slug>_final_scored_row_decisions.csv`
- `<rule_slug>_final_scored_analysis.json`
- `<rule_slug>_scoring_manual_validation.tsv`
- `<rule_slug>_scoring_no_write_ledger.json`
- `<rule_slug>_scoring_README.md`

## Unified scoring continuation prompt

Use this if the user wants to run only the five scoring prompts:

```text
Run the pathway-bearing counsel-scoring insert for <RULE_OR_PART>. Use the uploaded counsel package and any already-generated scoring artifacts. Process only the next incomplete scoring prompt, preserve candidate-only/no-write status, update the scoring ledger, stop after producing that prompt's artifacts, and tell me the next required scoring or handoff phase. No graph writes.
```

Use the universal 15-prompt continuation prompt in `SKILL.md` when the user wants one same prompt for both scoring and Phase-A handoff phases.

## Integration with handoff phases

After Scoring Prompt 5, use the final scored row-decision CSV and final scored analysis JSON as the canonical row-level counsel package for Phase 3 - Counsel normalization.

If the user skips scoring, Phase 3 may consume the existing counsel package, but the worker ledger must record `counsel_scoring_insert_status = skipped_or_not_requested`.
