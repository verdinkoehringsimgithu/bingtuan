"""Audit frozen sources, measured curves and native journey event ledgers."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import sqlite3

import measure_response as lab
import confirm_paths as native
from order_search import reordered, snapshot
from run_bonds import atomic_json


def equivalent(a,b):
    return json.loads(json.dumps(a,sort_keys=True))==json.loads(json.dumps(b,sort_keys=True))


def check_manifest(path):
    d=json.loads(path.read_text(encoding='utf-8'))
    for source,digest in d['sources'].items():assert hashlib.sha256(Path(source).read_bytes()).hexdigest()==digest,source
    body={k:v for k,v in d.items() if k!='signature'}
    assert hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()==d['signature']
    return d


def measured(root):
    manifest=check_manifest(root/'manifest.json');counts={};replayed=0
    for phase in ('regions','curves'):
        if phase=='regions':
            # regions.json is the selected encounter API. Recover the full
            # calibration matrix from committed, signed checkpoint records.
            db=sqlite3.connect(root/'checkpoints.sqlite')
            rows=[dict(key=k,job=json.loads(j),result=json.loads(r)) for k,j,r in db.execute(
                'SELECT key,job,result FROM cells WHERE signature=? AND phase=?',(manifest['signature'],'regions'))]
            db.close()
            data=dict(signature=manifest['signature'],cells=len(rows),rows=rows,
                executed_battles=sum(r['result']['executed_battles'] for r in rows))
            atomic_json(root/'region_calibration_evidence.json',data)
        else:data=json.loads((root/(phase+'.json')).read_text(encoding='utf-8'))
        assert data['signature']==manifest['signature'] and len(data['rows'])==data['cells']
        total=0
        for cell in data['rows']:
            j=cell['job'];r=cell['result'];n=lab.STAGES[j['stage']][0]
            physical=([f for f in r['by_flow']] if phase=='regions' else [v for v in r['points'].values() if 'alias'not in v])
            for point in physical:
                trials=point['trials'] if phase=='regions' else point['outcomes']
                metrics=point['metrics'];length=len(trials)
                for name in ('win','hp','turns','censored','damage_exposure','minimum_bp_fraction'):
                    assert abs(sum(q[name] for q in trials)/length-metrics[name])<1e-12
                won=[q['hp'] for q in trials if q['win']]
                assert (metrics['winning_hp'] is None and not won) or abs(metrics['winning_hp']-sum(won)/len(won))<1e-12
            if phase=='regions':
                expected=6*((120 if n==5 else 16)*2+3*4+24)
            else:
                expected=(len(lab.PROFILES)*(len(lab.GRID)-1)+1)*((120 if n==5 else 16)*2+3*4+32)
                path=root/'curves'/f'{cell["key"]}.json.gz'
                with gzip.open(path,'rt',encoding='utf-8') as f:raw=json.load(f)
                assert all(raw['job'][k]==v for k,v in j.items())
                mm,_=lab.build(j['stage'],j['genre'],j['pool'],(),'front',j['bank'])
                ii=lab.supplies.equipment(mm,j['genre'],j['stage'],j['gear'])
                enemy,ei=lab.build(j['stage'],j['enemy_genre'],j['pool']+100003,(),'front',j['bank'])
                assert equivalent(raw['members'],snapshot(mm,ii)) and equivalent(raw['enemy'],snapshot(enemy,ei))
                assert len(mm)==len(enemy)==n and len({m.person_id for m in mm})==n
                for key,point in raw['points'].items():
                    public=r['points'][key]
                    if 'alias'in point:
                        assert public=={'alias':point['alias']};continue
                    assert equivalent(point['trials'],public['outcomes'])
                    assert equivalent(point['plan']['order'],public['order'])
                    assert not(set(point['seeds']['train'])&set(point['seeds']['test']))
                    assert not(set(point['seeds']['select'])&set(point['seeds']['test']))
                    if j['genre']=='C_I' and key in ('bp_only:0','bp_only:0.7','stats_only:0.7','mixed:0.7'):
                        profile,x=key.split(':');m,it=reordered(mm,ii,point['plan']['order'])
                        rr,*_=lab.engine.simulate(m,enemy,point['seeds']['test'][0],it,ei,p=j['macro'],
                            factors=lab.engine.factors(lab.PROFILES[profile],float(x)))
                        assert all(rr[k]==v for k,v in point['trials'][0].items());replayed+=1
            assert r['executed_battles']==expected,(root,phase,cell['key'],r['executed_battles'],expected)
            total+=expected
        assert total==data['executed_battles'];counts[phase]=dict(cells=data['cells'],executed_battles=total)
    return dict(phases=counts,exact_saved_battle_replays=replayed)


def confirmation(root):
    manifest=check_manifest(root/'manifest.json');data=json.loads((root/'summary.json').read_text(encoding='utf-8'))
    assert data['signature']==manifest['signature'] and data['cells']==len(data['rows'])==432
    total=0;replays=0;journeys=0;native_battles=0;censored=0;archives={}
    coverage=set()
    for cell in data['rows']:
        j=cell['job'];n=lab.STAGES[j['stage']][0]
        coverage.add((j['stage'],j['genre'],j['gear'],j['region']))
        path=root/'replicates'/f'{cell["key"]}.json.gz';archives[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        with gzip.open(path,'rt',encoding='utf-8') as f:raw=json.load(f)
        assert all(raw['job'][k]==v for k,v in j.items())
        mm,_=lab.build(j['stage'],j['genre'],1170000,(),'front','final')
        ii=lab.supplies.equipment(mm,j['genre'],j['stage'],j['gear'])
        enemy,ei=lab.build(j['stage'],j['enemy_genre'],1270003,(),'front','final')
        assert equivalent(snapshot(mm,ii),raw['members']) and equivalent(snapshot(enemy,ei),raw['enemy'])
        assert len(mm)==len(enemy)==n and sum(i.top for i in ii)==(4 if j['gear']=='four_top' else 0)
        count=0
        for key,point in raw['prepared'].items():
            if 'alias'in point:
                assert point['executed_battles']==0;continue
            count+=point['executed_battles']
            assert point['plan']['searched_orders']==(120 if n==5 else 16)
            assert not set(point['seeds']['train'])&set(point['seeds']['test'])
        assert count==cell['result']['preparation_executions']
        for name,value in raw['variants'].items():
            if 'alias'in value:
                assert cell['result']['variants'][name]['alias']==value['alias'];continue
            policy=value['policy'];journeys+=192
            for mode,length in (('travel',128),('dungeon',64)):
                routes=value[mode];assert len(routes)==length
                for route in routes:
                    wear=0.;won=0;fights=0
                    assert route['rows'][0]['node']==1 and len(route['rows'])<=30
                    for node,row in enumerate(route['rows'],1):
                        assert row['node']==node and abs(row['wear_before']-wear)<1e-12
                        roll=lambda channel:lab.seed('trip-event',j['stage'],j['genre'],j['gear'],j['region'],route['index'],node,channel)/(1<<64)
                        if row['type']=='event':
                            assert mode=='dungeon' and roll('node')>=.7
                            adverse=roll('adverse')<.5;assert adverse==row['adverse']
                            delta=-math.log1p(-(policy['loss0']+policy['loss_pressure'])) if adverse else 0.
                        else:
                            assert mode=='travel' or roll('node')<.7
                            fights+=1;native_battles+=1;rr=row['result'];censored+=rr['censored'];won+=rr['win']
                            delta=native.draw(policy,rr,roll('battle')) if rr['win'] else 0.
                            assert row['order']==native.order_at(raw['prepared'],policy['profile'],wear)
                            if not rr['win']:assert node==len(route['rows'])
                            if j['genre']=='C_I' and route['index']==0:
                                m,it=reordered(mm,ii,row['order']);trace='telemetry'in row
                                r,telemetry,*_=lab.engine.simulate(m,enemy,row['battle_seed'],it,ei,p=j['macro'],
                                    factors=lab.engine.factors(lab.PROFILES[policy['profile']],wear),telemetry=trace)
                                assert native.compact(r)==rr
                                if trace:assert equivalent(telemetry,row['telemetry'])
                                replays+=1
                        wear+=delta;assert abs(row['wear_after']-wear)<1e-12 and row['won_battles']==won
                    assert route['won_battles']==won and route['executed_battles']==fights
                    count+=fights
                for node in range(1,31):
                    actual=sum(len(route['rows'])>=node for route in routes)
                    public=cell['result']['variants'][name][mode][node-1]
                    assert public['entered']==actual and abs(public['reach_probability']-actual/length)<1e-12
                    if mode=='travel':
                        wins=sum(route['rows'][node-1]['result']['win'] for route in routes if len(route['rows'])>=node)
                        assert wins==public['wins']
        assert count==raw['executed_battles']==cell['result']['executed_battles'];total+=count
    assert len(coverage)==432 and total==data['executed_battles']
    result=dict(cells=len(coverage),executed_battles=total,physical_journeys=journeys,
        actual_journey_battles=native_battles,censored_actual_battles=censored,exact_saved_battle_replays=replays,
        archive_sha256=archives)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scope',choices=('measurements','prototype','refined','all'),default='all');args=p.parse_args()
    results={}
    if args.scope in ('measurements','all'):
        results['main_measurements']=measured(lab.OUT)
        results['low_margin_measurements']=measured(lab.OUT/'low_margin')
    if args.scope in ('prototype','all'):results['prototype_confirmation']=confirmation(lab.OUT/'confirmation')
    if args.scope in ('refined','all'):results['refined_confirmation']=confirmation(lab.OUT/'refined/confirmation')
    output=lab.OUT/f'audit_{args.scope}.json'
    atomic_json(output,dict(status='passed',validator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),results=results))
    print('audit',args.scope,'passed', {k:{x:y for x,y in v.items() if x!='archive_sha256'} for k,v in results.items()},flush=True)


if __name__=='__main__':main()
