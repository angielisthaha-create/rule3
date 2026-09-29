import re,sys
sys.path.insert(0,'/tmp/w')
import w
def fnmarks(pg):
    part=int(pg.split('-')[0]); 
    fn=[b for b,(p,L) in w.files.items() if p==part][0]
    L=w.files[fn][1]; pm=w.pm[fn]
    txt='\n'.join(l for l,p in zip(L,pm) if p==pg)
    # candidate footnote starts: digits (1-2) at line start or after '. ' / ' ' followed by capital letter or '*' 
    cands=[]
    for m in re.finditer(r"(?:(?<=^)|(?<=\n)|(?<=[.;:)\]\s\"”’]))(\d{1,2})(?=\*?(?:[A-Z][a-zA-Z]|\([A-Z]|R\.|See|Ibid|Quite|\.?\d))",txt):
        cands.append((int(m.group(1)),txt[m.end():m.end()+22].replace('\n',' ')))
    return cands
if __name__=='__main__':
    for pg in sys.argv[1:]:
        c=fnmarks(pg)
        # print sequence of numbers, dedupe consecutive
        print(pg,[x[0] for x in c])
