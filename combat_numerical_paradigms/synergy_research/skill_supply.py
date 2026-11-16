"""Compare identity-aware skill supply AND order without adding stat budget."""
import argparse
import concurrent.futures as cf
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import time

from run_bonds import atomic_json,average,count_options
from rosters import build,bank,encounter,GENRES,seed,natural
from bond_core import simulate
from settings import HERE,IDENTITIES

POLICIES=('random','repeatable','throughput','frontloaded','support_order','repeatable_order','throughput_order')


def transform(members,items,policy,bank_name,key):
    skills,_,_=bank(bank_name);pairs=[];target=set(IDENTITIES[key])
    for pos,(m,it) in enumerate(zip(members,items)):
        x=copy.copy(m)
        style=policy.replace('_order','')
        if m.identity in target and style in ('repeatable','throughput','frontloaded'):
            rows=skills[(m.skill.tier,natural.NAME_TO_LETTER[m.skill.genre])]
            def score(row):
                s=row[0];p=s.trigger_chance/100
                gates=int(s.turn_cond1>0)+int(s.turn_cond2>0)+int(s.self_bp_cond2>0)+int(s.enemy_bp_cond2>0)
                if style=='repeatable':return 2*(s.times_limit>=999)+p-gates
                horizon=3 if style=='frontloaded' else 10
                coverage=min(1,s.times_limit/horizon) if 0<s.times_limit<999 else 1.
                timing=max(0,1-s.turn_cond1/horizon)
                if s.turn_cond2>0:timing*=min(1,(s.turn_cond2-1)/horizon)
                value=s.main_param/100+(s.sub_param*12 if s.main_type=='Heal' else 0)
                return p*value*coverage*timing-.2*(int(s.self_bp_cond2>0)+int(s.enemy_bp_cond2>0))
            ranked=sorted(rows,key=score,reverse=True)[:max(1,len(rows)//4)]
            x.skill=copy.copy(ranked[seed('supply-choice',m.person_id,pos,policy)%len(ranked)][0]);x.skill.id=m.skill.id
        pairs.append((x,it))
    if policy.endswith('_order'):
        target=set(IDENTITIES[key])
        def priority(pair):
            m=pair[0];s=m.skill
            finite=0<s.times_limit<999
            # Gated skills can be inspected early without blocking while ineligible.
            gate=bool(s.turn_cond1 or s.turn_cond2 or s.self_bp_cond2 or s.enemy_bp_cond2)
            if key=='maid':
                return (2 if m.identity=='女仆' else 0 if finite or gate else 3,-s.main_param)
            if key=='heroine':return (0 if m.identity in target and finite else 1 if finite or gate else 2,-s.trigger_chance)
            return (0 if m.identity not in target and finite else 1 if m.identity in target else 2,-s.main_param*s.trigger_chance)
        pairs.sort(key=priority)
    return tuple(x[0] for x in pairs),tuple(x[1] for x in pairs)


def evaluate(job):
    s=job['stage'];g=job['genre'];key=job['bond'];policies=job['policies'];h,p=encounter(s,'extremely_hard')
    results={x:[] for x in policies}
    for trial in range(job['trials']):
        pool=job['offset']+trial;m,it=build(s,g,pool,((key,job['count']),),'front',job['bank'])
        e,ei=build(s,h,pool+100003,(),'front',job['bank'])
        bs=seed('supply-independent',s,g,pool)
        off,*_=simulate(m,e,bs,it,ei,p=p)
        on,*_=simulate(m,e,bs,it,ei,p=p,enabled=(key,),config=job['config'])
        for policy in policies:
            if policy=='random':a,b=off,on
            else:
                x,xt=transform(m,it,policy,job['bank'],key)
                a,*_=simulate(x,e,bs,xt,ei,p=p)
                b,*_=simulate(x,e,bs,xt,ei,p=p,enabled=(key,),config=job['config'])
            results[policy].append(dict(random_off=off['win'],random_on=on['win'],policy_off=a['win'],policy_on=b['win'],
                                        win_delta=b['win']-on['win'],interaction=b['win']-a['win']-on['win']+off['win'],
                                        turns=b['turns'],scholar_restored=b['metrics'].get('scholar_restored',0),
                                        growth_casts=b['metrics'].get('engineer_casts',0)+b['metrics'].get('ninja_casts',0),
                                        fruit_harvest=b['metrics'].get('fruit_harvest',0),censored=b['censored']))
    out=[]
    for policy,rows in results.items():
        d={k:average([r[k] for r in rows]) for k in rows[0]}
        delta=d['win_delta'];second=average([r['win_delta']**2 for r in rows])
        d.update(policy=policy,trials=len(rows),delta_se=max(0,(second-delta*delta)/(len(rows)-1))**.5)
        out.append(d)
    return out


def run(db,pool,phase,jobs,sig):
    missing={}
    for job in jobs:
        text=json.dumps(job,sort_keys=True);key=hashlib.sha256((sig+text).encode()).hexdigest()
        if db.execute('SELECT key FROM cells WHERE key=?',(key,)).fetchone():continue
        missing[pool.submit(evaluate,job)]=(key,text)
    print(f'skill {phase}: {len(missing)} cells',flush=True)
    for i,future in enumerate(cf.as_completed(missing),1):
        key,text=missing[future];result=future.result()
        db.execute('INSERT INTO cells VALUES (?,?,?,?,?)',(key,phase,text,json.dumps(result),sig));db.commit()
        if i%100==0 or i==len(missing):print(f'skill {phase}: saved {i}/{len(missing)}',flush=True)
    out=[]
    for text,result in db.execute('SELECT job,result FROM cells WHERE phase=? AND signature=?',(phase,sig)):
        job=json.loads(text)
        for row in json.loads(result):out.append({**job,**row})
    return out


def main():
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=8)
    p.add_argument('--output',type=Path,default=HERE/'results');args=p.parse_args()
    manifest=json.loads((args.output/'input_manifest.json').read_text(encoding='utf-8'))
    chosen=json.loads((args.output/'selected_coefficients.json').read_text(encoding='utf-8'))
    configs={(r['stage'],r['bond']):r['config'] for r in chosen if r['soft_delta_reference']==.1}
    sig=hashlib.sha256((manifest['signature']+Path(__file__).read_text(encoding='utf-8')+json.dumps(chosen,sort_keys=True)).encode()).hexdigest()
    db=sqlite3.connect(args.output/'skill_supply_checkpoints.sqlite');db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS cells (key TEXT PRIMARY KEY,phase TEXT,job TEXT,result TEXT,signature TEXT)');db.commit()
    atomic_json(args.output/'skill_supply_manifest.json',dict(signature=sig,combat_signature=manifest['signature'],policies=POLICIES,
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),preserved_budget=True))
    jobs=[]
    for s in range(6):
        for key in IDENTITIES:
            opts=count_options(s,key)
            if not opts:continue
            count=min(opts,key=lambda x:abs(x-max(1,(5*(s+1))//3)))
            for g in GENRES:
                jobs.append(dict(stage=s,genre=g,bond=key,count=count,config=configs[(s,key)],policies=POLICIES,
                                 bank='validation',offset=100000,trials=12))
    try:
        with cf.ProcessPoolExecutor(args.workers) as pool:
            validation=run(db,pool,'validation',jobs,sig)
            atomic_json(args.output/'skill_supply_validation.json',validation)
            groups={}
            for row in validation:groups.setdefault((row['stage'],row['bond'],row['policy']),[]).append(row)
            ranked={}
            for (s,key,policy),rows in groups.items():
                delta=average([r['win_delta'] for r in rows])
                spread=(average([(r['win_delta']-delta)**2 for r in rows]))**.5
                value=delta-.2*spread
                if (s,key) not in ranked or value>ranked[(s,key)][0]:ranked[(s,key)]=(value,policy)
            final=[{**job,'bank':'final','offset':110000,'trials':48,'policies':(ranked[(job['stage'],job['bond'])][1],)} for job in jobs]
            confirmation=run(db,pool,'confirmation',final,sig)
            atomic_json(args.output/'skill_supply_confirmation.json',confirmation)
    finally:db.close()


if __name__=='__main__':main()
