import re,sys,glob,os
R='/home/user/rule3/'
def norm(t): return re.sub(r'[^a-z0-9]','',t.lower().replace('ﬁ','fi').replace('ﬂ','fl'))
files={}
for f in glob.glob(R+'combined*.txt'):
    b=os.path.basename(f)
    m=re.search(r'rule ?(\d+)',b); part=int(m.group(1))
    L=open(f,encoding='utf-8',errors='replace').read().split('\n')
    files[b]=(part,L)
def pagemap(part,L):
    cur=None;out=[]
    for l in L:
        m=re.match(r'\*\*PAGE (\d+)',l) if part==3 else re.match(rf'^{part}-(\d+)\s*$',l.strip())
        if m: cur=f'{part}-'+m.group(1)
        out.append(cur)
    return out
pm={b:pagemap(p,L) for b,(p,L) in files.items()}
def where(q,only=None,maxhits=12):
    nq=norm(q); n=0
    for b,(part,L) in sorted(files.items(),key=lambda x:x[1][0]):
        if only and part!=only: continue
        # search across joined lines with map
        joined='';idx=[]
        for i,l in enumerate(L):
            nl=norm(l)
            joined+=nl; idx+= [i]*len(nl)
        pos=0
        while True:
            j=joined.find(nq,pos)
            if j<0: break
            ln=idx[j]+1
            print(f'{b} p.{pm[b][ln-1]} line {ln}: {L[ln-1][:110]!r}')
            n+=1
            if n>=maxhits: return
            pos=j+len(nq)
if __name__=='__main__':
    where(sys.argv[1], int(sys.argv[2]) if len(sys.argv)>2 else None)
