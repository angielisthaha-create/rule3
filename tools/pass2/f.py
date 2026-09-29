import re,sys,pickle,glob,os,json
R='/home/user/rule3/'
big=pickle.load(open('/tmp/w/norm.pkl','rb'))
def norm(t): return re.sub(r'[^a-z0-9]','',t.lower().replace('ﬁ','fi').replace('ﬂ','fl'))
q=sys.argv[1]; n=norm(q)
print('len',len(n))
for k in (18,):
    for label,frag in (('head',n[:k]),('tail',n[-k:]),('mid',n[len(n)//2-9:len(n)//2+9])):
        hits=[(f,v.count(frag)) for f,v in big.items() if frag in v]
        print(label,frag,hits[:6])
# show context of first head hit in book A rule3
v=big.get('combined rule3.txt','')
i=v.find(n[:18])
if i>=0:
    print('ctx head in rule3:',v[i:i+len(n)+40])
    print('quote norm     :',n)
