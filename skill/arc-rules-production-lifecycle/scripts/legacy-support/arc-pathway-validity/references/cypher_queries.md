# Bounded Read-Only Cypher Query Templates

Use these templates with LexGraph Neo4j MCP read-only tools or a local read-only runner. Keep queries aggregate-oriented and below the 80-second planning target.

## Parameters

```json
{
  "target_parts": ["2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "13", "14"],
  "parts_requiring_reprobe": ["2", "3", "4", "6", "13", "14"]
}
```

## Target UnifiedRule inventory

```cypher
MATCH (r:UnifiedRule)
WHERE r.rule_number IS NOT NULL
  AND any(p IN $target_parts WHERE toString(r.rule_number) STARTS WITH p + '.')
RETURN split(toString(r.rule_number),'.')[0] AS part,
       count(r) AS unified_rules
ORDER BY toInteger(part)
```

## Part 12 exclusion

```cypher
MATCH (r:UnifiedRule)
WHERE r.rule_number IS NOT NULL
  AND toString(r.rule_number) STARTS WITH '12.'
OPTIONAL MATCH (r)-[rel]->(n:ARCWriteCandidate)
WHERE type(rel) IN [
  'HAS_INTERPRETIVE_ISSUE',
  'HAS_PATHWAY',
  'HAS_CONFLICT_SIGNAL',
  'HAS_MANUAL_VALIDATION_TASK',
  'HAS_DISCARD_LEDGER_ENTRY'
]
RETURN count(DISTINCT r) AS part12_unified_rules,
       count(DISTINCT n) AS part12_arc_write_candidates,
       count(rel) AS part12_arc_anchor_rels
```

## Canonical ARC labels

```cypher
MATCH (n:ARCWriteCandidate)
WITH n, labels(n) AS labels
UNWIND labels AS label
WITH label, count(*) AS count
WHERE label STARTS WITH 'ARC'
RETURN label, count
ORDER BY label
```

## Canonical ARC relationships

```cypher
MATCH (a)-[rel]-(b)
WHERE any(x IN labels(a) WHERE x STARTS WITH 'ARC')
   OR any(x IN labels(b) WHERE x STARTS WITH 'ARC')
RETURN type(rel) AS rel_type, count(*) AS rels
ORDER BY rel_type
```

## Direct pathway traversal

```cypher
MATCH (r:UnifiedRule)-[:HAS_PATHWAY]->(p:ARCProceduralPathway)
WHERE r.rule_number IS NOT NULL
  AND any(x IN $target_parts WHERE toString(r.rule_number) STARTS WITH x + '.')
RETURN split(toString(r.rule_number),'.')[0] AS part,
       count(DISTINCT p) AS pathways
ORDER BY toInteger(part)
```

## Same-rule anchor check

```cypher
MATCH (p:ARCProceduralPathway:ARCWriteCandidate)
WITH p,
     coalesce(p.resolved_rule_number, p.rule_number, p.rule, p.subrule) AS pathway_rule
WHERE pathway_rule IS NOT NULL
OPTIONAL MATCH (r:UnifiedRule)-[:HAS_PATHWAY]->(p)
RETURN pathway_rule,
       count(DISTINCT p) AS pathways,
       count(DISTINCT r) AS unified_rule_anchors,
       collect(DISTINCT r.rule_number)[0..5] AS sample_anchors
ORDER BY pathway_rule
```

## Duplicate UnifiedRule anchors

```cypher
MATCH (r:UnifiedRule)
WHERE r.rule_number IS NOT NULL
  AND any(p IN $parts_requiring_reprobe WHERE toString(r.rule_number) STARTS WITH p + '.')
WITH r.rule_number AS rule_number, count(r) AS c, collect(r.uid)[0..10] AS sample_uids
WHERE c > 1
RETURN rule_number, c, sample_uids
ORDER BY rule_number
```

## RuleProvision fallback risk

```cypher
MATCH (p:ARCProceduralPathway:ARCWriteCandidate)
WHERE any(x IN $target_parts WHERE coalesce(p.resolved_rule_number, p.rule_number, p.rule, '') STARTS WITH x + '.')
OPTIONAL MATCH (u:UnifiedRule)-[:HAS_PATHWAY]->(p)
OPTIONAL MATCH (rp:RuleProvision)-[:HAS_PATHWAY]->(p)
RETURN count(DISTINCT p) AS pathways,
       count(DISTINCT u) AS unified_rule_anchored,
       count(DISTINCT rp) AS rule_provision_anchored
```

## Internal UnifiedRule text alignment sample

```cypher
MATCH (r:UnifiedRule)-[:HAS_PATHWAY]->(p:ARCProceduralPathway)
WHERE r.rule_number IS NOT NULL
  AND any(x IN $target_parts WHERE toString(r.rule_number) STARTS WITH x + '.')
RETURN r.rule_number AS rule_number,
       coalesce(r.title, r.rule_title) AS rule_title,
       substring(coalesce(r.text, r.rule_text, r.body, r.content, ''), 0, 600) AS internal_rule_excerpt,
       coalesce(
         p.safe_formulation,
         p.proposed_legal_statement,
         p.candidate_answer_requirement,
         p.pathway_condition,
         p.trigger
       ) AS pathway_formulation
LIMIT 50
```

## Minimum pathway field integrity

```cypher
MATCH (r:UnifiedRule)-[:HAS_PATHWAY]->(p:ARCProceduralPathway)
WHERE r.rule_number IS NOT NULL
  AND any(x IN $target_parts WHERE toString(r.rule_number) STARTS WITH x + '.')
RETURN split(toString(r.rule_number),'.')[0] AS part,
       count(p) AS pathways,
       sum(CASE WHEN p.uid IS NULL THEN 1 ELSE 0 END) AS missing_uid,
       sum(CASE WHEN p.migration_id IS NULL THEN 1 ELSE 0 END) AS missing_migration_id,
       sum(CASE WHEN p.write_allowed <> false THEN 1 ELSE 0 END) AS not_candidate_only,
       sum(CASE WHEN coalesce(p.trigger, p.pathway_condition, p.candidate_answer_requirement, p.safe_formulation, p.proposed_legal_statement) IS NULL THEN 1 ELSE 0 END) AS missing_legal_operation_field
ORDER BY toInteger(part)
```

## Authority status

```cypher
MATCH (r:UnifiedRule)-[:HAS_PATHWAY]->(p:ARCProceduralPathway)
WHERE r.rule_number IS NOT NULL
  AND any(x IN $target_parts WHERE toString(r.rule_number) STARTS WITH x + '.')
OPTIONAL MATCH (p)-[:HAS_AUTHORITY_STATUS]->(a:ARCAuthorityStatus)
RETURN split(toString(r.rule_number),'.')[0] AS part,
       count(DISTINCT p) AS pathways,
       count(DISTINCT a) AS authority_status_nodes,
       count(DISTINCT CASE WHEN a IS NULL THEN p END) AS pathways_without_authority_status,
       collect(DISTINCT coalesce(p.authority_grade, a.grade, a.status))[0..10] AS sample_grades
ORDER BY toInteger(part)
```

## Phase-B leakage

```cypher
MATCH (h:ARCCasePathwayHolding)
RETURN count(h) AS case_pathway_holdings
```

```cypher
MATCH ()-[rel:SUPPORTS_PATHWAY_HOLDING]-()
RETURN count(rel) AS supports_pathway_holding_rels
```

```cypher
MATCH ()-[rel:CITES_PATHWAY_HOLDING]-()
RETURN count(rel) AS cites_pathway_holding_rels
```

## Manual validation task matrix

```cypher
MATCH (r:UnifiedRule)-[:HAS_MANUAL_VALIDATION_TASK]->(t:ARCManualValidationTask)
WHERE r.rule_number IS NOT NULL
  AND any(x IN $target_parts WHERE toString(r.rule_number) STARTS WITH x + '.')
RETURN split(toString(r.rule_number),'.')[0] AS part,
       coalesce(t.task_type, t.type, t.category, '<uncategorized>') AS task_type,
       count(t) AS tasks
ORDER BY toInteger(part), task_type
```

## Discard ledger

```cypher
MATCH (r:UnifiedRule)-[:HAS_DISCARD_LEDGER_ENTRY]->(d:ARCDiscardLedgerEntry)
WHERE r.rule_number IS NOT NULL
  AND any(x IN $target_parts WHERE toString(r.rule_number) STARTS WITH x + '.')
RETURN split(toString(r.rule_number),'.')[0] AS part,
       count(d) AS discard_entries,
       sum(CASE WHEN coalesce(d.reason, d.discard_reason, d.notes) IS NULL THEN 1 ELSE 0 END) AS missing_reason
ORDER BY toInteger(part)
```

## Companion rules

```cypher
MATCH (r:UnifiedRule)-[rel:REFERENCES_COMPANION_RULE]->(c:UnifiedRule)
WHERE r.rule_number IS NOT NULL
  AND any(x IN $target_parts WHERE toString(r.rule_number) STARTS WITH x + '.')
RETURN split(toString(r.rule_number),'.')[0] AS source_part,
       count(rel) AS companion_edges,
       count(DISTINCT c) AS distinct_companion_rules,
       sum(CASE WHEN c.rule_number IS NULL THEN 1 ELSE 0 END) AS missing_target_rule_number
ORDER BY toInteger(source_part)
```
