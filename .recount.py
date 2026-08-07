import glob, re
from collections import defaultdict
suites=defaultdict(lambda:[0,0,0,0]); files=0; total=active=quar=pend=0
for f in glob.glob('tests/*/features/**/*.feature', recursive=True):
    files+=1; suite=f.split('/')[1]; ftags=[]; tags=[]
    for line in open(f):
        line=line.strip()
        if line.startswith('@'): tags=line.split()
        elif line.startswith('Feature:'): ftags=tags; tags=[]
        elif re.match(r'(Scenario|Scenario Outline|Scenario Template):', line):
            s=set(tags)|set(ftags)
            if '@quarantine' in s: q,a,p=1,0,0
            elif '@hardware_blocked' in s or '@future' in s or '@pending' in s: q,a,p=0,0,1
            else: q,a,p=0,1,0
            r=suites[suite]; r[0]+=1; r[1]+=a; r[2]+=q; r[3]+=p
            total+=1; active+=a; quar+=q; pend+=p; tags=[]
print(f"TOTAL {total} files {files} active {active} quarantined {quar} pending {pend}")
for s in sorted(suites): print(s, *suites[s])
