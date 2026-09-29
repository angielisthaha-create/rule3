#!/usr/bin/env python3
"""Verify consistency and packet binding of an ARC no-write ledger; this is not independent graph proof."""
from __future__ import annotations
import argparse,hashlib,json,re,sys
from pathlib import Path
HEX64=re.compile(r'^[0-9a-f]{64}$')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('ledger',type=Path); ap.add_argument('--candidate-packet',type=Path); a=ap.parse_args(); d=json.loads(a.ledger.read_text(encoding='utf-8')); e=[]
    for f in ('run_id','canonical_rule_uid','candidate_packet_sha256','database','endpoint','tool_build','source_fingerprint','created_at'):
        if not str(d.get(f,'')).strip(): e.append(f'missing {f}')
    if d.get('graph_writes_performed') is not False: e.append('graph_writes_performed must be false')
    if str(d.get('write_mode','')).lower() not in {'none','read_only','no_write'}: e.append('write_mode must be none/read_only/no_write')
    if str(d.get('approval_status','')).lower() not in {'not_approved','candidate_only','manual_validation_required'}: e.append('approval_status must not imply write approval')
    if not HEX64.fullmatch(str(d.get('candidate_packet_sha256',''))): e.append('candidate_packet_sha256 invalid')
    if a.candidate_packet and hashlib.sha256(a.candidate_packet.read_bytes()).hexdigest()!=d.get('candidate_packet_sha256'): e.append('candidate_packet_sha256 does not match supplied packet')
    r={'valid':not e,'errors':e,'evidence_scope':'ledger_consistency_only_not_independent_graph_proof'}; print(json.dumps(r,indent=2)); return 0 if not e else 1
if __name__=='__main__': sys.exit(main())
