#!/usr/bin/env python3
"""Validate an ARC Rule text-reconciliation packet without graph access.

New packets must carry exact scope/review hashes. When three_book_mode=REQUIRED,
a separately validated three-book gate artifact must be hash-bound into the packet.
This script validates structure/hash bindings; it does not certify current law.
"""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from pathlib import Path

HEX64 = re.compile(r"^[0-9a-f]{64}$")
THREE_BOOK_MODES = {"REQUIRED", "OPTIONAL_CORROBORATION", "NOT_APPLICABLE"}

def sha256_text(v:str)->str: return hashlib.sha256(v.encode('utf-8')).hexdigest()
def fail(msg:str)->None:
    print(f"FAIL: {msg}", file=sys.stderr); raise SystemExit(1)
def valid_hash(v)->bool: return isinstance(v,str) and bool(HEX64.fullmatch(v))
def require_hash(v,label):
    if not valid_hash(v): fail(f"{label} must be present lowercase SHA-256 hex")
def optional_hash(v,label):
    if v is not None and not valid_hash(v): fail(f"{label} must be lowercase SHA-256 hex")

def main()->None:
    ap=argparse.ArgumentParser(); ap.add_argument('packet',type=Path)
    ap.add_argument('--three-book-gate',type=Path)
    ap.add_argument('--expected-count',type=int); ap.add_argument('--expected-reviewed-count',type=int)
    args=ap.parse_args(); data=json.loads(args.packet.read_text(encoding='utf-8'))
    rows=data.get('rows'); holds=data.get('holds',[]); neg=data.get('negative_controls',[])
    if not isinstance(rows,list): fail('rows must be a list')
    if not isinstance(holds,list): fail('holds must be a list when present')
    if not isinstance(neg,list): fail('negative_controls must be a list when present')
    cc,hc=len(rows),len(holds); rc=cc+hc
    if args.expected_count is not None and cc!=args.expected_count: fail(f'expected {args.expected_count} candidate rows, found {cc}')
    if args.expected_reviewed_count is not None and rc!=args.expected_reviewed_count: fail(f'expected {args.expected_reviewed_count} reviewed rows, found {rc}')
    names=[]; uids=[]
    for i,row in enumerate(rows,1):
        for k in ('name','uid','candidate_text','candidate_text_len','candidate_text_sha256','before_text_sha256','full_text_sha256'):
            if k not in row: fail(f'candidate row {i} missing {k}')
        if row.get('decision')!='TEXT_REPAIR_CANDIDATE': fail(f'candidate row {i} decision is not TEXT_REPAIR_CANDIDATE')
        text=row['candidate_text']
        if not isinstance(text,str) or not text: fail(f'candidate row {i} candidate_text must be non-empty text')
        if len(text)!=row['candidate_text_len']: fail(f'candidate row {i} candidate_text_len mismatch')
        if sha256_text(text)!=row['candidate_text_sha256']: fail(f'candidate row {i} candidate_text_sha256 mismatch')
        for k in ('before_text_sha256','full_text_sha256','candidate_text_sha256'): require_hash(row.get(k),f'candidate row {i} {k}')
        optional_hash(row.get('vector_sha256'),f'candidate row {i} vector_sha256')
        names.append(row['name']); uids.append(row['uid'])
    for i,row in enumerate(holds,1):
        if 'uid' not in row: fail(f'hold row {i} missing uid')
        name=row.get('name') or row.get('rule')
        if not name: fail(f'hold row {i} missing name/rule')
        if not row.get('decision') or row.get('decision')=='TEXT_REPAIR_CANDIDATE': fail(f'hold row {i} must have a closed non-candidate decision')
        for k in ('text_sha256','before_text_sha256','full_text_sha256','vector_sha256'): optional_hash(row.get(k),f'hold row {i} {k}')
        names.append(str(name)); uids.append(row['uid'])
    for i,row in enumerate(neg,1):
        if 'uid' not in row: fail(f'negative control row {i} missing uid')
        name=row.get('name') or row.get('rule')
        if not name: fail(f'negative control row {i} missing name/rule')
        if not row.get('exclusion_reason'): fail(f'negative control row {i} missing exclusion_reason')
        names.append(str(name)); uids.append(row['uid'])
    if len(set(names))!=len(names): fail('duplicate Rule names across candidates/holds/negative_controls')
    if len(set(uids))!=len(uids): fail('duplicate Rule UIDs across candidates/holds/negative_controls')
    scope=data.get('scope',{}); reviewed=data.get('reviewed_scope',{}); hold_scope=data.get('hold_scope',{}); neg_scope=data.get('negative_control_scope',{})
    if scope.get('count') is not None and scope['count']!=cc: fail('scope.count mismatch')
    require_hash(scope.get('ordered_name_uid_sha256'),'scope.ordered_name_uid_sha256')
    if scope.get('topology_sha256') is not None:
        require_hash(scope.get('topology_sha256'),'scope.topology_sha256')
        if not scope.get('topology_canonicalizer_id') or not scope.get('topology_canonicalizer_version'): fail('topology canonicalizer id/version required when topology hash is present')
    if reviewed.get('count') is not None and reviewed['count']!=rc: fail('reviewed_scope.count mismatch')
    require_hash(reviewed.get('ordered_name_uid_sha256'),'reviewed_scope.ordered_name_uid_sha256')
    if hold_scope.get('count') is not None and hold_scope['count']!=hc: fail('hold_scope.count mismatch')
    if neg_scope.get('count') is not None and neg_scope['count']!=len(neg): fail('negative_control_scope.count mismatch')
    summary=data.get('summary',{})
    if summary.get('repair_candidates') is not None and summary['repair_candidates']!=cc: fail('summary.repair_candidates mismatch')
    for k in ('already_repaired_holds','hold_count','holds'):
        if isinstance(summary.get(k),int) and summary[k]!=hc: fail(f'summary.{k} mismatch')

    mode=data.get('three_book_mode','NOT_APPLICABLE')
    if mode not in THREE_BOOK_MODES: fail(f'three_book_mode must be one of {sorted(THREE_BOOK_MODES)}')
    gate=data.get('three_book_gate')
    if mode=='REQUIRED' and not isinstance(gate,dict): fail('three_book_gate object required when three_book_mode=REQUIRED')
    if gate is not None:
        if not isinstance(gate,dict): fail('three_book_gate must be an object')
        require_hash(gate.get('sha256'),'three_book_gate.sha256')
        for k in ('result','version_identity','source_registry_sha256','normalization_profile_sha256'):
            if not gate.get(k): fail(f'three_book_gate.{k} must be non-empty')
        require_hash(gate.get('source_registry_sha256'),'three_book_gate.source_registry_sha256')
        require_hash(gate.get('normalization_profile_sha256'),'three_book_gate.normalization_profile_sha256')
        if gate.get('version_identity')=='VERSION_IDENTITY_UNRESOLVED' and cc:
            fail('repair candidates prohibited while three-book version identity is unresolved')
        if args.three_book_gate:
            actual=hashlib.sha256(args.three_book_gate.read_bytes()).hexdigest()
            if actual!=gate['sha256']: fail('three_book_gate.sha256 does not match supplied gate artifact')
        elif mode=='REQUIRED':
            fail('--three-book-gate artifact required to verify REQUIRED gate hash binding')
    elif args.three_book_gate:
        fail('--three-book-gate supplied but packet has no three_book_gate binding')
    for flag in ('production_authorized','current_law_certified','court_facing_approved','filing_ready'):
        if data.get(flag) is True: fail(f'{flag} must not be true in source reconciliation')
    print(json.dumps({'ok':True,'candidate_count':cc,'hold_count':hc,'reviewed_count':rc,'negative_control_count':len(neg),'three_book_mode':mode,'packet_sha256':hashlib.sha256(args.packet.read_bytes()).hexdigest()},indent=2))
if __name__=='__main__': main()
