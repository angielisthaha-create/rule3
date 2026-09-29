import json,re,sys,glob
sys.path.insert(0,'/tmp/w')
from pv import notes_text
R='/home/user/rule3/'
# Book B paragraphs
Bpar={}
for f in sorted(glob.glob(R+'rule3_part*_document.json')):
    d=json.load(open(f,encoding='utf-8'))
    for p in d['document_structure']['paragraphs']:
        t=p.get('text','')
        m=re.match(r'Commentary § (3\.\d+):\d',t)
        if m: Bpar.setdefault(m.group(1),[]).append(len(t))
    # also all paragraph lengths per file for continuation
allB={}
for f in sorted(glob.glob(R+'rule3_part*_document.json')):
    d=json.load(open(f,encoding='utf-8'))
    for p in d['document_structure']['paragraphs']:
        allB.setdefault(len(p.get('text','')),set()).add(f[-22:-14])
def measured(n):
    d=json.load(open(R+f'rule3_subrules/3.{n}.json',encoding='utf-8'))
    a=d['sources'].get('BOOK_A') or {}
    m=set()
    for k in ('defined_terms','related_provisions','commentary','operative_text_raw'):
        v=a.get(k)
        if isinstance(v,str): m.add(len(v))
    for x in Bpar.get(f'3.{n}',[]): m.add(x)
    b=d['sources'].get('BOOK_B') or {}
    for c in (b.get('commentary') or []):
        m.add(len(c.get('text','')))
    c=d['sources'].get('BOOK_C') or {}
    for x in (c.get('commentary') or []):
        m.add(len(x.get('text','')))
    return m
for n in range(1,78):
    s=notes_text(n); m=measured(n)
    for mm in re.finditer(r"(\d[\d,]*) characters",s):
        v=int(mm.group(1).replace(',',''))
        if v in m or v in allB: continue
        ctx=s[max(0,mm.start()-70):mm.end()+30].replace('\n',' ')
        print(f'3.{n}: claim {v} not measured; measured={sorted(m)[:8]} | {ctx}')
