"""Fixed NPC, real roster variability, independent seed precision check."""
import hashlib
import json
import math
from pathlib import Path

import hard_regions as hard
from common import *

ROOT=OUT/'roster25'


def prepare(j):
    mm,_=old.lab.build(4,j['genre'],j['pool'],(),'front','final')
    ii=old.lab.supplies.equipment(mm,j['genre'],4,'basic')
    enemy,ei=hard.npc(4,j['enemy_genre'],j['profile'],3180003,'final')
    return mm,ii,enemy,ei,old.configured_trip(old.PARAMETERS)


def solve(j,wear,trials):
    mm,ii,enemy,ei,sim=prepare(j);seeds={s:[old.seed('roster25',j,wear,s,i) for i in range(n)] for s,n in
        (('train',2),('select',4),('test',trials))};count=0
    def run(order,split):
        nonlocal count
        m,it=hard.reordered(mm,ii,order)
        rr=[hard.project(sim(m,enemy,bs,it,ei,p=j['macro'],enabled=hard.ENABLED,
            factors=(math.exp(-wear),1.,1.,1.,1.))[0]) for bs in seeds[split]]
        count+=len(rr);return rr
    plan=hard.optimize(25,old.lab.native_orders(mm),lambda o,s:hard.rank_score(run(o,s)),old.seed('roster25-order',j,wear),16,3)
    trials=run(plan['order'],'test');won=[r for r in trials if r['win']]
    return dict(plan=plan,seeds=seeds,trials=trials,executed_battles=count,
        metrics=dict(wr=len(won)/len(trials),winning_hp=sum(r['hp'] for r in won)/len(won) if won else None))


def journey(j,prepared,policy,index):
    mm,ii,enemy,ei,sim=prepare(j);state=ExpeditionState('research-troop');rows=[]
    for node in range(1,4):
        wear=state.wear[0];point=min(hard.GRID,key=lambda x:(abs(x-wear),x));order=prepared[str(point)]['plan']['order']
        m,it=hard.reordered(mm,ii,order);bs=old.seed('roster25-journey',j,index,node);roll=old.seed('roster25-loss',j,index,node)/(1<<64)
        r,trace,*_=sim(m,enemy,bs,it,ei,p=j['macro'],enabled=hard.ENABLED,factors=state.factors,telemetry=index==0)
        loss=policy['l0']+policy['l1']*r['damage_exposure'] if roll<policy['p'] else 0.
        if r['win']:state.apply_loss(f'battle:{node}',(loss,0.,0.,0.,0.),'victory')
        row=dict(node=node,wear_before=wear,wear_after=state.wear[0],order=order,battle_seed=bs,event_roll=roll,result=hard.project(r))
        if trace:row['trace']=trace
        rows.append(row)
        if not r['win']:break
    return rows


def main():
    data=json.loads((hard.ROOT/'confirm.json').read_text(encoding='utf-8'))
    base=next(c['job'] for c in data['rows'] if c['job']['stage']==4 and c['job']['reference_kind']=='terminal')
    candidates=[]
    for index in range(24):
        for genre in ('C_I','C_R','M_C'):
            j={**base,'genre':genre,'gear':'basic','pool':3480000+1009*index,'fixed_npc_pool':3180003}
            candidates.append(dict(job=j,result=solve(j,0,128)))
    eligible=[c for c in candidates if c['result']['metrics']['wr']>=.55 and c['result']['metrics']['winning_hp']is not None and c['result']['metrics']['winning_hp']<=.18]
    if not eligible:eligible=[c for c in candidates if c['result']['metrics']['wr']>.5 and c['result']['metrics']['winning_hp']is not None and c['result']['metrics']['winning_hp']<=.2]
    selected=min(eligible,key=lambda c:((c['result']['metrics']['wr']-.7)/.2)**2+((c['result']['metrics']['winning_hp']-.15)/.1)**2) if eligible else None
    result=dict(candidates=candidates,selected=selected,sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        (Path(__file__),HERE/'ROSTER25_PROTOCOL.md',hard.ROOT/'confirm.json')})
    executed=sum(c['result']['executed_battles'] for c in candidates)
    if selected:
        j=selected['job'];mm,ii,enemy,ei,sim=prepare(j);order=selected['result']['plan']['order'];m,it=hard.reordered(mm,ii,order)
        seeds=[old.seed('roster25-independent',j,i) for i in range(2048)]
        rr=[hard.project(sim(m,enemy,bs,it,ei,p=j['macro'],enabled=hard.ENABLED)[0]) for bs in seeds]
        prepared={'0':selected['result']}
        for wear in hard.GRID[1:]:
            p=solve(j,wear,32);prepared[str(wear)]=p;executed+=p['executed_battles']
        policies=dict(control=dict(p=0.,l0=0.,l1=0.),immediate=previous.ORIGINAL,grace=dict(p=.65,l0=.005,l1=.025))
        journeys={name:[journey(j,prepared,p,i) for i in range(64)] for name,p in policies.items()}
        native=sum(len(r) for routes in journeys.values() for r in routes);executed+=2048+native
        result['confirmation']=dict(seeds=seeds,trials=rr,prepared=prepared,journeys=journeys,policies=policies,
            native_battles=native,members=old.snapshot(mm,ii),enemy=old.snapshot(enemy,ei))
        won=[r for r in rr if r['win']]
        print('roster25 confirmed',j['genre'],j['pool'],'WR',len(won)/2048,
            'winning_hp',sum(r['hp'] for r in won)/len(won) if won else None,flush=True)
    else:print('roster25 no qualifying candidate',flush=True)
    result['executed_battles']=executed;ROOT.mkdir(parents=True,exist_ok=True);atomic_json(ROOT/'results.json',result)


if __name__=='__main__':main()
