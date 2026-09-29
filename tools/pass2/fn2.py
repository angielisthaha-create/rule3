import re,sys
sys.path.insert(0,'/tmp/w')
import w
def chain(pg):
    part=int(pg.split('-')[0])
    fn=[b for b,(p,L) in w.files.items() if p==part][0]
    L=w.files[fn][1]; pm=w.pm[fn]
    txt='\n'.join(l for l,p in zip(L,pm) if p==pg)
    c=[int(m.group(1)) for m in re.finditer(r"(?:^|(?<=[\s.;:)\]\"”’*]))(\d{1,2})(?=\*?(?:[A-Z][a-zA-Z]|\([A-Z]|R\.|\d{4}\b))",txt,re.M) if 1<=int(m.group(1))<=20]
    # longest chain with steps of +1 (or same), starting from 1 or any
    best=[];
    for start in range(len(c)):
        if c[start]!=1: continue
        seq=[1];exp=2
        for x in c[start+1:]:
            if x==exp: seq.append(x);exp+=1
        if len(seq)>len(best): best=seq
    return best
for pg in sys.argv[1:]:
    b=chain(pg); print(pg,'max chain',max(b) if b else 0,b)
