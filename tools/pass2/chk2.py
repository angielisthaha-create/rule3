import json,re,sys
sys.path.insert(0,'/tmp/w')
import w
from pv import notes_text, QRE, norm
def run(n):
    s=notes_text(n)
    res=[]
    for m in re.finditer(r"lines? (\d{2,5})((?:(?:-|, ?|, and | and )\d{2,5})*)", s):
        ctx=s[max(0,m.start()-130):m.start()]
        post=s[m.end():m.end()+130]
        fm=re.findall(r"combined[ _]rule ?(\d+)(?:\.txt)?",ctx)
        pp=re.findall(r"pp?\.(\d{1,2})-(\d+)",ctx[-70:])
        part=int(fm[-1]) if fm else (int(pp[-1][0]) if pp else 3)
        fn=None
        for b,(p,L) in w.files.items():
            if p==part: fn=b
        if not fn: continue
        L=w.files[fn][1]
        nums=[int(m.group(1))]+[int(x) for x in re.findall(r"\d+",m.group(2))]
        qs=re.findall(QRE,ctx[-110:]+' '+post[:110])
        qs=[norm(q) for q in qs if len(norm(q))>=14]
        # text of the lines around
        for ln in nums[:2]:
            if ln>len(L): res.append(('BEYOND',part,ln,'')); continue
            win=norm(' '.join(L[max(0,ln-2):ln+2]))
            if not qs: res.append(('NOQ',part,ln,L[ln-1][:60])); continue
            okq=[q for q in qs if q[:30] in win or q[-30:] in win]
            res.append(('OK' if okq else 'MISS',part,ln,L[ln-1][:60]+' || Q='+qs[0][:40]))
    return res
if __name__=='__main__':
    show=len(sys.argv)>2 and sys.argv[2]=='all'
    for r in run(int(sys.argv[1])):
        if r[0] in('OK',) and not show: continue
        if r[0]=='NOQ' and not show: continue
        print(r)
