"""Fixed generated-skill NPC search and fresh high-stage low-margin probes."""
import argparse
import concurrent.futures as cf
import copy
from functools import lru_cache
import gzip
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import numpy as np

from common import *
from rosters import bank,NAME_TO_LETTER
from settings import IDENTITIES
from order_search import optimize,rank_score,reordered

ROOT=OUT/'hard_regions'
ENABLED=tuple(IDENTITIES)
GRID=(0,.1,.25,.5,.8)
FAMILIES=(('C_R','repeatable'),('M_I','throughput'),('R_I','debuff'))


@lru_cache(None)
def npc(stage,genre,profile,pool,bank_name):
    members,items=old.lab.build(stage,genre,pool,(),'front',bank_name);skills=bank(bank_name)[0];out=[]
    for member in members:
        m=copy.copy(member);s=m.skill;available=skills[(s.tier,NAME_TO_LETTER[s.genre])]
        if profile=='repeatable':
            eligible=[r for r in available if r[0].times_limit>=999 and not r[0].turn_cond1 and not r[0].turn_cond2]
        elif profile=='debuff':
            eligible=[r for r in available if r[0].sub_effect_name in ('四维削弱','虚弱压制','最大流失','已损流失')]
        else:eligible=[r for r in available if r[0].main_type!='Heal']
        if eligible:
            def score(r):
                sk=r[0];base=100 if sk.main_type=='Heal' else sk.main_param
                if profile=='repeatable':return (sk.trigger_chance,base)
                if profile=='debuff':return (sk.trigger_chance*sk.sub_param,base)
                return (sk.trigger_chance*base/(1+int(bool(sk.turn_cond1 or sk.turn_cond2 or sk.self_bp_cond2))),sk.trigger_chance)
            chosen=max(eligible,key=score)
            m.skill=copy.copy(chosen[0]);m.skill.id=s.id
        out.append(m)
    return tuple(out),items


def project(r):
    return {k:r[k] for k in ('win','hp','margin','turns','censored','minimum_bp_fraction','damage_exposure','owner_casts')} | {
        'worker_procs':r['metrics'].get('worker_procs',0.),'heal':sum(r['metrics'].get(k,0.) for k in ('self_heal','maid_heal','fruit_heal','lifesteal'))}


def prepare(j,pool,bank_name):
    mm,_=old.lab.build(j['stage'],j['genre'],pool,(),'front',bank_name)
    items=old.lab.supplies.equipment(mm,j['genre'],j['stage'],j['gear'])
    enemy,ei=npc(j['stage'],j['enemy_genre'],j['profile'],pool+100003,bank_name)
    sim=old.configured_trip(old.PARAMETERS)
    return mm,items,enemy,ei,sim


def solve(j,pool,bank_name,wear,trials,previous_order=None):
    mm,items,enemy,ei,sim=prepare(j,pool,bank_name);count=0
    seeds={split:[old.seed('hard-reference',j,pool,wear,split,i) for i in range(n)]
           for split,n in (('train',2),('select',4),('test',trials))}
    def run(order,split):
        nonlocal count
        m,it=reordered(mm,items,order);rows=[]
        for bs in seeds[split]:
            r,*_=sim(m,enemy,bs,it,ei,p=j['macro'],enabled=ENABLED,factors=(math.exp(-wear),1.,1.,1.,1.))
            rows.append(project(r))
        count+=len(rows);return rows
    starts=old.lab.native_orders(mm)
    if previous_order:starts=[previous_order]+starts
    plan=optimize(len(mm),starts,lambda o,s:rank_score(run(o,s)),old.seed('hard-order',j,pool,wear),16,3)
    rr=run(plan['order'],'test');won=[r for r in rr if r['win']]
    metrics=dict(wr=sum(r['win'] for r in rr)/len(rr),
        winning_hp=sum(r['hp'] for r in won)/len(won) if won else None,
        winning_minimum=sum(r['minimum_bp_fraction'] for r in won)/len(won) if won else None,
        winning_worker=sum(r['worker_procs'] for r in won)/len(won) if won else None)
    return dict(plan=plan,seeds=seeds,trials=rr,metrics=metrics,executed_battles=count)


def calibration_jobs():
    tasks=[]
    for stage in (3,4,5):
        for genre,profile in FAMILIES:
            rng=np.random.default_rng(old.seed('hard-latin',stage,genre,profile));matrix=np.empty((24,6))
            for k in range(6):matrix[:,k]=(rng.permutation(24)+rng.random(24))/24
            lo=np.array([.4,.5,0.,0.,-200.,.8]);hi=np.array([2.5,4.,.4,.12,500.,2.])
            for index,v in enumerate(lo+matrix*(hi-lo)):
                tasks.append(dict(stage=stage,enemy_genre=genre,profile=profile,index=index,macro=v.tolist()))
    return tasks


def calibrate(j):
    answers=[];count=0
    for genre in old.lab.GENRES:
        for gear in ('basic','four_top'):
            case=dict(**j,genre=genre,gear=gear)
            result=solve(case,2780000,'validation',0,24)
            answers.append(dict(genre=genre,gear=gear,**result));count+=result['executed_battles']
    return dict(cases=answers,executed_battles=count)


def choose(rows):
    selected=[]
    for stage in (3,4,5):
        candidates=[r for r in rows if r['job']['stage']==stage]
        def score(cell,kind):
            mm=[r['metrics'] for r in cell['result']['cases']]
            target='winning_hp' if kind=='terminal' else 'winning_minimum'
            qualifying=sum(r['wr']>.5 and r[target] is not None and r[target]<=.2 for r in mm)
            distance=sum(((r['wr']-.7)/.3)**2+(((r[target] if r[target]is not None else 1.)-.15)/.3)**2 for r in mm)/len(mm)
            return (-qualifying,distance)
        used=set()
        for kind in ('terminal','minimum'):
            available=[r for r in candidates if r['key']not in used]
            winner=min(available,key=lambda r:score(r,kind));used.add(winner['key'])
            selected.append(dict(**winner['job'],reference_kind=kind,source_key=winner['key'],calibration_score=score(winner,kind)))
    atomic_json(ROOT/'selected.json',dict(references=selected))


def journey(j,pool,prepared,policy,index):
    mm,items,enemy,ei,sim=prepare(j,pool,'final');state=ExpeditionState('research-troop');rows=[]
    for node in range(1,4):
        wear=state.wear[0];point=min(GRID,key=lambda x:(abs(x-wear),x));order=prepared[str(point)]['plan']['order']
        m,it=reordered(mm,items,order);bs=old.seed('hard-native',j,pool,index,node);roll=old.seed('hard-loss',j,pool,index,node)/(1<<64)
        r,trace,*_=sim(m,enemy,bs,it,ei,p=j['macro'],enabled=ENABLED,factors=state.factors,telemetry=index==0)
        loss=policy['l0']+policy['l1']*r['damage_exposure'] if roll<policy['p'] else 0.
        if r['win']:state.apply_loss(f'battle:{node}',(loss,0.,0.,0.,0.),'victory')
        row=dict(node=node,wear_before=wear,wear_after=state.wear[0],battle_seed=bs,event_roll=roll,order=order,result=project(r))
        if trace:row['trace']=trace
        rows.append(row)
        if not r['win']:break
    return rows


def confirm(j):
    pool=j['pool'];prepared={};last=None;count=0
    for wear in GRID:
        r=solve(j,pool,'final',wear,96 if wear==0 else 32,last)
        prepared[str(wear)]=r;last=r['plan']['order'];count+=r['executed_battles']
    grace=json.loads((previous.fit.OUT/'selected.json').read_text(encoding='utf-8'))['stage_policies'][str(j['stage'])]
    policies=dict(control=dict(p=0.,l0=0.,l1=0.),immediate=previous.ORIGINAL,grace=grace)
    journeys={name:[journey(j,pool,prepared,p,i) for i in range(64)] for name,p in policies.items()}
    native=sum(len(r) for rr in journeys.values() for r in rr);count+=native
    mm,ii,enemy,ei,_=prepare(j,pool,'final')
    raw=dict(job=j,members=old.snapshot(mm,ii),enemy=old.snapshot(enemy,ei),prepared=prepared,policies=policies,
        journeys=journeys,executed_battles=count)
    path=ROOT/'replicates'/(j['key']+'.json.gz');path.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(path.with_suffix('.tmp'),'wt',encoding='utf-8') as f:json.dump(raw,f,ensure_ascii=False)
    path.with_suffix('.tmp').replace(path)
    return dict(executed_battles=count,native_battles=native,baseline=prepared['0']['metrics'],
        survive3={name:sum(len(r)==3 and r[-1]['result']['win'] for r in rr)/64 for name,rr in journeys.items()})


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('calibrate','confirm'),required=True)
    parser.add_argument('--workers',type=int,default=3);args=parser.parse_args();ROOT.mkdir(parents=True,exist_ok=True)
    parent=check_manifest(previous.OUT/'manifest.json')
    sources={**parent['sources'],**{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        (Path(__file__),HERE/'common.py',HERE/'PROTOCOL.md')}}
    if args.phase=='confirm':sources[str(ROOT/'selected.json')]=hashlib.sha256((ROOT/'selected.json').read_bytes()).hexdigest()
    body=dict(sources=sources,enabled=ENABLED,scope='generated skills, fixed NPC, full player identity effects')
    sig=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()
    atomic_json(ROOT/(args.phase+'_manifest.json'),dict(signature=sig,**body))
    if args.phase=='calibrate':jobs=calibration_jobs();function=calibrate
    else:
        refs=json.loads((ROOT/'selected.json').read_text(encoding='utf-8'))['references'];jobs=[];function=confirm
        for ref in refs:
            for genre in old.lab.GENRES:
                for gear in ('basic','four_top'):
                    for pool in (2980000,3080000):jobs.append(dict(**ref,genre=genre,gear=gear,pool=pool))
    db=sqlite3.connect(ROOT/'checkpoints.sqlite');db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS cells(key TEXT PRIMARY KEY,signature TEXT,phase TEXT,job TEXT,result TEXT)');db.commit()
    pending={};wanted=set()
    with cf.ProcessPoolExecutor(args.workers) as executor:
        for j in jobs:
            encoded=json.dumps(j,sort_keys=True);key=hashlib.sha256((sig+encoded).encode()).hexdigest();wanted.add(key)
            if db.execute('SELECT 1 FROM cells WHERE key=?',(key,)).fetchone():continue
            pending[executor.submit(function,dict(**j,key=key))]=key,encoded
        print('hard reference',args.phase,len(pending),'/',len(jobs),flush=True)
        for i,f in enumerate(cf.as_completed(pending),1):
            key,encoded=pending[f];r=f.result();db.execute('INSERT INTO cells VALUES(?,?,?,?,?)',(key,sig,args.phase,encoded,json.dumps(r)));db.commit()
            if i%12==0 or i==len(pending):print('hard saved',i,'/',len(pending),flush=True)
    rows=[dict(key=k,job=json.loads(j),result=json.loads(r)) for k,j,r in db.execute(
        'SELECT key,job,result FROM cells WHERE signature=? AND phase=?',(sig,args.phase)) if k in wanted]
    db.close();assert len(rows)==len(jobs)
    atomic_json(ROOT/(args.phase+'.json'),dict(signature=sig,cells=len(rows),rows=rows,
        executed_battles=sum(r['result']['executed_battles'] for r in rows)))
    if args.phase=='calibrate':choose(rows)
    print('hard',args.phase,'complete',flush=True)


if __name__=='__main__':main()
