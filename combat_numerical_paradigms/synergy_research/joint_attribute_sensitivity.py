"""Paired common-equipment stat sensitivity at independently frozen skill/order plans.

This measures a local 0.75/1.00/1.25 stat band, not new order optima or universal caps.
Existing center battles are reused; only the two endpoints are executed here.
"""
import argparse
import concurrent.futures as cf
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3

import joint_research as lab
from order_search import reordered, snapshot
from run_bonds import atomic_json
from settings import HERE


def evaluate(task):
    out=Path(task['output']);cell=task['cell'];j=cell['job']
    with gzip.open(out/'replicates'/(cell['key']+'.json.gz'),'rt',encoding='utf-8') as f:raw=json.load(f)
    all_configs=lab.configs();cfg=all_configs[(j['stage'],j['bond'])]
    mm,ii,_=lab.player_members(j);enemy=lab.enemy_states(j,all_configs)[0]
    selection=json.loads((out/'selected_supply.json').read_text(encoding='utf-8'))
    ntest=min(task['trials'],j['test_trials']);records=[];executed=0
    for gear,scope in (('basic','all_base'),('four_top','all_base'),('four_top','non_top')):
        policy=selection[f'{j["stage"]}:{j["bond"]}:{gear}']
        entry=next(x for x in raw['variants'] if x['variant']==dict(policy=policy,gear=gear,scale=1.))
        if 'alias' in entry:entry=raw['variants'][entry['alias']]
        o=entry['outcomes'][0];vm,_=lab.skill_supply(mm,ii,policy,j['bank'],j['bond'])
        seeds=o['seeds']['test'][:ntest]
        for scale in (.75,1.,1.25):
            equipment=lab.equipment(vm,j['genre'],j['stage'],gear,scale if scope=='all_base' else 1.)
            if scope=='non_top':
                equipment=tuple(it if it.top else lab.natural.Item(it.kind,it.value,tuple(x*scale for x in it.stats),it.bp,it.top) for it in equipment)
            assert all(a['item']['kind']==it.kind and a['item']['value']==it.value for a,it in zip(entry['snapshot'],equipment))
            for state in ('off','on'):
                if scale==1.:
                    rows=o['trials'][state][:ntest]
                else:
                    a,ai=reordered(vm,equipment,o['plans'][state]['order']);rows=[]
                    for bs in seeds:
                        r,*_=lab.simulate(a,enemy['members'],bs,ai,enemy['items'],p=enemy['macro'],
                            enabled=(j['bond'],) if state=='on' else (),config=cfg,
                            enemy_enabled=enemy['enabled'],enemy_config=enemy['config'])
                        rows.append({k:r[k] for k in ('win','turns','hp','enemy_hp','margin','normal_rate','censored')})
                    executed+=len(rows)
                keep={k:sum(r[k] for r in rows)/len(rows) for k in ('win','turns','hp','enemy_hp','margin','normal_rate','censored')}
                records.append(dict(gear=gear,scope=scope,policy=policy,scale=scale,state=state,metrics=keep,
                                    seeds=seeds,trials=[{k:r[k] for k in keep} for r in rows],order=o['plans'][state]['order']))
    path=out/'attribute_replicates'/(cell['key']+'.json.gz');path.parent.mkdir(exist_ok=True)
    with gzip.open(path.with_suffix('.tmp'),'wt',encoding='utf-8') as f:
        json.dump(dict(cell=cell['key'],job=j,records=records,executed_battles=executed),f,ensure_ascii=False)
    path.with_suffix('.tmp').replace(path)
    summary=[{k:v for k,v in x.items() if k not in ('trials','seeds','order')} for x in records]
    return dict(records=summary,executed_battles=executed,trials=ntest)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=HERE/'results/joint')
    p.add_argument('--workers',type=int,default=6);p.add_argument('--trials',type=int,default=32)
    args=p.parse_args();out=args.output;assert args.trials>=2
    confirm=json.loads((out/'confirm.json').read_text(encoding='utf-8'))
    source=dict(joint_signature=confirm['signature'],source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                confirm_sha256=hashlib.sha256((out/'confirm.json').read_bytes()).hexdigest(),trials=args.trials)
    sig=hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest()
    atomic_json(out/'attribute_manifest.json',dict(signature=sig,**source))
    db=sqlite3.connect(out/'attribute_checkpoints.sqlite');db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS cells (key TEXT PRIMARY KEY,signature TEXT,result TEXT)');db.commit()
    wanted={};pending={}
    with cf.ProcessPoolExecutor(args.workers) as pool:
        for cell in confirm['rows']:
            k=hashlib.sha256((sig+cell['key']).encode()).hexdigest();wanted[k]=cell
            if db.execute('SELECT key FROM cells WHERE key=?',(k,)).fetchone():continue
            pending[pool.submit(evaluate,dict(output=str(out.resolve()),cell=cell,trials=args.trials))]=k
        print(f'attribute: {len(pending)} pending / {len(wanted)} cells',flush=True)
        for i,f in enumerate(cf.as_completed(pending),1):
            k=pending[f];db.execute('INSERT INTO cells VALUES (?,?,?)',(k,sig,json.dumps(f.result())));db.commit()
            if i%48==0 or i==len(pending):print(f'attribute: saved {i}/{len(pending)}',flush=True)
    cells=[dict(cell=wanted[k],result=json.loads(r)) for k,r in db.execute('SELECT key,result FROM cells WHERE signature=?',(sig,)) if k in wanted]
    assert len(cells)==len(confirm['rows']);db.close()
    evidence=[]
    for c in cells:
        j=c['cell']['job'];r=c['result'];assert r['executed_battles']==12*r['trials']
        for gear,scope in (('basic','all_base'),('four_top','all_base'),('four_top','non_top')):
            group={(x['scale'],x['state']):x for x in r['records'] if x['gear']==gear and x['scope']==scope}
            point=lab.study.COMMON[(j['stage'],j['genre'])]
            row=dict(stage=j['stage']+1,capacity=5*(j['stage']+1),bond=j['bond'],genre=j['genre'],difficulty=j['difficulty'],gear=gear,scope=scope,
                     policy=group[(1.,'on')]['policy'],base_common_points_per_member=point,trials=r['trials'])
            row['modified_item_count']=5*(j['stage']+1)-(4 if scope=='non_top' else 0)
            for scale in (.75,1.,1.25):
                for state in ('on','off'):
                    row[f'{state}_wr_{scale}']=group[(scale,state)]['metrics']['win']
                row[f'on_censored_{scale}']=group[(scale,'on')]['metrics']['censored']
            row['wr_slope_per_common_point']=(row['on_wr_1.25']-row['on_wr_0.75'])/(point*.5)
            row['bond_slope_per_common_point']=row['wr_slope_per_common_point']-(row['off_wr_1.25']-row['off_wr_0.75'])/(point*.5)
            evidence.append(row)
    with (out/'attribute_band_evidence.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(evidence[0]));w.writeheader();w.writerows(evidence)
    atomic_json(out/'attribute_sensitivity.json',dict(signature=sig,cells=len(cells),
        executed_battles=sum(x['result']['executed_battles'] for x in cells),rows=evidence,
        scope='frozen confirmed skill/order; all base attributes and non-top attributes separately; existing center reused'))
    print(f'attribute: complete {len(cells)} cells / {sum(x["result"]["executed_battles"] for x in cells):,} new executions',flush=True)


if __name__=='__main__':main()
