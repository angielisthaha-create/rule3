# ARC Pathway Ontology Schema

## Candidate node classes

- `RuleInterpretationIssue`: recurring interpretive question for a rule/subrule.
- `ProceduralPathway`: procedural/factual/evidentiary branch that changes the rule answer.
- `CasePathwayHolding`: case-specific holding supporting, limiting, distinguishing, confirming, conflicting with, or analogizing a pathway.
- `AuthorityStatus`: status node for binding/persuasive/current/analogue/reform/uncertain authority.
- `RuleConflictSignal`: candidate conflict, tension, limitation, or split.
- `ReformProposalSignal`: reform or commentary proposal, never current law unless confirmed.
- `ManualValidationTask`: verification task required before current-law or graph-write status.
- `AnaloguePathwaySignal`: analogy-only authority or pathway.

## AuthorityStatus enum

```text
binding_current
binding_possible_but_needs_citator
persuasive_current
persuasive_needs_citator
historical_predecessor_rule
analogue_only
commentary_only
reform_proposal
overruled_or_reversed
distinguished
uncertain
do_not_use_until_verified
```

## Court level enum

```text
SCC
ABCA
ABKB
ABQB
ApplicationsJudge
Master
FederalCourt
FCA
OutOfProvince
Tribunal
Commentary
Unknown
```

## Authority role enum

```text
root_doctrine
codification
scope_limit
leave_test
threshold_test
public_record_exception
anti_circumvention
regulator_disclosure_granted
regulator_disclosure_refused
related_action_granted
related_action_refused
same_action_use
breach_sanction
contempt_limit
admissibility_limit
analogue_only
privilege_limit
non_party_privacy_limit
remedy_selection
current_application
historical_root
contrary_or_distinguishing
```

## Paragraph grade enum

```text
A = public paragraph pin verified and quoted text confirmed
B = LexGraph paragraph found but public pin not checked
C = case cited but paragraph missing
D = commentary-derived case only
F = cannot verify case or citation
```

## ReformProposalSignal rule

A `ReformProposalSignal` must not connect directly to `RuleProvision` or `RuleInterpretationIssue` as current law. It must carry source, proposal date, proposal status, not-current-law warning, and confirming authority requirement.
