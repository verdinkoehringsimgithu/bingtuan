# -*- coding: utf-8 -*-
"""
Progression Stages & Experience Balance Simulator (V2.0)
Key Highlights:
1. Multi-scale roster progression: 5, 10, 15, 20, 25, 30 limits (T1-T6 introduction).
2. Perceived skill impact (Swing Ratio: single-skill impact vs max HP).
3. Magic split into TWO distinct gameplay avenues:
   - 纯真伤穿透流 (True Damage / High Defense Bypass Burst)
   - 持续流失侵蚀流 (DoT Erosion: Max BP pre-turn, Lost BP post-turn, Flat DoT)
4. "Punching Above Weight" (越级挑战): Underdog player vs High-Defense / High-HP Bosses.
5. Magic amplification curve (early game responsiveness vs late game scaling).
6. Archetype Fantasy Fulfillment (do builds win by their thematic mechanics?).
"""
import random
import math
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# ==============================================================================
# 1. 核心公式与转化逻辑
# ==============================================================================

def calc_magic_amp_linear(magic):
    """当前线性魔力放大公式: 1 + M / 600"""
    return 1.0 + max(0.0, magic) / 600.0

def calc_magic_amp_responsive(magic):
    """
    改进的非线性响应式魔力放大公式 (供对比测试):
    早期提供快速可感知的基底增益，中后期平滑收敛，避免前期白板/后期爆炸
    M=50 -> 1.27x; M=150 -> 1.66x; M=300 -> 2.08x; M=600 -> 2.64x; M=1000 -> 3.16x
    """
    if magic <= 0: return 1.0
    return 1.0 + (magic / (magic + 350.0)) * 1.6 + (magic / 1200.0)

def calc_courage_stats(courage):
    crit_rate = (courage / (courage + 700.0)) * 0.45
    crit_bonus = 0.35 + (courage / (courage + 650.0)) * 0.65
    return crit_rate, crit_bonus

def calc_resilience_dr(resilience):
    flat_dr = resilience * 16.0
    pct_dr = min(0.65, 0.20 + (resilience / (resilience + 500.0)) * 0.45)
    return flat_dr, pct_dr

def calc_initiative_stats(initiative, enemy_initiative):
    dodge_rate = min(0.28, (initiative / (initiative + 700.0)) * 0.32)
    diff = max(0.0, initiative - enemy_initiative)
    preempt_bonus = (diff / (diff + 600.0)) * 0.28 if diff > 0 else 0.0
    return dodge_rate, preempt_bonus


# ==============================================================================
# 2. 实体模型与技能
# ==============================================================================

class BattleSkill:
    def __init__(self, skill_id, name, tier, genre, main_type="Attack", main_param=100.0,
                 trigger_chance=25.0, times_limit=999,
                 turn_cond1=0, turn_cond2=0, self_bp_cond2=0, enemy_bp_cond2=0,
                 is_true_damage=False, ignore_def_base=0.0,
                 sub_effect=None, sub_param=0.0, sub_param2=0.0, sub_duration=0, sub_base=0.0):
        self.id = skill_id
        self.name = name
        self.tier = tier
        self.genre = genre              # "勇气", "坚韧", "先机", "魔力真伤", "魔力DoT"
        self.main_type = main_type      # "Attack" 或 "Heal"
        self.main_param = main_param
        self.trigger_chance = trigger_chance
        self.times_limit = times_limit
        self.turn_cond1 = turn_cond1
        self.turn_cond2 = turn_cond2
        self.self_bp_cond2 = self_bp_cond2
        self.enemy_bp_cond2 = enemy_bp_cond2
        
        self.is_true_damage = is_true_damage      # 纯粹真伤 (完全无视防御)
        self.ignore_def_base = ignore_def_base    # 破防基数 (魔力放大)
        
        self.sub_effect = sub_effect
        self.sub_param = sub_param
        self.sub_param2 = sub_param2
        self.sub_duration = sub_duration
        self.sub_base = sub_base

    def can_trigger(self, current_turn, self_bp_pct, enemy_bp_pct, used_count):
        if self.times_limit > 0 and self.times_limit < 999 and used_count >= self.times_limit:
            return False
        if current_turn <= self.turn_cond1:
            return False
        if self.turn_cond2 > 0 and current_turn >= self.turn_cond2:
            return False
        if self.self_bp_cond2 > 0 and self_bp_pct >= self.self_bp_cond2:
            return False
        if self.enemy_bp_cond2 > 0 and enemy_bp_pct >= self.enemy_bp_cond2:
            return False
        return True


class BattleTroop:
    def __init__(self, troop_id, name, scale, courage, resilience, initiative, magic, max_bp):
        self.id = troop_id
        self.name = name
        self.scale = scale
        self.max_bp = float(max_bp)
        self.current_bp = float(max_bp)
        
        self.base_courage = float(courage)
        self.base_resilience = float(resilience)
        self.base_initiative = float(initiative)
        self.base_magic = float(magic)
        
        self.mod_courage = 0.0
        self.mod_resilience = 0.0
        self.mod_initiative = 0.0
        self.mod_magic = 0.0
        
        self.skills = []
        self.skill_usage_counts = {}
        self.max_bp_dots = []
        self.turn_end_dots = []
        self.buffs = []
        
        # 体验与反馈统计
        self.total_damage_dealt = 0.0
        self.normal_damage = 0.0
        self.true_damage = 0.0          # 魔力真伤/穿透直伤贡献
        self.dot_damage = 0.0           # 魔力持续流失贡献
        self.crit_damage = 0.0          # 勇气暴击伤害贡献
        self.crit_hits = 0
        self.total_heal_done = 0.0      # 坚韧恢复总量
        self.dodge_count = 0            # 先机闪避次数
        self.action_swings = []

    def reset(self):
        self.current_bp = self.max_bp
        self.mod_courage = 0.0
        self.mod_resilience = 0.0
        self.mod_initiative = 0.0
        self.mod_magic = 0.0
        self.skill_usage_counts = {}
        self.max_bp_dots = []
        self.turn_end_dots = []
        self.buffs = []
        self.total_damage_dealt = 0.0
        self.normal_damage = 0.0
        self.true_damage = 0.0
        self.dot_damage = 0.0
        self.crit_damage = 0.0
        self.crit_hits = 0
        self.total_heal_done = 0.0
        self.dodge_count = 0
        self.action_swings = []

    @property
    def bp_pct(self):
        return (self.current_bp / self.max_bp) * 100.0

    @property
    def courage(self):
        return max(0.0, self.base_courage + self.mod_courage)

    @property
    def resilience(self):
        return max(0.0, self.base_resilience + self.mod_resilience)

    @property
    def initiative(self):
        return max(0.0, self.base_initiative + self.mod_initiative)

    @property
    def magic(self):
        return max(0.0, self.base_magic + self.mod_magic)

    def get_magic_amp(self, use_responsive=False):
        if use_responsive:
            return calc_magic_amp_responsive(self.magic)
        return calc_magic_amp_linear(self.magic)

    def is_dead(self):
        return self.current_bp <= 0.0001

    def heal(self, amount):
        old_bp = self.current_bp
        self.current_bp = min(self.max_bp, self.current_bp + amount)
        actual = self.current_bp - old_bp
        self.total_heal_done += actual
        return actual


# ==============================================================================
# 3. 战斗驱动引擎
# ==============================================================================

def execute_action(acting, defender, is_first, turn, use_responsive_magic=False):
    acting_amp = acting.get_magic_amp(use_responsive_magic)
    base_power = acting.max_bp * 0.20 + acting.current_bp * 0.10
    
    flat_dr, pct_dr = calc_resilience_dr(defender.resilience)
    dodge_rate, preempt_bonus = calc_initiative_stats(acting.initiative, defender.initiative)
    preempt_factor = (1.0 + preempt_bonus) if (is_first and preempt_bonus > 0) else 1.0
    courage_crit_rate, courage_crit_bonus = calc_courage_stats(acting.courage)
    
    weak_factor = 1.0
    for b in acting.buffs:
        if b['type'] == 'weak':
            weak_factor *= max(0.0, 1.0 - b['val'])

    # 1. 技能决策
    selected_skill = None
    for s in acting.skills:
        used = acting.skill_usage_counts.get(s.id, 0)
        if s.can_trigger(turn, acting.bp_pct, defender.bp_pct, used):
            if random.random() * 100.0 < s.trigger_chance:
                selected_skill = s
                acting.skill_usage_counts[s.id] = used + 1
                break

    if selected_skill is None:
        selected_skill = BattleSkill(999999, "普通攻击", 1, "通用", "Attack", main_param=100.0)

    # 2. 暴击判定 (仅勇气赋予暴击率，勇气技能可带微量基底)
    skill_crit_boost = 0.10 if selected_skill.genre == "勇气" else 0.0
    effective_crit_rate = min(0.95, skill_crit_boost + courage_crit_rate)
    is_crit = (random.random() < effective_crit_rate)

    # 3. 闪避判定 (暴击必定命中；未暴击受对方先机闪避判定)
    if not is_crit:
        if random.random() < dodge_rate:
            defender.dodge_count += 1
            acting.action_swings.append({'type': 'miss', 'ratio': 0.0, 'skill': selected_skill.name})
            return

    # 4. 主效果、真伤与破防判定
    ignore_def_ratio = 0.0
    lifesteal_ratio = 0.0
    is_pure_true = selected_skill.is_true_damage

    if selected_skill.ignore_def_base > 0:
        ignore_def_ratio = min(1.0, selected_skill.ignore_def_base * acting_amp)

    eff = selected_skill.sub_effect
    if eff == "lifesteal":
        lifesteal_ratio = selected_skill.sub_param * acting_amp

    if is_pure_true:
        effective_def_factor = 1.0
        effective_flat_dr = 0.0
    else:
        effective_pct_dr = pct_dr * (1.0 - ignore_def_ratio)
        effective_def_factor = max(0.0, 1.0 - effective_pct_dr)
        effective_flat_dr = flat_dr * (1.0 - ignore_def_ratio)

    direct_damage = 0.0
    if selected_skill.main_type == "Attack":
        mult = selected_skill.main_param / 100.0
        if is_crit:
            mult += courage_crit_bonus
        direct_damage = base_power * mult * effective_def_factor * preempt_factor

    elif selected_skill.main_type == "Heal":
        heal_val = 0.0
        if eff == "self_cur_heal":
            heal_val = acting.current_bp * (selected_skill.sub_param * acting_amp)
        elif eff == "self_max_heal":
            heal_val = acting.max_bp * (selected_skill.sub_param * acting_amp)
        actual_heal = acting.heal(heal_val)
        
        mult = 1.0
        if is_crit:
            mult += courage_crit_bonus
        direct_damage = base_power * mult * effective_def_factor * preempt_factor

    direct_damage *= weak_factor
    if direct_damage > 0:
        direct_damage = max(1.0, direct_damage - effective_flat_dr)

    # 伤害分类统计
    if direct_damage > 0:
        defender.current_bp -= direct_damage
        acting.total_damage_dealt += direct_damage
        
        if is_pure_true or ignore_def_ratio >= 0.50:
            # 标记为真伤/穿透直伤
            acting.true_damage += direct_damage
        else:
            acting.normal_damage += direct_damage
            
        if is_crit:
            acting.crit_hits += 1
            acting.crit_damage += direct_damage

    if lifesteal_ratio > 0 and direct_damage > 0:
        acting.heal(direct_damage * lifesteal_ratio)

    # 5. 附加效果结算
    extra_dmg = 0.0
    if eff == "self_lost_dmg":
        lost = max(0.0, acting.max_bp - acting.current_bp)
        extra_dmg = lost * (selected_skill.sub_param * acting_amp) * effective_def_factor
    elif eff == "enemy_lost_dmg":
        lost = max(0.0, defender.max_bp - defender.current_bp)
        extra_dmg = lost * (selected_skill.sub_param * acting_amp) * effective_def_factor
    elif eff == "enemy_cur_dmg":
        extra_dmg = defender.current_bp * (selected_skill.sub_param * acting_amp) * effective_def_factor
    elif eff == "stat_debuff":
        deb = selected_skill.sub_param
        dc = defender.base_courage * deb; dr = defender.base_resilience * deb
        di = defender.base_initiative * deb; dm = defender.base_magic * deb
        defender.mod_courage -= dc; defender.mod_resilience -= dr
        defender.mod_initiative -= di; defender.mod_magic -= dm
        defender.buffs.append({'type': 'stat_debuff', 'dc': dc, 'dr': dr, 'di': di, 'dm': dm, 'turns': selected_skill.sub_duration})
        if selected_skill.sub_param2 > 0:
            defender.buffs.append({'type': 'weak', 'val': selected_skill.sub_param2, 'turns': selected_skill.sub_duration})
    elif eff == "dot_max":
        defender.max_bp_dots.append({'val': selected_skill.sub_param * acting_amp, 'turns': selected_skill.sub_duration})
    elif eff == "dot_lost":
        defender.turn_end_dots.append({'mode': 'lost', 'val': selected_skill.sub_param * acting_amp, 'turns': selected_skill.sub_duration})
    elif eff == "dot_flat":
        flat_val = selected_skill.sub_base * acting_amp
        defender.turn_end_dots.append({'mode': 'flat', 'val': flat_val, 'turns': selected_skill.sub_duration})
    elif eff == "combo_dot":
        defender.max_bp_dots.append({'val': selected_skill.sub_param * acting_amp, 'turns': selected_skill.sub_duration})
        defender.turn_end_dots.append({'mode': 'flat', 'val': selected_skill.sub_base * acting_amp, 'turns': selected_skill.sub_duration})

    if extra_dmg > 0:
        defender.current_bp -= extra_dmg
        acting.total_damage_dealt += extra_dmg
        acting.normal_damage += extra_dmg

    total_action_dmg = direct_damage + extra_dmg
    swing_ratio = (total_action_dmg / defender.max_bp) * 100.0
    acting.action_swings.append({
        'type': 'hit',
        'is_crit': is_crit,
        'dmg': total_action_dmg,
        'ratio': swing_ratio,
        'skill': selected_skill.name,
        'genre': selected_skill.genre
    })


def run_single_battle(troop_a, troop_b, max_turns=30, use_responsive_magic=False):
    troop_a.reset()
    troop_b.reset()
    turn = 0

    while turn < max_turns:
        turn += 1
        
        # 1. 回合前结算: 最大战力流失 (坚韧全局百分比减伤全额生效)
        for trp, oppo in [(troop_a, troop_b), (troop_b, troop_a)]:
            if trp.is_dead(): continue
            if trp.max_bp_dots:
                _, pct_dr = calc_resilience_dr(trp.resilience)
                new_dots = []
                for dot in trp.max_bp_dots:
                    base_loss = trp.max_bp * dot['val']
                    actual = max(1.0, base_loss * (1.0 - pct_dr))
                    trp.current_bp -= actual
                    oppo.dot_damage += actual
                    oppo.total_damage_dealt += actual
                    dot['turns'] -= 1
                    if dot['turns'] > 0:
                        new_dots.append(dot)
                trp.max_bp_dots = new_dots
                if trp.is_dead(): trp.current_bp = 0

        if troop_a.is_dead() or troop_b.is_dead(): break

        # 2. 交锋阶段
        if troop_a.initiative >= troop_b.initiative:
            first, second = troop_a, troop_b
        else:
            first, second = troop_b, troop_a

        execute_action(first, second, True, turn, use_responsive_magic)
        if second.is_dead(): break

        execute_action(second, first, False, turn, use_responsive_magic)
        if first.is_dead(): break

        # 3. 回合后结算: 已损流失与固定流失
        for trp, oppo in [(troop_a, troop_b), (troop_b, troop_a)]:
            if trp.is_dead(): continue
            if trp.turn_end_dots:
                _, pct_dr = calc_resilience_dr(trp.resilience)
                new_dots = []
                for dot in trp.turn_end_dots:
                    if dot['mode'] == 'lost':
                        cur_lost = max(0.0, trp.max_bp - trp.current_bp)
                        base_loss = cur_lost * dot['val']
                    else:
                        base_loss = dot['val']
                    actual = max(1.0, base_loss * (1.0 - pct_dr))
                    trp.current_bp -= actual
                    oppo.dot_damage += actual
                    oppo.total_damage_dealt += actual
                    dot['turns'] -= 1
                    if dot['turns'] > 0:
                        new_dots.append(dot)
                trp.turn_end_dots = new_dots
                if trp.is_dead(): trp.current_bp = 0

        if troop_a.is_dead() or troop_b.is_dead(): break

        # 4. 回合末 Buff 倒计时
        for trp in [troop_a, troop_b]:
            new_buffs = []
            for b in trp.buffs:
                b['turns'] -= 1
                if b['turns'] <= 0:
                    if b['type'] == 'stat_debuff':
                        trp.mod_courage += b['dc']; trp.mod_resilience += b['dr']
                        trp.mod_initiative += b['di']; trp.mod_magic += b['dm']
                else:
                    new_buffs.append(b)
            trp.buffs = new_buffs

    winner = troop_a if (not troop_a.is_dead() and troop_b.is_dead()) else (troop_b if (not troop_b.is_dead() and troop_a.is_dead()) else (troop_a if troop_a.bp_pct >= troop_b.bp_pct else troop_b))
    return {'winner': winner, 'turns': turn}


# ==============================================================================
# 4. 各阶段阵容生成器 (支持魔力区分 真伤玩法 与 DoT玩法)
# ==============================================================================

def create_roster_for_scale(scale, genre_name, base_bp=None):
    stage_configs = {
        5:  {'bp': 60000,   'main': 120,  'sub': 50,  'other': 20, 'max_tier': 2},
        10: {'bp': 180000,  'main': 280,  'sub': 130, 'other': 40, 'max_tier': 3},
        15: {'bp': 360000,  'main': 480,  'sub': 220, 'other': 60, 'max_tier': 4},
        20: {'bp': 600000,  'main': 700,  'sub': 340, 'other': 80, 'max_tier': 5},
        25: {'bp': 820000,  'main': 880,  'sub': 430, 'other': 90, 'max_tier': 6},
        30: {'bp': 1000000, 'main': 1000, 'sub': 500, 'other': 100, 'max_tier': 6},
    }
    cfg = stage_configs[scale]
    actual_bp = base_bp if base_bp is not None else cfg['bp']
    max_t = cfg['max_tier']
    
    # 属性分配
    c, r, i, m = cfg['other'], cfg['other'], cfg['other'], cfg['other']
    if "勇气" in genre_name and "先机" in genre_name:
        c = cfg['main']; i = cfg['sub']
    elif "勇气" in genre_name and "坚韧" in genre_name:
        c = cfg['main']; r = cfg['sub']
    elif "勇气" in genre_name and "魔力" in genre_name:
        c = cfg['main']; m = cfg['sub']
    elif "坚韧" in genre_name and "先机" in genre_name:
        r = cfg['main']; i = cfg['sub']
    elif "坚韧" in genre_name and "魔力" in genre_name:
        r = cfg['main']; m = cfg['sub']
    elif "先机" in genre_name and "魔力" in genre_name:
        i = cfg['main']; m = cfg['sub']
    elif "魔力真伤" in genre_name:
        m = cfg['main']; i = cfg['sub']
    elif "魔力DoT" in genre_name:
        m = cfg['main']; r = cfg['sub']
    
    troop = BattleTroop(1, f"{genre_name}[{scale}人]", scale, courage=c, resilience=r, initiative=i, magic=m, max_bp=actual_bp)

    # 技能配置
    if "魔力真伤" in genre_name or (genre_name == "勇气+魔力" and "真伤" in genre_name):
        # 玩法 A: 魔力直伤破防/纯真伤流 (靠穿甲、纯粹真伤爆发破高防)
        if max_t <= 2:
            troop.skills.append(BattleSkill(311, "透甲穿心刺", 1, "魔力真伤", "Attack", main_param=120.0, trigger_chance=35.0, ignore_def_base=0.30))
            troop.skills.append(BattleSkill(312, "奥术真伤破", 2, "魔力真伤", "Attack", main_param=130.0, trigger_chance=30.0, ignore_def_base=0.45))
        elif max_t <= 3:
            troop.skills.append(BattleSkill(311, "透甲先锋", 2, "魔力真伤", "Attack", main_param=130.0, trigger_chance=40.0, turn_cond2=3, times_limit=1, ignore_def_base=0.45))
            troop.skills.append(BattleSkill(312, "崩界纯粹击", 3, "魔力真伤", "Attack", main_param=145.0, trigger_chance=35.0, is_true_damage=True))
            troop.skills.append(BattleSkill(313, "断魂魔刃", 3, "魔力真伤", "Attack", main_param=150.0, trigger_chance=30.0, ignore_def_base=0.55))
        elif max_t <= 4:
            # 15人 (引入T4): 纯粹真伤 + 高额穿透
            troop.skills.append(BattleSkill(311, "奥能贯通炮", 4, "魔力真伤", "Attack", main_param=170.0, trigger_chance=40.0, turn_cond2=3, times_limit=1, is_true_damage=True))
            troop.skills.append(BattleSkill(312, "虚空穿甲杀", 4, "魔力真伤", "Attack", main_param=180.0, trigger_chance=35.0, ignore_def_base=0.70))
            troop.skills.append(BattleSkill(313, "断罪真伤刃", 3, "魔力真伤", "Attack", main_param=140.0, trigger_chance=30.0, is_true_damage=True))
        elif max_t <= 5:
            troop.skills.append(BattleSkill(311, "天顶贯穿击", 5, "魔力真伤", "Attack", main_param=210.0, trigger_chance=45.0, is_true_damage=True, times_limit=1))
            troop.skills.append(BattleSkill(312, "虚空湮灭刃", 5, "魔力真伤", "Attack", main_param=190.0, trigger_chance=40.0, ignore_def_base=0.85))
            troop.skills.append(BattleSkill(313, "常态穿透刺", 4, "魔力真伤", "Attack", main_param=150.0, trigger_chance=30.0, is_true_damage=True))
        else:
            troop.skills.append(BattleSkill(311, "弑神断界斩", 6, "魔力真伤", "Attack", main_param=240.0, trigger_chance=50.0, is_true_damage=True, times_limit=1))
            troop.skills.append(BattleSkill(312, "深渊真伤极光", 6, "魔力真伤", "Attack", main_param=210.0, trigger_chance=45.0, ignore_def_base=0.95))
            troop.skills.append(BattleSkill(313, "纯粹裂魂杀", 5, "魔力真伤", "Attack", main_param=170.0, trigger_chance=30.0, is_true_damage=True))
            troop.skills.append(BattleSkill(314, "常态魔刃", 5, "魔力真伤", "Attack", main_param=150.0, trigger_chance=25.0, ignore_def_base=0.75))

    elif "魔力DoT" in genre_name or (genre_name == "坚韧+魔力" and "DoT" in genre_name):
        # 玩法 B: 魔力持续流失侵蚀流 (靠最大生命流失、已损流失、固定伤害层层磨血)
        if max_t <= 2:
            troop.skills.append(BattleSkill(321, "腐蚀毒雾", 1, "魔力DoT", "Attack", main_param=105.0, trigger_chance=35.0, sub_effect="dot_max", sub_param=0.025, sub_duration=2))
            troop.skills.append(BattleSkill(322, "暗影流失", 2, "魔力DoT", "Attack", main_param=110.0, trigger_chance=30.0, sub_effect="dot_flat", sub_base=cfg['bp']*0.03, sub_duration=2))
        elif max_t <= 3:
            troop.skills.append(BattleSkill(321, "万毒始发", 2, "魔力DoT", "Attack", main_param=105.0, trigger_chance=40.0, turn_cond2=3, times_limit=1, sub_effect="dot_max", sub_param=0.030, sub_duration=3))
            troop.skills.append(BattleSkill(322, "剧毒侵蚀", 3, "魔力DoT", "Attack", main_param=110.0, trigger_chance=35.0, sub_effect="combo_dot", sub_param=0.030, sub_base=cfg['bp']*0.035, sub_duration=3))
            troop.skills.append(BattleSkill(323, "蚀骨诅咒", 3, "魔力DoT", "Attack", main_param=115.0, trigger_chance=30.0, sub_effect="dot_lost", sub_param=0.045, sub_duration=2))
        elif max_t <= 4:
            # 15人 (引入T4): 复合强力流失
            troop.skills.append(BattleSkill(321, "天谴腐蚀", 4, "魔力DoT", "Attack", main_param=115.0, trigger_chance=45.0, turn_cond2=3, times_limit=1, sub_effect="combo_dot", sub_param=0.040, sub_base=cfg['bp']*0.045, sub_duration=3))
            troop.skills.append(BattleSkill(322, "死脉流失", 4, "魔力DoT", "Attack", main_param=120.0, trigger_chance=35.0, sub_effect="dot_lost", sub_param=0.060, sub_duration=3))
            troop.skills.append(BattleSkill(323, "常态毒沼", 3, "魔力DoT", "Attack", main_param=110.0, trigger_chance=30.0, sub_effect="dot_max", sub_param=0.030, sub_duration=2))
        elif max_t <= 5:
            troop.skills.append(BattleSkill(321, "深渊毒爆", 5, "魔力DoT", "Attack", main_param=125.0, trigger_chance=50.0, turn_cond2=3, times_limit=1, sub_effect="combo_dot", sub_param=0.048, sub_base=cfg['bp']*0.055, sub_duration=3))
            troop.skills.append(BattleSkill(322, "生命剥离", 5, "魔力DoT", "Attack", main_param=130.0, trigger_chance=40.0, sub_effect="dot_lost", sub_param=0.075, sub_duration=3))
            troop.skills.append(BattleSkill(323, "暗流蚀魂", 4, "魔力DoT", "Attack", main_param=115.0, trigger_chance=30.0, sub_effect="dot_flat", sub_base=cfg['bp']*0.040, sub_duration=2))
        else:
            troop.skills.append(BattleSkill(321, "灭世剧毒", 6, "魔力DoT", "Attack", main_param=130.0, trigger_chance=50.0, turn_cond2=3, times_limit=1, sub_effect="combo_dot", sub_param=0.055, sub_base=cfg['bp']*0.065, sub_duration=3))
            troop.skills.append(BattleSkill(322, "绝命凋零", 6, "魔力DoT", "Attack", main_param=135.0, trigger_chance=45.0, sub_effect="dot_lost", sub_param=0.090, sub_duration=3))
            troop.skills.append(BattleSkill(323, "常态侵蚀", 5, "魔力DoT", "Attack", main_param=120.0, trigger_chance=30.0, sub_effect="dot_max", sub_param=0.035, sub_duration=2))
            troop.skills.append(BattleSkill(324, "冥界汲取", 5, "魔力DoT", "Attack", main_param=115.0, trigger_chance=25.0, sub_effect="lifesteal", sub_param=0.35))

    elif "勇气" in genre_name:
        if max_t <= 2:
            troop.skills.append(BattleSkill(101, "破阵斩", 1, "勇气", "Attack", main_param=135.0, trigger_chance=30.0))
            troop.skills.append(BattleSkill(102, "强袭破", 2, "勇气", "Attack", main_param=145.0, trigger_chance=30.0))
        elif max_t <= 3:
            troop.skills.append(BattleSkill(101, "先锋突刺", 2, "勇气", "Attack", main_param=145.0, trigger_chance=35.0, turn_cond2=3, times_limit=1))
            troop.skills.append(BattleSkill(102, "破阵狂斩", 3, "勇气", "Attack", main_param=165.0, trigger_chance=30.0))
            troop.skills.append(BattleSkill(103, "残血重击", 3, "勇气", "Attack", main_param=180.0, trigger_chance=30.0, enemy_bp_cond2=50))
        elif max_t <= 4:
            troop.skills.append(BattleSkill(101, "疾风先锋", 3, "勇气", "Attack", main_param=150.0, trigger_chance=35.0, turn_cond2=3, times_limit=1))
            troop.skills.append(BattleSkill(102, "绝境浴血斩", 4, "勇气", "Attack", main_param=220.0, trigger_chance=35.0, self_bp_cond2=45, times_limit=1, sub_effect="self_lost_dmg", sub_param=0.18))
            troop.skills.append(BattleSkill(103, "裂地巨刃", 4, "勇气", "Attack", main_param=160.0, trigger_chance=30.0))
        elif max_t <= 5:
            troop.skills.append(BattleSkill(101, "风暴突击", 4, "勇气", "Attack", main_param=160.0, trigger_chance=40.0, turn_cond2=3, times_limit=1))
            troop.skills.append(BattleSkill(102, "致命裁决", 5, "勇气", "Attack", main_param=280.0, trigger_chance=45.0, enemy_bp_cond2=45, times_limit=1))
            troop.skills.append(BattleSkill(103, "逆风狂战", 5, "勇气", "Attack", main_param=240.0, trigger_chance=35.0, self_bp_cond2=40, times_limit=1, sub_effect="self_lost_dmg", sub_param=0.25))
        else:
            troop.skills.append(BattleSkill(101, "开局压制", 5, "勇气", "Attack", main_param=160.0, trigger_chance=50.0, turn_cond2=3, times_limit=1))
            troop.skills.append(BattleSkill(102, "终极绝命斩", 6, "勇气", "Attack", main_param=340.0, trigger_chance=50.0, enemy_bp_cond2=45, times_limit=1))
            troop.skills.append(BattleSkill(103, "背水逆转击", 6, "勇气", "Attack", main_param=300.0, trigger_chance=50.0, self_bp_cond2=40, times_limit=1, sub_effect="self_lost_dmg", sub_param=0.35))
            troop.skills.append(BattleSkill(104, "常态巨刃", 5, "勇气", "Attack", main_param=170.0, trigger_chance=30.0))

    elif "坚韧" in genre_name:
        if max_t <= 2:
            troop.skills.append(BattleSkill(201, "圣佑急救", 1, "坚韧", "Heal", main_param=100.0, trigger_chance=30.0, self_bp_cond2=80, sub_effect="self_max_heal", sub_param=0.06))
            troop.skills.append(BattleSkill(202, "坚毅壁垒", 2, "坚韧", "Heal", main_param=100.0, trigger_chance=30.0, self_bp_cond2=75, sub_effect="self_max_heal", sub_param=0.08))
        elif max_t <= 3:
            troop.skills.append(BattleSkill(201, "战场包扎", 2, "坚韧", "Heal", main_param=100.0, trigger_chance=35.0, self_bp_cond2=75, sub_effect="self_max_heal", sub_param=0.08))
            troop.skills.append(BattleSkill(202, "重整旗鼓", 3, "坚韧", "Heal", main_param=100.0, trigger_chance=30.0, self_bp_cond2=60, sub_effect="self_max_heal", sub_param=0.10))
            troop.skills.append(BattleSkill(203, "反击盾刺", 3, "坚韧", "Attack", main_param=140.0, trigger_chance=30.0))
        elif max_t <= 4:
            troop.skills.append(BattleSkill(201, "危机苏生", 4, "坚韧", "Heal", main_param=100.0, trigger_chance=40.0, self_bp_cond2=50, times_limit=1, sub_effect="self_max_heal", sub_param=0.12))
            troop.skills.append(BattleSkill(202, "固守反攻", 4, "坚韧", "Attack", main_param=150.0, trigger_chance=30.0, sub_effect="weak", sub_param=0.25, sub_duration=2))
        elif max_t <= 5:
            troop.skills.append(BattleSkill(201, "不坏金身", 5, "坚韧", "Heal", main_param=100.0, trigger_chance=50.0, self_bp_cond2=45, times_limit=1, sub_effect="self_max_heal", sub_param=0.15))
            troop.skills.append(BattleSkill(202, "圣光守护", 4, "坚韧", "Heal", main_param=100.0, trigger_chance=35.0, self_bp_cond2=65, sub_effect="self_max_heal", sub_param=0.11))
        else:
            troop.skills.append(BattleSkill(201, "神恩涅槃", 6, "坚韧", "Heal", main_param=100.0, trigger_chance=50.0, self_bp_cond2=40, times_limit=1, sub_effect="self_max_heal", sub_param=0.18))
            troop.skills.append(BattleSkill(202, "生命复苏", 5, "坚韧", "Heal", main_param=100.0, trigger_chance=35.0, self_bp_cond2=55, sub_effect="self_max_heal", sub_param=0.14))
            troop.skills.append(BattleSkill(203, "常态吸血", 5, "坚韧", "Attack", main_param=130.0, trigger_chance=25.0, sub_effect="lifesteal", sub_param=0.35))

    elif "先机" in genre_name:
        if max_t <= 2:
            troop.skills.append(BattleSkill(401, "迅捷突刺", 1, "先机", "Attack", main_param=125.0, trigger_chance=35.0))
            troop.skills.append(BattleSkill(402, "影袭", 2, "先机", "Attack", main_param=135.0, trigger_chance=30.0))
        elif max_t <= 3:
            troop.skills.append(BattleSkill(401, "先发制人", 2, "先机", "Attack", main_param=135.0, trigger_chance=40.0, turn_cond2=3, times_limit=1))
            troop.skills.append(BattleSkill(402, "封脉刺", 3, "先机", "Attack", main_param=145.0, trigger_chance=35.0, sub_effect="stat_debuff", sub_param=0.15, sub_duration=2))
        elif max_t <= 4:
            troop.skills.append(BattleSkill(401, "疾速封脉", 4, "先机", "Attack", main_param=145.0, trigger_chance=40.0, turn_cond2=3, times_limit=1, sub_effect="stat_debuff", sub_param=0.20, sub_param2=0.20, sub_duration=2))
            troop.skills.append(BattleSkill(402, "幻影连刺", 4, "先机", "Attack", main_param=165.0, trigger_chance=30.0))
        elif max_t <= 5:
            troop.skills.append(BattleSkill(401, "极速衰弱袭", 5, "先机", "Attack", main_param=155.0, trigger_chance=45.0, turn_cond2=3, times_limit=1, sub_effect="stat_debuff", sub_param=0.25, sub_param2=0.25, sub_duration=2))
            troop.skills.append(BattleSkill(402, "无影刺杀", 5, "先机", "Attack", main_param=185.0, trigger_chance=35.0))
        else:
            troop.skills.append(BattleSkill(401, "瞬狱影杀", 6, "先机", "Attack", main_param=165.0, trigger_chance=50.0, turn_cond2=3, times_limit=1, sub_effect="stat_debuff", sub_param=0.30, sub_param2=0.30, sub_duration=2))
            troop.skills.append(BattleSkill(402, "死线贯穿", 6, "先机", "Attack", main_param=220.0, trigger_chance=45.0))
            troop.skills.append(BattleSkill(403, "疾风步法", 5, "先机", "Attack", main_param=160.0, trigger_chance=30.0))

    return troop


# ==============================================================================
# 5. 执行测试套件与数据输出
# ==============================================================================

def run_all_tests():
    print("=" * 95)
    print("【全阶段实战演化与体验平衡诊断套件】")
    print("涵盖: 5/10/15/20/25/30人阶段、魔力真伤与DoT双玩法解构、越级挑战破局力、技能感知度分析")
    print("=" * 95)

    # --------------------------------------------------------------------------
    # 诊断 1: 单技能实际摆动比 (Swing Ratio) 与存在感分析
    # --------------------------------------------------------------------------
    print("\n>>> 诊断 1: 各阶段核心技能释放时的血条摆动幅度 (Swing Ratio = 效果量 / 目标最大战力)")
    scales = [5, 10, 15, 20, 25, 30]
    for sc in scales:
        t_courage = create_roster_for_scale(sc, "勇气+先机")
        t_magic_true = create_roster_for_scale(sc, "魔力真伤")
        t_magic_dot = create_roster_for_scale(sc, "魔力DoT")
        t_resilience = create_roster_for_scale(sc, "坚韧+先机")
        
        swings = {}
        for p1, p2 in [(t_courage, t_resilience), (t_magic_true, t_resilience), (t_magic_dot, t_resilience)]:
            for _ in range(100):
                run_single_battle(p1, p2)
                for act in p1.action_swings:
                    if act['type'] == 'hit':
                        swings.setdefault(act['skill'], []).append(act['ratio'])
        
        print(f"\n【{sc} 人阵容阶段】(当前全队基准战力: {t_courage.max_bp:,.0f})")
        for sname, r_list in list(swings.items())[:5]:
            avg_r = sum(r_list) / len(r_list)
            grade = "严重刮痧(无存在感)" if avg_r < 8.0 else ("健康有效" if avg_r <= 28.0 else "核弹爆发")
            print(f"  * 技能【{sname:<8}】: 平均单发削减 {avg_r:>5.1f}% 战力 (极值 {min(r_list):>4.1f}% ~ {max(r_list):>4.1f}%) -> {grade}")

    # --------------------------------------------------------------------------
    # 诊断 2: 魔力真伤 vs 魔力 DoT 双玩法在越级挑战中的攻坚表现
    # --------------------------------------------------------------------------
    print("\n\n>>> 诊断 2: 越级挑战攻坚测试 (15人玩家 36万战力 VS 72万战力高防血牛 Boss)")
    print("Boss 设定: 720,000 战力, 600 坚韧 (固定减伤 9,600, 百分比减伤 54.5%), 先机 100")
    
    boss_heavy_tank = BattleTroop(99, "守门重装巨神", 15, courage=100, resilience=600, initiative=100, magic=100, max_bp=720000)
    boss_heavy_tank.skills.append(BattleSkill(9901, "巨岩猛击", 3, "通用", "Attack", main_param=120.0, trigger_chance=40.0))
    boss_heavy_tank.skills.append(BattleSkill(9902, "泰山压顶", 4, "通用", "Attack", main_param=140.0, trigger_chance=30.0))

    challengers = [
        ("纯物理[勇气+先机]", create_roster_for_scale(15, "勇气+先机")),
        ("纯防守[坚韧+先机]", create_roster_for_scale(15, "坚韧+先机")),
        ("魔力玩法A[纯粹真伤/穿透]", create_roster_for_scale(15, "魔力真伤")),
        ("魔力玩法B[持续流失/侵蚀]", create_roster_for_scale(15, "魔力DoT")),
    ]

    sims = 1000
    for c_name, c_troop in challengers:
        wins = 0
        total_turns = 0
        avg_boss_rem = 0.0
        true_share_list = []
        dot_share_list = []
        
        for _ in range(sims):
            res = run_single_battle(c_troop, boss_heavy_tank, max_turns=25)
            if res['winner'] == c_troop: wins += 1
            total_turns += res['turns']
            avg_boss_rem += (boss_heavy_tank.current_bp / boss_heavy_tank.max_bp) * 100.0
            total_d = max(1.0, c_troop.total_damage_dealt)
            true_share_list.append((c_troop.true_damage / total_d) * 100.0)
            dot_share_list.append((c_troop.dot_damage / total_d) * 100.0)

        wr = (wins / sims) * 100.0
        avg_t = total_turns / sims
        rem = avg_boss_rem / sims
        avg_true_s = sum(true_share_list) / len(true_share_list)
        avg_dot_s = sum(dot_share_list) / len(dot_share_list)

        print(f"\n  * 【{c_name}】:")
        print(f"      胜率: {wr:>5.1f}% | 平均存活: {avg_t:>4.1f} 回合 | 战局结束Boss平均剩余血量: {rem:>5.1f}%")
        print(f"      真伤穿透输出占比: {avg_true_s:>5.1f}% | 持续流失(DoT)输出占比: {avg_dot_s:>5.1f}%")

    # --------------------------------------------------------------------------
    # 诊断 3: 魔力放大曲线分析 (线性 1+M/600 vs 改进响应式曲线)
    # --------------------------------------------------------------------------
    print("\n\n>>> 诊断 3: 魔力放大曲线各阶段实测数值")
    points = [
        (5, 50, "5人(M=50)"),
        (10, 130, "10人(M=130)"),
        (15, 220, "15人(M=220)"),
        (20, 340, "20人(M=340)"),
        (25, 430, "25人(M=430)"),
        (30, 500, "30人副魔力(M=500)"),
        (30, 1000, "30人主魔力(M=1000)")
    ]
    print(f"{'阶段节点':<18} {'当前线性倍数':<14} {'真伤破防(T4基准50%)':<22} {'DoT流失(T4基准4%)':<22}")
    print("-" * 75)
    for sc, mval, desc in points:
        lamp = calc_magic_amp_linear(mval)
        pierce_val = min(100.0, 50.0 * lamp)
        dot_val = 4.0 * lamp
        print(f"{desc:<16} {lamp:>6.2f}x          破防: {pierce_val:>5.1f}%            流失: {dot_val:>4.1f}%/回合")

    # --------------------------------------------------------------------------
    # 诊断 4: 30人终局生态下 各核心流派的高光机制达成率
    # --------------------------------------------------------------------------
    print("\n\n>>> 诊断 4: 30人终局完全体 流派特色达成率 (Fantasy Fulfillment)")
    genres = ["勇气+先机", "坚韧+先机", "魔力真伤", "魔力DoT"]
    for g1 in genres:
        crit_r = []; true_r = []; dot_r = []; heal_r = []; dodge_c = []; turns = []
        for g2 in genres:
            if g1 == g2: continue
            for _ in range(150):
                t1 = create_roster_for_scale(30, g1)
                t2 = create_roster_for_scale(30, g2)
                res = run_single_battle(t1, t2)
                turns.append(res['turns'])
                tot = max(1.0, t1.total_damage_dealt)
                crit_r.append((t1.crit_damage / tot) * 100.0)
                true_r.append((t1.true_damage / tot) * 100.0)
                dot_r.append((t1.dot_damage / tot) * 100.0)
                heal_r.append((t1.total_heal_done / t1.max_bp) * 100.0)
                dodge_c.append(t1.dodge_count)

        print(f"\n【{g1}】终局实战画像:")
        print(f"  - 暴击伤害占比: {sum(crit_r)/len(crit_r):>5.1f}%")
        print(f"  - 真伤穿透占比: {sum(true_r)/len(true_r):>5.1f}%")
        print(f"  - 持续流失占比: {sum(dot_r)/len(dot_r):>5.1f}%")
        print(f"  - 累计战力恢复: {sum(heal_r)/len(heal_r):>5.1f}% MaxBP")
        print(f"  - 平均闪避次数: {sum(dodge_c)/len(dodge_c):>5.1f} 次/局")
        print(f"  - 平均交锋回合: {sum(turns)/len(turns):>5.1f} 回合")

if __name__ == '__main__':
    run_all_tests()
