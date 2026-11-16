"""Independent mixed-bond, equipment-owner and supply-loop native experiment."""
import argparse
import concurrent.futures as cf
import gzip
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import measure_response as lab
from bond_trip_core import configured_trip
from configured_compound_core import variants
from order_search import initial_orders,optimize,rank_score,reordered,snapshot
from rosters import availability
from run_bonds import atomic_json
from state_contract import ExpeditionState,victory_losses

OUT=HERE/'results'
GRID=(0,.35,.7,1.2,2.1,3.4,4.2)
MIXES={'engineer_scholar':('engineer','scholar'),'ninja_worker':('ninja','worker'),
       'farmer_scholar':('farmer','scholar'),'maid_engineer':('maid','engineer')}
PARAMETERS=dict(variants('maid'))['addition_0.5']


def seed(label,*values):
    return lab.seed('closure-20261027',label,json.dumps(values,sort_keys=True,separators=(',',':')))


def public_result(r):
    keys=('win','hp','margin','turns','censored','damage_exposure','minimum_bp_fraction','normal_rate','owner_casts')
    diagnostics=('engineer_casts','scholar_restored','absolute_dodges','worker_saves','maid_casts',
                 'fruit_harvest','fruit_heal','fruit_stats_total','maid_heal','damage_received')
    return {**{k:r[k] for k in keys},'metrics':{k:r['metrics'].get(k,0.) for k in diagnostics}}


def equipment_candidates(mm,j):
    original=lab.supplies.equipment(mm,j['genre'],j['stage'],'four_top')
    base=lab.supplies.equipment(mm,j['genre'],j['stage'],'basic')
    out=list(base);remaining=set(range(len(mm)))
    top=[i for i in original if i.top]
    first_maid=next((i for i,m in enumerate(mm) if m.identity=='女仆'),None)
    for source in sorted(top,key=lambda it:(it.kind=='opening_shield',it.kind)):
        def score(i):
            m=mm[i];s=m.skill
            p=1. if i==first_maid else s.trigger_chance/100
            heal=(i==first_maid or s.main_type=='Heal' or s.sub_effect_name=='战力吸收')
            if source.kind=='owner_stats':return sum(m.stats)
            if source.kind=='opening_shield':return -p*s.main_param
            if source.kind in ('skill_heal','overheal_shield'):return p*heal
            if source.kind=='extra_use':return p*(i!=first_maid and 0<s.times_limit<999)
            if source.kind=='skill_dot':return p*(i!=first_maid and s.sub_effect_name in ('最大流失','已损流失','固定流失'))
            if source.kind=='normal_damage':return 1-p
            return p*(1. if i==first_maid else s.main_param/100)
        owner=max(remaining,key=lambda i:(score(i),-i));remaining.remove(owner)
        item=lab.supplies.natural.Item(source.kind,source.value,base[owner].stats,base[owner].bp,True)
        out[owner]=item
    candidate=tuple(out)
    assert len(candidate)==len(mm) and sum(it.top for it in candidate)==4
    assert all(a.stats==b.stats and a.bp==b.bp for a,b in zip(candidate,original))
    assert sorted((i.kind,i.value) for i in candidate if i.top)==sorted((i.kind,i.value) for i in original if i.top)
    return dict(original=original,reassigned=candidate)


def prepare(j):
    mm,_=lab.build(j['stage'],j['genre'],j['pool'],tuple(tuple(c) for c in j['composition']),'front','final')
    enemy,ei=lab.build(j['stage'],j['enemy_genre'],j['pool']+100003,(),'front','final')
    return mm,equipment_candidates(mm,j),enemy,ei,configured_trip(PARAMETERS)


def solve(j,mm,gears,enemy,ei,simulate,enabled,wear,previous=None):
    seeds={split:[seed('battle',j,wear,split,i) for i in range(n)] for split,n in
           (('train',2),('select',4),('test',96 if wear==0 else 24))}
    count=0;cache={}
    def run(gear,order,split):
        nonlocal count
        key=(gear,tuple(order),split)
        if key not in cache:
            m,it=reordered(mm,gears[gear],order)
            rr=[public_result(simulate(m,enemy,bs,it,ei,p=j['macro'],enabled=enabled,
                factors=(math.exp(-wear),1.,1.,1.,1.))[0]) for bs in seeds[split]]
            cache[key]=rr;count+=len(rr)
        return cache[key]
    starts=[]
    for bond in MIXES[j['mix']]:starts+=initial_orders(mm,bond)
    if previous:starts=[previous]+starts
    plans={}
    for gear in gears:
        plans[gear]=optimize(len(mm),starts,lambda o,s:rank_score(run(gear,o,s)),
            seed('order',j,enabled,wear,gear),16,3)
    chosen=max(gears,key=lambda gear:(rank_score(run(gear,plans[gear]['order'],'select')),gear=='original'))
    # Final test is never observed when choosing ownership or order.
    rr=run(chosen,plans[chosen]['order'],'test')
    alternative={g:run(g,plans[g]['order'],'test') for g in gears}
    return dict(plans=plans,chosen=chosen,order=plans[chosen]['order'],seeds=seeds,trials=rr,
        alternative_trials=alternative,executed_battles=count)


def route(j,mm,gears,enemy,ei,simulate,prepared,index,removal):
    state=ExpeditionState('research-troop');rows=[]
    for node in range(1,31):
        wear=state.wear[0];point=min(GRID,key=lambda x:(abs(x-wear),x));chosen=prepared[str(point)]
        order=chosen['order'];gear=chosen['chosen'];m,it=reordered(mm,gears[gear],order)
        bs=seed('journey',j,index,node);roll=seed('loss',j,index,node)/(1<<64)
        r,trace,*_=simulate(m,enemy,bs,it,ei,p=j['macro'],enabled=MIXES[j['mix']],
            factors=state.factors,telemetry=index==0 and node<=2)
        before=state.wear[0]
        if r['win']:
            state.apply_loss(f'battle:{node}',victory_losses(r['hp'],r['damage_exposure'],roll),'victory')
        after_battle=state.wear[0]
        if r['win'] and node==6 and removal:
            state.supply('supply:6',(removal,)*5)
        row=dict(node=node,wear_before=before,wear_after_battle=after_battle,wear_after=state.wear[0],
            result=public_result(r),order=order,gear=gear,battle_seed=bs,event_roll=roll)
        if trace:row['trace']=trace
        rows.append(row)
        if not r['win']:break
    return dict(rows=rows,state=state.to_dict())


def evaluate(j):
    mm,gears,enemy,ei,simulate=prepare(j);prepared={};previous=None;count=0
    for wear in GRID:
        p=solve(j,mm,gears,enemy,ei,simulate,MIXES[j['mix']],wear,previous)
        prepared[str(wear)]=p;previous=p['order'];count+=p['executed_battles']
    ablation={}
    for enabled in ((),(MIXES[j['mix']][0],),(MIXES[j['mix']][1],)):
        label='+'.join(enabled) or 'off'
        answer=solve(j,mm,gears,enemy,ei,simulate,enabled,0)
        ablation[label]=answer;count+=answer['executed_battles']
    routes={str(removal):[route(j,mm,gears,enemy,ei,simulate,prepared,i,removal) for i in range(32)]
            for removal in (0.,.5,1.)}
    native=sum(len(r['rows']) for routeset in routes.values() for r in routeset);count+=native
    raw=dict(job=j,members={g:snapshot(mm,ii) for g,ii in gears.items()},enemy=snapshot(enemy,ei),
        prepared=prepared,ablation=ablation,routes=routes,executed_battles=count)
    path=OUT/'replicates'/(j['key']+'.json.gz');path.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(path.with_suffix('.tmp'),'wt',encoding='utf-8') as f:json.dump(raw,f,ensure_ascii=False)
    path.with_suffix('.tmp').replace(path)
    win=lambda p:sum(r['win'] for r in p['trials'])/len(p['trials'])
    return dict(executed_battles=count,native_journey_battles=native,
        baseline_wr=win(prepared['0']),ablation_wr={k:win(v) for k,v in ablation.items()},
        state_wr={x:win(p) for x,p in prepared.items()},
        reach30={removal:sum(len(r['rows'])==30 for r in rr)/32 for removal,rr in routes.items()},
        censored=sum(q['result']['censored'] for rr in routes.values() for r in rr for q in r['rows']))


def signature():
    _,manifest=lab.signature()
    paths=[Path(__file__),HERE/'state_contract.py',lab.HERE/'bond_trip_core.py',
           lab.OUT/'regions.json',lab.engine.SYNERGY/'configured_compound_core.py',
           lab.engine.SYNERGY/'compound_core.py',lab.engine.SYNERGY/'compound_effects.json']
    sources={**manifest['sources'],**{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
    body=dict(sources=sources,grid=GRID,parameters=PARAMETERS,mixes=MIXES,protocol='closure-20261027-v1')
    return hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest(),body


def jobs():
    regions=json.loads((lab.OUT/'regions.json').read_text(encoding='utf-8'))['regions']
    available={(r['stage']-1,r['bond']):r['available'] for r in availability()}
    result=[]
    for r in regions:
        if r['region'] not in ('dominant','clutch'):continue
        s=r['stage'];n=lab.STAGES[s][0]
        for g in lab.GENRES:
            for pool in (1570000,1670000):
                for name,bonds in MIXES.items():
                    composition=[(key,min(n//2,available[s,key])) for key in bonds]
                    result.append(dict(stage=s,genre=g,pool=pool,mix=name,composition=composition,
                        region=r['region'],enemy_genre=r['enemy_genre'],macro=r['macro']))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workers',type=int,default=6);p.add_argument('--limit',type=int)
    args=p.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    sig,body=signature();atomic_json(OUT/'manifest.json',dict(signature=sig,**body))
    db=sqlite3.connect(OUT/'checkpoints.sqlite');db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS cells(key TEXT PRIMARY KEY,signature TEXT,job TEXT,result TEXT)');db.commit()
    planned=jobs();planned=planned[:args.limit] if args.limit else planned
    wanted=set();pending={}
    with cf.ProcessPoolExecutor(args.workers) as pool:
        for j in planned:
            encoded=json.dumps(j,sort_keys=True);key=hashlib.sha256((sig+encoded).encode()).hexdigest();wanted.add(key)
            if db.execute('SELECT 1 FROM cells WHERE key=?',(key,)).fetchone():continue
            pending[pool.submit(evaluate,dict(**j,key=key))]=(key,encoded)
        print('closure:',len(pending),'pending /',len(planned),flush=True)
        for i,f in enumerate(cf.as_completed(pending),1):
            key,encoded=pending[f];answer=f.result()
            db.execute('INSERT INTO cells VALUES(?,?,?,?)',(key,sig,encoded,json.dumps(answer)));db.commit()
            if i%6==0 or i==len(pending):print('saved',i,'/',len(pending),flush=True)
    rows=[dict(key=k,job=json.loads(j),result=json.loads(r)) for k,j,r in db.execute(
        'SELECT key,job,result FROM cells WHERE signature=?',(sig,)) if k in wanted]
    db.close();assert len(rows)==len(planned)
    atomic_json(OUT/('smoke_summary.json' if args.limit else 'summary.json'),dict(signature=sig,cells=len(rows),rows=rows,
        executed_battles=sum(r['result']['executed_battles'] for r in rows)))
    print('complete:',len(rows),'cells',sum(r['result']['executed_battles'] for r in rows),'executions',flush=True)


if __name__=='__main__':main()
