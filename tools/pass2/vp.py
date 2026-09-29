import sys,re
sys.path.insert(0,'/tmp/w')
import w
# input lines: part|phrase|expected page(s) comma sep e.g. 1-12   ; part may be 0 for any
for line in sys.stdin:
    line=line.strip()
    if not line or line.startswith('#'): continue
    part,phrase,exp=[x.strip() for x in line.split('|')]
    nq=w.norm(phrase); hits=[]
    for b,(p,L) in w.files.items():
        if int(part) and p!=int(part): continue
        joined='';idx=[]
        for i,l in enumerate(L):
            nl=w.norm(l); joined+=nl; idx+=[i]*len(nl)
        pos=0
        while True:
            j=joined.find(nq,pos)
            if j<0: break
            ln=idx[j]+1; hits.append((w.pm[b][ln-1],ln)); pos=j+len(nq)
    pages=sorted({h[0] for h in hits})
    expl=[e.strip() for e in exp.split(',')]
    ok = any(e in pages for e in expl)
    print(('OK  ' if ok else 'CHK ')+f'{phrase[:60]!r} expected {exp} found {pages[:8]} lines {[h[1] for h in hits][:5]}')
