#!/usr/bin/env python3
"""Run active-pathway component self-tests for the merged ARC lifecycle skill."""
from __future__ import annotations
import hashlib,json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PY=sys.executable
FIX=ROOT/'tests/fixtures/sample_candidate_packet_minimal.json'

def run(cmd,expect=True):
    p=subprocess.run(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    ok=p.returncode==0; passed=ok if expect else not ok
    return {'cmd':[str(x) for x in cmd],'returncode':p.returncode,'expected_success':expect,'passed':passed,'stdout':p.stdout[-500:],'stderr':p.stderr[-500:]}

def main():
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); manual=td/'manual.tsv'; discard=td/'discard.tsv'; ledger=td/'no_write.json'; conflict=td/'conflict.tsv'
        fp=hashlib.sha256(b'fixture-source').hexdigest()
        good=[
            [PY,'scripts/validate_candidate_packet.py','tests/fixtures/sample_candidate_packet_minimal.json'],
            [PY,'scripts/check_graph_relationship_allowlist.py','tests/fixtures/sample_candidate_packet_minimal.json'],
            [PY,'scripts/build_manual_validation_ledger.py','tests/fixtures/sample_candidate_packet_minimal.json','--out',str(manual)],
            [PY,'scripts/build_discard_ledger.py','--out',str(discard)],
            [PY,'scripts/build_no_write_ledger.py','--rule','5.33','--canonical-rule-uid','UnifiedRule|5.33','--candidate-packet',str(FIX),'--database','neo4j','--source-fingerprint',fp,'--out',str(ledger)],
            [PY,'scripts/check_public_verification_status.py','tests/fixtures/sample_candidate_packet_minimal.json'],
            [PY,'scripts/build_conflict_matrix.py','tests/fixtures/sample_candidate_packet_minimal.json','--out',str(conflict)],
        ]
        results=[run(c,True) for c in good]
        if results[-3]['passed']:
            results.append(run([PY,'scripts/verify_no_write_ledger.py',str(ledger),'--candidate-packet',str(FIX)],True))
        bad=[
            [PY,'scripts/validate_candidate_packet.py','tests/fixtures/sample_bad_packet_missing_case_ladder.json'],
            [PY,'scripts/validate_candidate_packet.py','tests/fixtures/sample_bad_packet_write_status.json'],
            [PY,'scripts/check_graph_relationship_allowlist.py','tests/fixtures/sample_relationship_allowlist_violation.json'],
        ]
        results += [run(c,False) for c in bad]
    report={'tests_run':len(results),'passed':sum(1 for r in results if r['passed']),'failed':[r for r in results if not r['passed']]}
    print(json.dumps(report,indent=2)); return 0 if not report['failed'] else 1
if __name__=='__main__': raise SystemExit(main())
