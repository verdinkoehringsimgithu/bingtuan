"""Source, coverage, paired-result and exact-replay audit for the D4 grid."""
import gzip
import hashlib
import itertools
import json
from pathlib import Path

import compound_d4_research as lab
from order_search import snapshot
from run_bonds import atomic_json


def equivalent(a, b):
    return json.loads(json.dumps(a, sort_keys=True)) == json.loads(json.dumps(b, sort_keys=True))


def main():
    out = lab.OUT; data = json.loads((out / 'summary.json').read_text(encoding='utf-8'))
    manifest = json.loads((out / 'manifest.json').read_text(encoding='utf-8'))
    sig, current = lab.signature()
    assert sig == data['signature'] == manifest['signature']
    assert current == {k: v for k, v in manifest.items() if k != 'signature'}
    expected = set(itertools.product(range(6), lab.GENRES, lab.pilot.BONDS, ('small', 'full'), ('basic', 'four_top')))
    actual = {(r['job']['stage'], r['job']['genre'], r['job']['bond'], r['job']['density'], r['job']['gear']) for r in data['rows']}
    assert actual == expected and len(actual) == data['cells'] == len(data['rows']) == 432
    executions = 0; final_executions = 0; replays = 0; archives = {}
    for cell in data['rows']:
        j = cell['job']; path = out / 'replicates' / (cell['key'] + '.json.gz')
        assert hashlib.sha256((sig + json.dumps(j, sort_keys=True)).encode()).hexdigest() == cell['key']
        archives[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        with gzip.open(path, 'rt', encoding='utf-8') as f: raw = json.load(f)
        assert all(raw['job'][k] == v for k, v in j.items())
        mm, ii, enemy, ei, macro = lab.pilot.prepare(j)
        assert equivalent(raw['members'], snapshot(mm, ii)) and equivalent(raw['enemy'], snapshot(enemy, ei))
        assert equivalent(raw['macro'], macro)
        assert j['difficulty'] == 'extremely_hard' and j['pool'] == 790000
        assert len(mm) == len(enemy) == lab.STAGES[j['stage']][0]
        assert len({m.person_id for m in mm}) == len(mm)
        assert sum(m.identity == lab.CN[j['bond']] for m in mm) == j['count']
        assert sum(i.top for i in ii) == (4 if j['gear'] == 'four_top' else 0)
        models = dict([('off', {})] + lab.variants(j['bond']))
        assert models == raw['models']
        for a, b in itertools.combinations(raw['seeds'], 2):
            assert not set(raw['seeds'][a]) & set(raw['seeds'][b])
        for split, values in raw['seeds'].items(): assert len(values) == j[split + '_trials']
        search = 0
        for label, plan in raw['plans'].items():
            assert label in models and sorted(plan['order']) == list(range(len(mm)))
            assert plan['searched_orders'] == (120 if len(mm) == 5 else j['budget'])
            search += plan['searched_orders'] * j['train_trials'] + plan['selected_orders'] * j['select_trials']
        count = search + len(models) * (len(raw['shared_orders']) * j['cross_trials'] + j['test_trials'])
        assert count == raw['executed_battles'] == cell['result']['executed_battles']
        executions += count; final_executions += len(models) * j['test_trials']
        for label, values in cell['result']['metrics'].items():
            trials = raw['trials'][label]; assert len(trials) == j['test_trials']
            for key, value in values.items(): assert abs(sum(r[key] for r in trials) / len(trials) - value) < 1e-12
            expected_difference = dict(vs_off=lab.pilot.paired(trials, raw['trials']['off']),
                                       vs_v1=lab.pilot.paired(trials, raw['trials']['v1']))
            assert equivalent(expected_difference, cell['result']['differences'][label])
            for key, value in cell['result']['diagnostics'][label].items():
                assert abs(sum(r['metrics'].get(key, 0.) for r in trials) / len(trials) - value) < 1e-10
            if label != 'off' and j['bond'] == 'adventurer':
                goals = models[label].get('adventurer', {}).get('goals', lab.pilot.engine.DEFINITIONS['adventurer']['goals'])
                rate = models[label].get('adventurer', {}).get('per_goal_damage', .06)
                assert abs(rate * len(goals) - .36) < 1e-12
                for r in trials:
                    assert r['adventure_goals'] == len(set(goals) & set(r['first_events']))
                    assert r['adventure_boosted_casts'] <= r['adventure_casts']
            if j['genre'] == 'C_I':
                r, trace = lab.run_once(j, mm, ii, enemy, ei, macro, label, models[label],
                    raw['plans'][label]['order'], raw['seeds']['test'][0], True)
                assert equivalent(r, trials[0]) and equivalent(trace, raw['traces'][label][0])
                replays += 1
    assert executions == data['executed_battles']
    result = dict(status='passed', signature=sig, cells=len(data['rows']), executed_battles=executions,
        heldout_battle_executions=final_executions, exact_saved_battle_replays=replays,
        validator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        summary_sha256=hashlib.sha256((out / 'summary.json').read_bytes()).hexdigest(), archive_sha256=archives)
    atomic_json(out / 'validation.json', result)
    print({k: v for k, v in result.items() if k != 'archive_sha256'})


if __name__ == '__main__': main()
