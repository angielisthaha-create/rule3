# Graph Relationship Model

Allowed candidate relationship patterns:

```cypher
(:RuleProvision)-[:HAS_INTERPRETIVE_ISSUE]->(:RuleInterpretationIssue)
(:RuleInterpretationIssue)-[:HAS_PATHWAY]->(:ProceduralPathway)
(:Case)-[:SUPPORTS_PATHWAY_HOLDING]->(:CasePathwayHolding)
(:CasePathwayHolding)-[:INTERPRETS_SUBRULE]->(:RuleProvision)
(:CasePathwayHolding)-[:LIMITED_BY]->(:CasePathwayHolding)
(:CasePathwayHolding)-[:DISTINGUISHED_BY]->(:CasePathwayHolding)
(:CasePathwayHolding)-[:CONFIRMED_BY]->(:CasePathwayHolding)
(:CasePathwayHolding)-[:CONFLICTS_WITH]->(:CasePathwayHolding)
(:CasePathwayHolding)-[:ANALOGOUS_TO]->(:CasePathwayHolding)
(:CasePathwayHolding)-[:REQUIRES_ADMISSIBILITY_GATE]->(:RuleProvision)
(:CasePathwayHolding)-[:REQUIRES_PRIVILEGE_SCREEN]->(:ManualValidationTask)
(:CasePathwayHolding)-[:REQUIRES_PRIVACY_SCREEN]->(:ManualValidationTask)
(:ReformProposalSignal)-[:NOT_GOVERNING_UNLESS_CONFIRMED_BY]->(:AuthorityStatus)
```

Prohibited before separate approval:

```text
MERGE duplicate case nodes
DELETE duplicate rule nodes
mark GOVERNING
mark CURRENT_LAW_VERIFIED
bulk attach all cases citing a rule
convert placeholder relationships
write pathway holdings without paragraph pins
write pathway holdings to duplicate/stub rule nodes
write migration without rollback plan
```

A pathway packet may contain relationship candidates only. It must not contain executable write Cypher.
