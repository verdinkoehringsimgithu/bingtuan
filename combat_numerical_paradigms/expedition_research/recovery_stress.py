"""Six-stage native recovery-bond journeys; paired end-HP / damage-exposure wear."""
import argparse
import concurrent.futures as cf
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import sqlite3

import measure_response as lab
import trip_core
from bond_trip_core import configured_trip
from configured_compound_core import configured, variants
from confirm_paths import compact, draw
from order_search import initial_orders, optimize, rank_score, reordered, snapshot
from rosters import availability
from run_bonds import atomic_json

OUT = lab.OUT / 'recovery_stress'
MODELS = {'maid_half': ('maid', dict(variants('maid'))['addition_0.5']),
          'maid_full': ('maid', dict(variants('maid'))['addition_1']),
          'farmer': ('farmer', {})}


def prepare(j):
    bond, parameters = MODELS[j['model']]
    mm, _ = lab.build(j['stage'], j['genre'], 1370000, ((bond, j['count']),), 'front', 'final')
    ii = lab.supplies.equipment(mm, j['genre'], j['stage'], 'four_top')
    enemy, ei = lab.build(j['stage'], j['enemy_genre'], 1470003, (), 'front', 'final')
    simulator = configured_trip(parameters)
    return mm, ii, enemy, ei, simulator, bond


def solve(j, mm, ii, enemy, ei, simulator, bond, wear, previous):
    executed = 0
    seeds = {s: [lab.seed('recovery-order', j, wear, s, i) for i in range(n)]
             for s, n in (('train', 2), ('select', 4), ('test', 128 if wear == 0 else 32))}
    def run(order, split):
        nonlocal executed
        m, it = reordered(mm, ii, order)
        rows = [simulator(m, enemy, bs, it, ei, p=j['macro'], enabled=(bond,),
                         factors=trip_core.factors(lab.PROFILES['bp_only'], wear))[0] for bs in seeds[split]]
        executed += len(rows)
        return rows
    starting = ([previous] if previous is not None else []) + initial_orders(mm, bond)
    plan = optimize(len(mm), starting, lambda o, s: rank_score(run(o, s)),
                    lab.seed('recovery-search', j, wear), 16, 3)
    rows = run(plan['order'], 'test')
    wins = [r for r in rows if r['win']]
    return dict(plan=plan, seeds=seeds, trials=[compact(r) for r in rows],
        metrics={**{k: sum(r[k] for r in rows) / len(rows) for k in ('win', 'censored', 'hp', 'damage_exposure')},
                 'winning_hp': sum(r['hp'] for r in wins) / len(wins) if wins else None,
                 'effective_heal': sum(sum(v for k, v in r['metrics'].items() if k.endswith('_heal')) for r in rows) / len(rows)},
        executed_battles=executed)


def route(j, prepared, simulator, bond, mm, ii, enemy, ei, signal, index):
    wear = 0.; rows = []
    policy = dict(profile='bp_only', signal=signal, p0=.65, p_pressure=0., loss0=.08, loss_pressure=.2)
    for node in range(1, 31):
        nearest = min(lab.GRID, key=lambda x: (abs(x - wear), x))
        order = prepared[str(nearest)]['plan']['order']; m, it = reordered(mm, ii, order)
        bs = lab.seed('recovery-native', j, index, node)
        r, trace, *_ = simulator(m, enemy, bs, it, ei, p=j['macro'], enabled=(bond,),
            factors=trip_core.factors(lab.PROFILES['bp_only'], wear), telemetry=index == 0 and node <= 3)
        roll = lab.seed('recovery-event', j, index, node) / (1 << 64)
        delta = draw(policy, r, roll) if r['win'] else 0.
        row = dict(node=node, order=order, battle_seed=bs, event_roll=roll, wear_before=wear,
            wear_after=wear + delta, result=compact(r))
        if trace: row['trace'] = trace
        rows.append(row); wear += delta
        if not r['win']: break
    return rows


def evaluate(j):
    mm, ii, enemy, ei, simulator, bond = prepare(j)
    prepared = {}; previous = None
    for wear in lab.GRID:
        answer = solve(j, mm, ii, enemy, ei, simulator, bond, wear, previous)
        prepared[str(wear)] = answer; previous = answer['plan']['order']
    routes = {signal: [route(j, prepared, simulator, bond, mm, ii, enemy, ei, signal, i)
                      for i in range(64)] for signal in ('end_hp', 'exposure')}
    executed = sum(v['executed_battles'] for v in prepared.values()) + sum(len(r) for rr in routes.values() for r in rr)
    raw = dict(job=j, members=snapshot(mm, ii), enemy=snapshot(enemy, ei), prepared=prepared, routes=routes,
               executed_battles=executed)
    path = OUT / 'replicates' / (j['key'] + '.json.gz'); path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path.with_suffix('.tmp'), 'wt', encoding='utf-8') as f: json.dump(raw, f, ensure_ascii=False)
    path.with_suffix('.tmp').replace(path)
    curves = {}
    for signal, rr in routes.items():
        curves[signal] = [dict(battle=n, entered=sum(len(r) >= n for r in rr),
            wins=sum(len(r) >= n and r[n-1]['result']['win'] for r in rr),
            cap_sum=sum(math.exp(-r[n-1]['wear_before']) for r in rr if len(r) >= n)) for n in range(1, 31)]
    return dict(executed_battles=executed, preparation_executions=sum(v['executed_battles'] for v in prepared.values()),
        baseline=prepared['0']['metrics'], curves=curves,
        state_responses={k: v['metrics'] for k, v in prepared.items()},
        journey_battles=sum(len(r) for rr in routes.values() for r in rr),
        censored=sum(q['result']['censored'] for rr in routes.values() for r in rr for q in r))


def signature():
    old, sources = lab.signature()
    paths = [Path(__file__), lab.HERE/'bond_trip_core.py', lab.HERE/'confirm_paths.py', lab.OUT/'regions.json']
    paths += [trip_core.SYNERGY/name for name in ('configured_compound_core.py', 'compound_core.py', 'compound_effects.json')]
    manifest = dict(response_signature=old, sources={**sources['sources'],
        **{str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}})
    return hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(), manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--workers', type=int, default=6)
    args = parser.parse_args(); OUT.mkdir(parents=True, exist_ok=True)
    sig, manifest = signature(); atomic_json(OUT/'manifest.json', dict(signature=sig, **manifest))
    regions = json.loads((lab.OUT/'regions.json').read_text(encoding='utf-8'))['regions']
    counts = {(r['stage']-1, r['bond']): r['available'] for r in availability()}
    jobs = []
    for region in regions:
        if region['region'] not in ('dominant', 'clutch'): continue
        for genre in lab.GENRES:
            for model, (bond, _) in MODELS.items():
                stage = region['stage']
                jobs.append(dict(stage=stage, genre=genre, model=model,
                    count=min(lab.STAGES[stage][0], counts[stage, bond]), region=region['region'],
                    enemy_genre=region['enemy_genre'], macro=region['macro']))
    db = sqlite3.connect(OUT/'checkpoints.sqlite'); db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS cells(key TEXT PRIMARY KEY,signature TEXT,job TEXT,result TEXT)'); db.commit()
    pending = {}; wanted = set()
    with cf.ProcessPoolExecutor(args.workers) as pool:
        for j in jobs:
            encoded = json.dumps(j, sort_keys=True); key = hashlib.sha256((sig+encoded).encode()).hexdigest(); wanted.add(key)
            if db.execute('SELECT 1 FROM cells WHERE key=?', (key,)).fetchone(): continue
            pending[pool.submit(evaluate, dict(**j, key=key))] = key, encoded
        print('recovery stress:', len(pending), '/', len(jobs), flush=True)
        for i, future in enumerate(cf.as_completed(pending), 1):
            key, encoded = pending[future]; result = future.result()
            db.execute('INSERT INTO cells VALUES(?,?,?,?)', (key, sig, encoded, json.dumps(result))); db.commit()
            if i % 6 == 0 or i == len(pending): print('saved', i, '/', len(pending), flush=True)
    rows = [dict(key=k, job=json.loads(j), result=json.loads(r)) for k,j,r in db.execute(
        'SELECT key,job,result FROM cells WHERE signature=?', (sig,)) if k in wanted]
    db.close(); assert len(rows) == len(jobs)
    atomic_json(OUT/'summary.json', dict(signature=sig, cells=len(rows), rows=rows,
        executed_battles=sum(r['result']['executed_battles'] for r in rows)))
    print('complete:', sum(r['result']['executed_battles'] for r in rows), 'executions', flush=True)


if __name__ == '__main__': main()
