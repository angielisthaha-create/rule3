import re,sys
sys.path.insert(0,'/tmp/w')
from pv import notes_text
# usage: win.py RULE 'p.X-Y' 'label snippet'
n=int(sys.argv[1]); pg=sys.argv[2]; lab=sys.argv[3]
s=notes_text(n)
for m in re.finditer(re.escape(pg)+r"(?!\d)",s):
    win=s[max(0,m.start()-160):m.end()+160]
    if lab in win:
        print(f'3.{n} ::',win.replace('\n',' ')); print(); break
