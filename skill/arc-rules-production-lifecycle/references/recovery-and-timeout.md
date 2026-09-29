# Neo4j promotion recovery and timeout protocol

## Binding rule

A timeout means commit state is unknown. Do not retry the same write, run a global migration scan, or assume rollback is needed.

## Recovery sequence

1. Query the exact `IngestionBatch` or migration marker by its indexed identity.
2. Query each expected production label using exact UIDs or a bounded deterministic UID prefix.
3. Query the exact review-candidate cohort and terminal lifecycle fields.
4. Query the exact canary UID and its expected relationships.
5. Classify:
   - `NOT_COMMITTED`: no batch, production identities, or lifecycle changes.
   - `PARTIALLY_COMMITTED`: only a strict subset exists.
   - `COMMITTED_UNVERIFIED`: expected write surface exists but invariants are not yet closed.
   - `COMMITTED_VERIFIED`: all exact checks pass.
6. For partial state, execute exact-UID rollback in dependency order.
7. Replace the failed query with a narrower family-bounded transaction.

## Forbidden recovery shapes

Do not use:

```cypher
MATCH (n) WHERE n.migration_id = $migration
MATCH ({uid: $uid})
MATCH (n) RETURN n
```

Use labels and exact projections:

```cypher
MATCH (n:LegalProposition {migration_id: $migration})
RETURN n.uid
ORDER BY n.uid
LIMIT 100
```

When UID indexes are label-scoped, always include the correct label.

## Canary cleanup

Delete only the exact canary identities and relationships. Verify zero residue with exact UIDs. Never delete by a broad migration property after a failed or timed-out canary.

## Oversized writes

If one transaction exceeds the host wall-clock limit:

- do not repeat it;
- split by semantic family;
- create shared proof/proposition substrate first;
- use batched `UNWIND` or bounded cohort queries;
- verify after every family;
- retain one migration ID only if rollback and verification can still distinguish phases; otherwise use phase-specific IDs under one campaign.

## Import failures

If APOC or file import is unavailable, do not weaken security settings or improvise a new import path. Prefer direct candidate-cohort Cypher, registered scripts, or a bounded Whitebox execution route. Record the unavailable mechanism as a non-state-changing failure.

## Execution ledger fields

Record:

- query/phase name;
- migration ID;
- start/end timestamps;
- result or timeout;
- commit-state classification;
- exact recovery queries;
- recovered counts;
- rollback action;
- replacement query shape;
- final verification artifact hash.
