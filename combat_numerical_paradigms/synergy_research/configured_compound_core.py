"""Independent configurable successor of the frozen compound-v1 experiment.

Each parameter set owns its module namespace. Existing v1 globals and result
hashes are never changed; no factory mutates the live production engine.
"""
import copy
from functools import lru_cache
import json
from pathlib import Path
import types

SOURCE = Path(__file__).with_name('compound_core.py')


@lru_cache(maxsize=128)
def engine(encoded='{}'):
    parameters = json.loads(encoded)
    module = types.ModuleType('configured_compound_' + str(len(encoded)))
    module.__file__ = str(SOURCE)
    exec(compile(SOURCE.read_text(encoding='utf-8'), str(SOURCE), 'exec'), module.__dict__)
    module.DEFINITIONS = copy.deepcopy(module.DEFINITIONS)
    for key, fields in parameters.items():
        if key in ('maid', 'farmer', 'adventurer'):
            module.DEFINITIONS[key].update(fields)
    if parameters.get('maid', {}).get('true_mode') == 'additional':
        configure = module.configure_maid

        def configure_maid(team, enemy, pos, mod):
            configure(team, enemy, pos, mod)
            # The fifth component grants a separately budgeted true-damage
            # addition. Ordinary direct damage and gear piercing still use
            # the native defense pipeline; courage does not gain penetration.
            if team.maid_level >= 5:
                mod.ignore_def_ratio = 0.

        module.configure_maid = configure_maid
        module._select_ns['configure_maid'] = configure_maid
        original_deal = module.deal

        def deal(acting, defender, amount, kind, ctx=None, clamp=True, owner=-1):
            result = original_deal(acting, defender, amount, kind, ctx, clamp, owner)
            if (kind == 'direct' and acting.active('maid') and acting.maid_mod is not None
                    and acting.maid_level >= 5 and acting.selected_owner == acting.maid_owner
                    and not defender.is_dead() and not acting.is_dead()):
                # ctx.raw_dmg already contains this hit's native crit and
                # preempt factors. The explicit true component gets no extra
                # magic multiplier. Shield, absorption, rich and death-lock
                # continue through the existing deal implementation.
                rate = module.DEFINITIONS['maid']['true_addition'] * acting.q('女仆') * acting.gain
                requested = ctx['raw_dmg'] * rate
                acting.add('maid_true_requested', requested)
                original_deal(acting, defender, requested, 'maid_true')
            return result

        module.deal = deal
        module._simulate_ns['deal'] = deal
        module._post_ns['deal'] = deal
    return module


def configured(parameters):
    return engine(json.dumps(parameters, sort_keys=True))


def variants(bond):
    if bond == 'maid':
        result = [('v1', {})]
        for scale in (.25, .5, 1.):
            result.append((f'addition_{scale:g}', {'maid': dict(true_mode='additional',
                true_addition=.35 * scale, attack_gain=1.8 * scale, heal=.08 * scale,
                stats_per_cast=.025 * scale, debuff_percent=12 * scale, skill_crit=.2 * scale)}))
        return result
    if bond == 'farmer':
        return [('mixed_half', {'farmer': dict(heal=.06, stats_per_axis=.05)}),
                ('v1', {}),
                ('mixed_high', {'farmer': dict(heal=.18, stats_per_axis=.15)}),
                ('heal_only', {'farmer': dict(heal=.12, stats_per_axis=0.)}),
                ('stats_only', {'farmer': dict(heal=0., stats_per_axis=.1)})]
    if bond == 'adventurer':
        progress = ['enemy_below_100', 'enemy_below_75', 'enemy_below_50', 'enemy_below_25']
        sparse = ['enemy_below_75', 'enemy_below_25', 'first_crit', 'first_dodge']
        channels = ['enemy_below_75', 'first_crit', 'first_dodge', 'first_heal', 'first_dot', 'first_debuff']
        # Equal maximum direct bonus .36*q, before comparing actual completion
        # timing, reachable goals and later adventurer casting opportunities.
        return [('v1', {}), ('progress', {'adventurer': dict(goals=progress, per_goal_damage=.09)}),
                ('sparse', {'adventurer': dict(goals=sparse, per_goal_damage=.09)}),
                ('channels', {'adventurer': dict(goals=channels, per_goal_damage=.06)})]
    raise ValueError(bond)
