"""Fresh-roster native confirmation of stage wear and earlier supplies."""
import argparse
import concurrent.futures as cf
import gzip
import hashlib
import json
import math
from pathlib import Path
import sqlite3

import fit_policies as fit
from audit_research import check_manifest
from state_contract import ExpeditionState
from supply_adapter import restore_missing_caps
from run_bonds import atomic_json

old=fit.old
OUT=fit.OUT/'confirmation'
GRID=(0,.05,.1,.2,.35,.5,.7,1,1.4,2,2.8,4.2)
ORIGINAL=dict(p=.65,l0=.08,l1=.2)


def conditions(new):
    return dict(control=dict(policy=dict(p=0.,l0=0.,l1=0.),at=0,rest=0.),
        original=dict(policy=ORIGINAL,at=0,rest=0.),
        original_early=dict(policy=ORIGINAL,at=2,rest=1.),
        original_late=dict(policy=ORIGINAL,at=6,rest=1.),
        revised=dict(policy=new,at=0,rest=0.),
        revised_full=dict(policy=new,at=6,rest=1.),
        revised_partial=dict(policy=new,at=6,rest=.5))


def project(r):
    # Drop the unavailable diagnostic from the old study projection. This
    # changes recorded metadata only, never physics or random draws.
    answer=old.public_result(r)
    answer['metrics'].pop('worker_saves',None)
    answer['metrics']['worker_procs']=r['metrics'].get('worker_procs',0.)
    return answer


def prepare(j):
    return old.prepare(j)


def solve(j,mm,gears,enemy,ei,simulate,wear,previous):
    answer=old.solve(j,mm,gears,enemy,ei,simulate,old.MIXES[j['mix']],wear,previous)
    for rows in [answer['trials']]+list(answer['alternative_trials'].values()):
        for r in rows:r['metrics'].pop('worker_saves',None)
    return answer


def route(j,mm,gears,enemy,ei,simulate,prepared,condition,index):
    state=ExpeditionState('research-troop');rows=[]
    for node in range(1,31):
        wear=state.wear[0];point=min(GRID,key=lambda x:(abs(x-wear),x));choice=prepared[str(point)]
        order=choice['order'];gear=choice['chosen'];m,it=old.reordered(mm,gears[gear],order)
        bs=old.seed('retune-journey',j,index,node);roll=old.seed('retune-loss',j,index,node)/(1<<64)
        r,trace,*_=simulate(m,enemy,bs,it,ei,p=j['macro'],enabled=old.MIXES[j['mix']],
            factors=state.factors,telemetry=index==0 and node<=2)
        policy=condition['policy'];before=state.wear[0]
        loss=policy['l0']+policy['l1']*r['damage_exposure'] if roll<policy['p'] else 0.
        if r['win']:state.apply_loss(f'battle:{node}',(loss,0.,0.,0.,0.),'victory')
        after_battle=state.wear[0]
        if r['win'] and node==condition['at']:
            restore_missing_caps(state,f'supply:{node}',(condition['rest'],)*5)
        row=dict(node=node,result=project(r),order=order,gear=gear,battle_seed=bs,event_roll=roll,
            wear_before=before,wear_after_battle=after_battle,wear_after=state.wear[0])
        if trace:row['trace']=trace
        rows.append(row)
        if not r['win']:break
    return dict(rows=rows,state=state.to_dict())


def evaluate(j):
    mm,gears,enemy,ei,simulate=prepare(j);prepared={};previous=None;executed=0
    for wear in GRID:
        p=solve(j,mm,gears,enemy,ei,simulate,wear,previous)
        prepared[str(wear)]=p;previous=p['order'];executed+=p['executed_battles']
    variants={name:[route(j,mm,gears,enemy,ei,simulate,prepared,c,i) for i in range(32)]
              for name,c in conditions(j['new_policy']).items()}
    native=sum(len(r['rows']) for rr in variants.values() for r in rr);executed+=native
    raw=dict(job=j,members={g:old.snapshot(mm,ii) for g,ii in gears.items()},enemy=old.snapshot(enemy,ei),
        prepared=prepared,variants=variants,executed_battles=executed)
    path=OUT/'replicates'/(j['key']+'.json.gz');path.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(path.with_suffix('.tmp'),'wt',encoding='utf-8') as f:json.dump(raw,f,ensure_ascii=False)
    path.with_suffix('.tmp').replace(path)
    baseline=prepared['0']['trials']
    return dict(executed_battles=executed,native_battles=native,
        preparation_executions=executed-native,baseline_wr=sum(r['win'] for r in baseline)/len(baseline),
        variants={name:dict(reach30=sum(len(r['rows'])==30 for r in rr)/32,
            survive6=sum(len(r['rows'])>=6 and r['rows'][5]['result']['win'] for r in rr)/32,
            censored=sum(q['result']['censored'] for r in rr for q in r['rows'])) for name,rr in variants.items()})


def signature():
    check_manifest(fit.OUT/'fit_manifest.json')
    selected=json.loads((fit.OUT/'selected.json').read_text(encoding='utf-8'))
    assert selected['calibration_sha256']==hashlib.sha256((fit.OUT/'calibration.json').read_bytes()).hexdigest()
    parent=check_manifest(old.OUT/'manifest.json')
    sources={**parent['sources'],**{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        (Path(__file__),fit.HERE/'fit_policies.py',fit.HERE/'PROTOCOL.md',fit.OUT/'selected.json',
         old.HERE/'supply_adapter.py')}}
    body=dict(sources=sources,grid=GRID,selection_signature=selected['signature'],
              protocol='stage-wear-retune-20261027-v1')
    return hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest(),body,selected


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workers',type=int,default=6)
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    sig,body,selected=signature();atomic_json(OUT/'manifest.json',dict(signature=sig,**body))
    jobs=[dict(**{**j,'pool':1780000},new_policy=selected['stage_policies'][str(j['stage'])])
          for j in old.jobs() if j['pool']==1570000 and j['region']=='dominant']
    assert len(jobs)==144
    db=sqlite3.connect(OUT/'checkpoints.sqlite');db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS cells(key TEXT PRIMARY KEY,signature TEXT,job TEXT,result TEXT)');db.commit()
    wanted=set();pending={}
    with cf.ProcessPoolExecutor(args.workers) as pool:
        for j in jobs:
            encoded=json.dumps(j,sort_keys=True);key=hashlib.sha256((sig+encoded).encode()).hexdigest();wanted.add(key)
            if db.execute('SELECT 1 FROM cells WHERE key=?',(key,)).fetchone():continue
            pending[pool.submit(evaluate,dict(**j,key=key))]=key,encoded
        print('fresh confirmation',len(pending),'/144',flush=True)
        for i,f in enumerate(cf.as_completed(pending),1):
            key,encoded=pending[f];result=f.result()
            db.execute('INSERT INTO cells VALUES(?,?,?,?)',(key,sig,encoded,json.dumps(result)));db.commit()
            if i%6==0 or i==len(pending):print('saved',i,'/',len(pending),flush=True)
    rows=[dict(key=k,job=json.loads(j),result=json.loads(r)) for k,j,r in db.execute(
        'SELECT key,job,result FROM cells WHERE signature=?',(sig,)) if k in wanted]
    db.close();assert len(rows)==144
    atomic_json(OUT/'summary.json',dict(signature=sig,cells=144,rows=rows,
        executed_battles=sum(r['result']['executed_battles'] for r in rows)))
    print('fresh confirmation complete:',sum(r['result']['executed_battles'] for r in rows),'executions',flush=True)


if __name__=='__main__':main()
