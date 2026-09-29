#!/usr/bin/env python3
"""Package ARC rule outputs after validation; default completed mode refuses draft/incomplete work."""
from __future__ import annotations
import argparse,subprocess,sys,zipfile
from pathlib import Path
REQ=['*pathway_report.md','*graph_candidate_packet.json','*manual_validation.tsv','*discard_ledger.tsv','*no_write_run_ledger.json','README.md']
def one(d,pat):
    xs=list(d.glob(pat)); return xs[0] if len(xs)==1 else None
def ok(cmd): return subprocess.run(cmd,capture_output=True,text=True).returncode==0
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--rule-dir',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); ap.add_argument('--mode',choices=['completed','handoff'],default='completed'); a=ap.parse_args(); d=a.rule_dir
    if not d.is_dir(): print(f'not a directory: {d}',file=sys.stderr); return 1
    miss=[p for p in REQ if not list(d.glob(p))]
    if miss: print('missing required files: '+', '.join(miss),file=sys.stderr); return 1
    cand=one(d,'*graph_candidate_packet.json'); manual=one(d,'*manual_validation.tsv'); ledger=one(d,'*no_write_run_ledger.json'); readme=d/'README.md'
    if not all((cand,manual,ledger,readme)): print('ambiguous/missing required singleton artifacts',file=sys.stderr); return 1
    here=Path(__file__).resolve().parent
    checks=[['python3',str(here/'validate_candidate_packet.py'),str(cand),'--json'],['python3',str(here/'check_graph_relationship_allowlist.py'),str(cand)],['python3',str(here/'check_public_verification_status.py'),str(cand)],['python3',str(here/'verify_no_write_ledger.py'),str(ledger),'--candidate-packet',str(cand)]]
    if a.mode=='completed': checks.append(['python3',str(here/'check_manual_validation_completeness.py'),str(manual)])
    for c in checks:
        if not ok(c): print('validation failed: '+' '.join(c),file=sys.stderr); return 1
    txt=readme.read_text(encoding='utf-8',errors='replace').lower()
    if a.mode=='completed' and any(x in txt for x in ('status: draft','status=draft','status: incomplete','status=incomplete')): print('README status is not completed',file=sys.stderr); return 1
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.out,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(d.rglob('*')):
            if p.is_file(): z.write(p,arcname=p.relative_to(d))
        z.writestr('_PACKAGE_MODE.txt',a.mode+'\n')
    print(a.out); return 0
if __name__=='__main__': raise SystemExit(main())
