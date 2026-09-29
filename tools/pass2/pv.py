import json,re,sys,pickle,os
R='/home/user/rule3/'
def fname(p):
    return {1:'combined rule1.txt',3:'combined rule3.txt',14:'combined rule14.txt',15:'combined rule15.txt'}.get(p, f'combined_rule{p}.txt')
def norm(t): return re.sub(r'[^a-z0-9]','',t.lower().replace('ﬁ','fi').replace('ﬂ','fl'))
pages={}
def load(p):
    if p in pages: return pages[p]
    L=open(R+fname(p),encoding='utf-8',errors='replace').read().split('\n')
    d={};cur=None;buf=[]
    for l in L:
        m=re.match(r'\*\*PAGE (\d+)',l) if p==3 else re.match(rf'^{p}-(\d+)\s*$',l.strip())
        if m:
            if cur: d.setdefault(cur,[]).append(' '.join(buf))
            cur=f'{p}-'+m.group(1); buf=[]
        else: buf.append(l)
    if cur: d.setdefault(cur,[]).append(' '.join(buf))
    pages[p]={k:norm(' '.join(v)) for k,v in d.items()}
    return pages[p]
def notes_text(n):
    t=open(R+'rule3_subrules/REVIEW_NOTES.txt',encoding='utf-8').read()
    d=json.load(open(R+f'rule3_subrules/3.{n}.json',encoding='utf-8'))
    s=json.dumps(d,ensure_ascii=False).replace('\\"','"').replace("\\'","'")
    m=re.search(rf'^3\.{n} [^\n]*\n(.*?)(?=^3\.\d+ [A-Z]|\Z)',t,re.S|re.M)
    return s+'\n'+(m.group(1) if m else '')
QRE=r"(?<![A-Za-z0-9])'((?:[^']|(?<=[A-Za-z])'(?=[A-Za-z])){14,}?)'(?![A-Za-z0-9])"
def run(n):
    s=notes_text(n)
    out=[]
    for m in re.finditer(r"pp?\.(\d{1,2})-(\d+)",s):
        part=int(m.group(1)); pg=f'{part}-{m.group(2)}'
        try: P=load(part)
        except Exception as e: continue
        win=s[max(0,m.start()-160):m.end()+160]
        for q in re.findall(QRE,win):
            nq=norm(q)
            if len(nq)<16: continue
            if nq[:40] in ''.join(P.values()) or True:
                found=[k for k,v in P.items() if nq[:60] in v]
                if not found: continue
                # adjacent pages allowed (page-straddling)
                num=int(m.group(2))
                if pg in found: continue
                near=[k for k in found if abs(int(k.split('-')[1])-num)<=1]
                out.append((pg,found[:4],q[:80],bool(near)))
    return out
if __name__=='__main__':
    for n in map(int,sys.argv[1:]):
        r=run(n)
        seen=set()
        print(f'=== 3.{n}: {len(r)} page/quote disagreements')
        for pg,found,q,near in r:
            if (pg,q) in seen: continue
            seen.add((pg,q))
            print(f'  claim p.{pg} found on {found} {"(adjacent)" if near else ""} | {q}')
