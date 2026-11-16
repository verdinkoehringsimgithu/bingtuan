"""Frozen-region calibration and native battle response to persistent limits."""
import argparse
import concurrent.futures as cf
import gzip
import hashlib
import json
import math
from pathlib import Path
import sqlite3

import trip_core as engine
from rosters import build, encounter, seed, GENRES, STAGES
import joint_research as supplies
from order_search import optimize, rank_score, reordered, snapshot
from run_bonds import atomic_json, signature as base_signature

HERE = Path(__file__).resolve().parent
OUT = HERE / 'results'
DEFINITION = json.loads((HERE / 'requirements.json').read_text(encoding='utf-8'))
PROFILES = DEFINITION['research']['profiles']
GRID = DEFINITION['research']['wear_grid']
REGIONS = ('dominant', 'comfortable', 'hard', 'very_hard', 'clutch')


def signature():
    old, inputs = base_signature()
    paths = [Path(__file__), HERE / 'trip_core.py', HERE / 'requirements.json',
        engine.SYNERGY / 'joint_core.py', engine.SYNERGY / 'joint_research.py',
        engine.SYNERGY / 'order_search.py', HERE.parent / 'natural_research/results/equipment_operating_candidates.csv']
    sources = {str(supplies.ROOT / k): v for k, v in inputs.items()}
    sources.update({str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    manifest = dict(base_signature=old, sources=sources)
    return hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(), manifest


def native_orders(mm):
    order = tuple(range(len(mm)))
    candidates = [order, order[::-1]]
    for score in (lambda m: -m.skill.trigger_chance,
        lambda m: -m.skill.trigger_chance * (1 if m.skill.main_type == 'Heal' else m.skill.main_param / 100),
        lambda m: (not (0 < m.skill.times_limit < 999), -m.skill.main_param),
        lambda m: (bool(m.skill.turn_cond1 or m.skill.turn_cond2 or m.skill.self_bp_cond2 or m.skill.enemy_bp_cond2), -m.skill.trigger_chance)):
        candidates.append(tuple(sorted(order, key=lambda i: (score(mm[i]), i))))
    return list(dict.fromkeys(candidates))


def solve(mm, items, enemy, ei, macro, factors, stream, trials=32, previous=None):
    seed_map = {split: [seed('expedition-response', stream, split, i) for i in range(n)]
                for split, n in (('train', 2), ('select', 4), ('test', trials))}
    executed = 0
    def run(order, split):
        nonlocal executed
        m, it = reordered(mm, items, order); rows = []
        for bs in seed_map[split]:
            r, *_ = engine.simulate(m, enemy, bs, it, ei, p=macro, factors=factors)
            rows.append({k:r[k] for k in ('win', 'hp', 'margin', 'turns', 'censored', 'damage_exposure', 'minimum_bp_fraction')})
        executed += len(rows)
        return rows
    starting = ([tuple(previous)] if previous is not None else []) + native_orders(mm)
    plan = optimize(len(mm), starting, lambda o, s: rank_score(run(o, s)), seed('travel-order', stream), 16, 3)
    rr = run(plan['order'], 'test'); wins = [r for r in rr if r['win']]
    metrics = {key:sum(r[key] for r in rr)/len(rr) for key in ('win','hp','turns','censored','damage_exposure','minimum_bp_fraction')}
    metrics['winning_hp'] = sum(r['hp'] for r in wins)/len(wins) if wins else None
    return dict(plan=plan, seeds=seed_map, trials=rr, metrics=metrics, executed_battles=executed)


def calibration_jobs():
    jobs = []
    for s in range(6):
        h, p = encounter(s, 'hard')
        for scale in (.4, .5, .6, .7, .8, .9, 1.):
            jobs.append(dict(stage=s, kind='easy_scale', code=str(scale), enemy_genre=h,
                macro=(p[0]*scale,p[1]*scale,0,0,0,1)))
        h, p = encounter(s, 'extremely_hard')
        for alpha in (.5, .75, 1., 1.5, 2.):
            for beta in (.75, 1., 1.25, 1.5, 1.8):
                jobs.append(dict(stage=s, kind='clutch_grid', code=f'{alpha}:{beta}', enemy_genre=h,
                    macro=(p[0]*alpha,p[1]*beta,0,0,0,1)))
    return jobs


def calibrate(j):
    s = j['stage']; macro = j['macro']; by_flow = []; executed = 0
    enemy, ei = build(s,j['enemy_genre'],1030003,(),'front','validation')
    for g in GENRES:
        mm, _ = build(s,g,930000,(),'front','validation')
        items = supplies.equipment(mm,g,s,'basic')
        answer = solve(mm,items,enemy,ei,macro,(1.,)*5,('regions',s,g,j['kind'],j['code']),24)
        by_flow.append(dict(genre=g,**answer)); executed += answer['executed_battles']
    return dict(by_flow=by_flow, executed_battles=executed)


def select_regions(rows, output):
    selected = []
    for s in range(6):
        for name, target in (('dominant',.99),('comfortable',.90)):
            pool = [r for r in rows if r['job']['stage']==s and r['job']['kind']=='easy_scale']
            chosen = min(pool,key=lambda r:(abs(sum(f['metrics']['win'] for f in r['result']['by_flow'])/6-target),float(r['job']['code'])))
            selected.append(dict(stage=s,region=name,enemy_genre=chosen['job']['enemy_genre'],macro=chosen['job']['macro'],
                design_wr=target, calibration_wr=sum(f['metrics']['win'] for f in chosen['result']['by_flow'])/6,
                source_cell=chosen['key']))
        for name in ('hard','very_hard'):
            h,p = encounter(s,name)
            selected.append(dict(stage=s,region=name,enemy_genre=h,macro=p,source='existing fixed encounter'))
        pool = [r for r in rows if r['job']['stage']==s and r['job']['kind']=='clutch_grid']
        def distance(r):
            flows=r['result']['by_flow']; wr=sum(f['metrics']['win'] for f in flows)/6
            wins=[q['hp'] for f in flows for q in f['trials'] if q['win']]
            hp=sum(wins)/len(wins) if wins else 1.
            return ((wr-.65)/.15)**2+((hp-.15)/.15)**2
        chosen=min(pool,key=distance); flows=chosen['result']['by_flow']
        wins=[q['hp'] for f in flows for q in f['trials'] if q['win']]
        selected.append(dict(stage=s,region='clutch',enemy_genre=chosen['job']['enemy_genre'],macro=chosen['job']['macro'],
            design_wr=.65,design_winning_hp=.15,calibration_wr=sum(f['metrics']['win'] for f in flows)/6,
            calibration_winning_hp=sum(wins)/len(wins) if wins else None,score=distance(chosen),source_cell=chosen['key']))
    atomic_json(output/'regions.json',dict(regions=selected,scope='Fixed by stage/reference population; never adapts to live player'))


def curve_jobs(output):
    regions=json.loads((output/'regions.json').read_text(encoding='utf-8'))['regions']
    return [dict(stage=r['stage'],genre=g,gear=gear,region=r['region'],enemy_genre=r['enemy_genre'],macro=r['macro'],
                 pool=1010000,bank='validation') for r in regions for g in GENRES for gear in ('basic','four_top')]


def curve(j):
    s=j['stage'];g=j['genre'];mm,_=build(s,g,j['pool'],(),'front',j['bank'])
    ii=supplies.equipment(mm,g,s,j['gear'])
    enemy,ei=build(s,j['enemy_genre'],j['pool']+100003,(),'front',j['bank'])
    points={}; baseline=None; executed=0
    for profile,weights in PROFILES.items():
        previous=None
        for x in GRID:
            key=f'{profile}:{x}'
            if x==0 and baseline is not None:
                points[key]=dict(alias=baseline);previous=points[baseline]['plan']['order'];continue
            a=solve(mm,ii,enemy,ei,j['macro'],engine.factors(weights,x),
                ('curve',s,g,j['gear'],j['region'],profile,x),32,previous)
            points[key]=a;previous=a['plan']['order'];executed+=a['executed_battles']
            if x==0:baseline=key
    raw=dict(job=j,members=snapshot(mm,ii),enemy=snapshot(enemy,ei),points=points,executed_battles=executed)
    path=Path(j['output'])/'curves'/f'{j["key"]}.json.gz';path.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(path.with_suffix('.tmp'),'wt',encoding='utf-8') as f:json.dump(raw,f,ensure_ascii=False)
    path.with_suffix('.tmp').replace(path)
    return dict(executed_battles=executed,points={k:({'alias':v['alias']} if 'alias'in v else
        dict(metrics=v['metrics'],order=v['plan']['order'],outcomes=v['trials'])) for k,v in points.items()})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',choices=('regions','curves'),required=True)
    p.add_argument('--workers',type=int,default=6);p.add_argument('--output',type=Path,default=OUT)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    sig,manifest=signature();atomic_json(args.output/'manifest.json',{**manifest,'signature':sig})
    if args.phase=='curves':
        provenance=json.loads((args.output/'regions_provenance.json').read_text(encoding='utf-8'))
        assert provenance['signature']==sig
        assert hashlib.sha256((args.output/'regions.json').read_bytes()).hexdigest()==provenance['regions_sha256']
    db=sqlite3.connect(args.output/'checkpoints.sqlite');db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS cells(key TEXT PRIMARY KEY,signature TEXT,phase TEXT,job TEXT,result TEXT)');db.commit()
    pending={};wanted=set();jobs=calibration_jobs() if args.phase=='regions' else curve_jobs(args.output)
    with cf.ProcessPoolExecutor(args.workers) as pool:
        for j in jobs:
            encoded=json.dumps(j,sort_keys=True);key=hashlib.sha256((sig+args.phase+encoded).encode()).hexdigest();wanted.add(key)
            if db.execute('SELECT 1 FROM cells WHERE key=?',(key,)).fetchone():continue
            pending[pool.submit(calibrate if args.phase=='regions' else curve,{**j,'key':key,'output':str(args.output.resolve())})]=(key,encoded)
        print(f'{args.phase}: {len(pending)} pending / {len(jobs)}',flush=True)
        for i,f in enumerate(cf.as_completed(pending),1):
            key,encoded=pending[f];result=f.result()
            db.execute('INSERT INTO cells VALUES(?,?,?,?,?)',(key,sig,args.phase,encoded,json.dumps(result)));db.commit()
            if i%6==0 or i==len(pending):print(f'{args.phase}: saved {i}/{len(pending)}',flush=True)
    rows=[dict(key=k,job=json.loads(j),result=json.loads(r)) for k,j,r in db.execute(
        'SELECT key,job,result FROM cells WHERE signature=? AND phase=?',(sig,args.phase)) if k in wanted];db.close()
    assert len(rows)==len(jobs)
    atomic_json(args.output/(args.phase+'.json'),dict(signature=sig,cells=len(rows),executed_battles=sum(r['result']['executed_battles'] for r in rows),rows=rows))
    if args.phase=='regions':
        select_regions(rows,args.output)
        atomic_json(args.output/'regions_provenance.json',dict(signature=sig,
            regions_sha256=hashlib.sha256((args.output/'regions.json').read_bytes()).hexdigest()))
    print(args.phase,'complete:',len(rows),'cells;',sum(r['result']['executed_battles'] for r in rows),'executions',flush=True)


if __name__=='__main__':main()
