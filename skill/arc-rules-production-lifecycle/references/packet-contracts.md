# Packet Contracts

## Contents

- Source reconciliation JSON
- Pre-write manifest
- Reviewed packet
- Rollback contract
- Owner authorization
- Receipt
- Independent verification JSON

## Source reconciliation JSON

Minimum top-level fields:

- `schema`
- `batch_id`
- `database`
- `mode`
- parent manifest/closeout hashes
- `scope.count`
- `scope.ordered_name_uid_sha256`
- source authority/baseline information
- normalization contract
- source-property mutation decision
- summary counts
- `rows`
- optional/declared `holds`
- next state
- governance booleans

A reconciliation with `rows: []` is valid when every reviewed row is a closed hold. Never convert zero counts to sentinels.

Each candidate row should contain:

- ordinal
- Rule name
- exact UID
- existing `source`
- defect class
- prior text length/hash
- `full_text` length/hash
- exact candidate text
- candidate length/hash
- source-comparison basis
- decision `TEXT_REPAIR_CANDIDATE`

Each hold row should freeze exact identity, live text/source/full_text preimages, closed hold reason, and external migration/receipt identity when applicable.

When three-book mode is active, bind the exact Book A source package plus Book B/C artifact paths/hashes or a separate three-book gate path/hash.

## Pre-write manifest

Freeze:

- database
- exact target UIDs/names/order
- exact count and authorized max count
- ordered name+UID hash
- target topology hash
- topology canonicalizer ID/version used to produce the hash
- source-reconciliation path/hash
- required three-book gate path/hash when active
- migration ID
- operator name/version and specialization/wrapper SHA
- permitted mutation footprint
- prohibited mutation footprint, including explicit hold rows
- receipt contract
- rollback contract path/hash
- production/current-law/court-facing/filing flags false

## Reviewed packet

For every row freeze:

- exact target identity
- prior text and prior hash/length
- expected `source`
- expected `full_text` hash
- candidate text and candidate hash/length
- expected stale vector hash/dimension **per row** when invalidation is in scope
- expected tracked embedding metadata **per row**
- expected topology fingerprint/binding plus canonicalizer ID/version

Bind packet to the manifest and source reconciliation by SHA-256.

Do not assume one shared vector family across the tranche. A shared contract may be referenced only when it reconstructs the exact prior vector value; any exceptional row needs its own frozen vector preimage.

## Rollback contract

Rollback must be self-contained. Store the exact prior text, exact target UID, and exact prior vector/metadata state required to restore the preimage.

A rollback contract containing only hashes is insufficient if the prior value cannot be reconstructed deterministically.

For vectors, either store the exact prior value directly or bind to an immutable contract/artifact containing the exact bytes/value. Never regenerate a rollback vector from model inference.

Restrict rollback to properties changed by APPLY. Do not widen rollback into unrelated graph cleanup.

## Owner authorization

Use a one-time file bound to the exact frozen scope. Suggested fields:

- schema/version
- database
- migration ID
- operation/version
- manifest SHA
- packet SHA
- reconciliation SHA
- rollback SHA
- expected count
- authorized maximum count
- action `APPLY`
- `authorized: true`
- non-empty authority reference to the user's current instruction
- `embedding_generation_authorized: false`
- higher-use flags false

Any owner-authorized APPLY attempt that actually starts consumes this artifact, even if later recovery proves `NOT_COMMITTED`. Never reuse it for a retry.

Do not reuse an authorization for another migration or tranche. Platform execution acknowledgements are not substitutes for this artifact.

## Receipt

Require exactly one receipt for the migration. Prefer fields including:

- migration ID
- operation
- operation version
- status
- verification state
- manifest SHA
- reviewed packet SHA
- reconciliation SHA
- rollback SHA
- authorization SHA
- expected count and maximum count
- applied count
- exact receipt `phase` and any declared stage/campaign identity
- topology canonicalizer ID/version when topology is receipt-bound
- `embedding_regeneration_authorized=false`
- production/current-law/court-facing/filing-ready flags false

## Independent verification JSON

Record exact per-target postimages and invariant checks, not only aggregate counts. Include receipt readback, including exact `phase`/stage/campaign identity, topology canonicalizer ID/version, and regression result.

Stage C result artifacts may contain immediate safety readback, but the Stage D verification artifact must be created in the next nudge from a fresh independent read.


## Nullable preimage and atomic-eligibility contract

For every nullable Neo4j property in a guarded preimage:

- freeze whether the expected value is null or non-null;
- implement a null-safe equality predicate rather than relying on ordinary `=`;
- add negative controls for null-to-value and value-to-null drift where practical;
- expose a read-only atomic-preimage eligibility probe that mirrors the complete APPLY `MATCH`/`WHERE` predicate;
- require exact `N/N` eligible before Stage C authorization can be consumed.

A green high-level guard cannot substitute for this mirrored eligibility proof.

## Stale-vector-only invalidation packet

When text is already source-faithful and only stale vector state remains, freeze per row:

- exact Rule UID/name/order;
- immutable `text` hash/length, `source`, and `full_text` hash/length;
- exact stale vector value/hash/dimension if present;
- every tracked embedding metadata field, including explicit nulls;
- topology hash plus canonicalizer ID/version;
- external text-repair receipt/proof binding;
- mutation footprint limited to vector/metadata fields and this lane's receipt;
- rollback payload sufficient to restore exact prior vector/metadata without generating a new embedding.

## Denominator and negative-control contract

Freeze separately:

- `current_parent_denominator` exact names/UIDs/count/order/hash;
- `negative_controls` exact names/UIDs and exclusion reason (for example repealed temporal/identity control).

Negative controls must not appear in repair candidate rows. Their exclusion does not establish current-law correctness.

## Receipt-metadata correction contract

For a separately authorized governance correction to an existing receipt, freeze:

- exact target `MigrationRegistry` identity and count;
- exact before/after metadata value;
- all non-mutated receipt properties as immutable preimages;
- target receipt topology plus canonicalizer ID/version;
- a distinct corrective migration/receipt ID;
- permitted footprint restricted to the exact target metadata property plus the corrective receipt;
- rollback that restores the prior metadata value and marks, rather than deletes, the corrective audit receipt.
