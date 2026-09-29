import json,re,sys
sys.path.insert(0,'/tmp/w')
import w
from pv import notes_text, QRE, norm
def linehit(fn,nq):
    L=w.files[fn][1]
    joined='';idx=[]
    for i,l in enumerate(L):
        nl=norm(l); joined+=nl; idx+=[i]*len(nl)
    out=[];pos=0
    while True:
        j=joined.find(nq,pos)
        if j<0: break
        out.append(idx[j]+1); pos=j+1
    return out
def run(n):
    s=notes_text(n); res=[]
    for m in re.finditer(r"lines? (\d{2,5})((?:(?:-|, ?|, and | and )\d{2,5})*)", s):
        ctx=s[max(0,m.start()-100):m.start()]; post=s[m.end():m.end()+100]
        fm=re.findall(r"combined[ _]rule ?(\d+)(?:\.txt)?",ctx)
        pp=re.findall(r"pp?\.(\d{1,2})-(\d+)",ctx[-70:])
        part=int(fm[-1]) if fm else (int(pp[-1][0]) if pp else 3)
        fn=[b for b,(p,L) in w.files.items() if p==part]
        if not fn: continue
        fn=fn[0]; L=w.files[fn][1]
        ln=int(m.group(1))
        if ln>len(L): continue
        qs=[norm(q) for q in re.findall(QRE,ctx[-100:]+' '+post[:100])]
        qs=[q for q in qs if len(q)>=14]
        for q in qs[:2]:
            hits=linehit(fn,q[:40])
            if not hits: continue          # quote from elsewhere
            near=[h for h in hits if abs(h-ln)<=2]
            if near: continue
            res.append((n,part,ln,hits[:4],q[:40]))
    return res
for n in map(int,sys.argv[1:]):
    for r in run(n): print(r)
