"""Broader fixed NPC alpha/beta bracket after a failed local check."""
import hashlib
import itertools
import json
from pathlib import Path

import hard_regions as hard
from common import *

ROOT=OUT/'terminal25'


def main():
    data=json.loads((hard.ROOT/'confirm.json').read_text(encoding='utf-8'))
    source=next(c for c in data['rows'] if c['job']['stage']==4 and c['job']['genre']=='C_I'
        and c['job']['gear']=='basic' and c['job']['pool']==3080000 and c['job']['reference_kind']=='terminal')
    candidates=[]
    for alpha,beta in itertools.product((.3,.4,.5,.6,.8,1.),(2.,2.5,3.,3.5,4.,5.)):
        j={**source['job'],'macro':[alpha,beta,0.,0.,-200.,1.],'terminal_band':True}
        answer=hard.solve(j,j['pool'],'final',0,256)
        candidates.append(dict(job=j,result=answer))
    eligible=[c for c in candidates if c['result']['metrics']['wr']>=.55 and c['result']['metrics']['winning_hp']is not None
        and c['result']['metrics']['winning_hp']<=.18]
    if not eligible:eligible=[c for c in candidates if c['result']['metrics']['wr']>.5 and c['result']['metrics']['winning_hp']is not None
        and c['result']['metrics']['winning_hp']<=.2]
    selected=min(eligible,key=lambda c:((c['result']['metrics']['wr']-.7)/.2)**2+
        ((c['result']['metrics']['winning_hp']-.15)/.1)**2) if eligible else None
    result=dict(parent_key=source['key'],candidates=candidates,selected=selected,
        sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (Path(__file__),HERE/'TERMINAL25_PROTOCOL.md',hard.ROOT/'confirm.json')})
    executed=sum(c['result']['executed_battles'] for c in candidates)
    if selected:
        j=selected['job'];mm,ii,enemy,ei,sim=hard.prepare(j,j['pool'],'final');order=selected['result']['plan']['order']
        m,it=hard.reordered(mm,ii,order);seeds=[old.seed('terminal25-independent',j,i) for i in range(2048)]
        assert not set(seeds)&set(selected['result']['seeds']['test'])
        trials=[hard.project(sim(m,enemy,bs,it,ei,p=j['macro'],enabled=hard.ENABLED)[0]) for bs in seeds]
        prepared={'0':selected['result']};last=order
        for wear in hard.GRID[1:]:
            r=hard.solve(j,j['pool'],'final',wear,32,last);prepared[str(wear)]=r;last=r['plan']['order'];executed+=r['executed_battles']
        grace=json.loads((previous.fit.OUT/'selected.json').read_text(encoding='utf-8'))['stage_policies']['4']
        policies=dict(control=dict(p=0.,l0=0.,l1=0.),immediate=previous.ORIGINAL,grace=grace)
        journeys={name:[hard.journey(j,j['pool'],prepared,p,i) for i in range(64)] for name,p in policies.items()}
        native=sum(len(r) for rr in journeys.values() for r in rr);executed+=2048+native
        result['confirmation']=dict(seeds=seeds,trials=trials,order=order,prepared=prepared,policies=policies,
            journeys=journeys,native_battles=native,members=old.snapshot(mm,ii),enemy=old.snapshot(enemy,ei))
        won=[r for r in trials if r['win']]
        print('terminal25 confirmed WR',len(won)/2048,'winning_hp',sum(r['hp'] for r in won)/len(won) if won else None,
            'macro',j['macro'],flush=True)
    else:print('terminal25 no qualifying calibration candidate',flush=True)
    result['executed_battles']=executed;ROOT.mkdir(parents=True,exist_ok=True);atomic_json(ROOT/'results.json',result)


if __name__=='__main__':main()
