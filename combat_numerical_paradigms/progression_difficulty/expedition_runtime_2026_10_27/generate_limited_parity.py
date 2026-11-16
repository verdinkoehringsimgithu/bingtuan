"""Replay frozen roster fixtures through the native Python pipeline with travel limits.

No source edits: inject only the Team cap/stat adapter and an explicit RNG tape.
This validates plain combat/equipment, not the research-only identity mechanisms.
"""
import hashlib
import inspect
import json
from pathlib import Path
import random
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'combat_numerical_paradigms/roster_research'))
sys.path.insert(0, str(ROOT / 'combat_numerical_paradigms/natural_research'))
import roster_core as core
import natural_core  # Installs the generator's current-pressure / current-heal / fixed-loss channels.


class Tape:
    def seed(self, value):
        self.rng = random.Random(value)
        self.values = []

    def random(self):
        value = self.rng.random()
        self.values.append(value)
        return value

    def randrange(self, count):
        # Same one-uniform fallback owner selection as the production C# core.
        return min(count - 1, int(self.random() * count))


tape = Tape()
core.random = tape
core.ACTION.__globals__['random'] = tape
LIMITS = (1.,) * 5
TEAMS = []


class LimitedTeam(core.Team):
    def __init__(self, *args, **kwargs):
        self.limits = (1.,) * 5
        self.minimum = 1.
        super().__init__(*args, **kwargs)
        if self.name == 'player':
            self.limits = LIMITS
            self.max_bp *= LIMITS[0]
            self.current_bp = self.max_bp
        TEAMS.append(self)

    def get_effective_stats(self):
        return tuple(x * factor for x, factor in zip(super().get_effective_stats(), self.limits[1:]))

    def add(self, key, value):
        super().add(key, value)
        if key == 'damage_received':
            self.minimum = min(self.minimum, max(0., self.current_bp) / self.max_bp)


namespace = dict(vars(core), Team=LimitedTeam)
exec(compile(inspect.getsource(core.simulate), '<limited-native-simulate>', 'exec'), namespace)
simulate = namespace['simulate']


def unpack(roster):
    members, items = [], []
    for pos, member in enumerate(roster):
        s = member.get('skill')
        if s:
            assert not s.get('selfLower') and not s.get('enemyLower'), 'Fixture requires supported native gates'
            skill = core.engine.BattleSkill(pos, s['name'], s['tier'], s['axis'],
                main_type=s['mainType'], main_param=s['mainParam'], trigger_chance=s['chance'],
                times_limit=s['limit'], turn_cond1=s['turnLower'], turn_cond2=s['turnUpper'],
                self_bp_cond2=s['selfUpper'], enemy_bp_cond2=s['enemyUpper'],
                base_crit_rate=s['baseCrit'], ignore_def_ratio=s['pierce'],
                sub_effect_name=s['subEffect'], sub_param=s['subParam'], sub_duration=s['duration'],
                ini_bonus=s['initiativeBonus'])
        else:
            skill = None
        members.append(core.Member(pos, member.get('role') or 'filler', tuple(member['stats']), member['bp'], skill))
        item = member.get('item') or {}
        items.append(core.Item(item.get('kind', 'none'), item.get('value', 0.), tuple(item.get('stats', (0.,)*4)),
                               item.get('bp', 0.), item.get('top', False)))
    return tuple(members), tuple(items)


def main():
    global LIMITS
    inputs = HERE.parent / 'runtime_parity_cases.json'
    fixtures = json.loads(inputs.read_text(encoding='utf-8-sig'))
    profiles = ((.6, 1., 1., 1., 1.), (1., .7, .8, .5, .9),
                (.6, .7, .8, .5, .9), (1., 1., 1., .25, 1.), (.25, .3, .4, .5, .6))
    cases = []
    for index, fixture in enumerate(fixtures):
        left, left_items = unpack(fixture['left'])
        right, right_items = unpack(fixture['right'])
        for profile_index, LIMITS in enumerate(profiles):
            TEAMS.clear()
            result, *_ = simulate(left, right, 270000 + index*10 + profile_index,
                left_items, right_items, p=fixture.get('macro'), max_turns=fixture['rounds'])
            a, b = TEAMS
            cases.append(dict(name=fixture['name'] + ':limits-' + str(profile_index),
                left=fixture['left'], right=fixture['right'], macro=fixture.get('macro'), rounds=fixture['rounds'],
                limits=dict(zip(('bp','courage','resilience','initiative','magic'), LIMITS)), random=tape.values,
                hp=result['hp'], enemy_hp=result['enemy_hp'], turns=result['turns'], win=result['win'],
                censored=result['censored'], draw=result['draw'],
                left_received=a.metrics['damage_received'], right_received=b.metrics['damage_received'],
                left_min=a.minimum, right_min=b.minimum,
                left_stats=a.get_effective_stats(), right_stats=b.get_effective_stats(),
                left_uses=[a.usage.get(i,0) for i in range(len(left))],
                right_uses=[b.usage.get(i,0) for i in range(len(right))]))
    (HERE/'limited_parity_cases.json').write_text(json.dumps(cases, ensure_ascii=False, separators=(',',':')), encoding='utf-8')
    source_paths = [inputs, Path(core.__file__), Path(natural_core.__file__), core.SOURCE, Path(__file__)]
    provenance = dict(cases=len(cases), profiles=profiles, stages=sorted({len(c['left']) for c in cases}),
                      sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths},
                      random_protocol='one uniform per fallback owner; shared tape for Python and C#')
    (HERE/'limited_parity_sources.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
    print(f'{len(cases)} native limited battle fixtures generated')


if __name__ == '__main__':
    main()
