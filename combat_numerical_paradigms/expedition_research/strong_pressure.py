"""Pre-existing scan's strongest BP/exposure policy on full-budget maid cases.

This is a paired exploratory intensity bound, not a fresh independent holdout.
Player skills, equipment, enemies and independently prepared orders stay fixed.
"""
import argparse
import concurrent.futures as cf
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3

import recovery_stress as stress
from analyze_expedition import model, predict, horizon
from audit_research import check_manifest, equivalent
from confirm_paths import compact, draw
from order_search import reordered
from run_bonds import atomic_json

OUT=stress.lab.OUT/'strong_pressure'
POLICY=dict(profile='bp_only',signal='exposure',p0=.65,p_pressure=.5,loss0=.08,loss_pressure=.3)


def evaluate(cell):
    path=stress.OUT/'replicates'/(cell['key']+'.json.gz')
    with gzip.open(path,'rt',encoding='utf-8') as f:parent=json.load(f)
    j=parent['job'];mm,ii,enemy,ei,simulator,bond=stress.prepare(j)
    routes=[];executed=0;replays=0;censored=0
    for index in range(64):
        wear=0.;route=[]
        for node in range(1,31):
            point=min(stress.lab.GRID,key=lambda x:(abs(x-wear),x));order=parent['prepared'][str(point)]['plan']['order']
            m,it=reordered(mm,ii,order);bs=stress.lab.seed('recovery-native',j,index,node)
            r,trace,*_=simulator(m,enemy,bs,it,ei,p=j['macro'],enabled=(bond,),
                factors=stress.trip_core.factors(stress.lab.PROFILES['bp_only'],wear),telemetry=index==0 and node<=3)
            roll=stress.lab.seed('recovery-event',j,index,node)/(1<<64)
            delta=draw(POLICY,r,roll) if r['win'] else 0.
            row=dict(node=node,order=order,battle_seed=bs,event_roll=roll,wear_before=wear,
                wear_after=wear+delta,result=compact(r))
            if trace:row['trace']=trace
            route.append(row);wear+=delta;executed+=1;censored+=r['censored']
            # Exact first encounter shares the parent stream and no-wear state.
            if node==1:assert equivalent(compact(r),parent['routes']['exposure'][index][0]['result'])
            if j['genre']=='C_I' and index==0:
                q,t,*_=simulator(m,enemy,bs,it,ei,p=j['macro'],enabled=(bond,),
                    factors=stress.trip_core.factors(stress.lab.PROFILES['bp_only'],row['wear_before']),telemetry=bool(trace))
                assert equivalent(compact(q),row['result']) and equivalent(t,trace);replays+=1
            if not r['win']:break
        routes.append(route)
    response=model({f'bp_only:{x}':p for x,p in parent['prepared'].items()},'bp_only')
    forecast=predict(response,POLICY,cell['key'])
    raw=dict(parent_key=cell['key'],parent_archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        policy=POLICY,routes=routes,forecast=forecast,executed_battles=executed,exact_saved_battle_replays=replays)
    destination=OUT/'replicates'/(cell['key']+'.json.gz');destination.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(destination.with_suffix('.tmp'),'wt',encoding='utf-8') as f:json.dump(raw,f,ensure_ascii=False)
    destination.with_suffix('.tmp').replace(destination)
    return dict(stage=j['stage']+1,capacity=stress.lab.STAGES[j['stage']][0],genre=j['genre'],region=j['region'],
        baseline_wr=cell['result']['baseline']['win'],reach30=sum(len(r)>=30 for r in routes)/64,
        forecast_half_battle=horizon(forecast),executed_battles=executed,censored=censored,
        exact_saved_battle_replays=replays)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workers',type=int,default=6);args=p.parse_args()
    parent_manifest=check_manifest(stress.OUT/'manifest.json')
    data=json.loads((stress.OUT/'summary.json').read_text(encoding='utf-8'))
    assert data['signature']==parent_manifest['signature']
    sources={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in
        (Path(__file__),stress.OUT/'summary.json',stress.lab.HERE/'analyze_expedition.py')}
    manifest=dict(parent_signature=data['signature'],sources={**parent_manifest['sources'],**sources},policy=POLICY)
    sig=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    OUT.mkdir(parents=True,exist_ok=True);atomic_json(OUT/'manifest.json',dict(signature=sig,**manifest))
    cells=[r for r in data['rows'] if r['job']['model']=='maid_full'];assert len(cells)==72
    db=sqlite3.connect(OUT/'checkpoints.sqlite');db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS cells(key TEXT,signature TEXT,result TEXT,PRIMARY KEY(key,signature))');db.commit()
    futures={}
    with cf.ProcessPoolExecutor(args.workers) as pool:
        for c in cells:
            if db.execute('select 1 from cells where key=? and signature=?',(c['key'],sig)).fetchone():continue
            futures[pool.submit(evaluate,c)]=c['key']
        print('strong pressure:',len(futures),'/72',flush=True)
        for i,f in enumerate(cf.as_completed(futures),1):
            key=futures[f];result=f.result()
            db.execute('insert into cells values(?,?,?)',(key,sig,json.dumps(result)));db.commit()
            if i%12==0 or i==len(futures):print('saved',i,'/',len(futures),flush=True)
    rows=[dict(key=k,**json.loads(r)) for k,r in db.execute('select key,result from cells where signature=?',(sig,))]
    db.close();assert len(rows)==72
    with (OUT/'case_evidence.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary=dict(signature=sig,cells=72,rows=rows,policy=POLICY,
        executed_battles=sum(r['executed_battles'] for r in rows),
        exact_saved_battle_replays=sum(r['exact_saved_battle_replays'] for r in rows))
    atomic_json(OUT/'summary.json',summary)
    print('strong pressure complete:',summary['executed_battles'],'battles',flush=True)


if __name__=='__main__':main()
