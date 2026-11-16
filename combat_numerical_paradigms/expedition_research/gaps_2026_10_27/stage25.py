"""Old-response selection and independent native confirmation of stage-25 tails."""
import argparse
import concurrent.futures as cf
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
import sqlite3
import numpy as np

from common import *

ROOT=OUT/'stage25'
PREFIX=dict(p=.65,l0=.005,l1=.025)


def forecast(raw,tail):
    grid=np.array(previous.GRID);pp=[];ex=[];counts=[]
    for x in previous.GRID:
        rr=raw['prepared'][str(x)]['trials'];ww=[r for r in rr if r['win']]
        pp.append(len(ww)/len(rr));counts.append(len(ww));ex.append([r['damage_exposure'] for r in ww]+[1.]*(96-len(ww)))
    pp=np.array(pp);counts=np.array(counts);ex=np.array(ex)
    n=512;rng=np.random.default_rng(old.seed('stage25-fit',raw['job']['genre'],raw['job']['mix']))
    wear=np.zeros(n);weights=np.ones(n);half=31;q30=None
    for node in range(1,31):
        hi=np.searchsorted(grid,wear,side='right').clip(1,len(grid)-1);lo=hi-1
        t=((wear-grid[lo])/(grid[hi]-grid[lo])).clip(0,1);p=(1-t)*pp[lo]+t*pp[hi];mass=weights.sum()
        q=float(np.dot(weights,p)/mass) if mass>1e-100 else 0.
        if q<=.5 and half==31:half=node
        point=np.where(rng.random(n)<np.divide(t*pp[hi],p,out=np.zeros(n),where=p>0),hi,lo)
        pos=(rng.random(n)*np.maximum(1,counts[point])).astype(int).clip(0,95)
        policy=PREFIX if node<=6 else tail
        wear+=np.where(rng.random(n)<policy['p'],-np.log1p(-(policy['l0']+policy['l1']*ex[point,pos])),0.)
        weights*=p;q30=q
    return dict(half=half,wr30=q30)


def fit():
    manifest=check_manifest(previous.OUT/'manifest.json')
    data=json.loads((previous.OUT/'summary.json').read_text(encoding='utf-8'))
    cells=[r for r in data['rows'] if r['job']['stage']==4]
    references=[];archives={}
    for c in cells:
        path=previous.OUT/'replicates'/(c['key']+'.json.gz')
        with gzip.open(path,'rt',encoding='utf-8') as f:references.append(json.load(f))
        archives[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    answers=[]
    for p,l0 in itertools.product((.65,.85,1.),(.08,.12,.16,.2)):
        policy=dict(p=p,l0=l0,l1=.2);rr=[forecast(r,policy) for r in references]
        answers.append(dict(policy=policy,coverage=sum(r['half']<=30 for r in rr)/len(rr),
            expected_zero_exposure_log_loss=p*-math.log1p(-l0),references=rr))
    feasible=[r for r in answers if r['coverage']>=.9]
    chosen=min(feasible,key=lambda r:(r['expected_zero_exposure_log_loss'],r['policy']['l0'])) if feasible else max(answers,key=lambda r:r['coverage'])
    ROOT.mkdir(parents=True,exist_ok=True)
    result=dict(prefix=PREFIX,tail=chosen['policy'],calibration_coverage=chosen['coverage'],
        calibration_candidates=answers,calibration_archives=archives,parent_signature=manifest['signature'])
    atomic_json(ROOT/'selected.json',result)
    print('stage25 chosen',chosen['policy'],'coverage',chosen['coverage'],flush=True)


def conditions(tail):
    return dict(control=dict(tail=dict(p=0.,l0=0.,l1=0.),prefix=dict(p=0.,l0=0.,l1=0.),rest=0.,reset=False),
        old=dict(tail=previous.ORIGINAL,prefix=PREFIX,rest=0.,reset=False),
        revised=dict(tail=tail,prefix=PREFIX,rest=0.,reset=False),
        full_reset=dict(tail=tail,prefix=PREFIX,rest=1.,reset=True),
        clear_only=dict(tail=tail,prefix=PREFIX,rest=1.,reset=False),
        half_only=dict(tail=tail,prefix=PREFIX,rest=.5,reset=False))


def route(j,mm,gears,enemy,ei,sim,prepared,condition,index):
    state=ExpeditionState('research-troop');counter=0;rows=[]
    for node in range(1,31):
        wear=state.wear[0];point=min(previous.GRID,key=lambda x:(abs(x-wear),x));choice=prepared[str(point)]
        m,it=old.reordered(mm,gears[choice['chosen']],choice['order'])
        bs=old.seed('stage25-journey',j,index,node);roll=old.seed('stage25-loss',j,index,node)/(1<<64)
        r,trace,*_=sim(m,enemy,bs,it,ei,p=j['macro'],enabled=old.MIXES[j['mix']],
            factors=state.factors,telemetry=index==0 and node<=2)
        policy=condition['prefix'] if counter<6 else condition['tail'];before=counter
        loss=policy['l0']+policy['l1']*r['damage_exposure'] if roll<policy['p'] else 0.
        if r['win']:state.apply_loss(f'battle:{node}',(loss,0.,0.,0.,0.),'victory');counter+=1
        after_battle=state.wear[0]
        if r['win'] and node==6 and condition['rest']:
            restore_missing_caps(state,'supply:6',(condition['rest'],)*5)
            if condition['reset']:counter=0
        row=dict(node=node,result=previous.project(r),gear=choice['chosen'],order=choice['order'],battle_seed=bs,
            event_roll=roll,wear_before=wear,wear_after_battle=after_battle,wear_after=state.wear[0],
            counter_before=before,counter_after=counter)
        if trace:row['trace']=trace
        rows.append(row)
        if not r['win']:break
    return dict(rows=rows,state=state.to_dict(),counter=counter)


def evaluate(j):
    mm,gears,enemy,ei,sim=previous.prepare(j);prepared={};last=None;executed=0
    for wear in previous.GRID:
        p=previous.solve(j,mm,gears,enemy,ei,sim,wear,last);prepared[str(wear)]=p;last=p['order'];executed+=p['executed_battles']
    variants={name:[route(j,mm,gears,enemy,ei,sim,prepared,c,i) for i in range(32)] for name,c in conditions(j['tail']).items()}
    native=sum(len(r['rows']) for rr in variants.values() for r in rr);executed+=native
    raw=dict(job=j,members={g:old.snapshot(mm,it) for g,it in gears.items()},enemy=old.snapshot(enemy,ei),
        prepared=prepared,variants=variants,executed_battles=executed)
    path=ROOT/'replicates'/(j['key']+'.json.gz');path.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(path.with_suffix('.tmp'),'wt',encoding='utf-8') as f:json.dump(raw,f,ensure_ascii=False)
    path.with_suffix('.tmp').replace(path)
    return dict(executed_battles=executed,native_battles=native,
        baseline_wr=sum(r['win'] for r in prepared['0']['trials'])/96,
        variants={name:dict(reach30=sum(len(r['rows'])==30 for r in rr)/32,
            s6=sum(len(r['rows'])>=6 and r['rows'][5]['result']['win'] for r in rr)/32) for name,rr in variants.items()})


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('fit','confirm'),required=True)
    parser.add_argument('--workers',type=int,default=3);args=parser.parse_args()
    if args.phase=='fit':fit();return
    selected=json.loads((ROOT/'selected.json').read_text(encoding='utf-8'))
    parent=check_manifest(previous.OUT/'manifest.json')
    paths=[Path(__file__),HERE/'PROTOCOL.md',HERE/'common.py',ROOT/'selected.json']
    body=dict(parent_signature=parent['signature'],sources={**parent['sources'],
        **{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}},tail=selected['tail'])
    sig=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest();atomic_json(ROOT/'manifest.json',dict(signature=sig,**body))
    templates=[j for j in old.jobs() if j['stage']==4 and j['pool']==1570000 and j['region']=='dominant']
    jobs=[dict(**{**j,'pool':pool},tail=selected['tail']) for j in templates for pool in (2580000,2680000)]
    db=sqlite3.connect(ROOT/'checkpoints.sqlite');db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS cells(key TEXT PRIMARY KEY,signature TEXT,job TEXT,result TEXT)');db.commit()
    pending={};wanted=set()
    with cf.ProcessPoolExecutor(args.workers) as pool:
        for j in jobs:
            encoded=json.dumps(j,sort_keys=True);key=hashlib.sha256((sig+encoded).encode()).hexdigest();wanted.add(key)
            if db.execute('SELECT 1 FROM cells WHERE key=?',(key,)).fetchone():continue
            pending[pool.submit(evaluate,dict(**j,key=key))]=key,encoded
        print('stage25 confirmation',len(pending),'/48',flush=True)
        for i,f in enumerate(cf.as_completed(pending),1):
            key,encoded=pending[f];r=f.result();db.execute('INSERT INTO cells VALUES(?,?,?,?)',(key,sig,encoded,json.dumps(r)));db.commit()
            if i%6==0:print('stage25 saved',i,flush=True)
    rows=[dict(key=k,job=json.loads(j),result=json.loads(r)) for k,j,r in db.execute('SELECT key,job,result FROM cells WHERE signature=?',(sig,)) if k in wanted]
    db.close();assert len(rows)==48
    atomic_json(ROOT/'summary.json',dict(signature=sig,cells=48,rows=rows,
        executed_battles=sum(r['result']['executed_battles'] for r in rows)))
    print('stage25 complete',flush=True)


if __name__=='__main__':main()
