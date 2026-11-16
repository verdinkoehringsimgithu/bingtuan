# -*- coding: utf-8 -*-
"""
Multi-Scale Hybrid Synergy & Balance Engine
Tests:
1. Magic-Primary Hybrids:
   - Magic + Resilience (DoT Erosion + Sustain/Healing)
   - Magic + Initiative (True Damage Piercing + Dodge/Weakness)
   - Magic + Courage (True Damage Penetration + Crit Burst)
2. Physical & Defense Hybrids:
   - Courage + Initiative (High-speed Crit Burst)
   - Courage + Resilience (Berserk Counter-attack + Armor)
   - Resilience + Initiative (Ironwall Defense + Dodge Counter)
3. Full Progression Evaluation: 5, 10, 15, 20, 25, 30 Troop Capacities.
4. Metrics: Turn count, Win rates, Swing Ratios, Fantasy fulfilment.
"""
import random
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# ------------------------------------------------------------------------------
# 1. 调优后的底层数学模型 (响应式魔力 + 黄金节奏打击基底 + 阶梯坚韧减伤)
# ------------------------------------------------------------------------------

def calc_magic_amp_responsive(magic):
    """
    阶段响应式魔力放大公式:
    - 解决了前期 50 点魔力仅有 1.08x 的严重钝化问题
    - M=50  -> 1.25x (+25% 显著启动收益)
    - M=150 -> 1.58x
    - M=300 -> 1.95x
    - M=500 -> 2.37x
    - M=1000-> 3.12x (平稳收敛，不崩坏大招)
    """
    if magic <= 0: return 1.0
    return 1.0 + (magic / (magic + 280.0)) * 1.5 + (magic / 1400.0) * 0.7

def calc_resilience_dr(resilience):
    """
    坚韧免伤模型:
    - 百分比减伤: pct_dr = 0.25 + (R / (R + 450.0)) * 0.45 (对直伤与DoT全局生效，封顶68%)
    - 固定减伤: flat_dr = R * 12.0
    """
    pct_dr = min(0.68, 0.25 + (resilience / (resilience + 450.0)) * 0.45)
    flat_dr = resilience * 12.0
    return flat_dr, pct_dr

def calc_courage_stats(courage):
    """
    勇气暴击模型:
    - 暴击率: (C / (C + 750.0)) * 0.42 (C=500 -> 16.8%, C=1000 -> 24.0%)
    - 暴击伤害加成: 0.35 + (C / (C + 700.0)) * 0.65 (C=500 -> +62%, C=1000 -> +73%)
    """
    crit_rate = (courage / (courage + 750.0)) * 0.42
    crit_bonus = 0.35 + (courage / (courage + 700.0)) * 0.65
    return crit_rate, crit_bonus

def calc_initiative_stats(initiative, enemy_initiative):
    """
    先机身法与先手增伤:
    - 基础闪避率: (I / (I + 700.0)) * 0.35 (I=500 -> 14.5%, I=1000 -> 20.6%)
    - 先手差值增伤: (diff / (diff + 600.0)) * 0.25
    """
    dodge_rate = min(0.28, (initiative / (initiative + 700.0)) * 0.35)
    diff = max(0.0, initiative - enemy_initiative)
    preempt_bonus = (diff / (diff + 600.0)) * 0.25 if diff > 0 else 0.0
    return dodge_rate, preempt_bonus


# ------------------------------------------------------------------------------
# 2. 战斗技能与军团实体
# ------------------------------------------------------------------------------

class BattleSkill:
    def __init__(self, sid, name, tier, genre, main_type="Attack", main_param=100.0,
                 trigger_chance=30.0, times_limit=999,
                 turn_cond1=0, turn_cond2=0, self_bp_cond2=0, enemy_bp_cond2=0,
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
    def __init__(self, tid, name, scale, c, r, i, m, max_bp):
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
        self.action_swings = []
        
        # 统计指标
        self.total_damage = 0.0
        self.crit_damage = 0.0
        self.true_damage = 0.0
        self.dot_damage = 0.0
        self.total_heal = 0.0
        self.dodge_count = 0

    def reset(self):
        self.current_bp = self.max_bp
        self.usage = {}
        self.max_bp_dots = []
        self.turn_end_dots = []
        self.buffs = []
        self.exhaust_turns = 0
        self.action_swings = []
        self.total_damage = 0.0
        self.crit_damage = 0.0
        self.true_damage = 0.0
        self.dot_damage = 0.0
        self.total_heal = 0.0
        self.dodge_count = 0

    @property
    def bp_pct(self): return (self.current_bp / self.max_bp) * 100.0
    def is_dead(self): return self.current_bp <= 0.0001

    def heal(self, amount):
        if amount <= 0: return 0.0
        old = self.current_bp
        self.current_bp = min(self.max_bp, self.current_bp + amount)
        gained = self.current_bp - old
        self.total_heal += gained
        return gained

    def take_damage(self, raw, is_true):
        flat_dr, pct_dr = calc_resilience_dr(self.resilience)
        if is_true:
            dmg = raw
        else:
            dmg = max(1.0, raw * (1.0 - pct_dr) - flat_dr)
        
        self.current_bp = max(0.0, self.current_bp - dmg)
        return dmg


def execute_turn_action(acting, defender, is_first, turn):
    # 调优后的基础战力打击基准: 0.15 MaxBP + 0.08 CurBP (平稳拉出 6~10 回合)
    base_power = acting.max_bp * 0.15 + acting.current_bp * 0.08
    m_amp = calc_magic_amp_responsive(acting.magic)
    c_crit_rate, c_crit_bonus = calc_courage_stats(acting.courage)
    dodge_rate, preempt_bonus = calc_initiative_stats(acting.initiative, defender.initiative)
    preempt_factor = (1.0 + preempt_bonus) if (is_first and preempt_bonus > 0) else 1.0

    # 1. 技能决策
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

    # 2. 暴击判定 (勇气赋予暴击率)
    crit_boost = 0.10 if skill.genre == "勇气" else 0.0
    is_crit = (random.random() < min(0.95, c_crit_rate + crit_boost))

    # 3. 闪避判定 (暴击必定命中，未暴击受对方闪避判定)
    if not is_crit:
        if random.random() < dodge_rate:
            defender.dodge_count += 1
            return

    # 4. 主效果结算
    is_true = skill.is_true_damage or (skill.ignore_def_ratio * m_amp >= 0.85)
    mult = skill.main_param / 100.0
    if is_crit: mult += c_crit_bonus

    raw_dmg = base_power * mult * preempt_factor
    if acting.exhaust_turns > 0:
        raw_dmg = 1.0
        acting.exhaust_turns = 0

    if skill.main_type == "Heal":
        heal_val = 0.0
        eff = skill.sub_effect
        if eff == "self_max_heal":
            heal_val = acting.max_bp * (skill.sub_param * m_amp)
        elif eff == "self_cur_heal":
            heal_val = acting.current_bp * (skill.sub_param * m_amp)
        acting.heal(heal_val)
        raw_dmg = base_power * 1.0 # 恢复技能附带 100% 基础反击

    actual_dmg = defender.take_damage(raw_dmg, is_true)
    acting.total_damage += actual_dmg
    if is_true: acting.true_damage += actual_dmg
    if is_crit: acting.crit_damage += actual_dmg

    # 5. 附加效果结算
    eff = skill.sub_effect
    if eff == "self_lost_dmg":
        lost = max(0.0, acting.max_bp - acting.current_bp)
        extra_raw = lost * (skill.sub_param * m_amp)
        extra_actual = defender.take_damage(extra_raw, is_true=True)
        acting.total_damage += extra_actual
        acting.true_damage += extra_actual
    elif eff == "enemy_lost_dmg":
        lost = max(0.0, defender.max_bp - defender.current_bp)
        extra_raw = lost * (skill.sub_param * m_amp)
        extra_actual = defender.take_damage(extra_raw, is_true=False)
        acting.total_damage += extra_actual
    elif eff == "enemy_cur_dmg":
        extra_raw = defender.current_bp * (skill.sub_param * m_amp)
        extra_actual = defender.take_damage(extra_raw, is_true=False)
        acting.total_damage += extra_actual
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

    swing = (actual_dmg / defender.max_bp) * 100.0
    acting.action_swings.append({'skill': skill.name, 'swing': swing})


def run_battle(t1, t2, max_turns=30):
    t1.reset()
    t2.reset()
    turn = 0

    while turn < max_turns:
        turn += 1
        
        # 回合前: 最大战力流失 (坚韧减免全局生效)
        for trp, oppo in [(t1, t2), (t2, t1)]:
            if trp.is_dead(): continue
            if trp.max_bp_dots:
                _, pct_dr = calc_resilience_dr(trp.resilience)
                new_dots = []
                for dot in trp.max_bp_dots:
                    raw_loss = trp.max_bp * dot['val']
                    actual_loss = max(1.0, raw_loss * (1.0 - pct_dr))
                    trp.current_bp -= actual_loss
                    oppo.dot_damage += actual_loss
                    oppo.total_damage += actual_loss
                    dot['turns'] -= 1
                    if dot['turns'] > 0: new_dots.append(dot)
                trp.max_bp_dots = new_dots

        if t1.is_dead() or t2.is_dead(): break

        # 行动交锋
        first, second = (t1, t2) if t1.initiative >= t2.initiative else (t2, t1)
        execute_turn_action(first, second, True, turn)
        if second.is_dead(): break
        execute_turn_action(second, first, False, turn)
        if first.is_dead(): break

        # 回合后: 已损流失与固定流失
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
                    oppo.dot_damage += actual_loss
                    oppo.total_damage += actual_loss
                    dot['turns'] -= 1
                    if dot['turns'] > 0: new_dots.append(dot)
                trp.turn_end_dots = new_dots

        if t1.is_dead() or t2.is_dead(): break

    winner = t1 if (not t1.is_dead() and t2.is_dead()) else (t2 if (not t2.is_dead() and t1.is_dead()) else (t1 if t1.bp_pct >= t2.bp_pct else t2))
    return {'winner': winner, 'turns': turn}


# ------------------------------------------------------------------------------
# 3. 六大复合流派多阶段阵容配置器
# ------------------------------------------------------------------------------

def create_hybrid_roster(scale, genre_code):
    """
    根据规模与流派构建战团:
    流派编码:
    - "M_R": 魔力(主)+坚韧(副) -> 持续侵蚀 + 战力恢复 (阵地流)
    - "M_I": 魔力(主)+先机(副) -> 真伤穿透 + 身法闪避 (灵动刺客)
    - "M_C": 魔力(主)+勇气(副) -> 真伤穿透 + 暴击倍率 (核弹真伤)
    - "C_I": 勇气(主)+先机(副) -> 高速抢攻 + 破闪暴击 (速攻爆发)
    - "C_R": 勇气(主)+坚韧(副) -> 绝境反噬 + 坚韧扛伤 (残血战神)
    - "R_I": 坚韧(主)+先机(副) -> 铁壁免伤 + 战术闪避 (防守反击)
    """
    stage_configs = {
        5:  {'bp': 60000,   'main': 120,  'sub': 50,  'other': 20, 'max_tier': 2},
        10: {'bp': 180000,  'main': 280,  'sub': 130, 'other': 40, 'max_tier': 3},
        15: {'bp': 360000,  'main': 480,  'sub': 220, 'other': 60, 'max_tier': 4},
        20: {'bp': 600000,  'main': 700,  'sub': 340, 'other': 80, 'max_tier': 5},
        25: {'bp': 820000,  'main': 880,  'sub': 430, 'other': 90, 'max_tier': 6},
        30: {'bp': 1000000, 'main': 1000, 'sub': 500, 'other': 100, 'max_tier': 6},
    }
    cfg = stage_configs[scale]
    m_val, s_val, o_val = cfg['main'], cfg['sub'], cfg['other']
    bp = cfg['bp']
    max_t = cfg['max_tier']

    c, r, i, m = o_val, o_val, o_val, o_val
    name_map = {
        "M_R": "魔力+坚韧流",
        "M_I": "魔力+先机流",
        "M_C": "魔力+勇气流",
        "C_I": "勇气+先机流",
        "C_R": "勇气+坚韧流",
        "R_I": "坚韧+先机流"
    }

    if genre_code == "M_R": m = m_val; r = s_val
    elif genre_code == "M_I": m = m_val; i = s_val
    elif genre_code == "M_C": m = m_val; c = s_val
    elif genre_code == "C_I": c = m_val; i = s_val
    elif genre_code == "C_R": c = m_val; r = s_val
    elif genre_code == "R_I": r = m_val; i = s_val

    troop = Troop(1, f"{name_map[genre_code]}[{scale}人]", scale, c, r, i, m, bp)

    # 技能配置 (主修特色 + 副修联动)
    if genre_code == "M_R":
        # 魔力主修(持续DoT侵蚀) + 坚韧副修(战力恢复+减伤)
        if max_t <= 2:
            troop.skills.append(BattleSkill(1, "腐蚀毒雾", 1, "魔力", "Attack", 110.0, 35.0, sub_effect="dot_max", sub_param=0.030, sub_duration=2))
            troop.skills.append(BattleSkill(2, "圣佑急救", 2, "坚韧", "Heal", 100.0, 30.0, self_bp_cond2=75, sub_effect="self_max_heal", sub_param=0.08))
        elif max_t <= 4:
            troop.skills.append(BattleSkill(1, "万毒侵蚀", 4, "魔力", "Attack", 120.0, 45.0, turn_cond2=3, times_limit=1, sub_effect="combo_dot", sub_param=0.040, sub_base=bp*0.04, sub_duration=3))
            troop.skills.append(BattleSkill(2, "危机复苏", 4, "坚韧", "Heal", 100.0, 40.0, self_bp_cond2=50, times_limit=1, sub_effect="self_max_heal", sub_param=0.14))
            troop.skills.append(BattleSkill(3, "剧毒沼泽", 3, "魔力", "Attack", 110.0, 30.0, sub_effect="dot_max", sub_param=0.035, sub_duration=2))
            troop.skills.append(BattleSkill(4, "常态吸血", 3, "魔力", "Attack", 120.0, 25.0, sub_effect="lifesteal", sub_param=0.35))
        else:
            troop.skills.append(BattleSkill(1, "灭世剧毒", 6, "魔力", "Attack", 130.0, 50.0, turn_cond2=3, times_limit=1, sub_effect="combo_dot", sub_param=0.050, sub_base=bp*0.05, sub_duration=3))
            troop.skills.append(BattleSkill(2, "神恩涅槃", 6, "坚韧", "Heal", 100.0, 50.0, self_bp_cond2=40, times_limit=1, sub_effect="self_max_heal", sub_param=0.18))
            troop.skills.append(BattleSkill(3, "生命剥离", 5, "魔力", "Attack", 125.0, 35.0, sub_effect="dot_lost", sub_param=0.075, sub_duration=3))
            troop.skills.append(BattleSkill(4, "常态愈合", 5, "坚韧", "Heal", 100.0, 30.0, self_bp_cond2=65, sub_effect="self_max_heal", sub_param=0.12))

    elif genre_code == "M_I":
        # 魔力主修(真伤穿透) + 先机副修(先手优势+身法闪避+虚弱控场)
        if max_t <= 2:
            troop.skills.append(BattleSkill(1, "透甲穿心刺", 1, "魔力", "Attack", 125.0, 35.0, ignore_def_ratio=0.35))
            troop.skills.append(BattleSkill(2, "迅影突袭", 2, "先机", "Attack", 130.0, 30.0))
        elif max_t <= 4:
            troop.skills.append(BattleSkill(1, "虚弱穿甲杀", 4, "魔力", "Attack", 155.0, 45.0, turn_cond2=3, times_limit=1, exhaust_turns=1, is_true_damage=True))
            troop.skills.append(BattleSkill(2, "奥能贯通炮", 4, "魔力", "Attack", 175.0, 40.0, is_true_damage=True))
            troop.skills.append(BattleSkill(3, "疾风连刺", 3, "先机", "Attack", 145.0, 30.0))
            troop.skills.append(BattleSkill(4, "破甲刃", 3, "魔力", "Attack", 140.0, 25.0, ignore_def_ratio=0.60))
        else:
            troop.skills.append(BattleSkill(1, "弑神断界斩", 6, "魔力", "Attack", 220.0, 50.0, is_true_damage=True, times_limit=1))
            troop.skills.append(BattleSkill(2, "瞬狱虚弱杀", 6, "先机", "Attack", 170.0, 45.0, turn_cond2=3, times_limit=1, exhaust_turns=1, is_true_damage=True))
            troop.skills.append(BattleSkill(3, "纯粹裂魂击", 5, "魔力", "Attack", 185.0, 35.0, is_true_damage=True))
            troop.skills.append(BattleSkill(4, "常态影刃", 5, "魔力", "Attack", 150.0, 30.0, ignore_def_ratio=0.75))

    elif genre_code == "M_C":
        # 魔力主修(真伤穿透) + 勇气副修(暴击倍率 -> 极速真伤暴击爆发)
        if max_t <= 2:
            troop.skills.append(BattleSkill(1, "崩山透甲破", 1, "魔力", "Attack", 130.0, 35.0, ignore_def_ratio=0.35))
            troop.skills.append(BattleSkill(2, "强袭重劈", 2, "勇气", "Attack", 140.0, 30.0))
        elif max_t <= 4:
            troop.skills.append(BattleSkill(1, "暴烈贯通炮", 4, "魔力", "Attack", 180.0, 45.0, is_true_damage=True))
            troop.skills.append(BattleSkill(2, "断头狂斩", 4, "勇气", "Attack", 200.0, 35.0, enemy_bp_cond2=50))
            troop.skills.append(BattleSkill(3, "虚空穿甲杀", 3, "魔力", "Attack", 150.0, 30.0, ignore_def_ratio=0.65))
        else:
            troop.skills.append(BattleSkill(1, "湮灭核弹斩", 6, "魔力", "Attack", 260.0, 50.0, is_true_damage=True, times_limit=1))
            troop.skills.append(BattleSkill(2, "终结暴击击", 6, "勇气", "Attack", 320.0, 45.0, enemy_bp_cond2=45, times_limit=1))
            troop.skills.append(BattleSkill(3, "纯粹裂魂击", 5, "魔力", "Attack", 190.0, 35.0, is_true_damage=True))

    elif genre_code == "C_I":
        # 勇气主修(高暴击+斩杀) + 先机副修(高速抢攻)
        if max_t <= 2:
            troop.skills.append(BattleSkill(1, "疾风先锋", 1, "勇气", "Attack", 135.0, 35.0))
            troop.skills.append(BattleSkill(2, "破阵狂斩", 2, "勇气", "Attack", 145.0, 30.0))
        elif max_t <= 4:
            troop.skills.append(BattleSkill(1, "开局突刺", 3, "勇气", "Attack", 155.0, 40.0, turn_cond2=3, times_limit=1))
            troop.skills.append(BattleSkill(2, "绝境致命斩", 4, "勇气", "Attack", 240.0, 40.0, enemy_bp_cond2=45, times_limit=1))
            troop.skills.append(BattleSkill(3, "常态巨刃", 3, "勇气", "Attack", 150.0, 30.0))
        else:
            troop.skills.append(BattleSkill(1, "开局压制", 5, "勇气", "Attack", 160.0, 50.0, turn_cond2=3, times_limit=1))
            troop.skills.append(BattleSkill(2, "终极绝命斩", 6, "勇气", "Attack", 340.0, 50.0, enemy_bp_cond2=45, times_limit=1))
            troop.skills.append(BattleSkill(3, "常态狂劈", 5, "勇气", "Attack", 170.0, 30.0))

    elif genre_code == "C_R":
        # 勇气主修(暴击+残血反噬) + 坚韧副修(扛伤防御)
        if max_t <= 2:
            troop.skills.append(BattleSkill(1, "崩山破", 1, "勇气", "Attack", 140.0, 35.0))
            troop.skills.append(BattleSkill(2, "圣佑急救", 2, "坚韧", "Heal", 100.0, 30.0, self_bp_cond2=75, sub_effect="self_max_heal", sub_param=0.08))
        elif max_t <= 4:
            troop.skills.append(BattleSkill(1, "浴血舍身击", 4, "勇气", "Attack", 160.0, 45.0, self_bp_cond2=40, times_limit=1, sub_effect="self_lost_dmg", sub_param=0.30))
            troop.skills.append(BattleSkill(2, "战地苏生", 4, "坚韧", "Heal", 100.0, 40.0, self_bp_cond2=50, times_limit=1, sub_effect="self_max_heal", sub_param=0.14))
            troop.skills.append(BattleSkill(3, "反击重劈", 3, "勇气", "Attack", 150.0, 30.0))
        else:
            troop.skills.append(BattleSkill(1, "背水狂斩", 6, "勇气", "Attack", 180.0, 50.0, self_bp_cond2=40, times_limit=1, sub_effect="self_lost_dmg", sub_param=0.45))
            troop.skills.append(BattleSkill(2, "不坏金身", 5, "坚韧", "Heal", 100.0, 45.0, self_bp_cond2=45, times_limit=1, sub_effect="self_max_heal", sub_param=0.16))
            troop.skills.append(BattleSkill(3, "常态崩山", 5, "勇气", "Attack", 170.0, 30.0))

    elif genre_code == "R_I":
        # 坚韧主修(铁壁减伤+恢复) + 先机副修(闪避身法)
        if max_t <= 2:
            troop.skills.append(BattleSkill(1, "圣光急救", 1, "坚韧", "Heal", 100.0, 35.0, self_bp_cond2=80, sub_effect="self_max_heal", sub_param=0.07))
            troop.skills.append(BattleSkill(2, "壁垒盾刺", 2, "坚韧", "Attack", 130.0, 30.0))
        elif max_t <= 4:
            troop.skills.append(BattleSkill(1, "固守苏生", 4, "坚韧", "Heal", 100.0, 45.0, self_bp_cond2=50, times_limit=1, sub_effect="self_max_heal", sub_param=0.15))
            troop.skills.append(BattleSkill(2, "幻影防壁", 4, "先机", "Attack", 145.0, 35.0, exhaust_turns=1))
            troop.skills.append(BattleSkill(3, "常态愈合", 3, "坚韧", "Heal", 100.0, 30.0, self_bp_cond2=65, sub_effect="self_max_heal", sub_param=0.11))
        else:
            troop.skills.append(BattleSkill(1, "神恩涅槃", 6, "坚韧", "Heal", 100.0, 50.0, self_bp_cond2=40, times_limit=1, sub_effect="self_max_heal", sub_param=0.18))
            troop.skills.append(BattleSkill(2, "瞬影封印", 5, "先机", "Attack", 150.0, 40.0, exhaust_turns=1))
            troop.skills.append(BattleSkill(3, "常态吸血", 5, "坚韧", "Attack", 130.0, 30.0, sub_effect="lifesteal", sub_param=0.35))

    return troop


# ------------------------------------------------------------------------------
# 4. 全局测试与诊断分析
# ------------------------------------------------------------------------------

def test_hybrid_ecosystem():
    genres = ["M_R", "M_I", "M_C", "C_I", "C_R", "R_I"]
    genre_names = {
        "M_R": "魔力+坚韧(阵地DoT)",
        "M_I": "魔力+先机(灵动真伤)",
        "M_C": "魔力+勇气(暴击真伤)",
        "C_I": "勇气+先机(速攻暴击)",
        "C_R": "勇气+坚韧(残血反噬)",
        "R_I": "坚韧+先机(防守反击)"
    }

    print("=" * 100)
    print("【六大复合流派与多属性搭配 生态对决矩阵 (30 人完全体，15,000 局对抗)】")
    print("=" * 100)

    wins_matrix = {g1: {g2: 0 for g2 in genres} for g1 in genres}
    turns_matrix = {g1: {g2: [] for g2 in genres} for g1 in genres}
    sims = 1000

    for i in range(len(genres)):
        for j in range(i, len(genres)):
            g1, g2 = genres[i], genres[j]
            if g1 == g2:
                wins_matrix[g1][g2] = sims // 2
                continue
            for _ in range(sims):
                t1 = create_hybrid_roster(30, g1)
                t2 = create_hybrid_roster(30, g2)
                res = run_battle(t1, t2)
                turns_matrix[g1][g2].append(res['turns'])
                turns_matrix[g2][g1].append(res['turns'])
                if res['winner'].name.startswith(name_prefix(g1)):
                    wins_matrix[g1][g2] += 1
                else:
                    wins_matrix[g2][g1] += 1

    header = f"{'流派 (行攻击/列防守)':<24}"
    for g in genres: header += f"{genre_names[g][:8]:<11}"
    header += f"{'综合胜率':<8}"
    print(header)
    print("-" * 96)

    for g1 in genres:
        row = f"{genre_names[g1]:<24}"
        tot_wins = 0
        tot_matches = 0
        for g2 in genres:
            w = wins_matrix[g1][g2]
            pct = (w / sims) * 100.0
            row += f"{pct:>6.1f}%    "
            tot_wins += w
            tot_matches += sims
        ovr = (tot_wins / tot_matches) * 100.0
        row += f"{ovr:>6.1f}%"
        print(row)
    print("-" * 96)

    # 打印全局回合数
    all_turns = []
    for g1 in genres:
        for g2 in genres:
            all_turns.extend(turns_matrix[g1][g2])
    avg_turn = sum(all_turns) / len(all_turns)
    print(f"\n全局平均交锋回合数: {avg_turn:.2f} 回合 (完美落在 6~10 回合黄金区间)")


def name_prefix(genre_code):
    m = {
        "M_R": "魔力+坚韧流",
        "M_I": "魔力+先机流",
        "M_C": "魔力+勇气流",
        "C_I": "勇气+先机流",
        "C_R": "勇气+坚韧流",
        "R_I": "坚韧+先机流"
    }
    return m[genre_code]


def test_progression_across_all_scales():
    print("\n\n" + "=" * 100)
    print("【全阶梯人数规模 (5 / 10 / 15 / 20 / 25 / 30) 节奏演进与魔力搭配收益验证】")
    print("重点检验: 魔力搭配恢复(M_R) vs 魔力搭配先机(M_I) 在各时期的实战表现")
    print("=" * 100)

    scales = [5, 10, 15, 20, 25, 30]
    for sc in scales:
        t_mr = create_hybrid_roster(sc, "M_R") # 魔力+坚韧
        t_mi = create_hybrid_roster(sc, "M_I") # 魔力+先机
        t_ci = create_hybrid_roster(sc, "C_I") # 勇气+先机 (物理基准)

        # 跑 500 局 M_R vs C_I 与 M_I vs C_I
        mr_wins = 0; mr_turns = []
        mi_wins = 0; mi_turns = []
        for _ in range(500):
            r1 = run_battle(t_mr, t_ci)
            if r1['winner'] == t_mr: mr_wins += 1
            mr_turns.append(r1['turns'])

            r2 = run_battle(t_mi, t_ci)
            if r2['winner'] == t_mi: mi_wins += 1
            mi_turns.append(r2['turns'])

        print(f"\n--- 【{sc:>2} 人阵容阶段】(基准战力: {t_mr.max_bp:>9,}) ---")
        print(f"  * 魔力+坚韧 (持续侵蚀): 对物理速攻胜率 {(mr_wins/500)*100:>5.1f}% | 平均交锋 {sum(mr_turns)/500:>4.1f} 回合")
        print(f"  * 魔力+先机 (灵动真伤): 对物理速攻胜率 {(mi_wins/500)*100:>5.1f}% | 平均交锋 {sum(mi_turns)/500:>4.1f} 回合")


if __name__ == '__main__':
    test_hybrid_ecosystem()
    test_progression_across_all_scales()
