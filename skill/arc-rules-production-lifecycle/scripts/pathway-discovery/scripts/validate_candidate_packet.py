#!/usr/bin/env python3
"""Validate an ARC pathway candidate packet with no-write and cross-field consistency checks."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
REQUIRED_TOP=['packet_type','write_status','loop_name','rules','candidate_nodes','candidate_pathways','recommended_relationships','manual_validation_required','ledger']
REQUIRED_PATHWAY=['pathway_uid','rule_anchor','companion_rules','case_ladder','safe_formulation','do_not_overstate_as','manual_validation_status','write_status']
REQUIRED_CASE=['case_name','neutral_citation','court_level','authority_level','authority_role','paragraphs','paragraph_status','holding_summary','do_not_overstate_as','current_status','manual_status']
ALLOWED_AUTHORITY_ROLES={'root_doctrine','codification','scope_limit','leave_test','threshold_test','public_record_exception','anti_circumvention','regulator_disclosure_granted','regulator_disclosure_refused','related_action_granted','related_action_refused','same_action_use','breach_sanction','contempt_limit','admissibility_limit','analogue_only','privilege_limit','non_party_privacy_limit','remedy_selection','contrary_or_distinguishing','current_application','historical_root'}
ALLOWED_COURT_LEVELS={'SCC','ABCA','ABKB','ABQB','ApplicationsJudge','Master','FederalCourt','FCA','OutOfProvince','Tribunal','Commentary','Unknown'}
ALLOWED_AUTHORITY_STATUS={'binding_current','binding_possible_but_needs_citator','persuasive_current','persuasive_needs_citator','historical_predecessor_rule','analogue_only','commentary_only','reform_proposal','overruled_or_reversed','distinguished','uncertain','do_not_use_until_verified','needs_citator','needs_public_verification'}
ALLOWED_WRITE_STATUSES={'candidate','candidate_only','no_graph_write','do_not_write','do_not_write_until_approved','not_approved','manual_validation_required','candidate_only_no_graph_write_performed_do_not_write_until_approved'}
FORBIDDEN_TRUE_FLAGS={'current_law_verified','current_law_certified','court_facing_approved','filing_ready','production_authorized','production_released','retrieval_released','unrestricted_retrieval'}
PUBLIC_FIELDS=['canlii_url','official_source_url','paragraphs_confirmed','quoted_text_confirmed','current_rule_text_confirmed','case_status_checked','negative_treatment_checked','verified_by','verified_date']
NONBINDING_COURTS={'Commentary','Unknown','OutOfProvince','Tribunal','FederalCourt','FCA'}
def load_json(p): return json.loads(p.read_text(encoding='utf-8'))
def no_write_status(v): return str(v or '').strip().lower() in ALLOWED_WRITE_STATUSES
def truthy(v): return str(v).strip().lower() in {'yes','true','1','complete','confirmed','verified'}
def check_forbidden(obj,path,e):
    if isinstance(obj,dict):
        for k,v in obj.items():
            if k in FORBIDDEN_TRUE_FLAGS and v is True: e.append(f'{path}.{k} must not be true in candidate packet')
            check_forbidden(v,f'{path}.{k}',e)
    elif isinstance(obj,list):
        for i,v in enumerate(obj): check_forbidden(v,f'{path}[{i}]',e)
def public_complete(obj):
    for f in PUBLIC_FIELDS:
        v=obj.get(f)
        if f.endswith('_confirmed') or f.endswith('_checked'):
            if not truthy(v): return False
        elif not str(v or '').strip(): return False
    return True
def validate(packet):
    e=[]
    for f in REQUIRED_TOP:
        if f not in packet: e.append(f'missing top-level field: {f}')
    if not no_write_status(packet.get('write_status')): e.append('write_status must be one exact no-write candidate status')
    if packet.get('manual_validation_required') is not True: e.append('manual_validation_required must be true')
    check_forbidden(packet,'packet',e)
    rules=packet.get('rules',[])
    if not isinstance(rules,list) or not rules: e.append('rules must be a non-empty list')
    nodes=packet.get('candidate_nodes',[])
    if not isinstance(nodes,list) or not nodes: e.append('candidate_nodes must be a non-empty list')
    for i,node in enumerate(nodes if isinstance(nodes,list) else []):
        if not isinstance(node,dict): e.append(f'candidate_nodes[{i}] is not an object'); continue
        if not (node.get('key') or node.get('candidate_id') or node.get('pathway_uid')): e.append(f'candidate_nodes[{i}] lacks key/candidate_id/pathway_uid')
        if not (node.get('label') or node.get('type')): e.append(f'candidate_nodes[{i}] lacks label/type')
    pathways=packet.get('candidate_pathways',[])
    if not isinstance(pathways,list) or not pathways: e.append('candidate_pathways must be a non-empty list'); pathways=[]
    for i,p in enumerate(pathways):
        if not isinstance(p,dict): e.append(f'candidate_pathways[{i}] is not an object'); continue
        uid=p.get('pathway_uid') or f'candidate_pathways[{i}]'
        for f in REQUIRED_PATHWAY:
            if f not in p: e.append(f'{uid}: missing required pathway field: {f}')
        if not no_write_status(p.get('write_status',packet.get('write_status'))): e.append(f'{uid}: write_status must be one exact no-write candidate status')
        if not p.get('companion_rules'): e.append(f"{uid}: companion_rules must be non-empty or explicitly include 'none_verified'")
        status=p.get('authority_status')
        if status and status not in ALLOWED_AUTHORITY_STATUS: e.append(f'{uid}: invalid authority_status {status}')
        if status=='binding_current':
            if str(p.get('manual_validation_status','')).lower()!='verified': e.append(f'{uid}: binding_current requires manual_validation_status=verified')
            if not public_complete(p): e.append(f'{uid}: binding_current requires complete public verification fields')
        kind=p.get('pathway_kind','CASE_INTERPRETIVE')
        if kind not in {'CASE_INTERPRETIVE','RULE_TEXT_ONLY'}: e.append(f'{uid}: invalid pathway_kind {kind}')
        ladder=p.get('case_ladder',[])
        if not isinstance(ladder,list): e.append(f'{uid}: case_ladder must be a list'); ladder=[]
        if kind=='CASE_INTERPRETIVE' and not ladder: e.append(f'{uid}: CASE_INTERPRETIVE pathway requires non-empty case_ladder')
        if kind=='RULE_TEXT_ONLY':
            if ladder: e.append(f'{uid}: RULE_TEXT_ONLY pathway must not use case_ladder; use a separate interpretive candidate')
            spans=p.get('source_proof_spans',[])
            if not isinstance(spans,list) or not spans: e.append(f'{uid}: RULE_TEXT_ONLY pathway requires source_proof_spans')
            if status in {'binding_current','persuasive_current'}: e.append(f'{uid}: RULE_TEXT_ONLY candidate cannot assert case-authority status {status}')
        for j,c in enumerate(ladder):
            if not isinstance(c,dict): e.append(f'{uid}: case_ladder[{j}] is not an object'); continue
            for f in REQUIRED_CASE:
                if f not in c: e.append(f'{uid}: case_ladder[{j}] missing {f}')
            role=c.get('authority_role'); court=c.get('court_level'); alev=c.get('authority_level'); cur=c.get('current_status')
            if role and role not in ALLOWED_AUTHORITY_ROLES: e.append(f'{uid}: case_ladder[{j}] invalid authority_role {role}')
            if court and court not in ALLOWED_COURT_LEVELS: e.append(f'{uid}: case_ladder[{j}] invalid court_level {court}')
            if alev and alev not in ALLOWED_AUTHORITY_STATUS: e.append(f'{uid}: case_ladder[{j}] invalid authority_level {alev}')
            if cur and cur not in ALLOWED_AUTHORITY_STATUS: e.append(f'{uid}: case_ladder[{j}] invalid current_status {cur}')
            if alev=='binding_current' or cur=='binding_current':
                if str(c.get('manual_status','')).lower()!='verified': e.append(f'{uid}: case_ladder[{j}] binding_current requires manual_status=verified')
                if not public_complete(c): e.append(f'{uid}: case_ladder[{j}] binding_current requires complete public verification fields')
            if court in NONBINDING_COURTS and (alev=='binding_current' or cur=='binding_current'): e.append(f'{uid}: case_ladder[{j}] {court} cannot be marked binding_current in this Alberta pathway packet')
            if court=='Commentary' and alev not in {None,'commentary_only','analogue_only','reform_proposal'}: e.append(f'{uid}: case_ladder[{j}] Commentary requires commentary/analogue/reform authority level')
            if str(c.get('manual_status','')).lower()=='verified' and not c.get('paragraphs'): e.append(f'{uid}: verified case_ladder[{j}] requires paragraphs')
    if not isinstance(packet.get('recommended_relationships',[]),list): e.append('recommended_relationships must be a list')
    return e

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('packet',type=Path); ap.add_argument('--json',action='store_true'); a=ap.parse_args(); p=load_json(a.packet); e=validate(p); r={'valid':not e,'errors':e,'error_count':len(e)}
    if a.json: print(json.dumps(r,indent=2))
    elif e:
        print('INVALID'); [print('- '+x) for x in e]
    else: print('VALID')
    return 0 if not e else 1
if __name__=='__main__': sys.exit(main())
