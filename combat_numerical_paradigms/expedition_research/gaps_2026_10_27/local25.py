"""Fixed-roster local NPC difficulty bracket, independently checked by seed."""
import gzip
import hashlib
import itertools
import json
from pathlib import Path

import hard_regions as hard
from common import *

ROOT=OUT/'local25'


def main():
    parent=check_manifest(hard.ROOT/'confirm_manifest.json')
    data=json.loads((hard.ROOT/'confirm.json').read_text(encoding='utf-8'))
    source=next(c for c in data['rows'] if c['job']['stage']==4 and c['job']['genre']=='C_I'
        and c['job']['gear']=='basic' and c['job']['pool']==3080000 and c['job']['reference_kind']=='terminal')
    base=source['job'];candidates=[]
    for a,b in itertools.product((.95,1.,1.05),(.9,.94,.98,1.02)):
        macro=list(base['macro']);macro[0]*=a;macro[1]*=b
        j={**base,'macro':macro,'local_alpha':a,'local_beta':b}
        answer=hard.solve(j,j['pool'],'final',0,128)
        candidates.append(dict(job=j,result=answer))
    eligible=[c for c in candidates if c['result']['metrics']['wr']>.5 and c['result']['metrics']['winning_hp']is not None
        and c['result']['metrics']['winning_hp']<=.2]
    ROOT.mkdir(parents=True,exist_ok=True)
    selected=min(eligible,key=lambda c:((c['result']['metrics']['wr']-.65)/.2)**2+
        ((c['result']['metrics']['winning_hp']-.15)/.1)**2) if eligible else None
    result=dict(parent_signature=parent['signature'],parent_key=source['key'],candidates=candidates,selected=selected,
        scope='one fixed known roster, new seed confirmation; not new people',
        sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (Path(__file__),HERE/'LOCAL25_PROTOCOL.md',hard.ROOT/'confirm.json')})
    executed=sum(c['result']['executed_battles'] for c in candidates)
    if selected:
        j=selected['job'];mm,ii,enemy,ei,sim=hard.prepare(j,j['pool'],'final');order=selected['result']['plan']['order']
        m,it=hard.reordered(mm,ii,order);seeds=[old.seed('local25-independent',j,i) for i in range(1024)]
        assert not set(seeds)&set(selected['result']['seeds']['test'])
        trials=[hard.project(sim(m,enemy,bs,it,ei,p=j['macro'],enabled=hard.ENABLED)[0]) for bs in seeds]
        prepared={'0':selected['result']};previous_order=order
        for wear in hard.GRID[1:]:
            p=hard.solve(j,j['pool'],'final',wear,32,previous_order);prepared[str(wear)]=p;previous_order=p['plan']['order']
            executed+=p['executed_battles']
        grace=json.loads((previous.fit.OUT/'selected.json').read_text(encoding='utf-8'))['stage_policies']['4']
        policies=dict(control=dict(p=0.,l0=0.,l1=0.),immediate=previous.ORIGINAL,grace=grace)
        journeys={name:[hard.journey(j,j['pool'],prepared,p,i) for i in range(64)] for name,p in policies.items()}
        native=sum(len(r) for rr in journeys.values() for r in rr)
        result.update(confirmation=dict(seeds=seeds,trials=trials,prepared=prepared,journeys=journeys,
            policies=policies,native_battles=native,members=old.snapshot(mm,ii),enemy=old.snapshot(enemy,ei)))
        executed+=1024+native
        won=[r for r in trials if r['win']]
        print('local25 confirmed WR',len(won)/1024,'winning_hp',sum(r['hp'] for r in won)/len(won) if won else None,
            'scale',j['local_alpha'],j['local_beta'],flush=True)
    else:print('local25: no qualifying calibration candidate',flush=True)
    result['executed_battles']=executed
    atomic_json(ROOT/'results.json',result)


if __name__=='__main__':main()
