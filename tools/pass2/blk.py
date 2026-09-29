import re,sys
s=open('/home/user/rule3/rule3_subrules/REVIEW_NOTES.txt',encoding='utf-8').read()
for n in sys.argv[1:]:
    m=re.search(rf'^3\.{n} [^\n]*\n((?:     [^\n]*\n)*)',s,re.M); print(f'##### 3.{n}\n'+m.group(1))
