import re,json
P='/home/user/rule3/tools/build_rule3_reconciliation.py'
N='/home/user/rule3/rule3_subrules/REVIEW_NOTES.txt'
class Fix:
    def __init__(s):
        s.b=open(P,encoding='utf-8').read(); s.n=open(N,encoding='utf-8').read()
    def rep(s,old,new,count=1,where='b'):
        txt=getattr(s,where)
        pat=''.join('(?: ?" *\\n *" ?| )' if ch==' ' else re.escape(ch) for ch in old)
        ms=list(re.finditer(pat,txt))
        assert len(ms)==count,(len(ms),old[:70])
        txt=re.sub(pat,lambda m:new,txt)
        setattr(s,where,txt)
    def note(s,rule,line):
        """append a [2nd pass] line to the rule's REVIEW_NOTES block"""
        pat=re.compile(rf'(^{re.escape(rule)} [^\n]*\n(?:     [^\n]*\n)*)',re.M)
        m=pat.search(s.n); assert m,rule
        s.n=s.n[:m.end()]+'     '+line+'\n'+s.n[m.end():]
    def save(s):
        open(P,'w',encoding='utf-8').write(s.b); open(N,'w',encoding='utf-8').write(s.n)
