#!/usr/bin/env python3
"""Validate a three-book ARC source-gate artifact. Structural/provenance validation only."""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
HEX64=re.compile(r'^[0-9a-f]{64}$')
MODES={'REQUIRED','OPTIONAL_CORROBORATION'}
ROLES={'FIRST_HAND_RULE_CARRIER','OFFICIAL_REPRODUCTION','ANNOTATED_RULES','SECONDARY_COMMENTARY','DERIVED_COPY','UNKNOWN'}
VERSIONS={'SAME_VERSION_PROVEN','LEGITIMATE_VERSION_DIFFERENCE','VERSION_IDENTITY_UNRESOLVED'}
RESULTS={'THREE_BOOK_SOURCE_RECONCILED','THREE_BOOK_VERSION_DIFFERENCE_EXPLAINED','STALE_CORROBORATOR_RECONCILED','SOURCE_CARRIER_DEFECT_INDEPENDENTLY_CLOSED','THREE_BOOK_RECONCILIATION_HOLD'}
def h(v): return isinstance(v,str) and bool(HEX64.fullmatch(v))
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('gate',type=Path); args=ap.parse_args(); d=json.loads(args.gate.read_text(encoding='utf-8')); e=[]
    if d.get('schema_version')!='arc-three-book-gate-v1': e.append('schema_version must be arc-three-book-gate-v1')
    if d.get('three_book_mode') not in MODES: e.append('three_book_mode must be REQUIRED or OPTIONAL_CORROBORATION')
    for k in ('rule_identity','source_registry_sha256','normalization_profile','version_identity','result'):
        if k not in d: e.append(f'missing {k}')
    if not h(d.get('source_registry_sha256')): e.append('source_registry_sha256 must be 64 lowercase hex')
    norm=d.get('normalization_profile',{})
    if not isinstance(norm,dict) or not all(str(norm.get(k,'')).strip() for k in ('id','version')) or not h(norm.get('sha256')): e.append('normalization_profile requires id, version, sha256')
    vi=d.get('version_identity')
    if vi not in VERSIONS: e.append(f'version_identity must be one of {sorted(VERSIONS)}')
    result=d.get('result')
    if result not in RESULTS: e.append(f'result must be one of {sorted(RESULTS)}')
    carriers=d.get('carriers')
    if not isinstance(carriers,dict): e.append('carriers must be an object'); carriers={}
    required_ids=d.get('required_carriers',[])
    if not isinstance(required_ids,list): e.append('required_carriers must be a list'); required_ids=[]
    if d.get('three_book_mode')=='REQUIRED' and not required_ids: e.append('REQUIRED mode requires required_carriers')
    origins=[]
    for cid,c in carriers.items():
        if not isinstance(c,dict): e.append(f'carrier {cid} must be object'); continue
        for k in ('carrier_id','artifact_sha256','text_sha256','source_role','origin_id','locator'):
            if not c.get(k): e.append(f'carrier {cid} missing {k}')
        if c.get('carrier_id')!=cid: e.append(f'carrier {cid} carrier_id mismatch')
        if not h(c.get('artifact_sha256')): e.append(f'carrier {cid} artifact_sha256 invalid')
        if not h(c.get('text_sha256')): e.append(f'carrier {cid} text_sha256 invalid')
        if c.get('source_role') not in ROLES: e.append(f'carrier {cid} source_role invalid')
        if c.get('origin_id'): origins.append(c['origin_id'])
    for cid in required_ids:
        if cid not in carriers: e.append(f'required carrier missing: {cid}')
    if result!='THREE_BOOK_RECONCILIATION_HOLD':
        if vi=='VERSION_IDENTITY_UNRESOLVED': e.append('non-hold result prohibited when version identity unresolved')
        for cid in required_ids:
            c=carriers.get(cid,{})
            if c.get('source_role')=='UNKNOWN': e.append(f'required carrier {cid} source_role UNKNOWN requires hold')
    independent=len(set(origins))
    if 'independent_origin_count' in d and d.get('independent_origin_count')!=independent: e.append('independent_origin_count mismatch')
    out={'valid':not e,'errors':e,'independent_origin_count':independent}
    print(json.dumps(out,indent=2)); return 0 if not e else 1
if __name__=='__main__': sys.exit(main())
