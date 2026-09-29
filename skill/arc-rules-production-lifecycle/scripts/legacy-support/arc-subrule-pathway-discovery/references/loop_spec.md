# ARC Subrule Pathway Discovery Loop Spec

## Loop Name

ARC Subrule Pathway Discovery Loop

## Trigger

Manual start for a selected Alberta Rules of Court rule or subrule.

## Goal

For each selected rule, identify narrow interpretive pathways where cases apply the same rule differently depending on context, remedy, procedure, evidence posture, authority status, or factual trigger.

## Completion Condition

A rule is complete when the loop has produced:

1. canonical rule/subrule text;
2. companion-rule map;
3. top case authorities from LexGraph, uploaded files, textbooks/commentary, and public sources;
4. pathway catalogue;
5. binding/persuasive/analogue authority ranking;
6. contrary or limiting authorities;
7. filing-safe formulation;
8. do-not-overstate warnings;
9. graph enhancement candidates;
10. manual verification queue;
11. discard ledger;
12. no-write run ledger.

## Editable Surface

Produce a Markdown rule pathway report plus a JSON graph-candidate packet. When asked for downloads, also produce TSV ledgers and ZIP package.

## Protected Evaluator/Data

- Do not overwrite existing graph doctrine nodes.
- Do not treat textbook commentary as binding law.
- Do not treat reform proposals as current law.
- Do not create graph writes until a human approves exact IDs, citations, expected counts, and rollback plan.
- Do not treat generated summaries as case holdings.

## Tooling

Preferred order:

1. LexGraph Neo4j read-only queries for canonical nodes and authority signals.
2. Uploaded files for user-provided records.
3. CanLII or official public sources for current rule/case verification.
4. Optional web search for current-status and citator checks.
5. Local scripts for packet validation and ledgers.

## Workspace Isolation

Use one folder per rule:

```text
arc_pathway_pilot/rule_6_8/
arc_pathway_pilot/rule_6_14/
arc_pathway_pilot/rule_5_25_5_30/
arc_pathway_pilot/rule_5_33/
arc_pathway_pilot/rule_<rule>/
```

## Subagent Roles

Use these roles as mental workstreams or delegated subtasks:

1. rule-text extractor;
2. companion-rule mapper;
3. textbook/commentary authority miner;
4. LexGraph case-line miner;
5. source-material classifier;
6. pathway classifier;
7. authority hierarchy verifier;
8. graph-packet builder;
9. adversarial reviewer;
10. validation-ledger builder.

## Keep/Discard Rule

Keep a pathway only if it changes the legal answer, the safe formulation, the remedy, the admissibility route, the source-material treatment, or the authority status.

Discard generic case references that merely cite the rule without interpreting it.

## Budget Limits

- Limit first pass to top 20 authorities unless the pathway remains unresolved.
- Escalate if more than 3 contradictory case lines appear.
- Prefer aggregate counts and small samples before raw-text retrieval.

## Human Approval Gates

Human approval is required before:

- Neo4j writes;
- merging duplicate rule or case nodes;
- marking a pathway as governing;
- adding current-law status;
- using any conclusion in filed materials;
- executing exact-ID repair canaries or migration packets.

## Stop/Escalation Conditions

Stop if:

- rule text cannot be verified;
- canonical node is ambiguous;
- cases cannot be pinned to paragraphs;
- authority hierarchy is unresolved;
- current-status/citator conflict appears;
- privilege or confidentiality boundaries are unclear;
- proposed use is high-risk without public-interest analysis.
