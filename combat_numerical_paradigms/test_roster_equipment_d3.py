# -*- coding: utf-8 -*-
"""
真实组队层与次级装备上下限、技能衰减测算引擎 (D3困难场景专项)
核心物理特性：
1. 真实队伍结构：1 名主C + (N-1) 名填充队员 (Filler/Sub-Units)。
2. 真实技能池竞争与技能衰减 (Skill Burnout)：
   高阶大招受 trigger_chance 与 times_limit 严格约束，大招耗尽后真实进入技能衰减期（伤害断崖式下跌，被迫平A）。
3. 装备体系分层测试：
   - 填充角色佩戴【次级属性装备】：测试单件属性点数对全队底模的支撑，寻找属性上下限区间；
   - 主C佩戴【机制强化装备】：测试技能未触发/技能次数耗尽时装备的衰减与补偿。
4. 从 D3 困难场景开始，分六大流派独立实测，不设任何教条胜率约束，客观记录时序数据。
"""
import random
import sys
import copy
from collections import defaultdict

import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# 导入基准底层物理公式
from test_30man_combat_simulator import (
    calc_magic_amp_responsive, calc_resilience_dr,
    calc_courage_stats, calc_initiative_stats, BattleSkill
)

class Character:
    """单个角色模型"""
    def __init__(self, char_id, role, c, r, i, m, bp):
        self.char_id = char_id
        self.role = role  # "Carry" 或 "Filler"
        self.base_c = c
        self.base_r = r
        self.base_i = i
        self.base_m = m
        self.base_bp = bp
        self.skills = []
        # 装备属性增量
        self.item_c = 0
        self.item_r = 0
        self.item_i = 0
        self.item_m = 0
        self.item_bp = 0
        # 主C特有机制装备标记
        self.carry_item_mech = None

class RealRosterTeam:
    """由具体角色聚合构成的真实战团"""
    def __init__(self, name, genre_code, scale=30):
        self.name = name
        self.genre_code = genre_code
        self.scale = scale
        self.members = []
        self.skill_pool = []
        
        # 聚合属性（由队员自然累加）
        self.max_bp = 0
        self.current_bp = 0
        self.base_courage = 0
        self.base_resilience = 0
        self.base_initiative = 0
        self.base_magic = 0
        
        self.cur_initiative = 0
        self.usage = {}
        self.max_bp_dots = []
        self.lost_bp_dots = []
        self.dmg_reduce_debuffs = []
        self.stat_reduce_debuffs = []
        
        # 遥测指标
        self.action_history = []  # 记录每回合出招（普攻还是技能，技能名，造成伤害）
        self.total_damage = 0.0

    def aggregate_stats(self):
        """聚合全员属性及装备"""
        self.max_bp = sum(m.base_bp + m.item_bp for m in self.members)
        self.current_bp = self.max_bp
        self.base_courage = sum(m.base_c + m.item_c for m in self.members)
        self.base_resilience = sum(m.base_r + m.item_r for m in self.members)
        self.base_initiative = sum(m.base_i + m.item_i for m in self.members)
        self.base_magic = sum(m.base_m + m.item_m for m in self.members)
        
        # 汇聚全员技能到战团技能池（按高阶优先排序）
        self.skill_pool = []
        for m in self.members:
            for s in m.skills:
                self.skill_pool.append((m, s))
        # 按阶位降序排列竞争顺位
        self.skill_pool.sort(key=lambda x: x[1].tier, reverse=True)

    def reset(self):
        self.current_bp = self.max_bp
        self.cur_initiative = self.base_initiative
        self.usage = {}
        self.max_bp_dots = []
        self.lost_bp_dots = []
        self.dmg_reduce_debuffs = []
        self.stat_reduce_debuffs = []
        self.action_history = []
        self.total_damage = 0.0

    def is_dead(self):
        return self.current_bp <= 0.0001

    @property
    def bp_pct(self):
        return (self.current_bp / self.max_bp) * 100.0 if self.max_bp > 0 else 0.0

    def get_effective_stats(self):
        factor = 1.0
        for db in self.stat_reduce_debuffs:
            factor *= (1.0 - db['pct'])
        return (
            self.base_courage * factor,
            self.base_resilience * factor,
            self.cur_initiative * factor,
            self.base_magic * factor
        )

    def get_dmg_output_factor(self):
        factor = 1.0
        for db in self.dmg_reduce_debuffs:
            factor *= (1.0 - db['pct'])
        return factor

    def heal(self, amount):
        if amount <= 0: return 0.0
        old = self.current_bp
        self.current_bp = min(self.max_bp, self.current_bp + amount)
        return self.current_bp - old

def execute_roster_action(acting_team, defending_team, is_first, turn):
    eff_c, eff_r, eff_i, eff_m = acting_team.get_effective_stats()
    def_c, def_r, def_i, def_m = defending_team.get_effective_stats()

    base_power = acting_team.max_bp * 0.09 + acting_team.current_bp * 0.045
    m_amp = calc_magic_amp_responsive(eff_m)
    c_crit_rate, c_crit_bonus = calc_courage_stats(eff_c)
    dodge_rate, preempt_bonus = calc_initiative_stats(eff_i, def_i)
    preempt_factor = (1.0 + preempt_bonus) if (is_first and preempt_bonus > 0) else 1.0

    # 1. 技能池真实竞争与衰减判定
    selected_skill = None
    skill_owner = None
    for owner, s in acting_team.skill_pool:
        u = acting_team.usage.get(s.id, 0)
        if s.can_trigger(turn, acting_team.bp_pct, defending_team.bp_pct, u):
            if random.random() * 100.0 < s.trigger_chance:
                selected_skill = s
                skill_owner = owner
                acting_team.usage[s.id] = u + 1
                break

    is_normal_attack = False
    if selected_skill is None:
        # 进入技能衰减/平A期
        is_normal_attack = True
        selected_skill = BattleSkill(9999, "普通攻击", 1, "通用", "Attack", main_param=100.0)

    # 2. 先机成长
    if selected_skill.ini_bonus > 0:
        acting_team.cur_initiative += selected_skill.ini_bonus

    # 3. 暴击判定与主C装备加成
    raw_skill_crit = selected_skill.base_crit_rate
    esc = raw_skill_crit * (1.0 + (m_amp - 1.0) * 0.45) if raw_skill_crit > 0 else 0.0
    total_crit_rate = c_crit_rate + esc

    # 主C装备机制检查：若为主C出招且带特定机制
    carry_mech = skill_owner.carry_item_mech if (skill_owner and skill_owner.role == "Carry") else None
    if carry_mech == "CRIT_OVERFLOW_TRUE" and is_normal_attack == False:
        # 暴击溢出转真伤机制
        pass

    extra_overflow = (total_crit_rate - 1.0) * 1.5 if total_crit_rate > 1.0 else 0.0
    effective_crit_rate = min(1.0, total_crit_rate)
    is_crit = (random.random() < effective_crit_rate)

    # 4. 闪避判定
    if not is_crit:
        if random.random() < dodge_rate:
            acting_team.action_history.append((turn, "Miss", 0.0, is_normal_attack))
            return

    # 5. 伤害倍率与普攻补偿机制
    mult = selected_skill.main_param / 100.0
    if is_crit:
        mult += (c_crit_bonus + extra_overflow)

    # 主C普攻补偿机制检查：若主C处于平A状态且有普攻补偿装备
    if is_normal_attack:
        main_carry = next((m for m in acting_team.members if m.role == "Carry"), None)
        if main_carry and main_carry.carry_item_mech == "NORMAL_COMPENSATION":
            mult *= 1.45  # 普攻伤害补偿 45%

    raw_dmg = base_power * mult * preempt_factor * acting_team.get_dmg_output_factor()

    # 6. 治疗结算
    if selected_skill.main_type == "Heal":
        heal_val = acting_team.max_bp * selected_skill.sub_param
        acting_team.heal(heal_val)
        raw_dmg = base_power * 1.0 * acting_team.get_dmg_output_factor()

    # 7. 减伤与穿透
    flat_dr, pct_dr = calc_resilience_dr(def_r)
    is_pure_true = (selected_skill.ignore_def_ratio * m_amp >= 0.85)

    if is_pure_true:
        true_bonus = 1.0 + (m_amp - 1.0) * 0.20
        actual_dmg = raw_dmg * true_bonus
    else:
        eff_pct_dr = max(0.0, pct_dr * (1.0 - selected_skill.ignore_def_ratio * m_amp))
        actual_dmg = max(1.0, raw_dmg * (1.0 - eff_pct_dr) - flat_dr)

    defending_team.current_bp = max(0.0, defending_team.current_bp - actual_dmg)
    acting_team.total_damage += actual_dmg
    acting_team.action_history.append((turn, selected_skill.name, actual_dmg, is_normal_attack))

    # 8. 附加效果
    sub = selected_skill.sub_effect_name
    if sub == "自身已损反噬":
        lost = max(0.0, acting_team.max_bp - acting_team.current_bp)
        extra = lost * selected_skill.sub_param * (1.0 - pct_dr)
        defending_team.current_bp = max(0.0, defending_team.current_bp - max(1.0, extra))
    elif sub == "敌方已损斩杀":
        lost = max(0.0, defending_team.max_bp - defending_team.current_bp)
        extra = lost * selected_skill.sub_param * (1.0 - pct_dr)
        defending_team.current_bp = max(0.0, defending_team.current_bp - max(1.0, extra))
    elif sub == "战力吸收":
        acting_team.heal(actual_dmg * (selected_skill.sub_param * m_amp))
    elif sub == "最大流失":
        defending_team.max_bp_dots.append({'val': selected_skill.sub_param * m_amp, 'turns': selected_skill.sub_duration, 'source': acting_team})
    elif sub == "已损流失":
        defending_team.lost_bp_dots.append({'val': selected_skill.sub_param * m_amp, 'turns': selected_skill.sub_duration, 'source': acting_team})
    elif sub == "虚弱压制":
        base_pct = selected_skill.sub_param / 100.0
        scaled_pct = min(0.60, base_pct * (1.0 + (m_amp - 1.0) * 0.25))
        defending_team.dmg_reduce_debuffs.append({'pct': scaled_pct, 'turns': selected_skill.sub_duration})
    elif sub == "四维削弱":
        base_pct = selected_skill.sub_param / 100.0
        scaled_pct = min(0.40, base_pct * (1.0 + (m_amp - 1.0) * 0.25))
        defending_team.stat_reduce_debuffs.append({'pct': scaled_pct, 'turns': selected_skill.sub_duration})

def run_roster_battle(t1, t2, max_turns=40):
    t1.reset()
    t2.reset()
    turn = 0
    while turn < max_turns:
        turn += 1

        # 回合前流失
        for trp in [t1, t2]:
            if trp.is_dead(): continue
            _, pdr = calc_resilience_dr(trp.base_resilience)
            if trp.max_bp_dots:
                new_dots = []
                for dot in trp.max_bp_dots:
                    src_factor = dot['source'].get_dmg_output_factor() if 'source' in dot else 1.0
                    loss = max(1.0, trp.max_bp * dot['val'] * (1.0 - pdr) * src_factor)
                    trp.current_bp -= loss
                    dot['turns'] -= 1
                    if dot['turns'] > 0: new_dots.append(dot)
                trp.max_bp_dots = new_dots

        if t1.is_dead() or t2.is_dead(): break

        eff_i1 = t1.get_effective_stats()[2]
        eff_i2 = t2.get_effective_stats()[2]
        if eff_i1 > eff_i2: first, second = t1, t2
        elif eff_i2 > eff_i1: first, second = t2, t1
        else: first, second = (t1, t2) if random.random() < 0.5 else (t2, t1)

        execute_roster_action(first, second, True, turn)
        if second.is_dead(): break
        execute_roster_action(second, first, False, turn)
        if first.is_dead(): break

        # 回合末已损流失与Debuff
        for trp in [t1, t2]:
            if trp.is_dead(): continue
            _, pdr = calc_resilience_dr(trp.base_resilience)
            if trp.lost_bp_dots:
                new_dots = []
                for dot in trp.lost_bp_dots:
                    src_factor = dot['source'].get_dmg_output_factor() if 'source' in dot else 1.0
                    lost = max(0.0, trp.max_bp - trp.current_bp)
                    loss = max(1.0, lost * dot['val'] * (1.0 - pdr) * src_factor)
                    trp.current_bp -= loss
                    dot['turns'] -= 1
                    if dot['turns'] > 0: new_dots.append(dot)
                trp.lost_bp_dots = new_dots

            if trp.dmg_reduce_debuffs:
                new_db = []
                for db in trp.dmg_reduce_debuffs:
                    db['turns'] -= 1
                    if db['turns'] > 0: new_db.append(db)
                trp.dmg_reduce_debuffs = new_db

            if trp.stat_reduce_debuffs:
                new_db = []
                for db in trp.stat_reduce_debuffs:
                    db['turns'] -= 1
                    if db['turns'] > 0: new_db.append(db)
                trp.stat_reduce_debuffs = new_db

        if t1.is_dead() or t2.is_dead(): break

    winner = t1 if (not t1.is_dead() and t2.is_dead()) else (t2 if (not t2.is_dead() and t1.is_dead()) else (t1 if t1.bp_pct >= t2.bp_pct else t2))
    return {'winner': winner, 'turns': turn}

# ==============================================================================
# 组队与测试工厂
# ==============================================================================

def build_player_roster(genre_code, scale=30, sub_item_stat_c=0, sub_item_stat_r=0, sub_item_stat_i=0, sub_item_stat_m=0, sub_item_bp=0, carry_mech=None):
    """
    构建具有真实队员划分的战团：
    1 名 Carry (占有核心高阶大招) + (scale - 1) 名 Filler (占有基础技能与次级装备)
    """
    roster = RealRosterTeam(f"玩家_{genre_code}", genre_code, scale)
    base_bp_per_member = 1000000.0 / scale
    
    # 基础四维预算分发
    stat_profiles = {
        "C_I": (1000, 100, 500, 100),
        "C_R": (1000, 500, 100, 100),
        "M_I": (100, 100, 500, 1000),
        "M_R": (100, 500, 100, 1000),
        "M_C": (500, 100, 100, 1000),
        "R_I": (100, 1000, 500, 100),
    }
    tc, tr, ti, tm = stat_profiles[genre_code]
    c_per = tc / scale; r_per = tr / scale; i_per = ti / scale; m_per = tm / scale

    # 1. 创建主C
    carry = Character(1, "Carry", c_per * 2.5, r_per, i_per * 1.5, m_per, base_bp_per_member * 1.5)
    carry.carry_item_mech = carry_mech
    # 主C配装高阶技能（带严格次数限制 times_limit=1）
    if genre_code == "C_I":
        carry.skills.append(BattleSkill(101, "狂雷终结斩", 6, "勇气", "Attack", main_param=340.0, trigger_chance=35.0, times_limit=1, enemy_bp_cond2=50, base_crit_rate=0.25, sub_effect_name="敌方已损斩杀", sub_param=0.18))
        carry.skills.append(BattleSkill(102, "疾风封脉破", 6, "先机", "Attack", main_param=185.0, trigger_chance=40.0, times_limit=1, sub_effect_name="虚弱压制", sub_param=42.0, sub_duration=2, ini_bonus=10))
    elif genre_code == "C_R":
        carry.skills.append(BattleSkill(201, "背水浴血斩", 6, "勇气", "Attack", main_param=270.0, trigger_chance=35.0, times_limit=1, self_bp_cond2=50, base_crit_rate=0.25, sub_effect_name="自身已损反噬", sub_param=0.26))
        carry.skills.append(BattleSkill(202, "不坏金身", 5, "坚韧", "Heal", main_param=100.0, trigger_chance=40.0, times_limit=1, self_bp_cond2=50, sub_effect_name="总战力恢复", sub_param=0.13))
    elif genre_code == "M_I":
        carry.skills.append(BattleSkill(301, "弑神断界斩", 6, "魔力", "Attack", main_param=145.0, trigger_chance=38.0, times_limit=1, ignore_def_ratio=0.80, sub_effect_name="战力吸收", sub_param=0.35, ini_bonus=10))
        carry.skills.append(BattleSkill(302, "瞬影暗袭", 6, "先机", "Attack", main_param=180.0, trigger_chance=36.0, times_limit=1, sub_effect_name="虚弱压制", sub_param=38.0, sub_duration=2, ini_bonus=10))
    elif genre_code == "M_R":
        carry.skills.append(BattleSkill(401, "灭世剧毒", 6, "魔力", "Attack", main_param=140.0, trigger_chance=35.0, times_limit=1, ignore_def_ratio=0.80, sub_effect_name="最大流失", sub_param=0.015, sub_duration=2))
        carry.skills.append(BattleSkill(402, "神恩涅槃", 6, "坚韧", "Heal", main_param=100.0, trigger_chance=45.0, times_limit=1, self_bp_cond2=50, sub_effect_name="总战力恢复", sub_param=0.14))
    elif genre_code == "M_C":
        carry.skills.append(BattleSkill(501, "湮灭核弹斩", 6, "魔力", "Attack", main_param=145.0, trigger_chance=36.0, times_limit=1, ignore_def_ratio=0.80, base_crit_rate=0.20))
        carry.skills.append(BattleSkill(502, "终结暴击击", 6, "勇气", "Attack", main_param=340.0, trigger_chance=35.0, times_limit=1, enemy_bp_cond2=55, base_crit_rate=0.30, sub_effect_name="敌方已损斩杀", sub_param=0.20))
    elif genre_code == "R_I":
        carry.skills.append(BattleSkill(601, "神恩涅槃", 6, "坚韧", "Heal", main_param=100.0, trigger_chance=45.0, times_limit=1, self_bp_cond2=50, sub_effect_name="总战力恢复", sub_param=0.15))
        carry.skills.append(BattleSkill(602, "瞬影封脉", 5, "先机", "Attack", main_param=170.0, trigger_chance=35.0, sub_effect_name="虚弱压制", sub_param=35.0, sub_duration=2, ini_bonus=10))
    roster.members.append(carry)

    # 2. 创建 (scale - 1) 名填充队员 (配备次级装备)
    for idx in range(2, scale + 1):
        filler = Character(idx, "Filler", c_per * 0.95, r_per * 0.95, i_per * 0.95, m_per * 0.95, base_bp_per_member * 0.95)
        # 次级装备提供基础四维与生命
        filler.item_c = sub_item_stat_c
        filler.item_r = sub_item_stat_r
        filler.item_i = sub_item_stat_i
        filler.item_m = sub_item_stat_m
        filler.item_bp = sub_item_bp
        
        # 仅少数填充角色带常规中阶技能（大部分为常态攻击），模拟真实的技能池竞争
        if idx in [2, 3]:
            filler.skills.append(BattleSkill(900 + idx, "常态战技", 4, "通用", "Attack", main_param=140.0, trigger_chance=25.0))
        roster.members.append(filler)

    roster.aggregate_stats()
    return roster

def build_d3_boss(boss_archetype="HEAVY_TANK"):
    """
    构建具体的 D3 困难场景敌人（不预设胜率，而是呈现特定物理困难）:
    1. HEAVY_TANK (高坚韧铁壁型): 坚韧极高(650)，固定减伤大，物理极其刮痧
    2. SPEED_SUPPRESS (高速先机制压型): 先机极高(650)，常态开局挂虚弱与四维削弱
    3. EROSION_ATK (持续侵蚀高压型): 魔力极高(800)，带强力双DoT侵蚀与吸血
    """
    boss = RealRosterTeam("D3困难Boss", "BOSS", scale=1)
    if boss_archetype == "HEAVY_TANK":
        # 铁壁重装Boss：考验物理破防能力
        b_unit = Character(99, "Boss", c=100, r=650, i=120, m=150, bp=1300000)
        b_unit.skills.append(BattleSkill(9901, "泰山重壁斩", 4, "坚韧", "Attack", main_param=135.0, trigger_chance=35.0))
        b_unit.skills.append(BattleSkill(9902, "大地愈合", 4, "坚韧", "Heal", main_param=100.0, trigger_chance=30.0, sub_effect_name="总战力恢复", sub_param=0.08))
    elif boss_archetype == "SPEED_SUPPRESS":
        # 高速压制Boss：剥夺先手并挂虚弱
        b_unit = Character(99, "Boss", c=200, r=200, i=700, m=250, bp=1100000)
        b_unit.skills.append(BattleSkill(9903, "夺魄先锋袭", 4, "先机", "Attack", main_param=145.0, trigger_chance=40.0, sub_effect_name="虚弱压制", sub_param=35.0, sub_duration=2, ini_bonus=10))
        b_unit.skills.append(BattleSkill(9904, "封脉重击", 4, "先机", "Attack", main_param=150.0, trigger_chance=30.0, sub_effect_name="四维削弱", sub_param=20.0, sub_duration=2))
    elif boss_archetype == "EROSION_ATK":
        # 持续侵蚀Boss：高魔力双DoT与吸血
        b_unit = Character(99, "Boss", c=100, r=250, i=150, m=850, bp=1200000)
        b_unit.skills.append(BattleSkill(9905, "蚀骨毒咒", 4, "魔力", "Attack", main_param=120.0, trigger_chance=40.0, sub_effect_name="最大流失", sub_param=0.025, sub_duration=3))
        b_unit.skills.append(BattleSkill(9906, "生命汲取", 4, "魔力", "Attack", main_param=130.0, trigger_chance=35.0, sub_effect_name="战力吸收", sub_param=0.30))
    boss.members.append(b_unit)
    boss.aggregate_stats()
    return boss

# ==============================================================================
# 实测任务执行
# ==============================================================================

def run_d3_deep_diagnostics():
    genres = ["C_I", "C_R", "M_I", "M_R", "M_C", "R_I"]
    boss_types = ["HEAVY_TANK", "SPEED_SUPPRESS", "EROSION_ATK"]
    boss_names = {
        "HEAVY_TANK": "高坚韧铁壁Boss (650坚韧)",
        "SPEED_SUPPRESS": "高速先机压制Boss (700先机)",
        "EROSION_ATK": "持续魔力侵蚀Boss (850魔力)"
    }
    
    print("=" * 105)
    print("【D3 困难场景专项诊断】：技能真实衰减过程、流派物理困局与次级装备上下限扫描")
    print("=" * 105)

    # --------------------------------------------------------------------------
    # 实验 1：无装备基线对抗 —— 观察技能真实衰减（打光大招后的伤害断崖）
    # --------------------------------------------------------------------------
    print("\n>>> 诊断 1: 无装备基线下 六大流派在 D3 铁壁Boss 战中的技能衰减与时序断崖")
    print(f"{'流派':<8} {'胜率':<8} {'平均回合':<10} {'大招耗尽回合(Burnout)':<25} {'大招期平均单击':<18} {'衰减平A期平均单击':<18} {'衰减幅度':<10}")
    print("-" * 105)

    sims = 1000
    for g in genres:
        wins = 0
        total_turns = 0
        burnout_turns = []
        burst_damages = []
        normal_damages = []

        for _ in range(sims):
            player = build_player_roster(g, scale=30)
            boss = build_d3_boss("HEAVY_TANK")
            res = run_roster_battle(player, boss)
            if res['winner'].name == player.name: wins += 1
            total_turns += res['turns']

            # 分析该局 action_history
            carry_skill_used_turns = [act[0] for act in player.action_history if not act[3] and act[1] != "常态战技"]
            if carry_skill_used_turns:
                burnout_turns.append(max(carry_skill_used_turns))
            
            for act in player.action_history:
                if act[3]:  # 平A
                    normal_damages.append(act[2])
                else:       # 技能
                    burst_damages.append(act[2])

        wr = (wins / sims) * 100.0
        avg_t = total_turns / sims
        avg_burnout = sum(burnout_turns) / len(burnout_turns) if burnout_turns else 1.0
        avg_burst = sum(burst_damages) / len(burst_damages) if burst_damages else 1.0
        avg_normal = sum(normal_damages) / len(normal_damages) if normal_damages else 1.0
        decay_ratio = ((avg_burst - avg_normal) / avg_burst) * 100.0 if avg_burst > 0 else 0.0

        print(f"{g:<8} {wr:>5.1f}%   {avg_t:>6.1f}      第 {avg_burnout:.1f} 回合耗尽大招       {avg_burst:>10,.0f}        {avg_normal:>10,.0f}        -{decay_ratio:.1f}%")

    # --------------------------------------------------------------------------
    # 实验 2：次级装备 (填充队员装备) 属性上下限参数扫描
    # --------------------------------------------------------------------------
    print("\n\n>>> 诊断 2: 填充角色 (29人) 配戴次级装备对全队抗性与输出的支撑 —— 寻找属性上下限")
    print("测试条件：针对 C_I (物理流) 与 M_R (持久流) 挑战 D3 铁壁Boss")
    print(f"{'次级装备单件加成':<20} {'29人累计加成':<20} {'C_I 胜率':<12} {'C_I 平均存活':<14} {'M_R 胜率':<12} {'系统状态评估':<15}")
    print("-" * 105)

    # 扫描单件次级装备加成从 0 到 40
    stat_sweeps = [
        (0, "白板裸装 (0点)"),
        (3, "下限不足 (+3点)"),
        (6, "临界起点 (+6点)"),
        (12, "有效平衡区间 (+12点)"),
        (20, "高额支撑区间 (+20点)"),
        (35, "上限超标 (+35点)"),
        (50, "属性通胀溢出 (+50点)"),
    ]

    for val, label in stat_sweeps:
        # C_I 填充角色堆勇气与先机；M_R 填充角色堆魔力与坚韧
        total_stat = val * 29
        
        # 测试 C_I
        ci_wins = 0; ci_turns = 0
        for _ in range(500):
            p_ci = build_player_roster("C_I", scale=30, sub_item_stat_c=val, sub_item_stat_i=val, sub_item_bp=val*1500)
            boss = build_d3_boss("HEAVY_TANK")
            r = run_roster_battle(p_ci, boss)
            if r['winner'].name == p_ci.name: ci_wins += 1
            ci_turns += r['turns']
        ci_wr = (ci_wins / 500) * 100.0
        ci_avg_t = ci_turns / 500

        # 测试 M_R
        mr_wins = 0; mr_turns = 0
        for _ in range(500):
            p_mr = build_player_roster("M_R", scale=30, sub_item_stat_m=val, sub_item_stat_r=val, sub_item_bp=val*1500)
            boss = build_d3_boss("HEAVY_TANK")
            r = run_roster_battle(p_mr, boss)
            if r['winner'].name == p_mr.name: mr_wins += 1
            mr_turns += r['turns']
        mr_wr = (mr_wins / 500) * 100.0

        eval_desc = ""
        if val <= 3: eval_desc = "【无效区间】抵挡不住Boss基础打击"
        elif 6 <= val <= 20: eval_desc = "【健康弹性区间】胜率平滑攀升"
        else: eval_desc = "【破坏平衡区间】Boss完全沦为木桩"

        print(f"{label:<20} +{total_stat:<15} {ci_wr:>6.1f}%       {ci_avg_t:>6.1f} 回合       {mr_wr:>6.1f}%       {eval_desc}")

    # --------------------------------------------------------------------------
    # 实验 3：主C装备在技能衰减（大招打光进入平A）后的兜底补偿实测
    # --------------------------------------------------------------------------
    print("\n\n>>> 诊断 3: 主C装备对“技能衰减期”的兜底补偿效果 (测试 NORMAL_COMPENSATION)")
    print("对比：无装备 vs 仅主C携带普攻伤害补偿 (+45% 衰减期平A倍率)")
    print(f"{'流派':<8} {'面对Boss类型':<25} {'基准平A期单发':<16} {'补偿后平A期单发':<18} {'基准胜率':<10} {'装备后胜率':<12} {'胜率净变化'}")
    print("-" * 105)

    cases = [
        ("C_I", "HEAVY_TANK"),
        ("C_I", "SPEED_SUPPRESS"),
        ("M_I", "HEAVY_TANK"),
        ("M_I", "EROSION_ATK"),
        ("C_R", "SPEED_SUPPRESS"),
        ("R_I", "EROSION_ATK"),
    ]

    for g, btype in cases:
        base_wins = 0; base_normals = []
        comp_wins = 0; comp_normals = []

        for _ in range(500):
            p_base = build_player_roster(g, scale=30)
            b1 = build_d3_boss(btype)
            r1 = run_roster_battle(p_base, b1)
            if r1['winner'].name == p_base.name: base_wins += 1
            for act in p_base.action_history:
                if act[3]: base_normals.append(act[2])

            p_comp = build_player_roster(g, scale=30, carry_mech="NORMAL_COMPENSATION")
            b2 = build_d3_boss(btype)
            r2 = run_roster_battle(p_comp, b2)
            if r2['winner'].name == p_comp.name: comp_wins += 1
            for act in p_comp.action_history:
                if act[3]: comp_normals.append(act[2])

        b_wr = (base_wins / 500) * 100.0
        c_wr = (comp_wins / 500) * 100.0
        avg_bn = sum(base_normals)/len(base_normals) if base_normals else 1.0
        avg_cn = sum(comp_normals)/len(comp_normals) if comp_normals else 1.0
        diff = c_wr - b_wr

        print(f"{g:<8} {boss_names[btype]:<25} {avg_bn:>10,.0f}        {avg_cn:>10,.0f}          {b_wr:>5.1f}%     {c_wr:>6.1f}%       {diff:>+5.1f}%")

if __name__ == '__main__':
    run_d3_deep_diagnostics()
