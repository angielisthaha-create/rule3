import re,sys,pickle
sys.path.insert(0,'/tmp/w')
import q
big=q.big; norm=q.norm
def classify(p):
    n=norm(p)
    if len(n)<40:
        return 'SHORT'
    h,t=n[:20],n[-20:]
    for f,v in big.items():
        i=0
        while True:
            i=v.find(h,i)
            if i<0: break
            j=v.find(t,i)
            if 0<=j-i<=len(n)+250: return 'NEAR:'+f+f' gap={j-i-len(n)}'
            i+=1
    hh=[f for f,v in big.items() if h in v]; tt=[f for f,v in big.items() if t in v]
    return f'HEAD={hh[:2]} TAIL={tt[:2]}'
if __name__=='__main__':
    for n in range(1,78):
        for path,p in q.check(n):
            c=classify(p)
            if c.startswith('NEAR'): continue
            print(f'3.{n} {path[-22:]} | {c} | {p[:150]}')
