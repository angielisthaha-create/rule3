# Frozen ARC Ontology for Phase-A Handoffs

Use only this ontology unless a separate registry approval authorizes additions.

## Candidate node labels

Phase-A substantive labels:

- `ARCRuleInterpretationIssue`
- `ARCProceduralPathway`
- `ARCRuleConflictSignal`
- `ARCDiscardLedgerEntry`

Phase-B parked authority label:

- `ARCCasePathwayHolding`

Meta labels:

- `ARCAuthorityStatus`
- `ARCManualValidationTask`

Canonical anchor label:

- `UnifiedRule`

## Canonical relationship types

- `HAS_INTERPRETIVE_ISSUE`: `UnifiedRule -> ARCRuleInterpretationIssue`
- `HAS_PATHWAY`: `UnifiedRule -> ARCProceduralPathway`
- `HAS_AUTHORITY_STATUS`: `ARCProceduralPathway -> ARCAuthorityStatus`
- `HAS_CONFLICT_SIGNAL`: `ARCProceduralPathway -> ARCRuleConflictSignal`
- `HAS_DISCARD_LEDGER_ENTRY`: `ARCProceduralPathway -> ARCDiscardLedgerEntry`
- `HAS_MANUAL_VALIDATION_TASK`: `ARCProceduralPathway -> ARCManualValidationTask`
- `REFERENCES_COMPANION_RULE`: `UnifiedRule -> UnifiedRule`

## Prohibited shortcuts

- Do not connect reform proposals directly as current law.
- Do not attach candidates to duplicate or stub rule nodes.
- Do not turn case mentions into case holdings.
- Do not treat LexGraph evidence as public verification.
- Do not write Phase-B case holdings into Phase-A artifacts.
