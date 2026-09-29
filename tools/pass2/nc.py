import json,re,sys
sys.path.insert(0,'/tmp/w')
from pv import load, notes_text
NC=re.compile(r"\b(?:19|20)\d\d (?:ABQB|ABKB|ABCA|SCC|ABPC|SKCA|ONCA|BCCA|FCA|FC|NWTSC|NUCA|ONSC|NSCA|MBCA|ABLAB) ?\d+")
def run(n):
    s=notes_text(n); out=[]
    for m in re.finditer(r"pp?\.(\d{1,2})-(\d+)",s):
        part=int(m.group(1)); pg=int(m.group(2))
        try: P=load(part)
        except Exception: continue
        win=s[max(0,m.start()-85):m.end()+85]
        for c in set(NC.findall(win)):
            cn=re.sub(r'\W','',c).lower()
            found=[k for k,v in P.items() if cn in v]
            if not found: continue
            pages={int(k.split('-')[1]) for k in found}
            if pg in pages: continue
            near=[p for p in pages if abs(p-pg)<=1]
            out.append((f'{part}-{pg}',c,sorted(pages)[:6],'ADJ' if near else 'FAR'))
    return out
for n in map(int,sys.argv[1:]):
    seen=set()
    for r in run(n):
        r=(r[0],r[1],tuple(r[2]),r[3])
        if r in seen: continue
        seen.add(r); print(n,r)
