import re,sys
sys.path.insert(0,'/tmp/w')
from pv import load, notes_text, norm
LAB=re.compile(r"\b(\d{1,2}\.\d{1,3}(?:\(\d+\))?(?:\([a-z]\))?)(?: ?\(([a-z][^()]{3,70})\))")
RULE=re.compile(r"\bR(?:r)?\.\s?(\d{1,2}\.\d{1,3}(?:\(\d+\))?(?:\([a-z]\))?)\s?n\.")
def run(n):
    s=notes_text(n); out=[]
    for m in re.finditer(r"pp?\.(\d{1,2})-(\d+)",s):
        part=int(m.group(1)); pg=m.group(2)
        try: P=load(part)
        except Exception: continue
        win=s[max(0,m.start()-70):m.end()+90]
        for lm in LAB.finditer(win):
            lab=norm(lm.group(1)+lm.group(2))
            cand=[k for k,v in P.items() if lab in v]
            if not cand: continue
            pages={int(k.split('-')[1]) for k in cand}
            if int(pg) in pages: continue
            out.append((f'{part}-{pg}',lm.group(0)[:60],sorted(pages)[:5]))
    return out
for n in map(int,sys.argv[1:]):
    seen=set()
    for r in run(n):
        r=(r[0],r[1],tuple(r[2]))
        if r in seen: continue
        seen.add(r); print(n,r)
