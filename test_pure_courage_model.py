# -*- coding: utf-8 -*-
"""
Testing Pure Courage Model (No Crit Pierce):
- REMOVED: Artificial crit penetration (暴击不带穿透，穿透纯属于魔力本职).
- ENHANCED: Courage skills have higher base damage multipliers (伤害倍率) and dedicated base crit rates (基础暴击率).
- Pure mechanics: Courage wins through overwhelming raw multipliers and guaranteed hits on crits.
"""
import random
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def calc_magic_amp_responsive(magic):
    if magic <= 0: return 1.0
    return 1.0 + (magic / (magic + 280.0)) * 1.5 + (magic / 1400.0) * 0.7

def calc_resilience_dr(resilience):
    pct_dr = min(0.68, 0.25 + (resilience / (resilience + 450.0)) * 0.45)
    flat_dr = resilience * 12.0
    return flat_dr, pct_dr

def calc_courage_stats(courage):
    crit_rate = (courage / (courage + 750.0)) * 0.45
    crit_bonus = 0.45 + (courage / (courage + 650.0)) * 0.75
    return crit_rate, crit_bonus

def calc_initiative_stats(initiative, enemy_initiative):
    dodge_rate = min(0.28, (initiative / (initiative + 700.0)) * 0.35)
    diff = max(0.0, initiative - enemy_initiative)
    preempt_bonus = (diff / (diff + 600.0)) * 0.25 if diff > 0 else 0.0
    return dodge_rate, preempt_bonus


class BattleSkill:
    def __init__(self, sid, name, tier, genre, main_type="Attack", main_param=100.0,
                 trigger_chance=30.0, times_limit=999,
                 turn_cond1=0, turn_cond2=0, self_bp_cond2=0, enemy_bp_cond2=0,
                 base_crit_rate=0.0, # 勇气技能专属基础暴击率
                 is_true_damage=False, ignore_def_ratio=0.0, exhaust_turns=0,
                 sub_effect=None, sub_param=0.0, sub_param2=0.0, sub_duration=0, sub_base=0.0):
        self.id = sid
        self.name = name
        self.tier = tier
        self.genre = genre
        self.main_type = main_type
        self.main_param = main_param
        self.trigger_chance = trigger_chance
        self.times_limit = times_limit
        self.turn_cond1 = turn_cond1
        self.turn_cond2 = turn_cond2
        self.self_bp_cond2 = self_bp_cond2
        self.enemy_bp_cond2 = enemy_bp_cond2
        
        self.base_crit_rate = base_crit_rate
        self.is_true_damage = is_true_damage
        self.ignore_def_ratio = ignore_def_ratio
        self.exhaust_turns = exhaust_turns
        self.sub_effect = sub_effect
        self.sub_param = sub_param
        self.sub_param2 = sub_param2
        self.sub_duration = sub_duration
        self.sub_base = sub_base

    def can_trigger(self, turn, self_bp_pct, enemy_bp_pct, used):
        if self.times_limit > 0 and self.times_limit < 999 and used >= self.times_limit: return False
        if turn <= self.turn_cond1: return False
        if self.turn_cond2 > 0 and turn >= self.turn_cond2: return False
        if self.self_bp_cond2 > 0 and self_bp_pct >= self.self_bp_cond2: return False
        if self.enemy_bp_cond2 > 0 and enemy_bp_pct >= self.enemy_bp_cond2: return False
        return True


class Troop:
    def __init__(self, tid, name, scale, c, r, i, m, max_bp=1000000):
        self.id = tid
        self.name = name
        self.scale = scale
        self.max_bp = float(max_bp)
        self.current_bp = float(max_bp)
        self.courage = float(c)
        self.resilience = float(r)
        self.initiative = float(i)
        self.magic = float(m)
        self.skills = []
        self.usage = {}
        self.max_bp_dots = []
        self.turn_end_dots = []
        self.buffs = []
        self.exhaust_turns = 0
        self.total_damage = 0.0
        self.dodge_count = 0

    def reset(self):
        self.current_bp = self.max_bp
        self.usage = {}
        self.max_bp_dots = []
        self.turn_end_dots = []
        self.buffs = []
        self.exhaust_turns = 0
        self.total_damage = 0.0
        self.dodge_count = 0

    @property
    def bp_pct(self): return (self.current_bp / self.max_bp) * 100.0
    def is_dead(self): return self.current_bp <= 0.0001

    def heal(self, amount):
        if amount <= 0: return 0.0
        old = self.current_bp
        self.current_bp = min(self.max_bp, self.current_bp + amount)
        return self.current_bp - old


def execute_turn_action(acting, defender, is_first, turn):
    base_power = acting.max_bp * 0.15 + acting.current_bp * 0.08
    m_amp = calc_magic_amp_responsive(acting.magic)
    c_crit_rate, c_crit_bonus = calc_courage_stats(acting.courage)
    dodge_rate, preempt_bonus = calc_initiative_stats(acting.initiative, defender.initiative)
    preempt_factor = (1.0 + preempt_bonus) if (is_first and preempt_bonus > 0) else 1.0

    skill = None
    for s in acting.skills:
        u = acting.usage.get(s.id, 0)
        if s.can_trigger(turn, acting.bp_pct, defender.bp_pct, u):
            if random.random() * 100.0 < s.trigger_chance:
                skill = s
                acting.usage[s.id] = u + 1
                break

    if skill is None:
        skill = BattleSkill(9999, "普通攻击", 1, "通用", "Attack", main_param=100.0)

    # 暴击判定: 角色自身四维勇气暴击率 + 勇气技能专属基础暴击率 (不偷带穿透，纯粹暴击！)
    skill_base_crit = getattr(skill, 'base_crit_rate', 0.0)
    effective_crit_rate = min(0.95, skill_base_crit + c_crit_rate)
    is_crit = (random.random() < effective_crit_rate)

    # 闪避判定: 暴击必定命中破闪避；未暴击受对方闪避判定
    if not is_crit:
        if random.random() < dodge_rate:
            defender.dodge_count += 1
            return

    # 主伤害倍率结算
    mult = skill.main_param / 100.0
    if is_crit:
        mult += c_crit_bonus # 纯粹高暴伤叠加！
    raw_dmg = base_power * mult * preempt_factor

    if acting.exhaust_turns > 0:
        raw_dmg = 1.0
        acting.exhaust_turns = 0

    if skill.main_type == "Heal":
        heal_val = 0.0
        eff = skill.sub_effect
        if eff == "self_max_heal":
            heal_val = acting.max_bp * (skill.sub_param * m_amp)
        acting.heal(heal_val)
        raw_dmg = base_power * 1.0

    # 防御减免: 暴击【绝不带有任何穿透】，纯粹以极高倍率正面重劈！
    # 破防与真伤【只属于魔力】！
    flat_dr, pct_dr = calc_resilience_dr(defender.resilience)
    is_pure_true = skill.is_true_damage or (skill.ignore_def_ratio * m_amp >= 0.85)

    if is_pure_true:
        actual_dmg = raw_dmg
    else:
        # 纯净直接伤害，正常经过防守方坚韧减伤
        actual_dmg = max(1.0, raw_dmg * (1.0 - pct_dr) - flat_dr)

    defender.current_bp = max(0.0, defender.current_bp - actual_dmg)
    acting.total_damage += actual_dmg

    # 附加效果
    eff = skill.sub_effect
    if eff == "self_lost_dmg":
        lost = max(0.0, acting.max_bp - acting.current_bp)
        extra_raw = lost * (skill.sub_param * m_amp)
        defender.current_bp = max(0.0, defender.current_bp - max(1.0, extra_raw))
        acting.total_damage += max(1.0, extra_raw)
    elif eff == "enemy_lost_dmg":
        lost = max(0.0, defender.max_bp - defender.current_bp)
        extra_raw = lost * (skill.sub_param * m_amp) * (1.0 - pct_dr)
        defender.current_bp = max(0.0, defender.current_bp - max(1.0, extra_raw))
        acting.total_damage += max(1.0, extra_raw)
    elif eff == "lifesteal":
        acting.heal(actual_dmg * (skill.sub_param * m_amp))
    elif eff == "dot_max":
        defender.max_bp_dots.append({'val': skill.sub_param * m_amp, 'turns': skill.sub_duration})
    elif eff == "dot_lost":
        defender.turn_end_dots.append({'mode': 'lost', 'val': skill.sub_param * m_amp, 'turns': skill.sub_duration})
    elif eff == "combo_dot":
        defender.max_bp_dots.append({'val': skill.sub_param * m_amp, 'turns': skill.sub_duration})
        defender.turn_end_dots.append({'mode': 'flat', 'val': skill.sub_base * m_amp, 'turns': skill.sub_duration})

    if skill.exhaust_turns > 0:
        defender.exhaust_turns = max(defender.exhaust_turns, skill.exhaust_turns)


def run_battle(t1, t2, max_turns=30):
    t1.reset()
    t2.reset()
    turn = 0
    while turn < max_turns:
        turn += 1
        for trp, oppo in [(t1, t2), (t2, t1)]:
            if trp.is_dead(): continue
            if trp.max_bp_dots:
                _, pct_dr = calc_resilience_dr(trp.resilience)
                new_dots = []
                for dot in trp.max_bp_dots:
                    raw_loss = trp.max_bp * dot['val']
                    actual_loss = max(1.0, raw_loss * (1.0 - pct_dr))
                    trp.current_bp -= actual_loss
                    dot['turns'] -= 1
                    if dot['turns'] > 0: new_dots.append(dot)
                trp.max_bp_dots = new_dots

        if t1.is_dead() or t2.is_dead(): break

        first, second = (t1, t2) if t1.initiative >= t2.initiative else (t2, t1)
        execute_turn_action(first, second, True, turn)
        if second.is_dead(): break
        execute_turn_action(second, first, False, turn)
        if first.is_dead(): break

        for trp, oppo in [(t1, t2), (t2, t1)]:
            if trp.is_dead(): continue
            if trp.turn_end_dots:
                _, pct_dr = calc_resilience_dr(trp.resilience)
                new_dots = []
                for dot in trp.turn_end_dots:
                    if dot['mode'] == 'lost':
                        cur_lost = max(0.0, trp.max_bp - trp.current_bp)
                        raw_loss = cur_lost * dot['val']
                    else:
                        raw_loss = dot['val']
                    actual_loss = max(1.0, raw_loss * (1.0 - pct_dr))
                    trp.current_bp -= actual_loss
                    dot['turns'] -= 1
                    if dot['turns'] > 0: new_dots.append(dot)
                trp.turn_end_dots = new_dots

        if t1.is_dead() or t2.is_dead(): break

    winner = t1 if (not t1.is_dead() and t2.is_dead()) else (t2 if (not t2.is_dead() and t1.is_dead()) else (t1 if t1.bp_pct >= t2.bp_pct else t2))
    return {'winner': winner, 'turns': turn}


def assemble_troop(genre_code, base_bp=1000000):
    configs = {
        "M_R": ("魔力+坚韧流", 100, 500, 100, 1000),
        "M_I": ("魔力+先机流", 100, 100, 500, 1000),
        "M_C": ("魔力+勇气流", 500, 100, 100, 1000),
        "C_I": ("勇气+先机流", 1000, 100, 500, 100),
        "C_R": ("勇气+坚韧流", 1000, 500, 100, 100),
        "R_I": ("坚韧+先机流", 100, 1000, 500, 100),
    }
    name, c, r, i, m = configs[genre_code]
    troop = Troop(1, name, 30, c, r, i, m, base_bp)

    if genre_code == "M_R":
        troop.skills.append(BattleSkill(1, "灭世剧毒", 6, "魔力", "Attack", 130.0, 50.0, turn_cond2=3, times_limit=1, sub_effect="combo_dot", sub_param=0.050, sub_base=base_bp*0.05, sub_duration=3))
        troop.skills.append(BattleSkill(2, "神恩涅槃", 6, "坚韧", "Heal", 100.0, 50.0, self_bp_cond2=40, times_limit=1, sub_effect="self_max_heal", sub_param=0.18))
        troop.skills.append(BattleSkill(3, "生命剥离", 5, "魔力", "Attack", 125.0, 35.0, sub_effect="dot_lost", sub_param=0.075, sub_duration=3))
        troop.skills.append(BattleSkill(4, "常态愈合", 5, "坚韧", "Heal", 100.0, 30.0, self_bp_cond2=65, sub_effect="self_max_heal", sub_param=0.12))

    elif genre_code == "M_I":
        troop.skills.append(BattleSkill(1, "弑神断界斩", 6, "魔力", "Attack", 220.0, 50.0, is_true_damage=True, times_limit=1))
        troop.skills.append(BattleSkill(2, "瞬狱虚弱杀", 6, "先机", "Attack", 170.0, 45.0, turn_cond2=3, times_limit=1, exhaust_turns=1, is_true_damage=True))
        troop.skills.append(BattleSkill(3, "纯粹裂魂击", 5, "魔力", "Attack", 185.0, 35.0, is_true_damage=True))
        troop.skills.append(BattleSkill(4, "常态影刃", 5, "魔力", "Attack", 150.0, 30.0, ignore_def_ratio=0.75))

    elif genre_code == "M_C":
        troop.skills.append(BattleSkill(1, "湮灭核弹斩", 6, "魔力", "Attack", 250.0, 50.0, is_true_damage=True, times_limit=1))
        troop.skills.append(BattleSkill(2, "终结暴击击", 6, "勇气", "Attack", 320.0, 45.0, enemy_bp_cond2=45, times_limit=1, base_crit_rate=0.20))
        troop.skills.append(BattleSkill(3, "纯粹裂魂击", 5, "魔力", "Attack", 190.0, 35.0, is_true_damage=True))

    elif genre_code == "C_I":
        # 勇气+先机: 拔除任何穿透！靠极高倍率(180%~380%) + 基础暴击率(20%~25%) + 先手虚弱！
        troop.skills.append(BattleSkill(1, "疾风封脉破", 6, "先机", "Attack", 170.0, 50.0, turn_cond2=3, times_limit=1, exhaust_turns=1))
        troop.skills.append(BattleSkill(2, "狂雷终结斩", 6, "勇气", "Attack", 380.0, 50.0, enemy_bp_cond2=45, times_limit=1, base_crit_rate=0.25))
        troop.skills.append(BattleSkill(3, "裂地狂劈",   5, "勇气", "Attack", 220.0, 40.0, base_crit_rate=0.20))
        troop.skills.append(BattleSkill(4, "常态影刃",   5, "先机", "Attack", 175.0, 30.0))

    elif genre_code == "C_R":
        # 勇气+坚韧: 纯粹高倍率(200%~360%) + 基础暴击率 + 自身残血反噬
        troop.skills.append(BattleSkill(1, "背水浴血斩", 6, "勇气", "Attack", 220.0, 50.0, self_bp_cond2=40, times_limit=1, base_crit_rate=0.25, sub_effect="self_lost_dmg", sub_param=0.45))
        troop.skills.append(BattleSkill(2, "不坏金身",   5, "坚韧", "Heal", 100.0, 45.0, self_bp_cond2=45, times_limit=1, sub_effect="self_max_heal", sub_param=0.16))
        troop.skills.append(BattleSkill(3, "崩山重劈",   5, "勇气", "Attack", 200.0, 35.0, base_crit_rate=0.15))

    elif genre_code == "R_I":
        troop.skills.append(BattleSkill(1, "神恩涅槃", 6, "坚韧", "Heal", 100.0, 50.0, self_bp_cond2=40, times_limit=1, sub_effect="self_max_heal", sub_param=0.18))
        troop.skills.append(BattleSkill(2, "瞬影封印", 5, "先机", "Attack", 150.0, 40.0, exhaust_turns=1))
        troop.skills.append(BattleSkill(3, "常态吸血", 5, "坚韧", "Attack", 130.0, 30.0, sub_effect="lifesteal", sub_param=0.35))

    return troop


def run_clean_matrix_test(sims=2000):
    genres = ["M_R", "M_I", "M_C", "C_I", "C_R", "R_I"]
    genre_names = {
        "M_R": "魔力+坚韧流",
        "M_I": "魔力+先机流",
        "M_C": "魔力+勇气流",
        "C_I": "勇气+先机流",
        "C_R": "勇气+坚韧流",
        "R_I": "坚韧+先机流"
    }

    wins = {g1: {g2: 0 for g2 in genres} for g1 in genres}
    all_turns = []

    for i in range(len(genres)):
        for j in range(i, len(genres)):
            g1, g2 = genres[i], genres[j]
            if g1 == g2:
                wins[g1][g2] = sims // 2
                continue
            for _ in range(sims):
                t1 = assemble_troop(g1)
                t2 = assemble_troop(g2)
                res = run_battle(t1, t2)
                all_turns.append(res['turns'])
                if res['winner'].name == t1.name:
                    wins[g1][g2] += 1
                else:
                    wins[g2][g1] += 1

    print("=" * 95)
    print("【纯净四维模型：暴击绝不带穿透，纯靠基础暴击率与倍率 (30,000 局对抗矩阵)】")
    print("=" * 95)
    header = f"{'流派 (行攻 / 列防)':<22}"
    for g in genres: header += f"{genre_names[g]:<11}"
    header += f"{'综合胜率':<8}"
    print(header)
    print("-" * 92)

    for g1 in genres:
        row = f"{genre_names[g1]:<22}"
        tot_w = 0; tot_m = 0
        for g2 in genres:
            w = wins[g1][g2]
            pct = (w / sims) * 100.0
            row += f"{pct:>6.1f}%    "
            tot_w += w
            tot_m += sims
        ovr = (tot_w / tot_m) * 100.0
        row += f"{ovr:>6.1f}%"
        print(row)
    print("-" * 92)

    avg_turn = sum(all_turns) / len(all_turns)
    print(f"\n全局平均交锋回合数: {avg_turn:.2f} 回合")

if __name__ == '__main__':
    run_clean_matrix_test(2000)
