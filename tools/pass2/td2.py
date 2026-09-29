import sys,re,json,difflib,importlib.util
spec=importlib.util.spec_from_file_location('b3','/home/user/rule3/tools/build_rule3_reconciliation.py')
b3=importlib.util.module_from_spec(spec); spec.loader.exec_module(b3)
off,_=b3.parse_official(); A,_=b3.parse_book_a(); B,_=b3.parse_book_b(); C,_=b3.parse_book_c()
import pickle
def n(t): return re.sub(r'[^a-z0-9]','',t.lower())
def strip_labels(t): return re.sub(r'\[[^\]]*\]','',t)
def raw(rec):
    if not rec: return None
    if isinstance(rec,dict):
        for k in ('operative_text_raw','operative_text','text'):
            if rec.get(k): return rec[k]
    return None
def small(o,c):
    sm=difflib.SequenceMatcher(None,o,c,autojunk=False)
    out=[]
    for tag,i1,i2,j1,j2 in sm.get_opcodes():
        if tag=='equal': continue
        a,b=o[i1:i2],c[j1:j2]
        if re.fullmatch(r'\d{0,2}',b) and not a: continue   # footnote marker digits
        out.append((tag,a,b,o[max(0,i1-14):i1]))
    return out

def run(r):
    key=f'3.{r}'
    o=n(strip_labels(off[key]['operative_text']))
    res={}
    for name,rec in (('A',A.get(key)),('B',B.get(key)),('C',C.get(key))):
        t=raw(rec) if rec else None
        if not t: res[name]=None; continue
        c=n(strip_labels(t))
        if len(c)>len(o)*1.6:   # footnote blocks etc: align the official inside the carrier
            sm=difflib.SequenceMatcher(None,o,c,autojunk=False)
            blocks=[b for b in sm.get_matching_blocks() if b.size>=8]
            res[name]=('LONG',len(c),round(sm.ratio(),2)); 
            # still list small diffs between consecutive matched blocks within official coverage
            d=[]
            for tag,i1,i2,j1,j2 in sm.get_opcodes():
                if tag=='equal': continue
                a,b=o[i1:i2],c[j1:j2]
                if (i2-i1)<=40 and (j2-j1)<=40 and not (re.fullmatch(r'\d{0,2}',b) and not a): d.append((tag,a,b))
            res[name]=('LONG',len(c),d[:8])
        else:
            res[name]=('OK',len(c),small(o,c)[:8])
    return res
if __name__=='__main__':
    for r in sys.argv[1:]:
        print('=====3.'+r)
        for k,v in run(r).items():
            if v is None: print(' ',k,'none'); continue
            print(' ',k,v[0],v[1],[ (x[0],x[1][:30],x[2][:30]) for x in (v[2] if isinstance(v[2],list) else [])])
