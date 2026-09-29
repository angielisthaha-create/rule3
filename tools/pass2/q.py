import json,re,sys,glob,os,pickle
R='/home/user/rule3/'
cachef='/tmp/w/norm.pkl'
def norm(t): return re.sub(r'[^a-z0-9]','',t.lower().replace('ﬁ','fi').replace('ﬂ','fl'))
if os.path.exists(cachef):
    big=pickle.load(open(cachef,'rb'))
else:
    big={}
    for f in glob.glob(R+'*.txt')+glob.glob(R+'*.json'):
        b=os.path.basename(f)
        if b.startswith('rule3.') or b in('_index.json',): continue
        try: t=open(f,encoding='utf-8',errors='replace').read()
        except: continue
        if f.endswith('.json'):
            try:
                t=json.dumps(json.loads(t),ensure_ascii=False)
                t=t.replace('\\n',' ').replace('\\"','"')
            except: pass
        big[b]=norm(t)
    pickle.dump(big,open(cachef,'wb'))
def notes(n):
    d=json.load(open(R+f'rule3_subrules/3.{n}.json',encoding='utf-8'))
    out=[]
    def walk(x,path=''):
        if isinstance(x,dict):
            for k,v in x.items(): walk(v,path+'/'+k)
        elif isinstance(x,list):
            for i,v in enumerate(x): walk(v,path)
        elif isinstance(x,str):
            if any(w in path for w in ('flag','note','see_also','dedupe','review')): out.append((path,x))
    walk(d)
    # review notes block
    t=open(R+'rule3_subrules/REVIEW_NOTES.txt',encoding='utf-8').read()
    m=re.search(rf'^3\.{n} [^\n]*\n(.*?)(?=^3\.\d+ [A-Z]|\Z)',t,re.S|re.M)
    if m: out.append(('REVIEW',m.group(1)))
    return out
def check(n,minlen=18):
    miss=[]
    seen=set()
    global tot
    tot=0
    for path,x in notes(n):
        for q in re.findall(r"(?<![A-Za-z0-9])'((?:[^']|(?<=[A-Za-z])'(?=[A-Za-z]))%s)'(?![A-Za-z0-9])"%('{'+str(minlen)+',}?'),x):
            if q in seen: continue
            seen.add(q)
            tot+=1
            parts=[p for p in re.split(r'\s*(?:\.\.\.|…|\[ ?\]|\[[^\]]*\])\s*',q) if len(norm(p))>=14]
            if not parts: continue
            for p in parts:
                np_=norm(p)
                if not any(np_ in v for v in big.values()):
                    miss.append((path,p)); break
    return miss
if __name__=='__main__':
    for n in map(int,sys.argv[1:]):
        m=check(n)
        print(f'=== 3.{n}: {len(m)} unmatched of {tot} quotes checked')
        for path,p in m: print('  ',path[-30:],'|',p[:200])
