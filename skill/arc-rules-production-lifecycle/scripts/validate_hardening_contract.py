#!/usr/bin/env python3
"""Fail-closed static check that remediation hardening remains encoded after skill consolidation."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
CHECKS={
  'SKILL.md':[
    'Stage C and Stage D are always separate nudges',
    'G4F footprint equality','G4H payload binding','G4L operation-enforced batch bound','G4D verifier discrimination',
    'topology canonicalizer ID/version','null-safe preimage equality','mirrored atomic-preimage eligibility',
    'Stale-vector-only invalidation','Receipt-governance defects','negative temporal or identity controls',
  ],
  'references/text-remediation-control-plane.md':[
    'G4F footprint equality','G4H payload binding','G4L operation-enforced batch bound','G4D verifier discrimination',
    'null-safe equality','mirrored atomic-preimage eligibility','topology hash plus canonicalizer ID/version',
    'recertify B',
  ],
  'references/workflow-state-machine.md':[
    'STALE_VECTOR_INVALIDATION_OPERATOR_GREEN_NO_DOMAIN_WRITE','RECEIPT_METADATA_REPAIR_OPERATOR_GREEN_NO_DOMAIN_WRITE','authorization becomes consumed','canonicalizer ID/version',
  ],
  'references/packet-contracts.md':[
    'Nullable preimage and atomic-eligibility contract','Stale-vector-only invalidation packet','Denominator and negative-control contract','Receipt-metadata correction contract','exact receipt `phase`',
  ],
  'references/failure-modes.md':[
    'Neo4j nullable equality can reject a correct preimage','High-level guard parity does not prove APPLY eligibility','Started APPLY consumes the one-time authorization','Topology hashes require canonicalizer identity','Receipt phase/stage/campaign is part of the postimage','Wrapper specialization can leak base receipt metadata','Stale-vector-only remediation is not text repair','Repealed controls are not denominator rows','Registration arguments are part of the executable contract',
  ],
  'references/output-contract.md':['Stale-vector-only invalidation closeout','Receipt-metadata correction closeout'],
  'references/concurrency-and-closure.md':['negative-control exclusion is not current-law certification'],
  'references/adversarial-replay-matrix.md':['AR-01','AR-10','AR-14','all frozen fixtures'],
  'scripts/run_adversarial_replay.py':['integrated_positive','authorization_reuse','topology_fingerprint','registry_required_args'],
}
def main():
    missing=[]
    for rel,needles in CHECKS.items():
        p=ROOT/rel
        if not p.exists(): missing.append({'file':rel,'required':'file exists'}); continue
        text=p.read_text(encoding='utf-8')
        for n in needles:
            if n not in text: missing.append({'file':rel,'required':n})
    result={'ok':not missing,'check_file_count':len(CHECKS),'missing':missing}
    print(json.dumps(result,indent=2)); return 0 if result['ok'] else 1
if __name__=='__main__': sys.exit(main())
