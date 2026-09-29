import re,sys
sys.path.insert(0,'/tmp/w')
import w
def page(pg):
    part=int(pg.split('-')[0])
    fn=[b for b,(p,L) in w.files.items() if p==part][0]
    L=w.files[fn][1]; pm=w.pm[fn]
    return '\n'.join(l for l,p in zip(L,pm) if p==pg)
for pg in sys.argv[1:]:
    t=page(pg)
    ms=[(m.group(1),t[m.end():m.end()+28].replace('\n',' ')) for m in re.finditer(r"(?<![\w.,§¶'\"(/-])(\d{1,2})(?=\*?[A-Z][a-z(]|\*?[A-Z]\.)",t)]
    print(pg,len(ms)); print('   ',' | '.join(f'{a}:{b[:16]}' for a,b in ms))
