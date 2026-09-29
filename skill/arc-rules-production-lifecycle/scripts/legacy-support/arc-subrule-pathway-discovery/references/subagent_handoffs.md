# Subagent Handoffs

Use these compact handoff templates when splitting work across focused agents or internal passes.

## Rule-text extractor
Input: rule number, jurisdiction, optional canonical UID.  
Task: verify current rule text, subrules, source URL, current-to date, and text hash.  
Output: rule anchor record plus duplicate/stub node warning.  
Stop if: current rule text or canonical node cannot be verified.

## Textbook authority miner
Input: rule number, textbook/commentary hits.  
Task: extract candidate cases and commentary propositions.  
Output: commentary-vs-case ledger.  
Stop if: commentary cannot be tied to a public case or rule source.

## Case-line clusterer
Input: candidate cases and paragraph snippets.  
Task: group cases by pathway, rule issue, remedy, and procedural posture.  
Output: pathway clusters and discard ledger rows.  
Stop if: cases merely cite the rule without applying it.

## Pathway classifier
Input: clusters and rule text.  
Task: assign pathway UIDs, source-material classes, use-purpose classes, proceeding relationships, remedy classes, safe formulation, and overstatement warnings.  
Output: candidate pathway records.  
Stop if: no material change in legal answer/formulation.

## Authority hierarchy verifier
Input: case ladder.  
Task: classify court level, binding/persuasive/analogue status, current-status need, paragraph grade, and contrary/limiting authorities.  
Output: authority ladder.  
Stop if: court level or citation cannot be verified.

## Graph-packet builder
Input: pathway records and authority ladder.  
Task: build JSON packet, relationship candidates, manual validation ledger, discard ledger, and no-write ledger.  
Output: candidate packet and ledgers.  
Stop if: write status is anything other than no-write/candidate.

## Adversarial reviewer
Input: packet and report.  
Task: test for overgeneralization, commentary-as-law, stale rule text, duplicate/stub graph nodes, analogue leakage, privilege/privacy omissions, and filing-readiness overclaim.  
Output: defect list and revision instructions.  
Stop if: any core authority lacks paragraph verification.
