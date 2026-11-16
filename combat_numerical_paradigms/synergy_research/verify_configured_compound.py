"""Check isolated parameter namespaces, ablations and the explicit true part."""
import json

import compound_core as frozen
from configured_compound_core import configured, variants
from rosters import build, GENRES
from run_bonds import atomic_json
from settings import HERE
from verify_compound_core import teams


def main():
    v1 = configured({})
    original_definitions = json.dumps(frozen.DEFINITIONS, sort_keys=True)
    parity = 0
    for s in range(6):
        for g in GENRES:
            for key in ('maid', 'farmer', 'adventurer'):
                mm, ii = build(s, g, 710000, ((key, min(5, s + 1)),), 'front', 'final')
                enemy, ei = build(s, g, 810003, (), 'front', 'final')
                a, trace, *_ = frozen.simulate(mm, enemy, 251, ii, ei, enabled=(key,), telemetry=True)
                b, rows, *_ = v1.simulate(mm, enemy, 251, ii, ei, enabled=(key,), telemetry=True)
                assert a == b and trace == rows
                parity += 1
    low = configured(variants('maid')[1][1]); high = configured(variants('maid')[-1][1])
    assert low.DEFINITIONS['maid']['heal'] == .02 and high.DEFINITIONS['maid']['heal'] == .08
    assert frozen.DEFINITIONS['maid']['heal'] == .08
    assert json.dumps(frozen.DEFINITIONS, sort_keys=True) == original_definitions
    # Actual full-team maid action gets native physical direct plus a separate
    # true component; damage is not globally changed into pure true.
    a, b = teams('女仆', 30)
    a = high.Team(a.members, a.items, 0, high.frozen.World(427), ('maid',))
    b = high.Team(b.members, b.items, 1, a.world)
    a.turn = b.turn = 1; a.world.actor = a; a.world.draw_index = 0
    high.make_action(a.world)(a, b, True, 1)
    assert a.metrics['physical'] + a.metrics['physical_crit'] > 0
    assert a.metrics['maid_true'] > 0 and a.maid_mod.ignore_def_ratio == 0
    assert a.metrics['pure_true'] + a.metrics['pure_true_crit'] == 0
    # Independently configured fruit ablations preserve maturity and omit
    # exactly their declared component.
    for label, parameters in variants('farmer')[-2:]:
        module = configured(parameters)
        a, b = teams('农民', 30)
        a = module.Team(a.members, a.items, 0, module.frozen.World(1), ('farmer',))
        b = module.Team(b.members, b.items, 1, a.world)
        a.turn = 10; a.fruit_ready = 7; a.current_bp = a.max_bp * .1
        before = a.current_bp; stats = a.get_effective_stats()
        module.fruit(a, b, 0)
        assert a.metrics['fruit_harvest'] == 1
        if label == 'heal_only': assert a.current_bp > before and a.get_effective_stats() == stats
        else: assert a.current_bp == before and all(x > y for x, y in zip(a.get_effective_stats(), stats))
    for _, parameters in variants('adventurer'):
        goals = parameters.get('adventurer', {}).get('goals', frozen.DEFINITIONS['adventurer']['goals'])
        rate = parameters.get('adventurer', {}).get('per_goal_damage', .06)
        assert abs(len(goals) * rate - .36) < 1e-12
    result = dict(status='passed', exact_v1_battles=parity,
                  checks=['independent parameter namespaces', 'physical plus explicit true component',
                          'fruit component ablations', 'equal maximum adventure reward'])
    atomic_json(HERE / 'results/configured_compound_validation.json', result)
    print(result)


if __name__ == '__main__': main()
