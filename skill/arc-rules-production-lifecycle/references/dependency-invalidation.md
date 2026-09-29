# ARC Dependency Invalidation

## Principle

Reuse settled proof until a dependency that can affect it changes. Do not globally rebuild the corpus.

Represent each release-bearing object or qualification with fingerprints for the lower-layer inputs it depends on, such as:

```text
source/carrier -> operative text -> Rule/version -> pathway validity -> semantic qualification
-> production carrier -> retrieval eligibility
```

## Invalidation rules

If a lower-layer fingerprint changes:

1. identify directly dependent objects by exact IDs/lineage;
2. preserve historical objects and receipts;
3. mark only affected qualifications/releases/retrieval predicates stale or held;
4. block retrieval where the change can affect returned legal meaning or applicability;
5. create a bounded requalification queue with the changed fingerprint and reason;
6. rerun only predicates whose truth can change;
7. restore eligibility only after the new dependency chain closes.

Examples:

- Rule text correction can invalidate pathways, propositions, tests, deontic operators, burdens/exceptions/remedies, vectors, and retrieval decisions whose proof spans depended on changed wording.
- RuleVersion/temporal change can invalidate current-interval/applicability/retrieval predicates without invalidating unrelated historical source proof.
- Reader/registry repair normally invalidates reader/retrieval predicates, not already settled legal meaning.

A chat change, worker change, packet regeneration, or missing convenience artifact does not invalidate settled proof unless it changes a controlling dependency.
