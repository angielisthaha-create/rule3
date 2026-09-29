#!/usr/bin/env python3
"""Integration/adversarial self-test for the merged ARC lifecycle skill."""
from __future__ import annotations
import copy,csv,hashlib,json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PY=sys.executable
BASE_MANIFEST=ROOT/'scripts/tests/manifest_candidate_envelope_valid.json'
BASE_CAND=ROOT/'scripts/pathway-discovery/tests/fixtures/sample_candidate_packet_minimal.json'
PD=ROOT/'scripts/pathway-discovery/scripts'

def run(cmd,expect=True,cwd=None):
    p=subprocess.run([str(x) for x in cmd],cwd=cwd or ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    ok=p.returncode==0; passed=ok if expect else not ok
    return {'cmd':[str(x) for x in cmd],'expect_success':expect,'returncode':p.returncode,'passed':passed,'stdout':p.stdout[-900:],'stderr':p.stderr[-900:]}

def writej(p,d): p.write_text(json.dumps(d,indent=2),encoding='utf-8')
def public_fields(o):
    o.update({'canlii_url':'https://example.invalid/case','official_source_url':'https://example.invalid/official','paragraphs_confirmed':True,'quoted_text_confirmed':True,'current_rule_text_confirmed':True,'case_status_checked':True,'negative_treatment_checked':True,'verified_by':'test','verified_date':'2026-09-28'})

def main():
    results=[]
    with tempfile.TemporaryDirectory() as tds:
        td=Path(tds)
        base=json.loads(BASE_MANIFEST.read_text(encoding='utf-8'))
        # valid manifest
        p=td/'valid_manifest.json'; writej(p,base); results.append(run([PY,ROOT/'scripts/validate_rule_manifest.py',p],True))
        # wrong stage names
        d=copy.deepcopy(base)
        for r in d['stage_ledger']: r['name']='WRONG_STAGE_NAME'
        p=td/'bad_names.json'; writej(p,d); results.append(run([PY,ROOT/'scripts/validate_rule_manifest.py',p],False))
        # impossible stage closure
        d=copy.deepcopy(base)
        for r in d['stage_ledger']:
            r['status']='PENDING'; r.pop('verification_artifact',None); r.pop('limitation',None)
        d['stage_ledger'][15].update({'status':'CLOSED_WITH_LIMITATIONS','verification_artifact':'x','limitation':'x'})
        p=td/'bad_transition.json'; writej(p,d); results.append(run([PY,ROOT/'scripts/validate_rule_manifest.py',p],False))
        # impossible auth
        d=copy.deepcopy(base); d['authorization']['issued']=False; d['authorization']['consumed']=True
        p=td/'bad_auth.json'; writej(p,d); results.append(run([PY,ROOT/'scripts/validate_rule_manifest.py',p],False))
        # missing governed ledger fields
        d=copy.deepcopy(base); d['source_materialization']['required_ledger_fields']=[]
        p=td/'bad_ledgers.json'; writej(p,d); results.append(run([PY,ROOT/'scripts/validate_rule_manifest.py',p],False))

        # allowlisted relationship plus executable MERGE must fail
        c=json.loads(BASE_CAND.read_text(encoding='utf-8'))
        c['recommended_relationships']=['MATCH (a)-[:HAS_PATHWAY]->(b) MERGE (x)-[:HAS_PATHWAY]->(y)']
        p=td/'write_rel.json'; writej(p,c); results.append(run([PY,PD/'check_graph_relationship_allowlist.py',p],False))
        # forbidden current law flag
        c=json.loads(BASE_CAND.read_text(encoding='utf-8')); c['current_law_verified']=True
        p=td/'currentlaw.json'; writej(p,c); results.append(run([PY,PD/'validate_candidate_packet.py',p,'--json'],False))
        # commentary cannot be binding current even with public fields
        c=json.loads(BASE_CAND.read_text(encoding='utf-8')); case=c['candidate_pathways'][0]['case_ladder'][0]; case['court_level']='Commentary'; case['authority_level']='binding_current'; case['current_status']='binding_current'; case['manual_status']='verified'; public_fields(case)
        p=td/'commentary_binding.json'; writej(p,c); results.append(run([PY,PD/'validate_candidate_packet.py',p,'--json'],False))
        # binding_current cannot coexist with needs review
        c=json.loads(BASE_CAND.read_text(encoding='utf-8')); case=c['candidate_pathways'][0]['case_ladder'][0]; case['authority_level']='binding_current'; case['current_status']='binding_current'; case['manual_status']='needs_review'; public_fields(case)
        p=td/'binding_needs_review.json'; writej(p,c); results.append(run([PY,PD/'validate_candidate_packet.py',p,'--json'],False))

        # incomplete manual ledger must fail
        m=td/'manual.tsv'
        with m.open('w',encoding='utf-8',newline='') as f:
            w=csv.writer(f,delimiter='\t'); w.writerow(['candidate_id','pathway_uid','case_name','neutral_citation','canlii_url','authority_level_confirmed','verified_by','verified_date','paragraphs_confirmed','case_status_checked','negative_treatment_checked']); w.writerow(['c','p','x','2020 ABCA 1','u','yes','v','2026-09-28','yes','yes','yes'])
        results.append(run([PY,PD/'check_manual_validation_completeness.py',m],False))

        # blank draft cannot be packaged as completed
        rd=td/'draft'; rd.mkdir();
        (rd/'x_pathway_report.md').write_text('# draft\n',encoding='utf-8'); (rd/'x_graph_candidate_packet.json').write_text('{}',encoding='utf-8'); (rd/'x_manual_validation.tsv').write_text('candidate_id\tpathway_uid\n',encoding='utf-8'); (rd/'x_discard_ledger.tsv').write_text('x\n',encoding='utf-8'); (rd/'x_no_write_run_ledger.json').write_text('{}',encoding='utf-8'); (rd/'README.md').write_text('status: draft\n',encoding='utf-8')
        results.append(run([PY,PD/'package_rule_outputs.py','--rule-dir',rd,'--out',td/'draft.zip'],False))

        # three-book gate good and unresolved non-hold bad
        h0='0'*64; h1='1'*64; h2='2'*64; h3='3'*64; h4='4'*64
        gate={'schema_version':'arc-three-book-gate-v1','three_book_mode':'REQUIRED','rule_identity':'Rule 1.1','source_registry_sha256':h0,'normalization_profile':{'id':'norm','version':'1','sha256':h1},'version_identity':'SAME_VERSION_PROVEN','result':'THREE_BOOK_SOURCE_RECONCILED','required_carriers':['A','B','C'],'carriers':{}}
        for cid,h,origin in [('A',h2,'originA'),('B',h3,'originB'),('C',h4,'originC')]: gate['carriers'][cid]={'carrier_id':cid,'artifact_sha256':h,'text_sha256':h,'source_role':'FIRST_HAND_RULE_CARRIER' if cid=='A' else 'ANNOTATED_RULES','origin_id':origin,'locator':'p1'}
        gate['independent_origin_count']=3
        gp=td/'gate.json'; writej(gp,gate); results.append(run([PY,ROOT/'scripts/validate_three_book_gate.py',gp],True))
        bad=copy.deepcopy(gate); bad['version_identity']='VERSION_IDENTITY_UNRESOLVED'; bad['result']='THREE_BOOK_SOURCE_RECONCILED'; bp=td/'gate_bad.json'; writej(bp,bad); results.append(run([PY,ROOT/'scripts/validate_three_book_gate.py',bp],False))

        # reconciliation must reject missing hashes and required gate without exact artifact binding
        rec={'rows':[],'holds':[],'negative_controls':[],'scope':{'count':0},'reviewed_scope':{'count':0},'summary':{'repair_candidates':0},'three_book_mode':'NOT_APPLICABLE'}
        rp=td/'rec_bad.json'; writej(rp,rec); results.append(run([PY,ROOT/'scripts/validate_reconciliation.py',rp],False))
        ordered=hashlib.sha256(b'ordered').hexdigest(); rec['scope']['ordered_name_uid_sha256']=ordered; rec['reviewed_scope']['ordered_name_uid_sha256']=ordered; rec['three_book_mode']='REQUIRED'; gsha=hashlib.sha256(gp.read_bytes()).hexdigest(); rec['three_book_gate']={'sha256':gsha,'result':gate['result'],'version_identity':gate['version_identity'],'source_registry_sha256':gate['source_registry_sha256'],'normalization_profile_sha256':gate['normalization_profile']['sha256']}
        rp2=td/'rec_good.json'; writej(rp2,rec); results.append(run([PY,ROOT/'scripts/validate_reconciliation.py',rp2,'--three-book-gate',gp],True))
        results.append(run([PY,ROOT/'scripts/validate_reconciliation.py',rp2],False))

        # no-write ledger IDs unique and packet-bound
        fp=hashlib.sha256(b'source').hexdigest(); l1=td/'l1.json'; l2=td/'l2.json'
        common=[PY,PD/'build_no_write_ledger.py','--rule','5.33','--canonical-rule-uid','UnifiedRule|5.33','--candidate-packet',BASE_CAND,'--database','neo4j','--source-fingerprint',fp]
        results.append(run(common+['--out',l1],True)); results.append(run(common+['--out',l2],True))
        if l1.exists() and l2.exists():
            j1=json.loads(l1.read_text()); j2=json.loads(l2.read_text()); results.append({'cmd':['assert_unique_no_write_run_id'],'expect_success':True,'returncode':0 if j1['run_id']!=j2['run_id'] else 1,'passed':j1['run_id']!=j2['run_id'],'stdout':'','stderr':''})
            results.append(run([PY,PD/'verify_no_write_ledger.py',l1,'--candidate-packet',BASE_CAND],True))

        # canary query must be exact and not full relationship scan
        cp=td/'canary.json'; results.append(run([PY,PD/'build_exact_id_canary_packet.py','--migration-id','M1','--source-rule-uid','R1','--case-uid','C1','--source-label','UnifiedRule','--target-label','LegalProposition','--relationship-type','HAS_PATHWAY','--source-uid','S1','--target-uid','T1','--paragraph-evidence','p1','--registry-fingerprint',h0,'--out',cp],True))
        if cp.exists():
            q=json.loads(cp.read_text())['post_write_verification_query']; ok='MATCH ()-[r]->()' not in q and 'uid:$source_uid' in q and 'uid:$target_uid' in q
            results.append({'cmd':['assert_exact_canary_query'],'expect_success':True,'returncode':0 if ok else 1,'passed':ok,'stdout':q,'stderr':''})

    report={'schema_version':'arc-merged-integration-test-v1','tests_run':len(results),'passed':sum(1 for r in results if r['passed']),'failed':[r for r in results if not r['passed']]}
    print(json.dumps(report,indent=2)); return 0 if not report['failed'] else 1
if __name__=='__main__': raise SystemExit(main())
