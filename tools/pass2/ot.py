import re,sys
sys.path.insert(0,'/tmp/w')
from pv import notes_text
T=open('/home/user/rule3/Alberta_Rules_of_Court.txt',encoding='utf-8').read().split('\n')
titles={}
i=0
while i<len(T)-1 and i<3000:
    m=re.match(r'^\s*(\d{1,2}\.\d{1,3})\s*$',T[i])
    if m and T[i+1].strip() and not re.match(r'^\s*\d',T[i+1]):
        titles.setdefault(m.group(1),T[i+1].strip())
    else:
        m2=re.match(r'^\s*(\d{1,2}\.\d{1,3})\s{2,}(\S.*)$',T[i])
    i+=1
def nt(x): return re.sub(r'[^a-z0-9]','',x.lower())
print(len(titles),titles.get('3.68'),titles.get('13.18'),titles.get('11.24'),file=sys.stderr)
pat=re.compile(r"official (\d{1,2}\.\d{1,3})(?:\([^)]{1,6}\))*(?: [a-zA-Z]+){0,3} '([^']{6,90})'")
pat2=re.compile(r"'([^']{6,90})' is the (?:official )?title of (\d{1,2}\.\d{1,3})")
bad=0
for n in range(1,78):
    s=notes_text(n); seen=set()
    for m in pat.finditer(s):
        r,t=m.group(1),m.group(2)
        if (r,t) in seen: continue
        seen.add((r,t))
        real=titles.get(r)
        if real is None: continue
        if nt(t)!=nt(real) and nt(t) not in nt(real) and nt(real) not in nt(t):
            bad+=1; print(f'3.{n}: official {r} claimed {t!r} real {real!r}')
print(bad)
