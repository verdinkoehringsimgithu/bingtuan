"""Versioned research extension for compound maid/fruit and real milestones.

Frozen studies and the production engine are unchanged. The native action is
retained for crit, miss, true damage, debuffs, equipment, and all other bonds.
"""
import ast
import inspect
import json
from pathlib import Path

import joint_core as joint

frozen = joint.frozen
ATTRS = frozen.ATTRS
DEFINITIONS = json.loads(Path(__file__).with_name('compound_effects.json').read_text(encoding='utf-8'))
ALL_EVENTS = tuple(DEFINITIONS['adventurer']['goals'] + DEFINITIONS['adventurer']['extra_observed_events'])


class Team(joint.Team):
    def __init__(self, *args, **kwargs):
        self.first_events = {}
        super().__init__(*args, **kwargs)
        self.opening_stats = tuple(getattr(self, 'cur_' + f) for f in ATTRS)
        self.maid_level = sum(self.q('女仆') >= x - 1e-12 for x in DEFINITIONS['maid']['unlocks'])
        self.fruit_axes = tuple(sorted(range(4), key=lambda k: (self.opening_stats[k], k)))
        self.maid_mod = None
        self.cfg['adventure_goals'] = tuple(DEFINITIONS['adventurer']['goals'])
        self.cfg['adventurer'] = DEFINITIONS['adventurer']['per_goal_damage']
        if not hasattr(self.world, 'teams'):
            self.world.teams = {}
        self.world.teams[self.side] = self

    def event(self, key, phase):
        if key not in self.first_events:
            self.first_events[key] = dict(turn=self.turn, phase=phase)
            self.add('event_' + key, 1)
            if self.active('adventurer') and key in self.cfg['adventure_goals']:
                self.adventure_done.add(key)
                self.add('adventure_completed', 1)

    def heal(self, amount):
        result = super().heal(amount)
        if result > 0 and self._base_ready:
            self.event('first_heal', self.heal_channel)
        return result


def configure_maid(team, enemy, pos, mod):
    d = DEFINITIONS['maid']; strength = team.q('女仆') * team.gain
    mod.main_type = 'Attack'
    mod.main_param = 100 * (1 + d['attack_gain'] * strength) * team.mu
    mod.sub_effect_name = ''; mod.sub_param = 0.; mod.sub_duration = 0
    mod.ignore_def_ratio = 0.; mod.base_crit_rate = 0.; mod.ini_bonus = 0
    if team.maid_level >= 3:
        mod.sub_effect_name = '四维削弱'
        mod.sub_param = d['debuff_percent'] * strength
        mod.sub_duration = d['debuff_duration']
    if team.maid_level >= 4:
        mod.base_crit_rate = d['skill_crit'] * strength
    if team.maid_level >= 5:
        mod.ignore_def_ratio = 1.
    team.add('maid_casts', 1)
    team.maid_mod = mod


class SelectAdapter(ast.NodeTransformer):
    def __init__(self):
        self.replaced = 0

    def visit_If(self, node):
        if ast.unparse(node.test) == "team.active('maid') and pos == team.maid_owner":
            # This exact condition occurs only at the replacement-skill block.
            self.replaced += 1
            node.body = ast.parse('configure_maid(team, enemy, pos, mod)').body
            return node
        return self.generic_visit(node)


_tree = ast.parse(inspect.getsource(frozen.select)); _adapter = SelectAdapter()
_tree = _adapter.visit(_tree); assert _adapter.replaced == 1
ast.fix_missing_locations(_tree)
_select_ns = {**vars(frozen), 'configure_maid': configure_maid}
exec(compile(_tree, '<compound-select>', 'exec'), _select_ns)
_select = _select_ns['select']


def select(team, enemy, turn):
    team.maid_mod = None
    mod = _select(team, enemy, turn)
    if (mod is not None and team.active('adventurer') and team.adventure_done
            and team.members[team.selected_owner].identity == '冒险者'):
        team.add('adventure_boosted_casts', 1)
    if team.maid_mod is not None:
        # The replacement is an attack with an independent self-recovery
        # component, so it keeps native crit/true damage instead of Heal's
        # native direct-multiplier reset. The consumed next-skill penalty and
        # this owner's healing/overheal equipment still apply exactly once.
        d = DEFINITIONS['maid']; amount = team.max_bp * d['heal'] * team.q('女仆') * team.gain
        item = team.items[team.selected_owner]
        if item.kind == 'skill_heal':
            amount *= 1 + item.value
        team.heal_channel = 'maid_heal'
        team.add('maid_heal_requested', amount)
        team.heal(amount)
        team.add('maid_components_cast', team.maid_level)
    return mod


def deal(acting, defender, amount, kind, ctx=None, clamp=True, owner=-1):
    old = defender.current_bp
    received = defender.metrics['damage_received']
    value = frozen.deal(acting, defender, amount, kind, ctx, clamp, owner)
    # Observe damage BEFORE a death-lock/resurrection heal can mask a crossing.
    damaged = defender.metrics['damage_received'] - received
    low = max(0., old - damaged)
    for pct in (100, 75, 50, 25):
        line = defender.max_bp * pct / 100
        if old >= line and low < line:
            acting.event('enemy_below_' + str(pct), kind)
    if kind == 'direct':
        acting.event('first_hit', 'direct')
        if ctx['is_crit']:
            acting.event('first_crit', 'direct')
    return value


def on_miss(acting):
    frozen.core.on_miss(acting)
    defender = acting.world.teams[1 - acting.side]
    defender.event('first_dodge', 'defence')


def absolute_miss(acting, defender):
    result = frozen.absolute_miss(acting, defender)
    if result:
        defender.event('first_absolute_dodge', 'defence')
    return result


def overflow(acting, defender, ctx):
    if ctx['is_crit'] and ctx['skill'].main_type != 'Heal' and acting.overflow_convert and ctx['_original_overflow'] > 0:
        amount = ctx['base_power'] * ctx['_original_overflow'] * ctx['preempt_factor'] * acting.get_dmg_output_factor() * acting.direct_factor
        deal(acting, defender, amount, 'overflow_true')


def make_action(world):
    ns = dict(vars(frozen.engine), select_skill=select, deal=deal, overflow=overflow,
              on_miss=on_miss, absolute_miss=absolute_miss, random=world)
    exec(frozen.ACTION_CODE, ns)
    return ns['execute_turn_action']


def fruit(team, enemy, owner):
    d = DEFINITIONS['farmer']
    if team.fruit_ready is None:
        team.fruit_ready = team.turn + d['ripen']; team.add('fruit_planted', 1)
    elif team.turn < team.fruit_ready:
        team.fruit_ready = max(team.turn, team.fruit_ready - d['accelerate'])
        team.add('fruit_accelerated', 1)
    else:
        wait = team.turn - team.fruit_ready
        strength = team.q('农民') * team.gain * (1 + wait * d['wait_gain'])
        amount = team.max_bp * d['heal'] * strength
        saved = team.recovery_factor; team.recovery_factor = 1.
        team.heal_channel = 'fruit_heal'; team.add('fruit_heal_requested', amount)
        team.heal(amount); team.recovery_factor = saved
        kinds = sum(team.q('农民') >= x - 1e-12 for x in d['axis_unlocks'])
        per_axis = sum(team.opening_stats) / 4 * d['stats_per_axis'] * strength
        for k in team.fruit_axes[:kinds]:
            f = ATTRS[k]
            setattr(team, 'cur_' + f, getattr(team, 'cur_' + f) + per_axis)
            team.add('fruit_stats_' + f, per_axis)
        team.add('fruit_stat_kinds', kinds); team.add('fruit_stats_total', per_axis * kinds)
        team.add('fruit_harvest', 1); team.add('fruit_wait', wait); team.fruit_ready = None


class PostAdapter(ast.NodeTransformer):
    def __init__(self):
        self.replaced = 0

    def visit_If(self, node):
        if ast.unparse(node.test) == "team.active('farmer') and identity == '农民'":
            self.replaced += 1
            node.body = ast.parse('fruit(team, enemy, owner)').body
            return node
        return self.generic_visit(node)


_tree = ast.parse(inspect.getsource(frozen.post_attack)); _adapter = PostAdapter()
_tree = _adapter.visit(_tree); assert _adapter.replaced == 1
ast.fix_missing_locations(_tree)
_post_ns = {**vars(frozen), 'fruit': fruit, 'deal': deal}
exec(compile(_tree, '<compound-post-attack>', 'exec'), _post_ns)
_post_attack = _post_ns['post_attack']


def post_attack(team, enemy, owner, was_skill, hit):
    _post_attack(team, enemy, owner, was_skill, hit)
    if team.maid_mod is not None and was_skill and owner == team.maid_owner and team.maid_level >= 2:
        scale = DEFINITIONS['maid']['stats_per_cast'] * team.q('女仆') * team.gain
        for k, f in enumerate(ATTRS):
            amount = team.opening_stats[k] * scale
            setattr(team, 'cur_' + f, getattr(team, 'cur_' + f) + amount)
            team.add('maid_stats_total', amount)
    if team.last_hit and was_skill:
        mod = team.maid_mod or team.selected_original
        if mod.sub_effect_name in ('最大流失', '已损流失', '固定流失'):
            team.event('first_dot', 'application')
        if mod.sub_effect_name in ('虚弱压制', '四维削弱'):
            team.event('first_debuff', 'application')


# Keep canonical extra-skill recursion. Event hooks replace only the old
# hand-selected adventure channel catalogue, not the action/recursion logic.
class AttackAdapter(ast.NodeTransformer):
    def visit_Expr(self, node):
        if 'team.adventure_done.intersection_update' in ast.unparse(node):
            return None
        return self.generic_visit(node)

    def visit_If(self, node):
        if 'team.adventure_done.add' in ast.unparse(node):
            return None
        return self.generic_visit(node)


_tree = AttackAdapter().visit(ast.parse(inspect.getsource(frozen.attack)))
ast.fix_missing_locations(_tree)
_attack_ns = {**vars(frozen), 'post_attack': post_attack}
exec(compile(_tree, '<compound-attack>', 'exec'), _attack_ns)
attack = _attack_ns['attack']

_simulate_ns = {**vars(frozen), 'Team': Team, 'make_action': make_action, 'deal': deal, 'attack': attack}
exec(compile(inspect.getsource(frozen.simulate), '<compound-simulate>', 'exec'), _simulate_ns)
_simulate = _simulate_ns['simulate']


def simulate(*args, **kwargs):
    result, rows, a, b = _simulate(*args, **kwargs)
    # Physics outputs match frozen paths when none of the three bonds is on.
    # Extra event fields are diagnostics, not changes to damage or random rolls.
    result['first_events'] = a.first_events
    result['enemy_first_events'] = b.first_events
    result['maid_effect_level'] = a.maid_level if a.active('maid') else 0
    return result, rows, a, b
