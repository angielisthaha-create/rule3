#!/usr/bin/env python3
"""Create a packet-bound no-write run ledger for ARC pathway discovery."""
from __future__ import annotations
import argparse,hashlib,json,secrets
from datetime import datetime,timezone
from pathlib import Path
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--rule',required=True); ap.add_argument('--out',type=Path,required=True); ap.add_argument('--canonical-rule-uid',required=True); ap.add_argument('--candidate-packet',type=Path,required=True); ap.add_argument('--database',required=True); ap.add_argument('--endpoint',default='whitebox'); ap.add_argument('--tool-build',default='unknown'); ap.add_argument('--source-fingerprint',required=True); ap.add_argument('--candidate-pathways-created',type=int,default=0); ap.add_argument('--case-ladder-entries-created',type=int,default=0); ap.add_argument('--discarded-noise-count',type=int,default=0); a=ap.parse_args()
    now=datetime.now(timezone.utc); run_id=f"arc_rule_{a.rule.replace('.','_')}_no_write_{now.strftime('%Y%m%dT%H%M%S%fZ')}_{secrets.token_hex(4)}"; packet_sha=sha(a.candidate_packet)
    d={'schema_version':'arc-no-write-ledger-v2','run_id':run_id,'rule_number':a.rule,'write_mode':'none','graph_writes_performed':False,'approval_status':'not_approved','rules_checked':[a.rule],'canonical_rule_uid':a.canonical_rule_uid,'candidate_packet_path':str(a.candidate_packet),'candidate_packet_sha256':packet_sha,'database':a.database,'endpoint':a.endpoint,'tool_build':a.tool_build,'source_fingerprint':a.source_fingerprint,'candidate_pathways_created':a.candidate_pathways_created,'case_ladder_entries_created':a.case_ladder_entries_created,'discarded_noise_count':a.discarded_noise_count,'manual_validation_required':True,'public_verification_required':True,'rollback_plan_required_before_write':True,'created_at':now.isoformat(),'created_by':'arc-rules-production-lifecycle'}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(d,indent=2),encoding='utf-8'); print(a.out); return 0
if __name__=='__main__': raise SystemExit(main())
