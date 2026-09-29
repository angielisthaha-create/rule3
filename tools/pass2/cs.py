import re,sys
sys.path.insert(0,'/tmp/w')
from pv import load, notes_text, norm
CS=re.compile(r"([A-Z][A-Za-z.&'’-]+(?: [A-Z][A-Za-z.&'’-]+){0,3} v\.? [A-Z][A-Za-z.&'’-]+(?: [A-Za-z.&'’-]+){0,2})")
def run(n):
    s=notes_text(n); out=[]
    for m in re.finditer(r"pp?\.(\d{1,2})-(\d+)( fn ?\d+)?",s):
        part=int(m.group(1)); pg=int(m.group(2))
        try: P=load(part)
        except Exception: continue
        # window: 70 chars before (clause) and 25 after
        win=s[max(0,m.start()-75):m.end()+30]
        for cm in CS.finditer(win):
            nm=norm(cm.group(1))
            if len(nm)<12: continue
            key=nm[:14]
            found=[int(k.split('-')[1]) for k,v in P.items() if key in v]
            if not found: continue   # not in this part's Book A at all (other book)
            if pg in found: continue
            near=[f for f in found if abs(f-pg)<=1]
            out.append((f'{part}-{pg}',cm.group(1)[:45],sorted(found)[:6],'ADJ' if near else 'FAR'))
    return out
for n in map(int,sys.argv[1:]):
    seen=set()
    for r in run(n):
        r=(r[0],r[1],tuple(r[2]),r[3])
        if r in seen: continue
        seen.add(r)
        if r[3]=='FAR': print(n,r)
