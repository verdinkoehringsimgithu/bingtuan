import json
from pathlib import Path
from model import character_stats

here = Path(__file__).parent
source = here.parent / 'natural_research/results'
old = json.loads((source/'catalog_before.json').read_text(encoding='utf-8'))
new = json.loads((source/'catalog_current.json').read_text(encoding='utf-8'))
key = lambda r: (r['tier'],r['genre'],r['sample'])
before = {key(r):r for r in old}
cases=[]
for row in new[::32]:
    a=[int(before[key(row)]['csv'][k]) for k in ('dodge','defense','speed','authority')]
    b=[int(row['csv'][k]) for k in ('dodge','defense','speed','authority')]
    for power in (.8,1.,1.25):
        for level in range(1,31):
            cases.append(dict(level=level,start=a,end=b,power=power,expected=list(character_stats(level,a,b,power).values())))
(here/'integration_growth_cases.json').write_text(json.dumps(cases),encoding='utf-8')
