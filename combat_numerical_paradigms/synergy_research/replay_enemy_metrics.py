"""Recover defender-side healing-prevention logs by replaying frozen test orders.

No optimization, coefficient selection, or test-set order selection happens here.
The original saved player records must match every replay exactly. The existing
killer counter measures reduced requested recovery before the BP cap, not the
counterfactual difference in effective BP actually restored.
"""
import argparse
import concurrent.futures as cf
import gzip
import hashlib
import json
from pathlib import Path

from bond_core import simulate
from order_search import reordered
from rosters import build, encounter
from run_bonds import atomic_json, signature
from settings import HERE


def evaluate(cell, output):
    job = cell['job']
    with gzip.open(output / 'replicates' / (cell['key'] + '.json.gz'), 'rt', encoding='utf-8') as stream:
        raw = json.load(stream)
    mm, ii = build(job['stage'], job['genre'], job['pool'], ((job['bond'], job['count']),), 'front', 'final')
    h, p = encounter(job['stage'], job['difficulty'])
    enemy, ei = build(job['stage'], h, job['pool'] + 100003, (), 'front', 'final')
    mm, ii = reordered(mm, ii, raw['plans']['on']['order'])
    trials = []
    for bs, record in zip(raw['seeds']['test'], raw['trials']):
        result, _, _, defender = simulate(mm, enemy, bs, ii, ei, p=p, enabled=(job['bond'],), config=job['config'])
        assert all(result[k] == value for k, value in record['on'].items())
        metrics = result['enemy_metrics']
        prevented = metrics.get('killer_healing_prevented', 0.)
        trials.append(dict(battle_seed=bs, enemy_metrics=metrics, prevented_bp=prevented,
                           prevented_bp_fraction=prevented / defender.max_bp))
    means = {name: sum(t[name] for t in trials) / len(trials)
             for name in ('prevented_bp', 'prevented_bp_fraction')}
    return dict(key=cell['key'], stage=job['stage'] + 1, bond=job['bond'], genre=job['genre'],
                trials=trials, means=means, replayed_battles=len(trials))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, default=HERE / 'results/optimal_order')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--bonds', nargs='+', default=['killer'])
    args = ap.parse_args(); output = args.output
    original = json.loads((output / 'completed.json').read_text(encoding='utf-8'))
    manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
    assert signature()[0] == manifest['combat_signature']
    target = output / 'enemy_metrics_replay.json'
    source_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result = dict(signature=original['signature'], source_sha256=source_sha, cells={})
    if target.exists():
        saved = json.loads(target.read_text(encoding='utf-8'))
        if (saved['signature'], saved['source_sha256']) == (result['signature'], source_sha): result = saved
    wanted = {c['key'] for c in original['rows'] if c['job']['bond'] in args.bonds}
    result['cells'] = {key: row for key, row in result['cells'].items() if key in wanted}
    jobs = [c for c in original['rows'] if c['job']['bond'] in args.bonds and c['key'] not in result['cells']]
    with cf.ProcessPoolExecutor(args.workers) as pool:
        pending = [pool.submit(evaluate, cell, output) for cell in jobs]
        for future in cf.as_completed(pending):
            row = future.result(); result['cells'][row['key']] = row
            atomic_json(target, result)
    result['replayed_battles'] = sum(c['replayed_battles'] for c in result['cells'].values())
    atomic_json(target, result)
    print(json.dumps(dict(cells=len(result['cells']), replayed_battles=result['replayed_battles'],
                          exact_player_record_matches=True), ensure_ascii=False))


if __name__ == '__main__': main()
