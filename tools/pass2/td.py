import json,re,sys,difflib
R='/home/user/rule3/'
def n(t): return re.sub(r'[^a-z0-9]','',t.lower())
def strip_labels(t): return re.sub(r'\[[^\]]*\]','',t)
def diffs(rule,src='BOOK_A'):
    d=json.load(open(R+f'rule3_subrules/3.{rule}.json',encoding='utf-8'))
    off=d['operative_text']['controlling']
    a=d['sources'].get(src) or {}
    # the raw text may have been dropped; use comparison from the original: recompute from source file not possible; use operative_text_raw if present
    raw=a.get('operative_text_raw')
    if not raw: return None
    # cut off footnote blocks: keep only the segment before the first line that starts with a digit+capital not part of rule text? keep whole for simplicity
    o=n(strip_labels(off)); c=n(strip_labels(raw))
    sm=difflib.SequenceMatcher(None,o,c,autojunk=False)
    out=[]
    for tag,i1,i2,j1,j2 in sm.get_opcodes():
        if tag=='equal': continue
        out.append((tag,o[max(0,i1-12):i2+12] if i2>i1 else o[max(0,i1-12):i1+12],c[max(0,j1-12):j2+12] if j2>j1 else '',o[i1:i2],c[j1:j2]))
    return out
if __name__=='__main__':
    for r in map(int,sys.argv[1:]):
        x=diffs(r)
        print(f'3.{r}:', 'raw dropped' if x is None else f'{len(x)} diffs')
        if x:
            for t in x[:8]: print('   ',t[0],'OFF:',repr(t[3][:50]),'A:',repr(t[4][:50]))
