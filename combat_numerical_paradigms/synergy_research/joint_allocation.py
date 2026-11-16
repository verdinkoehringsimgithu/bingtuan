"""Confirm equipment ownership using actual Heal/headmaid/gang action semantics."""
import argparse
import concurrent.futures as cf
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import time

import joint_research as lab
from order_search import snapshot
from run_bonds import atomic_json
from settings import HERE, DEFAULTS


def refined_equipment(mm,g,s,key,cfg):
    cfg={**DEFAULTS,**cfg}
    basic=lab.equipment(mm,g,s,'basic');out=list(basic);remaining=set(range(len(mm)))
    first_maid=next((i for i,m in enumerate(mm) if m.identity=='女仆'),None)
    # Propose the initial first maid as replacement-action gear owner. The order
    # search remains free to appoint another headmaid if the roster benefits.
    for _,kind,value in sorted(lab.study.LOADS[(s,g)],key=lambda x:x[1]=='opening_shield'):
        def score(i):
            m=mm[i];sk=m.skill;p=sk.trigger_chance/100
            gate=int(bool(sk.turn_cond1 or sk.turn_cond2 or sk.self_bp_cond2 or sk.enemy_bp_cond2))
            coverage=1 if sk.times_limit<=0 or sk.times_limit>=999 else min(1,sk.times_limit/8)
            # Heal resets the raw direct multiplier to 1 in the canonical action.
            mult=1. if sk.main_type=='Heal' else sk.main_param/100
            output=p*mult*coverage/(1+gate)
            gang_member=key=='gang' and m.identity=='帮派'
            if gang_member:
                n=sum(x.identity=='帮派' for x in mm);q=n/(n+cfg['count_k'])
                output=p*(1+cfg['gang']*q*cfg.get('gain',1.))
            if key=='maid' and i==first_maid:
                n=sum(x.identity=='女仆' for x in mm);q=n/(n+cfg['count_k'])
                potential=1. if cfg['maid_kind']=='heal' else 1+cfg['maid_power']*q*cfg.get('gain',1.)
                output=max(output,potential)
            if kind=='owner_stats':return sum(m.stats)
            if kind=='opening_shield':return -output
            if kind=='normal_damage':return 10+p if gang_member else 1-p
            if gang_member:return -1  # Replacement attacks never invoke skill gear.
            if kind in ('skill_heal','overheal_shield'):return p*(sk.main_type=='Heal' or sk.sub_effect_name=='战力吸收')
            if kind=='skill_dot':return p*(sk.sub_effect_name in ('最大流失','已损流失','固定流失'))
            if kind=='extra_use':return p*(0<sk.times_limit<999)
            return output
        pos=max(remaining,key=lambda i:(score(i),-i));remaining.remove(pos)
        old=out[pos];out[pos]=lab.natural.Item(kind,float(value),old.stats,old.bp,True)
    return tuple(out)


def physical_signature(mm,items):
    # Passive owner changes are equivalent if summed initial contributions match.
    return dict(stats=[round(sum(m.stats[k]+it.stats[k]+(m.stats[k]*it.value if it.kind=='owner_stats' else 0.) for m,it in zip(mm,items)),10) for k in range(4)],
                shield=sum(it.value for it in items if it.kind=='opening_shield'),
                bp=sum(m.bp+it.bp for m,it in zip(mm,items)),
                active=[(it.kind,it.value) if it.kind not in ('basic','opening_shield','owner_stats') else ('passive',0.) for it in items])


def prepare(cell,selection):
    j=cell['job'];mm,ii,_=lab.player_members(j);policy=selection[f'{j["stage"]}:{j["bond"]}:four_top']
    mm,_=lab.skill_supply(mm,ii,policy,j['bank'],j['bond']);cfg=lab.configs()[(j['stage'],j['bond'])]
    old=lab.equipment(mm,j['genre'],j['stage'],'four_top');new=refined_equipment(mm,j['genre'],j['stage'],j['bond'],cfg)
    assert sorted((i.kind,i.value,tuple(i.stats),i.bp) for i in old)==sorted((i.kind,i.value,tuple(i.stats),i.bp) for i in new)
    return j,mm,old,new,physical_signature(mm,old)==physical_signature(mm,new)


def evaluate(task):
    out=Path(task['output']);j,mm,old,new,equal=prepare(task['cell'],task['selection'])
    if equal:return dict(equivalent=True,executed_battles=0)
    j={**j,'phase':'allocation','budget':32,'shortlist':3,'train_trials':4,'select_trials':12,'cross_trials':12,'test_trials':64}
    configs=lab.configs();enemy=lab.enemy_states(j,configs)[0];outcomes=[]
    for label,items in (('reference',old),('refined',new)):
        o=lab.solve(mm,items,enemy,j,configs,label);outcomes.append(dict(label=label,snapshot=snapshot(mm,items),outcome=o))
    raw=dict(cell=task['cell']['key'],job=j,enemy={**enemy,'members':snapshot(enemy['members'],enemy['items']),'items':None},variants=outcomes)
    path=out/'allocation_replicates'/(task['cell']['key']+'.json.gz');path.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(path.with_suffix('.tmp'),'wt',encoding='utf-8') as f:json.dump(raw,f,ensure_ascii=False)
    path.with_suffix('.tmp').replace(path)
    a,b=(o['outcome'] for o in outcomes)
    return dict(equivalent=False,executed_battles=sum(x['outcome']['executed_battles'] for x in outcomes),
        reference_wr=a['metrics']['on']['win'],refined_wr=b['metrics']['on']['win'],
        owner_gain=b['metrics']['on']['win']-a['metrics']['on']['win'],
        bond_interaction=b['differences']['practical']['mean']-a['differences']['practical']['mean'],
        reference_censored=a['metrics']['on']['censored'],refined_censored=b['metrics']['on']['censored'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=HERE/'results/joint')
    p.add_argument('--workers',type=int,default=6);args=p.parse_args();out=args.output
    confirm=json.loads((out/'confirm.json').read_text(encoding='utf-8'))
    selection=json.loads((out/'selected_supply.json').read_text(encoding='utf-8'))
    source=dict(joint_signature=confirm['signature'],source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                confirm_sha256=hashlib.sha256((out/'confirm.json').read_bytes()).hexdigest())
    sig=hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest()
    atomic_json(out/'allocation_manifest.json',dict(signature=sig,**source))
    db=sqlite3.connect(out/'allocation_checkpoints.sqlite');db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS cells (key TEXT PRIMARY KEY,signature TEXT,result TEXT)');db.commit()
    wanted={};pending={}
    with cf.ProcessPoolExecutor(args.workers) as pool:
        for cell in confirm['rows']:
            key=hashlib.sha256((sig+cell['key']).encode()).hexdigest();wanted[key]=cell
            if db.execute('SELECT key FROM cells WHERE key=?',(key,)).fetchone():continue
            pending[pool.submit(evaluate,dict(cell=cell,selection=selection,output=str(out.resolve())))]=key
        print(f'allocation: {len(pending)} pending / {len(wanted)} input cells',flush=True)
        for i,f in enumerate(cf.as_completed(pending),1):
            key=pending[f];db.execute('INSERT INTO cells VALUES (?,?,?)',(key,sig,json.dumps(f.result())));db.commit()
            if i%96==0 or i==len(pending):print(f'allocation: saved {i}/{len(pending)}',flush=True)
    rows=[dict(cell=wanted[k],result=json.loads(r)) for k,r in db.execute('SELECT key,result FROM cells WHERE signature=?',(sig,)) if k in wanted]
    assert len(rows)==len(wanted);db.close()
    atomic_json(out/'allocation_confirmation.json',dict(signature=sig,cells=len(rows),changed_cells=sum(not r['result']['equivalent'] for r in rows),
        executed_battles=sum(r['result']['executed_battles'] for r in rows),rows=rows))
    print('allocation: complete',len(rows),'input cells;',sum(not r['result']['equivalent'] for r in rows),'changed;',sum(r['result']['executed_battles'] for r in rows),'executions',flush=True)


if __name__=='__main__':main()
