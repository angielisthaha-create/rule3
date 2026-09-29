#!/usr/bin/env python3
"""Check whether current/binding/verified pathway claims have required public-verification fields."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
REQ=['canlii_url','official_source_url','paragraphs_confirmed','quoted_text_confirmed','current_rule_text_confirmed','case_status_checked','negative_treatment_checked','verified_by','verified_date']
FINAL=('verified','current_law_verified','governing','filing_ready','binding_current')
def true(v): return str(v).strip().lower() in {'yes','true','1','complete','confirmed','verified'}
def final(o):
    blob=' '.join(str(o.get(k,'')).lower() for k in ('manual_status','manual_validation_status','current_status','authority_status','authority_level','filing_status'))
    if 'binding_current' in blob or 'current_law_verified' in blob or 'governing' in blob or 'filing_ready' in blob:
        return True
    return 'verified' in blob and 'needs' not in blob and 'possible' not in blob
def missing(o):
    out=[]
    for f in REQ:
        v=o.get(f)
        if f.endswith('_confirmed') or f.endswith('_checked'):
            if not true(v): out.append(f)
        elif not str(v or '').strip(): out.append(f)
    return out
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('packet',type=Path); a=ap.parse_args(); p=json.loads(a.packet.read_text(encoding='utf-8')); e=[]
    for i,path in enumerate(p.get('candidate_pathways',[])):
        pid=path.get('pathway_uid',f'pathway[{i}]')
        if final(path):
            m=missing(path)
            if m: e.append(f'{pid}: final/current authority status claimed without public fields: {m}')
        for j,c in enumerate(path.get('case_ladder',[])):
            if final(c):
                m=missing(c)
                if m: e.append(f'{pid}: case_ladder[{j}] final/current authority status claimed without public fields: {m}')
    print(json.dumps({'valid':not e,'errors':e},indent=2)); return 0 if not e else 1
if __name__=='__main__': sys.exit(main())
