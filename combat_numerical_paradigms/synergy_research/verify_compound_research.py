"""Audit the new pilot independently from its generated human-facing report."""
import gzip
import hashlib
import itertools
import json
from pathlib import Path

import compound_research as lab
from order_search import reordered, snapshot
from run_bonds import atomic_json


def equivalent(a, b):
    return json.loads(json.dumps(a, sort_keys=True)) == json.loads(json.dumps(b, sort_keys=True))


def main():
    out = lab.OUT
    data = json.loads((out / 'summary.json').read_text(encoding='utf-8'))
    manifest = json.loads((out / 'manifest.json').read_text(encoding='utf-8'))
    sig, current = lab.signature()
    assert sig == data['signature'] == manifest['signature']
    assert current == {k: v for k, v in manifest.items() if k != 'signature'}
    assert len(data['rows']) == data['cells'] == 432
    expected = set(itertools.product(range(6), lab.GENRES, lab.BONDS, ('small', 'full'), ('basic', 'four_top')))
    actual = {(r['job']['stage'], r['job']['genre'], r['job']['bond'], r['job']['density'], r['job']['gear']) for r in data['rows']}
    assert actual == expected
    executed = 0; replays = 0; heldout = 0; archive_hashes = {}
    for cell in data['rows']:
        j = cell['job']; path = out / 'replicates' / (cell['key'] + '.json.gz')
        archive_hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        with gzip.open(path, 'rt', encoding='utf-8') as f: raw = json.load(f)
        assert all(raw['job'][k] == v for k, v in j.items())
        mm, ii, enemy, ei, macro = lab.prepare(j)
        assert equivalent(snapshot(mm, ii), raw['members'])
        assert equivalent(snapshot(enemy, ei), raw['enemy'])
        assert equivalent(macro, raw['macro'])
        assert len(mm) == lab.STAGES[j['stage']][0] == len(enemy)
        assert len({m.person_id for m in mm}) == len(mm)
        assert sum(m.identity == lab.CN[j['bond']] for m in mm) == j['count']
        assert sum(i.top for i in ii) == (4 if j['gear'] == 'four_top' else 0)
        assert raw['config'] == {'gain': 1.}
        for a, b in itertools.combinations(raw['seeds'], 2):
            assert not set(raw['seeds'][a]) & set(raw['seeds'][b])
        for split, seeds in raw['seeds'].items():
            assert len(seeds) == j[split + '_trials']
        searches = 0
        for plan in raw['plans'].values():
            assert sorted(plan['order']) == list(range(len(mm)))
            assert plan['searched_orders'] == (120 if len(mm) == 5 else j['budget'])
            searches += plan['searched_orders'] * j['train_trials'] + plan['selected_orders'] * j['select_trials']
        count = searches + 3 * len(raw['candidates']) * j['cross_trials'] + 4 * j['test_trials']
        assert count == raw['executed_battles'] == cell['result']['executed_battles']
        executed += count; heldout += 4 * j['test_trials']
        for model, metrics in cell['result']['metrics'].items():
            rr = raw['trials'][model]; assert len(rr) == j['test_trials']
            for k, value in metrics.items():
                assert abs(sum(r[k] for r in rr) / len(rr) - value) < 1e-12
            if model != 'previous':
                for r in rr:
                    assert all(1 <= event['turn'] <= r['turns'] for event in r['first_events'].values())
                    assert len(r['first_events']) == sum(v for k, v in r['metrics'].items() if k.startswith('event_'))
                    if model == 'compound' and j['bond'] == 'adventurer':
                        expected_goals = set(r['first_events']) & set(lab.engine.DEFINITIONS['adventurer']['goals'])
                        assert r['adventure_goals'] == len(expected_goals)
                        assert r['adventure_boosted_casts'] <= r['adventure_casts']
                    elif model in ('off', 'off_at_compound'):
                        assert r['adventure_goals'] == 0
        for label, control in (('vs_off_optimized', 'off'), ('vs_previous_optimized', 'previous'), ('vs_off_same_order', 'off_at_compound')):
            assert equivalent(lab.paired(raw['trials']['compound'], raw['trials'][control]), cell['result']['differences'][label])
        # Replay every C_I cell's first final battle for ALL four final plans.
        if j['genre'] == 'C_I':
            for name in ('off', 'previous', 'compound', 'off_at_compound'):
                plan = 'compound' if name == 'off_at_compound' else name
                m, items = reordered(mm, ii, raw['plans'][plan]['order'])
                simulate = lab.old.simulate if name == 'previous' else lab.engine.simulate
                active = () if name in ('off', 'off_at_compound') else (j['bond'],)
                r, trace, a, _ = simulate(m, enemy, raw['seeds']['test'][0], items, ei, p=macro,
                    enabled=active, config=raw['config'], telemetry=name != 'off_at_compound')
                value = lab.compact(r)
                if name != 'previous':
                    value.update(adventure_casts=sum(a.casts[k] for k, member in enumerate(m) if member.identity == '冒险者'),
                                 adventure_boosted_casts=a.metrics['adventure_boosted_casts'])
                assert equivalent(value, raw['trials'][name][0]), (cell['key'], name)
                if name != 'off_at_compound': assert equivalent(trace, raw['traces'][name][0])
                replays += 1
    assert executed == data['executed_battles']
    result = dict(status='passed', signature=sig, cells=len(data['rows']), executed_battles=executed,
        heldout_battle_executions=heldout, exact_saved_battle_replays=replays,
        source_audit='all frozen and new input hashes matched', archive_sha256=archive_hashes,
        validator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        summary_sha256=hashlib.sha256((out / 'summary.json').read_bytes()).hexdigest())
    atomic_json(out / 'validation.json', result)
    print({k: v for k, v in result.items() if k != 'archive_sha256'})


if __name__ == '__main__': main()
