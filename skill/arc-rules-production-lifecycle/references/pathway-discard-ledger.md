# Discard Ledger Rules

## Purpose

Use a discard ledger to protect the graph from noisy matches and overbroad pathway creation.

## Discard Categories

Discard or separately classify:

```text
generic rule citations without interpretation
commentary-only references without underlying case verification
reform proposals not confirmed by current law
graph-generated summaries without paragraph support
generic Case nodes
duplicate case candidates
orphan/quarantined graph nodes
stub RuleProvision nodes
OCR artifacts
truncated citations
cases from other jurisdictions unless marked analogue
facts-only cases that do not interpret the rule
material with unresolved privilege or sealing restrictions
```

## Undertaking-Specific Noise

For Rules 5.25/5.30 and 5.33, separately classify:

```text
Rule 5.30 discovery undertakings
implied undertaking doctrine
solicitor undertakings
contractual undertakings
undertakings as to damages
undertakings to defend
settlement undertakings
appeal-related undertakings
```

Only Rule 5.30 discovery undertakings belong in the core Rule 5.30 pathway. Implied undertaking belongs in Rule 5.33.

## Discard Ledger Fields

```text
raw_hit_id
term
source_type
discard_reason
disposition
source
notes
```
