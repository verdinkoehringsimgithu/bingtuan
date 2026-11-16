"""Behavioural checks for the new, separately versioned research candidates."""
import copy
import json

import compound_core as new
import joint_core as old
from rosters import build, GENRES
from run_bonds import atomic_json
from settings import HERE


def physical(result):
    value = {k: v for k, v in result.items() if k not in (
        'adventure_goals', 'first_events', 'enemy_first_events', 'maid_effect_level')}
    for key in ('metrics', 'enemy_metrics'):
        value[key] = {k: v for k, v in value[key].items() if not k.startswith('event_')}
    return value


def teams(identity, count=1, n=30, cfg=None):
    s = n // 5 - 1
    mm, ii = build(s, 'C_I', 410000, (), 'front', 'final')
    mm = tuple(copy.deepcopy(m) for m in mm)
    for i, m in enumerate(mm):
        m.identity = identity if i < count else '学生'
    enemy, ei = build(s, 'M_R', 510003, (), 'front', 'final')
    world = new.frozen.World(427)
    key = {'女仆': 'maid', '农民': 'farmer', '冒险者': 'adventurer'}[identity]
    a = new.Team(mm, ii, 0, world, (key,), cfg)
    b = new.Team(enemy, ei, 1, world)
    a.turn = b.turn = 1
    return a, b


def main():
    exact = 0
    for s in range(6):
        for g in GENRES:
            mm, ii = build(s, g, 420000, (), 'front', 'final')
            enemy, ei = build(s, g, 520003, (), 'front', 'final')
            for active in ((), ('engineer', 'ninja', 'sword', 'worker', 'killer')):
                for bs in (327, 817):
                    a, *_ = old.simulate(mm, enemy, bs, ii, ei, enabled=active)
                    b, *_ = new.simulate(mm, enemy, bs, ii, ei, enabled=active)
                    assert physical(a) == physical(b), (s, g, active)
                    exact += 1

    # First maid remains a legal guaranteed fallback despite original gates,
    # trigger chance and exhausted finite uses; the original skill is untouched.
    a, b = teams('女仆', 30)
    sk = a.members[0].skill
    sk.trigger_chance = 0; sk.times_limit = 1; sk.turn_cond1 = 999
    sk.self_bp_cond2 = 1; a.usage[sk.id] = 100
    a.current_bp = a.max_bp * .3
    before_stats = a.get_effective_stats()
    skill = new.select(a, b, 1)
    assert a.selected_owner == 0 and skill is not None and a.maid_level == 5
    assert a.current_bp > a.max_bp * .3
    assert skill.sub_effect_name == '四维削弱' and skill.ignore_def_ratio == 1 and skill.base_crit_rate > 0
    assert sk.ignore_def_ratio != skill.ignore_def_ratio or sk.base_crit_rate != skill.base_crit_rate
    new.post_attack(a, b, 0, True, False)
    assert all(x > y for x, y in zip(a.get_effective_stats(), before_stats))
    assert not b.stat_reduce_debuffs  # Enemy debuff requires native hit pipeline.

    # No special maid replacement when the bond is absent.
    a, b = teams('冒险者', 1)
    for m in a.members:
        m.skill.trigger_chance = 100; m.skill.turn_cond1 = m.skill.turn_cond2 = 0
        m.skill.self_bp_cond2 = m.skill.enemy_bp_cond2 = 0
    original = a.members[0].skill
    skill = new.select(a, b, 1)
    assert a.maid_mod is None and skill.main_type == original.main_type

    # Healing equipment and next-skill healing penalty affect independent
    # recovery exactly once; overheal-to-shield uses the native Team.heal.
    for kind, value in (('skill_heal', .5), ('overheal_shield', .5)):
        a, b = teams('女仆', 1)
        items = list(a.items); it = items[0]
        items[0] = new.frozen.natural.Item(kind, value, it.stats, it.bp, True)
        a.items = tuple(items); a.current_bp = a.max_bp if kind == 'overheal_shield' else a.max_bp * .2
        a.next_heal_penalty = .5
        before = a.current_bp
        new.select(a, b, 1)
        request = a.max_bp * .08 * a.q('女仆') * (1.5 if kind == 'skill_heal' else 1.)
        assert abs(a.metrics['killer_healing_prevented'] - request * .5) < 1e-8
        if kind == 'skill_heal': assert abs(a.current_bp - before - request * .5) < 1e-8
        else: assert abs(a.shield - request * .5 * value) < 1e-8
        assert a.next_heal_penalty == 0

    # Shared fruit: planting, three accelerating attacks, then harvest; two
    # different farmers operate the same object. Mature wait grows both parts.
    for count, wait in ((1, 0), (30, 0), (30, 3)):
        a, b = teams('农民', count)
        a.current_bp = a.max_bp * .1
        new.fruit(a, b, 0); assert a.fruit_ready == 6
        for turn in (2, 3):
            a.turn = turn; new.fruit(a, b, min(1, count - 1))
        assert a.fruit_ready == 4
        a.turn = 4 + wait
        before = a.current_bp; stats = a.get_effective_stats()
        new.fruit(a, b, 0)
        assert a.fruit_ready is None and a.metrics['fruit_harvest'] == 1
        strength = a.q('农民') * (1 + wait * .15)
        assert abs(a.current_bp - before - a.max_bp * .12 * strength) < 1e-8
        kinds = 1 if count == 1 else 4
        assert sum(x > y for x, y in zip(a.get_effective_stats(), stats)) == kinds
        assert abs(a.max_bp - sum(m.bp + it.bp for m, it in zip(a.members, a.items))) < 1e-6

    # Strict threshold crossings, multiple goals per hit, recovery does not
    # reset, shield-only hits do not count as lowering BP.
    a, b = teams('冒险者', 5)
    new.deal(a, b, b.max_bp * .6, 'test_damage')
    assert a.adventure_done == {'enemy_below_100', 'enemy_below_75', 'enemy_below_50'}
    b.heal(b.max_bp)
    new.deal(a, b, b.max_bp * .6, 'test_damage')
    assert a.metrics['adventure_completed'] == 3
    b.current_bp = b.max_bp; b.shield = b.max_bp
    new.deal(a, b, b.max_bp * .1, 'test_damage')
    assert a.metrics['adventure_completed'] == 3
    # Exact 25% is not below 25%.
    b.shield = 0; b.current_bp = b.max_bp
    new.deal(a, b, b.max_bp * .75, 'test_damage')
    assert 'enemy_below_25' not in a.adventure_done
    new.deal(a, b, 1, 'test_damage')
    assert 'enemy_below_25' in a.adventure_done

    # A lethal hit crosses the lines even when equipment or the worker bond
    # immediately restores BP above those lines inside the same deal call.
    for method in ('equipment', 'worker'):
        attacker, defender = teams('冒险者', 5)
        if method == 'equipment':
            items = list(defender.items); it = items[0]
            items[0] = new.frozen.natural.Item('death_lock', .8, it.stats, it.bp, True)
            defender.items = tuple(items)
        else:
            defender.enabled.add('worker'); defender.counts['社畜'] = 30
            defender.cfg['worker'] = .8
        new.deal(attacker, defender, defender.max_bp * 1.1, 'test_damage')
        assert defender.current_bp > defender.max_bp * .25
        assert {'enemy_below_100', 'enemy_below_75', 'enemy_below_50', 'enemy_below_25'} <= attacker.adventure_done

    # Defensive dodge is registered for the defending side, with no need for
    # that side to receive a subsequent attacking turn.
    new.on_miss(b)
    assert 'first_dodge' in a.adventure_done and 'first_dodge' not in b.adventure_done
    before = len(a.adventure_done); new.on_miss(b)
    assert len(a.adventure_done) == before

    # Compare a real action against a hit forced only by courage crit. The
    # native compound skill can both critically strike and use pure true.
    a, b = teams('女仆', 30)
    a.cfg['maid_kind'] = 'attack'; a.current_bp = a.max_bp * .4
    action = new.make_action(a.world); a.world.actor = a; a.world.draw_index = 0
    action(a, b, True, 1)
    assert a.metrics['pure_true'] + a.metrics['pure_true_crit'] > 0
    assert b.stat_reduce_debuffs and a.metrics['maid_heal'] > 0

    report = dict(status='passed', unchanged_path_battles=exact,
                  behaviours=['maid guaranteed unlimited replacement', 'compound self/enemy timing',
                              'healing gear and next-skill penalty', 'shared fruit maturation and multi-stats',
                              'strict first-crossing goals including resurrection', 'defensive dodge', 'native pure-true pipeline'])
    atomic_json(HERE / 'results/compound_core_validation.json', report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
