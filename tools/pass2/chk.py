import json,re,sys
R='/home/user/rule3/'
def fname(p):
    return {1:'combined rule1.txt',3:'combined rule3.txt',14:'combined rule14.txt',15:'combined rule15.txt'}.get(p, f'combined_rule{p}.txt')
cache={}
def load(p):
    if p not in cache:
        L=open(R+fname(p),encoding='utf-8',errors='replace').read().split('\n')
        pm=[];cur=None
        for l in L:
            if p==3:
                m=re.match(r'\*\*PAGE (\d+)',l)
                if m: cur='3-'+m.group(1)
            else:
                m=re.match(rf'^{p}-(\d+)\s*$',l.strip())
                if m: cur=f'{p}-'+m.group(1)
            pm.append(cur)
        cache[p]=(L,pm)
    return cache[p]
def main(n,show_ok=False):
    d=json.load(open(R+f'rule3_subrules/3.{n}.json',encoding='utf-8'))
    s=json.dumps(d,ensure_ascii=False).replace('\\"','"').replace("\\'","'")
    for m in re.finditer(r"lines? (\d{2,5})((?:(?:-|, ?|, and | and )\d{2,5})*)", s):
        ctx=s[max(0,m.start()-110):m.start()]
        fm=re.findall(r"combined[ _]rule ?(\d+)(?:\.txt)?",ctx)
        pp=re.findall(r"pp?\.(\d{1,2})-(\d+)",ctx[-60:])
        if fm: part=int(fm[-1])
        elif pp: part=int(pp[-1][0])
        else: part=3
        claimed=f'{pp[-1][0]}-{pp[-1][1]}' if pp else '-'
        nums=[int(m.group(1))]+[int(x) for x in re.findall(r"\d+",m.group(2))]
        L,pm=load(part)
        for ln in nums[:3]:
            if ln>len(L): print(f'?? line {ln} > file {part}'); continue
            act=pm[ln-1]
            ok = claimed=='-' or claimed==act
            if ok and not show_ok: continue
            print(f"{'OK ' if ok else 'CHK'} file{part} claim {claimed} actual {act} ln{ln} ctx=..{ctx[-50:]!r} | {L[ln-1][:60]!r}")
if __name__=='__main__':
    main(int(sys.argv[1]), len(sys.argv)>2)
