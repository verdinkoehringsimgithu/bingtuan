"""Paired finite differences, fruit interaction and explicit parameter export."""
import gzip
import hashlib
import json
import math
from pathlib import Path

import compound_d4_research as lab
from run_bonds import atomic_json


def summarize(values):
    avg = sum(values) / len(values)
    se = math.sqrt(sum((x - avg)**2 for x in values) / (len(values) - 1) / len(values))
    return dict(mean=avg, se=se, normal_95_low=avg - 1.96 * se, normal_95_high=avg + 1.96 * se)


def main():
    out = lab.OUT; source = out / 'summary.json'; data = json.loads(source.read_text(encoding='utf-8'))
    slopes = []; interactions = []; packets = []
    for cell in data['rows']:
        j = cell['job']
        with gzip.open(out / 'replicates' / (cell['key'] + '.json.gz'), 'rt', encoding='utf-8') as f: raw = json.load(f)
        base = dict(stage=j['stage'] + 1, capacity=lab.STAGES[j['stage']][0], bond=j['bond'],
                    genre=j['genre'], density=j['density'], count=j['count'], gear=j['gear'])
        if j['bond'] == 'maid':
            pairs = [('addition_0.25', 'addition_0.5', .25), ('addition_0.5', 'addition_1', .5)]
        elif j['bond'] == 'farmer':
            pairs = [('mixed_half', 'v1', .5), ('v1', 'mixed_high', .5)]
            values = [mix['win'] - heal['win'] - stats['win'] + off['win'] for mix, heal, stats, off in zip(
                raw['trials']['v1'], raw['trials']['heal_only'], raw['trials']['stats_only'], raw['trials']['off'])]
            interactions.append({**base, **summarize(values)})
        else:
            pairs = []
            for label, rows in raw['trials'].items():
                if label == 'off': continue
                definition = raw['models'][label].get('adventurer', {})
                goals = definition.get('goals', lab.pilot.engine.DEFINITIONS['adventurer']['goals'])
                rate = definition.get('per_goal_damage', .06)
                count = len(rows)
                packets.append({**base, 'variant': label, 'goal_count': len(goals),
                    'max_damage_bonus_before_q': len(goals) * rate,
                    'completion_fraction': sum(r['adventure_goals'] / len(goals) for r in rows) / count,
                    'mean_adventure_casts': sum(r['adventure_casts'] for r in rows) / count,
                    'mean_boosted_casts': sum(r['adventure_boosted_casts'] for r in rows) / count,
                    'win': sum(r['win'] for r in rows) / count})
        for low, high, distance in pairs:
            values = [(b['win'] - a['win']) / distance for a, b in zip(raw['trials'][low], raw['trials'][high])]
            slopes.append({**base, 'lower_variant': low, 'upper_variant': high,
                           'scale_interval': distance, **summarize(values)})
    lab.pilot.table(out / 'directional_budget_slopes.csv', slopes)
    lab.pilot.table(out / 'fruit_practical_interactions.csv', interactions)
    lab.pilot.table(out / 'adventure_packet_diagnostics.csv', packets)
    atomic_json(out / 'candidate_parameters.json', {key: dict(lab.variants(key)) for key in lab.pilot.BONDS})
    atomic_json(out / 'resolved_candidate_parameters.json', {key: {name: lab.configured(parameters).DEFINITIONS
        for name, parameters in lab.variants(key)} for key in lab.pilot.BONDS})
    # Stage tables are descriptive averages. Do not present an average of
    # individual-cell standard errors/interval endpoints as an aggregate CI.
    groups = {}
    for cell in data['rows']:
        j = cell['job']
        for label, metrics in cell['result']['metrics'].items():
            key = (j['stage'], j['bond'], j['density'], j['count'], label)
            value = {**metrics, **{'delta_' + ref: diff['mean']
                for ref, diff in cell['result']['differences'][label].items()}}
            groups.setdefault(key, []).append(value)
    stage_rows = []
    for (s, bond, density, count, label), rows in groups.items():
        stage_rows.append(dict(stage=s + 1, capacity=lab.STAGES[s][0], bond=bond,
            density=density, count=count, variant=label, cells=len(rows),
            **{key: sum(row[key] for row in rows) / len(rows) for key in rows[0]}))
    lab.pilot.table(out / 'stage_responses.csv', stage_rows)
    atomic_json(out / 'response_analysis_provenance.json', dict(signature=data['signature'],
        summary_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        analyzer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        stage_table_sha256=hashlib.sha256((out / 'stage_responses.csv').read_bytes()).hexdigest(),
        slope_units='win fraction per unit common coefficient scale; multiply by 10 for pp per +0.1 scale',
        interpretation='all variants reorder independently; directional practical response, not isolated partial derivative'))
    print('D4 response evidence:', len(slopes), 'slopes,', len(interactions), 'fruit interactions,', len(packets), 'goal packets')


if __name__ == '__main__': main()
