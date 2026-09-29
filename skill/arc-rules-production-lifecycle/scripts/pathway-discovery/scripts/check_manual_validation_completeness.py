#!/usr/bin/env python3
"""Validate completeness of the governed ARC pathway manual-validation TSV."""
from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
REQUIRED_COLUMNS=['candidate_id','pathway_uid','case_name','neutral_citation','canlii_url','official_source_url','case_exists_publicly','paragraphs_confirmed','quoted_text_confirmed','case_status_checked','appeal_history_checked','negative_treatment_checked','authority_level_confirmed','current_rule_text_confirmed','source_material_classified','use_purpose_classified','same_or_related_action_classified','privilege_screen_complete','non_party_privacy_screen_complete','sealed_or_restricted_access_checked','verified_by','verified_date','notes']
CORE_TRUE=['case_exists_publicly','paragraphs_confirmed','quoted_text_confirmed','case_status_checked','appeal_history_checked','negative_treatment_checked','authority_level_confirmed','current_rule_text_confirmed','source_material_classified','use_purpose_classified']
CONTEXT_TRUE_OR_NA=['same_or_related_action_classified','privilege_screen_complete','non_party_privacy_screen_complete','sealed_or_restricted_access_checked']
def true(v): return str(v).strip().lower() in {'yes','true','1','complete','confirmed','verified'}
def ok_or_na(v): return true(v) or str(v).strip().lower() in {'n/a','na','not_applicable','not applicable'}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('ledger',type=Path); a=ap.parse_args()
    with a.ledger.open(encoding='utf-8',newline='') as f: rdr=csv.DictReader(f,delimiter='\t'); cols=rdr.fieldnames or []; rows=list(rdr)
    errors=[]; missing_cols=[c for c in REQUIRED_COLUMNS if c not in cols]
    if missing_cols: errors.append('missing required columns: '+', '.join(missing_cols))
    if not rows: errors.append('manual validation ledger has no rows')
    for i,r in enumerate(rows,2):
        for f in ('candidate_id','pathway_uid','case_name','neutral_citation','canlii_url','official_source_url','verified_by','verified_date'):
            if not str(r.get(f,'')).strip(): errors.append(f'row {i}: missing {f}')
        for f in CORE_TRUE:
            if not true(r.get(f,'')): errors.append(f'row {i}: {f} not confirmed')
        for f in CONTEXT_TRUE_OR_NA:
            if not ok_or_na(r.get(f,'')): errors.append(f'row {i}: {f} must be confirmed or explicit N/A')
    report={'total_cases':len(rows),'valid':not errors,'status':'complete' if not errors else 'incomplete','error_count':len(errors),'errors':errors}; print(json.dumps(report,indent=2)); return 0 if not errors else 1
if __name__=='__main__': sys.exit(main())
