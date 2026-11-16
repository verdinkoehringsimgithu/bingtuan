"""Instrument the live V11 action function, never edit or replace its rules.

Zero-intervention parity is checked against the canonical battle driver. The
research driver preserves its order, DoT resistance lookup, and timeout ruling.
Extensions are explicit counterfactuals on aggregate troops, not actor simulation.
"""
from __future__ import annotations
import ast
import copy
import hashlib
import importlib.util
import inspect
import random
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "test_30man_combat_simulator.py"
spec = importlib.util.spec_from_file_location("v11_canonical", SOURCE)
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
GENRES = ("C_I", "C_R", "M_I", "M_R", "M_C", "R_I")
LABELS = dict(zip(GENRES, ("勇气+先机", "勇气+坚韧", "魔力+先机", "魔力+坚韧", "魔力+勇气", "坚韧+先机")))
STAGES = ((5, 60000, 120, 50, 20, 2), (10, 180000, 280, 130, 40, 3),
          (15, 360000, 480, 220, 60, 4), (20, 600000, 700, 340, 80, 5),
          (25, 820000, 880, 430, 90, 6), (30, 1000000, 1000, 500, 100, 6))
BOUNDS = np.array(((.3, 3.5), (.3, 2.5), (0, .8), (0, .5), (-200, 500), (.8, 2.)))
PARAMS = ("alpha", "beta", "gamma", "delta", "theta", "mu")
CHANNELS = ("physical", "physical_crit", "pure_true", "pure_true_crit", "max_dot", "lost_dot",
            "backlash", "execute", "overflow_true", "lifesteal", "self_heal", "macro_heal",
            "overheal_shield", "death_lock", "absorption_saved", "shield_saved", "penetration_credit")

def stable_seed(*parts):
    return int.from_bytes(hashlib.sha256("|".join(map(str, parts)).encode()).digest()[:8], "little")

class ResearchTroop(engine.Troop):
    def reset(self):
        super().reset()
        self.metrics = defaultdict(float)
        self.round_metrics = defaultdict(float)
        self.attack_factor = 1.
        self.absorption = self.regen = self.hit_floor = self.normal_comp = 0.
        self.crit_grant = self.overflow_convert = self.overheal_convert = self.shield_cap = 0.
        self.ramp = self.death_lock_ratio = 0.
        self.shield = 0.
        self.lock_used = False
        self.focus = 1. / self.scale
        self.no_skill_runs = []
        self.no_skill_run = 0
        self.turn = 0
        self.heal_channel = "self_heal"

    def add(self, key, val):
        self.metrics[key] += val
        self.round_metrics[key] += val

    def heal(self, amount):
        old = self.current_bp
        result = super().heal(amount)
        self.add(self.heal_channel, result)
        excess = max(0., amount - result)
        self.add("overheal", excess)
        if self.overheal_convert > 0:
            gain = min(max(0., self.shield_cap * self.max_bp - self.shield), excess * self.overheal_convert)
            self.shield += gain
            self.add("overheal_shield", gain)
        return self.current_bp - old

def observe_selection(acting, skill):
    acting.add("actions", 1)
    if skill.id == 9999:
        acting.no_skill_run += 1
        acting.add("normal_actions", 1)
    else:
        acting.add("skill_actions", 1)
        if acting.no_skill_run:
            acting.no_skill_runs.append(acting.no_skill_run)
        acting.no_skill_run = 0

def damage(acting, defender, amount, kind, context=None, clamp=True):
    """Disjoint effective HP damage; extra diagnostics never summed as damage."""
    absorbed = amount * defender.absorption
    net = amount - absorbed
    shield_saved = min(defender.shield, net)
    defender.shield -= shield_saved
    net -= shield_saved
    defender.add("absorption_saved", absorbed)
    defender.add("shield_saved", shield_saved)
    old = defender.current_bp
    new = old - net
    defender.current_bp = max(0., new) if clamp else new
    effective = min(max(0., old), net)
    acting.add("nominal_damage", net)
    acting.add("effective_damage", effective)
    defender.add("damage_received", effective)
    if kind == "direct":
        c = context
        nocrit_raw = c["raw_dmg"] if c["skill"].main_type == "Heal" else c["raw_dmg"] * (c["skill"].main_param / 100.) / c["mult"]
        if c["is_pure_true"]:
            nc = nocrit_raw * (1. + (c["m_amp"] - 1.) * .20)
        else:
            dr = max(0., c["pct_dr"] * (1. - c["skill"].ignore_def_ratio * c["m_amp"]))
            nc = max(1., nocrit_raw * (1. - dr) - c["flat_dr"])
        crit_frac = max(0., min(1., (amount - nc) / amount)) if amount else 0.
        channel = "pure_true" if c["is_pure_true"] else "physical"
        acting.add(channel, effective * (1. - crit_frac))
        acting.add(channel + "_crit", effective * crit_frac)
        no_pierce = max(1., c["raw_dmg"] * (1. - c["pct_dr"]) - c["flat_dr"])
        acting.add("penetration_credit", max(0., amount - no_pierce) * (1. - defender.absorption))
        acting.add("hits", 1)
        acting.add("crit_hits", int(c["is_crit"]))
    else:
        acting.add(kind, effective)
    if defender.current_bp <= .0001 and defender.death_lock_ratio and not defender.lock_used:
        defender.current_bp = defender.max_bp * defender.death_lock_ratio
        defender.lock_used = True
        defender.add("death_lock", defender.current_bp - max(0., new))
    return net

def overflow_damage(acting, defender, ctx):
    if ctx["is_crit"] and acting.overflow_convert and ctx["_overflow_original"] > 0:
        amount = ctx["base_power"] * ctx["_overflow_original"] * acting.overflow_convert * ctx["preempt_factor"] * acting.get_dmg_output_factor()
        damage(acting, defender, amount, "overflow_true")

class Instrument(ast.NodeTransformer):
    def visit_Assign(self, node):
        node = self.generic_visit(node)
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if "base_power" in names:
            node.value = ast.BinOp(node.value, ast.Mult(), ast.parse("acting.attack_factor * (1.0 + acting.ramp * (turn - 1))").body[0].value)
        if "raw_skill_crit" in names:
            node.value = ast.BinOp(node.value, ast.Add(), ast.parse("acting.crit_grant").body[0].value)
        if "extra_overflow" in names:
            return [node, *ast.parse("_overflow_original = extra_overflow\nextra_overflow *= (1.0 - acting.overflow_convert)").body]
        if len(node.targets) == 1 and ast.unparse(node.targets[0]) == "defender.current_bp":
            amount = "actual_dmg" if "actual_dmg" in ast.unparse(node.value) else "max(1.0, extra)"
            if amount == "actual_dmg":
                return ast.parse("actual_dmg = damage(acting, defender, actual_dmg, 'direct', locals())\noverflow_damage(acting, defender, locals())").body
            # The two original extra-damage branches are distinguished by ancestry below.
            return ast.parse("damage(acting, defender, max(1.0, extra), _sub_channel)").body[0]
        if "raw_dmg" in names:
            return [node, *ast.parse("raw_dmg *= (1.0 + acting.normal_comp if skill.id == 9999 else 1.0)").body]
        return node

    def visit_If(self, node):
        text = ast.unparse(node.test)
        node = self.generic_visit(node)
        if text == "random.random() < dodge_rate":
            node.test = ast.parse("random.random() < dodge_rate * (1.0 - acting.hit_floor)").body[0].value
            node.body.insert(0, ast.parse("acting.add('misses', 1)").body[0])
        if text == "skill is None":
            return [node, ast.parse("observe_selection(acting, skill)").body[0]]
        if text in ('sub == \'自身已损反噬\'', 'sub == \'敌方已损斩杀\''):
            channel = "backlash" if "反噬" in text else "execute"
            node.body.insert(0, ast.parse(f"_sub_channel = '{channel}'").body[0])
        if text == "sub == '战力吸收'":
            node.body.insert(0, ast.parse("acting.heal_channel = 'lifesteal'").body[0])
        return node

tree = Instrument().visit(ast.parse(inspect.getsource(engine.execute_turn_action)))
ast.fix_missing_locations(tree)
ns = dict(engine.__dict__, damage=damage, overflow_damage=overflow_damage, observe_selection=observe_selection)
exec(compile(tree, str(SOURCE) + "[instrumented]", "exec"), ns)
action = ns["execute_turn_action"]

def assemble(stage, genre):
    trp = engine.assemble_hybrid_troop(genre)
    trp.__class__ = ResearchTroop
    n, bp, main, sub, other, cap = STAGES[stage]
    trp.scale, trp.max_bp, trp.name = n, float(bp), genre
    for field in ("courage", "resilience", "initiative", "magic"):
        old = getattr(trp, "base_" + field)
        setattr(trp, "base_" + field, float({1000:main, 500:sub, 100:other}[int(old)]))
    # S6 is an exact canonical preset. Earlier stages lack authoritative recipes.
    # Uniform tier projection is a declared experimental assumption, never a fix.
    if stage < 5:
        pierce = {1:.20, 2:.30, 3:.38, 4:.50, 5:.65, 6:.80}
        heal = {1:.04, 2:.06, 3:.09, 4:.12, 5:.15, 6:.18}
        for s in trp.skills:
            s.tier = min(s.tier, cap)
            s.main_param = 100. + (s.main_param - 100.) * s.tier / 6.
            if s.ignore_def_ratio: s.ignore_def_ratio = pierce[s.tier]
            if s.ini_bonus: s.ini_bonus = {1:0, 2:1, 3:2, 4:5, 5:7, 6:10}[s.tier]
            if s.main_type == "Heal": s.sub_param = heal[s.tier]
            elif s.sub_effect_name in ("虚弱压制", "四维削弱"):
                if s.tier < 3: s.sub_effect_name, s.sub_param = "", 0.
                else: s.sub_param = ({3:15.,4:22.,5:35.,6:42.} if s.sub_effect_name == "虚弱压制" else {3:12.,4:18.,5:22.,6:30.})[s.tier]
            elif s.sub_effect_name in ("自身已损反噬", "敌方已损斩杀"):
                if s.tier < 4: s.sub_effect_name, s.sub_param = "", 0.
                else: s.sub_param = ({4:.18,5:.25,6:.35} if s.sub_effect_name == "自身已损反噬" else {4:.15,5:.18,6:.20})[s.tier]
    trp.reset()
    return trp

def apply_macro(enemy, p):
    alpha, beta, gamma, delta, theta, mu = p
    enemy.max_bp *= alpha
    enemy.current_bp = enemy.max_bp
    # Decouple the native MaxBP-based attack from the health scaling intervention.
    enemy.attack_factor = beta / alpha
    enemy.absorption, enemy.regen = gamma, delta
    enemy.base_initiative = enemy.cur_initiative = max(0., enemy.base_initiative + theta)
    for s in enemy.skills:
        s.trigger_chance = min(100., s.trigger_chance * mu)
        if s.main_type != "Heal": s.main_param *= mu

def equip(player, config):
    """Single-contributor aggregate approximation with declared focus share."""
    f = config.get("focus", 1. / player.scale)
    player.focus = f
    player.attack_factor *= 1. + f * config.get("attack", 0.)
    player.ramp = f * config.get("ramp", 0.)
    player.hit_floor = min(1., f * config.get("hit_floor", 0.))
    player.normal_comp = f * config.get("normal_comp", 0.)
    player.crit_grant = f * config.get("crit", 0.)
    player.overflow_convert = config.get("overflow_true", 0.)
    player.overheal_convert = config.get("overheal_shield", 0.)
    player.shield_cap = f * config.get("shield_cap", .5)
    player.death_lock_ratio = f * config.get("death_lock", 0.)
    # Actor's stat grant is expressed as a fraction of the team's stat budget.
    total = sum(getattr(player, "base_" + s) for s in ("courage","resilience","initiative","magic"))
    for field in ("courage", "resilience", "initiative", "magic"):
        value = getattr(player, "base_" + field) + total * f * config.get(field, 0.)
        setattr(player, "base_" + field, value)
        setattr(player, "cur_" + field, value)
    for s in player.skills:
        s.ignore_def_ratio += f * config.get("pierce", 0.)
    if "allocation" in config:
        # A fixed-budget roster replacement; no actor identity is represented.
        share = config["share"]
        for j, field in enumerate(("courage","resilience","initiative","magic")):
            value = (1. - share) * getattr(player, "base_" + field) + share * total * config["allocation"][j]
            setattr(player, "base_" + field, value)
            setattr(player, "cur_" + field, value)

def state(t):
    eff = t.get_effective_stats()
    return dict(bp=max(0., t.current_bp) / t.max_bp, bp_raw=t.current_bp / t.max_bp,
                initiative=eff[2], output_factor=t.get_dmg_output_factor(),
                stat_factor=eff[0] / t.cur_courage if t.cur_courage else 1., shield=t.shield/t.max_bp)

def run(player, enemy, seed, p=None, config=None, telemetry=False, max_turns=40):
    random.seed(seed)
    player.reset(); enemy.reset()
    if p is not None: apply_macro(enemy, p)
    if config: equip(player, config)
    rows = []
    turn = 0
    for turn in range(1, max_turns + 1):
        for t in (player, enemy):
            t.turn = turn
            t.round_metrics.clear()
            t.heal_channel = "self_heal"
        initial = [state(t) for t in (player,enemy)] if telemetry else None
        # Preserve the canonical use of cur_resilience rather than effective R.
        for t in (player,enemy):
            if t.is_dead(): continue
            _, dr = engine.calc_resilience_dr(t.cur_resilience)
            dots = []
            for d in t.max_bp_dots:
                src = d.get("source", None)
                sf = src.get_dmg_output_factor() if src else 1.
                loss = max(1., t.max_bp * d["val"] * (1. - dr) * sf)
                damage(src or t, t, loss, "max_dot", clamp=False)
                d["turns"] -= 1
                if d["turns"] > 0: dots.append(d)
            t.max_bp_dots = dots
        terminal = player.is_dead() or enemy.is_dead()
        first = None
        if not terminal:
            i1, i2 = player.get_effective_stats()[2], enemy.get_effective_stats()[2]
            if i1 > i2: first, second = player, enemy
            elif i2 > i1: first, second = enemy, player
            else: first, second = (player,enemy) if random.random() < .5 else (enemy,player)
            action(first,second,True,turn)
            terminal = second.is_dead()
            if not terminal:
                action(second,first,False,turn)
                terminal = first.is_dead()
        if not terminal:
            for t in (player,enemy):
                if t.is_dead(): continue
                _, dr = engine.calc_resilience_dr(t.cur_resilience)
                dots = []
                for d in t.lost_bp_dots:
                    src = d.get("source", None)
                    sf = src.get_dmg_output_factor() if src else 1.
                    lost = max(0., t.max_bp - t.current_bp)
                    loss = max(1., lost * d["val"] * (1. - dr) * sf)
                    damage(src or t, t, loss, "lost_dot", clamp=False)
                    d["turns"] -= 1
                    if d["turns"] > 0: dots.append(d)
                t.lost_bp_dots = dots
                for attr in ("dmg_reduce_debuffs", "stat_reduce_debuffs"):
                    arr = []
                    for d in getattr(t,attr):
                        d["turns"] -= 1
                        if d["turns"] > 0: arr.append(d)
                    setattr(t,attr,arr)
            terminal = player.is_dead() or enemy.is_dead()
            # Experimental regen is after all native round-end settlement.
            for t in (player,enemy):
                if not t.is_dead() and t.regen:
                    t.heal_channel = "macro_heal"
                    t.heal(t.max_bp * t.regen)
        if telemetry:
            row = dict(turn=turn, first="player" if first is player else ("enemy" if first else "none"))
            for side, t, start in zip(("p","e"),(player,enemy),initial):
                end = state(t)
                for k,v in start.items(): row[f"{side}_{k}_start"] = v
                for k,v in end.items(): row[f"{side}_{k}_end"] = v
                for ch in (*CHANNELS,"actions","skill_actions","normal_actions","hits","misses","crit_hits"):
                    row[f"{side}_{ch}"] = t.round_metrics[ch] / t.max_bp if ch in CHANNELS else t.round_metrics[ch]
            rows.append(row)
        if terminal: break
    winner = player if (not player.is_dead() and enemy.is_dead()) else (enemy if (not enemy.is_dead() and player.is_dead()) else (player if player.bp_pct >= enemy.bp_pct else enemy))
    censored = not player.is_dead() and not enemy.is_dead()
    draw = player.is_dead() and enemy.is_dead()
    summary = dict(win=int(winner is player), decisive_win=int(not player.is_dead() and enemy.is_dead()),
                   censored=int(censored), draw=int(draw), turns=turn, hp=max(0.,player.current_bp)/player.max_bp,
                   enemy_hp=max(0.,enemy.current_bp)/enemy.max_bp,
                   damage_output=player.metrics["effective_damage"] / enemy.max_bp)
    if not telemetry: return summary, None, None
    # Full trajectories remain in JSONL; fixed-length representation feeds PCA.
    features = {}
    for side,t in (("p",player),("e",enemy)):
        bp = np.array([rows[0][f"{side}_bp_start"]] + [r[f"{side}_bp_end"] for r in rows])
        velocity = np.diff(bp)
        accel = np.diff(np.r_[0.,velocity])
        for j,row in enumerate(rows):
            row[f"{side}_dbp_dt"] = float(velocity[j])
            row[f"{side}_d2bp_dt2"] = float(accel[j])
        for signal, values in (("bp",bp),("velocity",velocity),("acceleration",accel)):
            vals = np.interp(np.linspace(0.,1.,12), np.linspace(0.,1.,len(values)),values)
            for j,v in enumerate(vals): features[f"{side}_{signal}_{j:02}"] = float(v)
        actions = max(1.,t.metrics["actions"])
        for ch in CHANNELS:
            features[f"{side}_{ch}_per_round"] = t.metrics[ch] / t.max_bp / turn
        for ch in ("skill_actions","normal_actions","hits","misses","crit_hits"):
            features[f"{side}_{ch}_rate"] = t.metrics[ch] / actions
        runs = t.no_skill_runs + ([t.no_skill_run] if t.no_skill_run else [])
        features[f"{side}_skill_gap_mean"] = float(np.mean(runs)) if runs else 0.
        features[f"{side}_skill_gap_max"] = max(runs, default=0)
        features[f"{side}_weak_area"] = float(np.mean([1-r[f"{side}_output_factor_start"] for r in rows]))
        features[f"{side}_stat_area"] = float(np.mean([1-r[f"{side}_stat_factor_start"] for r in rows]))
        features[f"{side}_skill_gap_var"] = float(np.var(runs)) if runs else 0.
        summary[f"{side}_gap_distribution"] = runs
    diff = [(r["p_initiative_start"]-r["e_initiative_start"])/sum(STAGES[player.scale//5-1][2:5]) for r in rows]
    features["initiative_diff_mean"] = float(np.mean(diff))
    features["initiative_diff_drift"] = float(diff[-1]-diff[0])
    features["first_share"] = float(np.mean([r["first"]=="player" for r in rows]))
    return summary, features, rows

def parity(cases=1200):
    """Compare outcomes and internal state on identical random streams."""
    for j in range(cases):
        g,h = GENRES[j%6],GENRES[(j//6)%6]
        seed = stable_seed("parity",j)
        a,b = engine.assemble_hybrid_troop(g),engine.assemble_hybrid_troop(h)
        random.seed(seed)
        original = engine.run_battle(a,b)
        c,d = assemble(5,g),assemble(5,h)
        observed,_,_ = run(c,d,seed,telemetry=j%20==0)
        assert observed["win"] == int(original["winner"] is a), (j,"winner")
        assert observed["turns"] == original["turns"], (j,"turns")
        for x,y in ((a,c),(b,d)):
            for attr in ("current_bp","cur_courage","cur_resilience","cur_initiative","cur_magic","total_damage","usage","dodge_count"):
                assert getattr(x,attr) == getattr(y,attr), (j,attr,getattr(x,attr),getattr(y,attr))
    return {"cases":cases,"exact_internal_state_parity":True,"source_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest()}

if __name__ == "__main__":
    import json
    print(json.dumps(parity(),indent=2))
