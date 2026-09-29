import sys,re
sys.path.insert(0,'/tmp/w')
import w
def show(phrase,part=3,span=2):
    n=w.norm(phrase)[:24]
    for b,(p,L) in w.files.items():
        if p!=part: continue
        joined='';idx=[]
        for i,l in enumerate(L):
            nl=w.norm(l); joined+=nl; idx+=[i]*len(nl)
        j=joined.find(n)
        if j<0: print('  head not found',phrase[:40]); return
        ln=idx[j]
        print(f'  [{w.pm[b][ln]} line {ln+1}]', ' | '.join(x[:230] for x in L[ln:ln+span]))
for arg in sys.argv[1:]:
    part=3
    if '::' in arg: part,arg=arg.split('::',1); part=int(part)
    show(arg,part)
