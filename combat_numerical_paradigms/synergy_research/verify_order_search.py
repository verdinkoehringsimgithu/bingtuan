"""Verify the order optimizer and completed held-out experiment artifacts."""
import argparse
import gzip
import hashlib
import itertools
import json
from pathlib import Path

from order_search import optimize, initial_orders, reordered, rank_score, snapshot
from rosters import build, encounter
from bond_core import simulate
from run_bonds import signature, atomic_json
from settings import HERE


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, default=HERE / 'results/optimal_order')
    args = ap.parse_args(); out = args.output
    expected = (4, 2, 0, 3, 1); seen = {'train': set(), 'select': set()}
    def objective(order, split):
        seen[split].add(order)
        return (int(order == expected), -sum(a != b for a, b in zip(order, expected)), 0)
    result = optimize(5, [tuple(range(5))], objective, 29)
    assert result['order'] == expected
    assert len(seen['train']) == 120 and len(seen['select']) == 8
    assert not result['global_population_optimum_proven']
    # A large-N result must be repeatable and respect the search budget.
    def large(order, split): return (-sum(abs(a - b) for a, b in enumerate(order)), 0, 0)
    first = optimize(10, [tuple(reversed(range(10)))], large, 37, budget=40)
    assert first == optimize(10, [tuple(reversed(range(10)))], large, 37, budget=40)
    assert first['searched_orders'] == 40 and not first['exhaustive_training']
    assert rank_score([dict(win=1, margin=-.9, censored=0)]) > rank_score([dict(win=0, margin=1, censored=0)])
    members, items = build(5, 'C_I', 160000, (('maid', 10),), 'front', 'final')
    before = json.dumps(snapshot(members, items), sort_keys=True)
    for order in initial_orders(members, 'maid'):
        mm, ii = reordered(members, items, order)
        assert all(mm[j] is members[k] and ii[j] is items[k] for j, k in enumerate(order))
        assert [m.skill.id for m in mm] == [members[k].skill.id for k in order]
    assert before == json.dumps(snapshot(members, items), sort_keys=True)
    manifest = json.loads((out / 'manifest.json').read_text(encoding='utf-8'))
    completed = json.loads((out / 'completed.json').read_text(encoding='utf-8'))
    assert signature()[0] == manifest['combat_signature']
    assert hashlib.sha256((HERE / 'order_search.py').read_bytes()).hexdigest() == manifest['optimizer_sha256']
    assert completed['signature'] == manifest['signature']
    jobs = [cell['job'] for cell in completed['rows']]
    requested = {name: {job[name] for job in jobs} for name in ('stage', 'bond', 'genre', 'pool')}
    coefficients = json.loads((HERE / 'results/selected_coefficients.json').read_text(encoding='utf-8'))
    available_pairs = {(r['stage'], r['bond']) for r in coefficients if r['soft_delta_reference'] == .1}
    expected_coverage = {(s, b, g, p) for s in requested['stage'] for b in requested['bond']
                         for g in requested['genre'] for p in requested['pool'] if (s, b) in available_pairs}
    actual_coverage = {(j['stage'], j['bond'], j['genre'], j['pool']) for j in jobs}
    assert expected_coverage == actual_coverage and len(jobs) == len(actual_coverage)
    executions = 0; test_battles = 0; replayed = 0
    for cell in completed['rows']:
        job, result = cell['job'], cell['result']
        path = out / 'replicates' / (cell['key'] + '.json.gz')
        with gzip.open(path, 'rt', encoding='utf-8') as stream: raw = json.load(stream)
        assert raw['plans'] == result['plans']
        assert len(raw['trials']) == job['test_trials']
        assert set(raw['seeds']) == {'train', 'select', 'test'}
        assert all(not set(raw['seeds'][a]) & set(raw['seeds'][b])
                   for a, b in itertools.combinations(raw['seeds'], 2))
        n = 5 * (job['stage'] + 1)
        assert len(raw['members']) == len(raw['enemy']) == len(raw['reference']) == n
        assert len({m['person_id'] for m in raw['members']}) == n
        assert len({m['skill']['id'] for m in raw['members']}) == n
        for side in ('members', 'enemy', 'reference'):
            assert all(isinstance(m['item'], dict) for m in raw[side])
            assert sum(bool(m['item'].get('top', False)) for m in raw[side]) <= 4
        for plan in result['plans'].values():
            assert sorted(plan['order']) == list(range(n))
            assert not plan['global_population_optimum_proven']
            assert plan['searched_orders'] == (120 if n == 5 else job['budget'])
            assert plan['selected_orders'] == job['shortlist']
        measured = sum(p['searched_orders'] * job['train_trials'] + p['selected_orders'] * job['select_trials']
                       for p in result['plans'].values()) + 4 * job['test_trials']
        assert measured == result['executed_battles']
        executions += measured; test_battles += 4 * job['test_trials']
        for name, metric in result['metrics'].items():
            for k, v in metric.items():
                assert abs(sum(r[name][k] for r in raw['trials']) / len(raw['trials']) - v) < 1e-12
        for label, left, right in (('practical_gain', 'on', 'off'), ('mechanical_same_order', 'on', 'off_at_on_order'),
                                    ('net_vs_unrestricted', 'on', 'reference')):
            value = sum(t[left]['win'] - t[right]['win'] for t in raw['trials']) / len(raw['trials'])
            assert abs(value - result['differences'][label]['mean']) < 1e-12
        # Replay one frozen held-out battle for each stage and identity.
        if job['genre'] == 'C_I':
            mm, ii = build(job['stage'], job['genre'], job['pool'], ((job['bond'], job['count']),), 'front', 'final')
            assert json.loads(json.dumps(snapshot(mm, ii))) == raw['members']
            h, p = encounter(job['stage'], job['difficulty'])
            enemy, ei = build(job['stage'], h, job['pool'] + 100003, (), 'front', 'final')
            mm, ii = reordered(mm, ii, result['plans']['on']['order'])
            r, *_ = simulate(mm, enemy, raw['seeds']['test'][0], ii, ei, p=p,
                             enabled=(job['bond'],), config=job['config'])
            assert all(r[k] == v for k, v in raw['trials'][0]['on'].items())
            replayed += 1
    assert executions == completed['executed_battles']
    validation = dict(status='passed', cells=len(completed['rows']), executed_battles=executions,
                      heldout_battle_executions=test_battles, replayed=replayed, signature=manifest['signature'],
                      checks=['complete requested stage/identity/flow/roster coverage',
                              'exhaustive finite-sample optimum', 'deterministic bounded search',
                              'win-rate-first objective', 'member/skill/gear identity preserved',
                              'disjoint seeds', 'exact count accounting', 'held-out metrics reconstructed',
                              'core signature unchanged', 'one item per member and at most four top items',
                              'held-out battle replay'])
    atomic_json(out / 'validation.json', validation)
    print(json.dumps(validation, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
