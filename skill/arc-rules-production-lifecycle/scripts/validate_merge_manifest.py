#!/usr/bin/env python3
"""Validate the ARC merge disposition manifest against the packaged skill tree.

Optionally verify the three original source ZIP hashes when those paths are supplied.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--manifest',type=Path,default=ROOT/'references/merge-manifest.json'); ap.add_argument('--semantic-zip',type=Path); ap.add_argument('--pipeline-zip',type=Path); ap.add_argument('--remediation-zip',type=Path); a=ap.parse_args()
    d=json.loads(a.manifest.read_text(encoding='utf-8')); errors=[]
    if d.get('schema_version')!='arc-merge-manifest-v2': errors.append('wrong schema_version')
    entries=d.get('entries',[])
    if not isinstance(entries,list) or not entries: errors.append('entries missing')
    seen=set()
    for i,e in enumerate(entries):
        key=(e.get('source_package'),e.get('source_path'))
        if key in seen: errors.append(f'duplicate source entry {key}')
        seen.add(key)
        if not e.get('disposition'): errors.append(f'entry {i} missing disposition')
        if e.get('disposition')=='UNRESOLVED_DISPOSITION': errors.append(f'unresolved disposition {key}')
        for fp in e.get('final_paths',[]):
            p=ROOT/fp
            if not p.exists(): errors.append(f'entry {i} target missing: {fp}'); continue
            if e.get('disposition') in {'RETAINED_IDENTICAL','PRESERVED_INACTIVE_PROVENANCE'} and sha(p)!=e.get('source_sha256'):
                errors.append(f'entry {i} claimed identical but hash differs: {fp}')
    if d.get('unresolved_count')!=sum(1 for e in entries if e.get('disposition')=='UNRESOLVED_DISPOSITION'):
        errors.append('unresolved_count mismatch')
    zmap={'semantic':a.semantic_zip,'pipeline':a.pipeline_zip,'remediation':a.remediation_zip}
    expected={x['id']:x for x in d.get('source_packages',[])}
    for sid,p in zmap.items():
        if p:
            if sid not in expected: errors.append(f'no expected source package {sid}')
            elif sha(p)!=expected[sid].get('sha256'): errors.append(f'{sid} source ZIP hash mismatch')
    print(json.dumps({'valid':not errors,'entry_count':len(entries),'errors':errors},indent=2)); return 0 if not errors else 1
if __name__=='__main__': sys.exit(main())
