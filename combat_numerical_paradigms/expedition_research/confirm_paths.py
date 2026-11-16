"""Held-out native journeys and dungeon prefixes with actual event rolls."""
import argparse
import concurrent.futures as cf
import gzip
import hashlib
import json
import math
from pathlib import Path
import sqlite3

import measure_response as lab
from order_search import reordered, snapshot
from run_bonds import atomic_json

OUT=lab.OUT/'confirmation'


def compact(r):
    return {k:r[k] for k in ('win','hp','turns','censored','damage_exposure','minimum_bp_fraction')}


def draw(policy,r,roll):
    pressure=1-r['hp'] if policy['signal']=='end_hp' else r['damage_exposure']
    probability=min(1.,policy['p0']+policy['p_pressure']*pressure)
    loss=policy['loss0']+policy['loss_pressure']*pressure
    return -math.log1p(-loss) if roll<probability else 0.


def order_at(prepared,profile,wear):
    point=min(lab.GRID,key=lambda x:(abs(x-wear),x))
    return prepared[f'{profile}:{point}']['plan']['order']


def journey(j,mm,ii,enemy,ei,prepared,policy,index,dungeon=False,trace=False):
    wear=0.;rows=[];fights=0;loot=0;executed=0
    profile=policy['profile'];weights=lab.PROFILES[profile]
    for node in range(1,31):
        # Per-channel random streams are independent of damage, order search,
        # event probability and previous native action random draws.
        rs=lambda channel:lab.seed('trip-event',j['stage'],j['genre'],j['gear'],
            j['region'],index,node,channel)/(1<<64)
        if dungeon and rs('node')>=.7:
            adverse=rs('adverse')<.5
            delta=-math.log1p(-(policy['loss0']+policy['loss_pressure'])) if adverse else 0.
            rows.append(dict(node=node,type='event',adverse=adverse,wear_before=wear,wear_after=wear+delta,
                             won_battles=loot,battle_index=fights))
            wear+=delta;continue
        fights+=1
        order=order_at(prepared,profile,wear);members,items=reordered(mm,ii,order)
        bs=lab.seed('trip-native',j['stage'],j['genre'],j['gear'],j['region'],index,node,'dungeon' if dungeon else 'travel')
        r,telemetry,*_=lab.engine.simulate(members,enemy,bs,items,ei,p=j['macro'],
            factors=lab.engine.factors(weights,wear),telemetry=trace and node<=3)
        executed+=1
        delta=draw(policy,r,rs('battle')) if r['win'] else 0.
        loot+=r['win']
        row=dict(node=node,type='battle',battle_index=fights,wear_before=wear,wear_after=wear+delta,
            result=compact(r),battle_seed=bs,order=list(order),won_battles=loot)
        if telemetry:row['telemetry']=telemetry
        rows.append(row);wear+=delta
        if not r['win']:break
    return dict(index=index,rows=rows,won_battles=loot,executed_battles=executed,
                last_node=rows[-1]['node'],survived_all=rows[-1]['node']==30 and ('result'not in rows[-1] or rows[-1]['result']['win']))


def evaluate(j):
    s=j['stage'];g=j['genre'];mm,_=lab.build(s,g,1170000,(),'front','final')
    ii=lab.supplies.equipment(mm,g,s,j['gear'])
    enemy,ei=lab.build(s,j['enemy_genre'],1270003,(),'front','final')
    profiles=sorted({p['profile'] for p in j['policies'].values()});prepared={};executed=0
    for profile in profiles:
        previous=None
        for x in lab.GRID:
            key=f'{profile}:{x}'
            if x==0 and prepared:
                source=next(k for k in prepared if k.endswith(':0'))
                prepared[key]={**prepared[source],'alias':source,'executed_battles':0}
                previous=prepared[key]['plan']['order'];continue
            answer=lab.solve(mm,ii,enemy,ei,j['macro'],lab.engine.factors(lab.PROFILES[profile],x),
                ('confirm-order',s,g,j['gear'],j['region'],profile,x),128 if x==0 else 32,previous)
            prepared[key]=answer;executed+=answer['executed_battles'];previous=answer['plan']['order']
    variants={};physical={}
    for name,policy in j['policies'].items():
        encoded=json.dumps(policy,sort_keys=True)
        if encoded in physical:variants[name]=dict(alias=physical[encoded]);continue
        physical[encoded]=name
        travel=[journey(j,mm,ii,enemy,ei,prepared,policy,index,False,index==0) for index in range(128)]
        dungeon=[journey(j,mm,ii,enemy,ei,prepared,policy,index,True,index==0) for index in range(64)]
        variants[name]=dict(policy=policy,travel=travel,dungeon=dungeon)
        executed+=sum(r['executed_battles'] for r in travel+dungeon)
    raw=dict(job=j,members=snapshot(mm,ii),enemy=snapshot(enemy,ei),prepared=prepared,variants=variants,
             executed_battles=executed,dungeon_conditions=dict(battle_probability=.7,adverse_given_event=.5,shock_multiplier=1))
    path=OUT/'replicates'/f'{j["key"]}.json.gz';path.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(path.with_suffix('.tmp'),'wt',encoding='utf-8') as f:json.dump(raw,f,ensure_ascii=False)
    path.with_suffix('.tmp').replace(path)
    public={}
    for name,value in variants.items():
        v=variants[value['alias']] if 'alias'in value else value
        travel=[];dungeon=[]
        for node in range(1,31):
            rr=[q for route in v['travel'] for q in route['rows'] if q['node']==node]
            travel.append(dict(battle=node,entered=len(rr),wins=sum(q['result']['win'] for q in rr),
                wr=sum(q['result']['win'] for q in rr)/len(rr) if rr else None,
                reach_probability=len(rr)/128,mean_bp_cap=sum(math.exp(-lab.PROFILES[v['policy']['profile']][0]*q['wear_before']) for q in rr)/len(rr) if rr else None))
            dd=[q for route in v['dungeon'] for q in route['rows'] if q['node']==node]
            dungeon.append(dict(node=node,entered=len(dd),reach_probability=len(dd)/64))
        baseline=prepared[f'{v["policy"]["profile"]}:0']['metrics']
        public[name]=dict(alias=value.get('alias'),policy=v['policy'],travel=travel,dungeon=dungeon,baseline=baseline,
            physical_native_journeys=0 if 'alias'in value else 192)
    return dict(executed_battles=executed,variants=public,
                preparation_executions=sum(r['executed_battles'] for r in prepared.values()))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workers',type=int,default=6);args=p.parse_args()
    selected_path=lab.OUT/'selected_policies.json';selected=json.loads(selected_path.read_text(encoding='utf-8'))
    for path,digest in selected['sources'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
    region_paths=[lab.OUT/'regions.json',lab.OUT/'low_margin/regions.json']
    regions=sum((json.loads(q.read_text(encoding='utf-8'))['regions'] for q in region_paths),[])
    sources={**selected['sources'],**{str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in [Path(__file__),selected_path]+region_paths}}
    base_sig,base_manifest=lab.signature();manifest=dict(response_signature=base_sig,
        sources={**base_manifest['sources'],**sources})
    sig=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest();OUT.mkdir(parents=True,exist_ok=True)
    atomic_json(OUT/'manifest.json',{**manifest,'signature':sig})
    db=sqlite3.connect(OUT/'checkpoints.sqlite');db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS cells(key TEXT PRIMARY KEY,signature TEXT,job TEXT,result TEXT)');db.commit()
    pending={};wanted=set();jobs=[]
    for r in regions:
        for g in lab.GENRES:
            for gear in ('basic','four_top'):
                j=dict(stage=r['stage'],genre=g,gear=gear,region=r['region'],enemy_genre=r['enemy_genre'],macro=r['macro'],
                    policies=dict(global_policy=selected['global_policy'],stage_policy=selected['stage_policies'][str(r['stage'])]))
                jobs.append(j)
    with cf.ProcessPoolExecutor(args.workers) as pool:
        for j in jobs:
            encoded=json.dumps(j,sort_keys=True);key=hashlib.sha256((sig+encoded).encode()).hexdigest();wanted.add(key)
            if db.execute('SELECT 1 FROM cells WHERE key=?',(key,)).fetchone():continue
            pending[pool.submit(evaluate,{**j,'key':key})]=(key,encoded)
        print('confirmation:',len(pending),'pending /',len(jobs),flush=True)
        for i,f in enumerate(cf.as_completed(pending),1):
            key,encoded=pending[f];result=f.result()
            db.execute('INSERT INTO cells VALUES(?,?,?,?)',(key,sig,encoded,json.dumps(result)));db.commit()
            if i%6==0 or i==len(pending):print('confirmation: saved',i,'/',len(pending),flush=True)
    rows=[dict(key=k,job=json.loads(j),result=json.loads(r)) for k,j,r in db.execute(
        'SELECT key,job,result FROM cells WHERE signature=?',(sig,)) if k in wanted];db.close()
    assert len(rows)==len(jobs)
    atomic_json(OUT/'summary.json',dict(signature=sig,cells=len(rows),rows=rows,
        executed_battles=sum(r['result']['executed_battles'] for r in rows)))
    print('confirmation complete:',len(rows),'cells',flush=True)


if __name__=='__main__':main()
