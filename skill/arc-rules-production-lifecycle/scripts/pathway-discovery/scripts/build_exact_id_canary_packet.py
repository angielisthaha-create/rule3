#!/usr/bin/env python3
"""Build a draft exact-ID canary packet using registry-resolved labels and relationship type."""
from __future__ import annotations
import argparse,hashlib,json,re
from pathlib import Path
IDENT=re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
def sha(t): return hashlib.sha256(t.encode('utf-8')).hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--migration-id',required=True); ap.add_argument('--source-rule-uid',required=True); ap.add_argument('--case-uid',required=True); ap.add_argument('--source-label',required=True); ap.add_argument('--target-label',required=True); ap.add_argument('--relationship-type',required=True); ap.add_argument('--source-uid',required=True); ap.add_argument('--target-uid',required=True); ap.add_argument('--paragraph-evidence',required=True); ap.add_argument('--registry-fingerprint',required=True); ap.add_argument('--out',type=Path,required=True); a=ap.parse_args()
    for n,v in [('source-label',a.source_label),('target-label',a.target_label),('relationship-type',a.relationship_type)]:
        if not IDENT.fullmatch(v): raise SystemExit(f'invalid registry-resolved {n}: {v}')
    q=f"MATCH (s:{a.source_label} {{uid:$source_uid}})-[r:{a.relationship_type}]->(t:{a.target_label} {{uid:$target_uid}}) WHERE r.migration_id=$migration_id RETURN count(r) AS rels"
    d={'packet_type':'legal_repair_canary_draft_only','execution_status':'draft_only_not_executable','migration_id':a.migration_id,'source_rule_uid':a.source_rule_uid,'case_uid':a.case_uid,'source_label':a.source_label,'target_label':a.target_label,'relationship_type':a.relationship_type,'source_uid':a.source_uid,'target_uid':a.target_uid,'paragraph_evidence':a.paragraph_evidence,'evidence_hash':sha(a.paragraph_evidence),'registry_fingerprint':a.registry_fingerprint,'human_approved':False,'repair_authorized':False,'expected_update_count':1,'rollback_plan':'remove only exact registry-resolved relationship between source_uid and target_uid with this migration id after verification','post_write_verification_query':q}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(d,indent=2),encoding='utf-8'); print(a.out); return 0
if __name__=='__main__': raise SystemExit(main())
