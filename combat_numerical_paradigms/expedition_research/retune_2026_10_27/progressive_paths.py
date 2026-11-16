"""Paired exploratory journeys with loss intensifying after six wins."""
import concurrent.futures as cf
import gzip
import hashlib
import json
import math
from pathlib import Path
import sqlite3

import confirm_policies as native
from audit_research import check_manifest,equivalent
from state_contract import ExpeditionState
from supply_adapter import restore_missing_caps
from run_bonds import atomic_json

OUT=native.fit.OUT/'progressive'
CONDITIONS={'progressive':0.,'progressive_full':1.,'progressive_partial':.5}


def route(j,mm,gears,enemy,ei,simulate,prepared,index,rest):
    state=ExpeditionState('research-troop');rows=[];counter=0
    for node in range(1,31):
        wear=state.wear[0];point=min(native.GRID,key=lambda x:(abs(x-wear),x));choice=prepared[str(point)]
        m,it=native.old.reordered(mm,gears[choice['chosen']],choice['order'])
        bs=native.old.seed('retune-journey',j,index,node);roll=native.old.seed('retune-loss',j,index,node)/(1<<64)
        r,trace,*_=simulate(m,enemy,bs,it,ei,p=j['macro'],enabled=native.old.MIXES[j['mix']],
            factors=state.factors,telemetry=index==0 and node<=2)
        before=state.wear[0];before_count=counter;policy=j['new_policy'] if counter<6 else native.ORIGINAL
        loss=policy['l0']+policy['l1']*r['damage_exposure'] if roll<policy['p'] else 0.
        if r['win']:
            state.apply_loss(f'battle:{node}',(loss,0.,0.,0.,0.),'victory');counter+=1
        after_battle=state.wear[0]
        if r['win'] and node==6 and rest:
            restore_missing_caps(state,'supply:6',(rest,)*5)
            if rest==1.:counter=0
        row=dict(node=node,result=native.project(r),order=choice['order'],gear=choice['chosen'],battle_seed=bs,
            event_roll=roll,wear_before=before,wear_after_battle=after_battle,wear_after=state.wear[0],
            counter_before=before_count,counter_after=counter)
        if trace:row['trace']=trace
        rows.append(row)
        if not r['win']:break
    return dict(rows=rows,state=state.to_dict(),counter=counter)


def evaluate(cell):
    path=native.OUT/'replicates'/(cell['key']+'.json.gz')
    with gzip.open(path,'rt',encoding='utf-8') as f:parent=json.load(f)
    j=parent['job'];mm,gears,enemy,ei,sim=native.prepare(j)
    variants={name:[route(j,mm,gears,enemy,ei,sim,parent['prepared'],i,rest) for i in range(32)]
              for name,rest in CONDITIONS.items()}
    for name,routes in variants.items():
        ref=parent['variants'][{'progressive':'revised','progressive_full':'revised_full','progressive_partial':'revised_partial'}[name]]
        for i,r in enumerate(routes):
            assert len(r['rows'])>=min(6,len(ref[i]['rows']))
            for a,b in zip(r['rows'][:6],ref[i]['rows'][:6]):
                assert equivalent(a['result'],b['result']) and a['wear_after']==b['wear_after']
    executed=sum(len(r['rows']) for rr in variants.values() for r in rr)
    raw=dict(job=j,parent_key=cell['key'],parent_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        variants=variants,executed_battles=executed)
    out=OUT/'replicates'/(cell['key']+'.json.gz');out.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(out.with_suffix('.tmp'),'wt',encoding='utf-8') as f:json.dump(raw,f,ensure_ascii=False)
    out.with_suffix('.tmp').replace(out)
    return dict(executed_battles=executed,variants={name:dict(reach30=sum(len(r['rows'])==30 for r in rr)/32,
        survive6=sum(len(r['rows'])>=6 and r['rows'][5]['result']['win'] for r in rr)/32,
        censored=sum(q['result']['censored'] for r in rr for q in r['rows'])) for name,rr in variants.items()})


def main():
    manifest=check_manifest(native.OUT/'manifest.json')
    data=json.loads((native.OUT/'summary.json').read_text(encoding='utf-8'))
    assert data['signature']==manifest['signature']
    sources={**manifest['sources'],**{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        (Path(__file__),native.fit.HERE/'PROGRESSIVE_PROTOCOL.md',native.OUT/'summary.json')}}
    body=dict(parent_signature=data['signature'],sources=sources,conditions=CONDITIONS)
    sig=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()
    OUT.mkdir(parents=True,exist_ok=True);atomic_json(OUT/'manifest.json',dict(signature=sig,**body))
    db=sqlite3.connect(OUT/'checkpoints.sqlite');db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS cells(key TEXT,signature TEXT,result TEXT,PRIMARY KEY(key,signature))');db.commit()
    pending={}
    with cf.ProcessPoolExecutor(6) as pool:
        for cell in data['rows']:
            if db.execute('SELECT 1 FROM cells WHERE key=? AND signature=?',(cell['key'],sig)).fetchone():continue
            pending[pool.submit(evaluate,cell)]=cell['key']
        print('progressive',len(pending),'/144',flush=True)
        for i,f in enumerate(cf.as_completed(pending),1):
            key=pending[f];result=f.result()
            db.execute('INSERT INTO cells VALUES(?,?,?)',(key,sig,json.dumps(result)));db.commit()
            if i%12==0 or i==len(pending):print('saved',i,'/',len(pending),flush=True)
    rows=[dict(key=k,result=json.loads(r)) for k,r in db.execute('SELECT key,result FROM cells WHERE signature=?',(sig,))]
    db.close();assert len(rows)==144
    atomic_json(OUT/'summary.json',dict(signature=sig,cells=144,rows=rows,
        executed_battles=sum(r['result']['executed_battles'] for r in rows)))
    print('progressive complete',sum(r['result']['executed_battles'] for r in rows),'native battles',flush=True)


if __name__=='__main__':main()
