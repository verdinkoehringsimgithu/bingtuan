"""Identity limits parity, healing ceilings, independent fights and rest."""
import math

import trip_core as new
from rosters import build, GENRES
from run_bonds import atomic_json


def main():
    parity = 0
    for s in range(6):
        for g in GENRES:
            mm, ii = build(s, g, 910000, (), 'front', 'final')
            enemy, ei = build(s, g, 1010003, (), 'front', 'final')
            for bs in (314, 918):
                a, trace, *_ = new.base.simulate(mm, enemy, bs, ii, ei, telemetry=True)
                b, rows, *_ = new.simulate(mm, enemy, bs, ii, ei, telemetry=True)
                assert all(b[k] == v for k, v in a.items()) and trace == rows
                parity += 1
            r, _, player, foe = new.simulate(mm, enemy, 314, ii, ei, factors=(.7, .8, .9, .5, .6))
            raw = new.base.Team(mm, ii, 0, new.base.frozen.World(1))
            fresh = new.Team(mm, ii, 0, new.base.frozen.World(1))
            # Each new fight starts full, at the damaged maximum; no previous
            # finite-use counts, accumulated healing or battle growth carry.
            token = new._limits.set((.7, .8, .9, .5, .6))
            try: limited = new.Team(mm, ii, 0, new.base.frozen.World(2))
            finally: new._limits.reset(token)
            assert limited.current_bp == limited.max_bp == raw.max_bp * .7
            assert limited.usage == {} and limited.casts == [0] * len(mm)
            assert all(abs(a - b * c) < 1e-9 for a, b, c in zip(limited.get_effective_stats(), raw.get_effective_stats(), (.8, .9, .5, .6)))
            limited.current_bp = 1
            limited.heal(limited.max_bp * 10)
            assert limited.current_bp == limited.max_bp
            limited.cur_initiative += 100
            assert abs(limited.get_effective_stats()[2] - (raw.cur_initiative + 100) * .5) < 1e-9
            assert fresh.travel_factors == (1.,) * 5 and foe.travel_factors == (1.,) * 5
    assert new.rest(2.) == 0 and new.rest(2., .5) == 1.
    assert abs(new.factors((1, .5, 0, 0, 0), -math.log(.8))[0] - .8) < 1e-12
    result = dict(status='passed', exact_no_travel_penalty_battles=parity,
        verified=['player only', 'full at effective cap', 'native battle growth scaled',
                  'healing cannot lift cap', 'new fight finite uses reset', 'rest restores limits'])
    atomic_json(new.HERE / 'results/core_validation.json', result)
    print(result)


if __name__ == '__main__': main()
