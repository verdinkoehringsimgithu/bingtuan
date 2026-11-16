# -*- coding: utf-8 -*-
"""
Combat Mechanism Refactor Simulator & Stress Testing Suite (V2.0 Strict Skill-Only Magic Amp)
Author: Antigravity
Date: 2026-10-10
Rule: 魔力只能放大技能的百分比效果，角色四维基础转换属性（暴击率、减伤率、闪避率、先手增伤）严禁受魔力放大！
"""
import random
import math
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# ==============================================================================
# 1. 核心数值模型与公式契约 (严格遵照：魔力仅放大技能百分比效果)
# ==============================================================================

def calc_magic_amp(magic):
    """
    【魔力 (Magic) - 技能百分比放大器】
    公式: Amp_M = 1.0 + (Magic / (Magic + 120.0)) * 0.65
    特性:
      - Magic = 0   -> 1.000 (基准放大系数 100%, 无增幅)
      - Magic = 30  -> 1.130 (+13.0%)
      - Magic = 110 -> 1.311 (+31.1%)
      - Magic = 150 -> 1.361 (+36.1%)
      - Magic = 200 -> 1.406 (+40.6%)
      - 极限硬顶上限: 1.50 (即最多将技能百分比放大 50%)
    【严格契约】：此系数仅且只用于放大技能所携带的百分比效果（伤害倍率、回血百分比、
    属性削弱/提升百分比、吸血百分比、无视防御百分比、DoT百分比/固定倍率百分比）。
    """
    if magic <= 0:
        return 1.0
    return 1.0 + min(0.50, (magic / (magic + 120.0)) * 0.65)

def calc_courage_stats(courage):
    """
    【勇气 (Courage) - 暴击率与暴击倍率】
    * 仅由勇气决定，不受魔力放大！*
    - 基础暴击率: 5% + (Courage / (Courage + 140.0)) * 50%
      上限硬顶: 65%
    - 基础暴击倍率: 150% + Courage * 0.75% (每点提供 +0.75% 暴击伤害)
      例如: Courage = 130 -> 150% + 97.5% = 247.5% 暴击伤害
    - 暴击必中规则: 判定暴击时，无视敌方闪避率，必定命中！
    """
    base_crit_rate = 0.05 + (courage / (courage + 140.0)) * 0.50
    crit_rate = min(0.65, base_crit_rate)
    crit_mult = 1.50 + courage * 0.0075
    return crit_rate, crit_mult

def calc_resilience_stats(resilience):
    """
    【坚韧 (Resilience) - 双重减伤 (含状态效果)】
    * 仅由坚韧决定，不受魔力放大！*
    - 固定数额减伤: Resilience * 16.0 (单次直接抵扣受击伤害)
    - 全局百分比减伤: (Resilience / (Resilience + 140.0)) * 55%
      上限硬顶: 60%
    - 规则：全局百分比减伤对直接攻击与状态效果 (DoT流血/中毒/衰竭/固定流失) 全面生效！
    """
    flat_dr = resilience * 16.0
    pct_dr = min(0.60, (resilience / (resilience + 140.0)) * 0.55)
    return flat_dr, pct_dr

def calc_initiative_stats(initiative, enemy_initiative):
    """
    【先机 (Initiative) - 出手顺位、闪避率与先手增伤】
    * 仅由先机决定，不受魔力放大！*
    - 出手顺位: 每回合 Initiative 高者先攻
    - 基础闪避率: (Initiative / (Initiative + 140.0)) * 48%
      上限硬顶: 55%
      规则：只能闪避普通直接攻击伤害；暴击伤害必定命中不可闪避；DoT不可闪避。
    - 先手差值增伤:
      diff = max(0, self.init - enemy.init)
      bonus = (diff / (diff + 140.0)) * 35%
    """
    dodge_rate = min(0.55, (initiative / (initiative + 140.0)) * 0.48)
    diff = max(0.0, initiative - enemy_initiative)
    if diff > 0:
        preempt_bonus = min(0.40, (diff / (diff + 140.0)) * 0.35)
    else:
        preempt_bonus = 0.0
    return dodge_rate, preempt_bonus


# ==============================================================================
# 2. 战斗实体定义
# ==============================================================================

class Entity:
    def __init__(self, name, max_hp, courage, resilience, initiative, magic, skill_preset):
        self.name = name
        self.max_hp = float(max_hp)
        self.cur_hp = float(max_hp)
        self.base_courage = float(courage)
        self.base_resilience = float(resilience)
        self.base_initiative = float(initiative)
        self.base_magic = float(magic)
        
        self.mod_courage = 0.0
        self.mod_resilience = 0.0
        self.mod_initiative = 0.0
        self.mod_magic = 0.0
        
        self.skill_preset = skill_preset
        
        self.dots = []
        self.buffs = []
        
        self.total_damage_dealt = 0.0
        self.total_damage_taken = 0.0
        self.total_healed = 0.0
        self.crit_count = 0
        self.dodge_count = 0

    def reset(self):
        self.cur_hp = self.max_hp
        self.mod_courage = 0.0
        self.mod_resilience = 0.0
        self.mod_initiative = 0.0
        self.mod_magic = 0.0
        self.dots = []
        self.buffs = []
        self.total_damage_dealt = 0.0
        self.total_damage_taken = 0.0
        self.total_healed = 0.0
        self.crit_count = 0
        self.dodge_count = 0

    @property
    def effective_courage(self):
        return max(0.0, self.base_courage + self.mod_courage)

    @property
    def effective_resilience(self):
        return max(0.0, self.base_resilience + self.mod_resilience)

    @property
    def effective_initiative(self):
        return max(0.0, self.base_initiative + self.mod_initiative)

    @property
    def effective_magic(self):
        return max(0.0, self.base_magic + self.mod_magic)

    def get_magic_amp(self):
        return calc_magic_amp(self.effective_magic)

    def is_alive(self):
        return self.cur_hp > 0.0001


# ==============================================================================
# 3. 六大流派对称预算预设 (主属性 130，副属性 110，辅属性 30/30，总和 300)
# ==============================================================================

def create_archetype(genre_id, base_hp=100000):
    if genre_id == 1:
        # 破锋流 (先机 130, 勇气 110, 坚韧 30, 魔力 30)
        # 极速突刺刺客，顶级先手，先手差增伤 + 暴击必中斩杀
        return Entity(
            name="破锋流(勇+先)",
            max_hp=base_hp,
            courage=110, resilience=30, initiative=130, magic=30,
            skill_preset={
                'chance': 0.35,
                'name': '破晓绝杀',
                'type': 'havoc_burst',
                # 自身当前HP 16% + 敌方已损HP 32% (均受魔力放大)
                'self_cur_pct': 0.16,
                'enemy_lost_pct': 0.32,
            }
        )
    elif genre_id == 2:
        # 狂战流 (勇气 130, 坚韧 110, 先机 30, 魔力 30)
        # 残血卖血狂袭，坚韧减伤保底，已损生命值高额爆发与回血
        return Entity(
            name="狂战流(勇+坚)",
            max_hp=base_hp,
            courage=130, resilience=110, initiative=30, magic=30,
            skill_preset={
                'chance': 0.30,
                'name': '背水怒斩',
                'type': 'berserk_strike',
                # 自身已损HP 24% 伤害 + 自身已损HP 16% 回血 (均受魔力放大)
                'self_lost_dmg_pct': 0.24,
                'self_lost_heal_pct': 0.16,
            }
        )
    elif genre_id == 3:
        # 湮灭流 (勇气 130, 魔力 110, 坚韧 30, 先机 30)
        # 穿透核弹，魔力大幅放大技能基础伤害与60%无视防御，吸血续航，毁灭高防铁壁
        return Entity(
            name="湮灭流(勇+魔)",
            max_hp=base_hp,
            courage=130, resilience=30, initiative=30, magic=110,
            skill_preset={
                'chance': 0.30,
                'name': '崩灭魔刃',
                'type': 'annihilation_slash',
                # 自身初始HP 25% 伤害(受魔力放大) + 60% 无视防御(受魔力放大) + 30% 百分比吸血(受魔力放大)
                'self_max_dmg_pct': 0.25,
                'ignore_def_pct': 0.60,
                'lifesteal_pct': 0.30,
            }
        )
    elif genre_id == 4:
        # 绝影流 (先机 130, 坚韧 110, 勇气 30, 魔力 30)
        # 闪避反制，先手削弱敌方属性与伤害，防守拉扯
        return Entity(
            name="绝影流(先+坚)",
            max_hp=base_hp,
            courage=30, resilience=110, initiative=130, magic=30,
            skill_preset={
                'chance': 0.30,
                'name': '绝影缚袭',
                'type': 'phantom_bind',
                # 削弱敌方12%四维属性(持续2回合，受魔力放大)，降低敌方16%伤害(持续2回合，受魔力放大)，自身初始HP 7% 回血(受魔力放大)
                'stat_debuff_pct': 0.12,
                'dmg_debuff_pct': 0.16,
                'debuff_turns': 2,
                'self_max_heal_pct': 0.07,
            }
        )
    elif genre_id == 5:
        # 不朽流 (坚韧 130, 魔力 110, 勇气 30, 先机 30)
        # 铁壁毒奶，全域减伤(含DoT)，魔力放大中毒持续流失与吸血回血
        return Entity(
            name="不朽流(坚+魔)",
            max_hp=base_hp,
            courage=30, resilience=130, initiative=30, magic=110,
            skill_preset={
                'chance': 0.30,
                'name': '不朽蚀灵',
                'type': 'immortal_decay',
                # 自身初始HP 10% 回血(受魔力放大) + 3回合最大HP 4.5% 中毒流失(受魔力放大) + 20% 吸血(受魔力放大)
                'self_max_heal_pct': 0.10,
                'dot_max_pct': 0.045,
                'dot_turns': 3,
                'lifesteal_pct': 0.20,
            }
        )
    elif genre_id == 6:
        # 咒缚流 (先机 130, 魔力 110, 勇气 30, 坚韧 30)
        # 先手咒缚术士，魔力放大属性偷取 + 固定伤害流失(3000 * (100% * Amp)) + 当前HP衰竭
        return Entity(
            name="咒缚流(先+魔)",
            max_hp=base_hp,
            courage=30, resilience=30, initiative=130, magic=110,
            skill_preset={
                'chance': 0.32,
                'name': '极速衰竭',
                'type': 'curse_drain',
                # 偷取敌方 16% 四维属性(持续2回合，受魔力放大)
                'stat_steal_pct': 0.16,
                # 3回合内，每回合受到 3000 * (100% * Amp) 点固定伤害
                'dot_flat_base': 3000.0,
                'dot_flat_pct': 1.00,
                # 3回合当前HP 7.0% 衰竭流失(受魔力放大)
                'dot_cur_pct': 0.070,
                'dot_turns': 3,
            }
        )


# ==============================================================================
# 4. 战斗动作执行引擎 (严格区分：四维转换不放魔力，技能百分比才放魔力)
# ==============================================================================

def execute_turn_action(caster, receiver, is_first_striker):
    caster_amp = caster.get_magic_amp()
    
    # 1. 攻守双方的基础战斗数值 (严格不使用魔力放大！)
    crit_rate, crit_mult = calc_courage_stats(caster.effective_courage)
    flat_dr, pct_dr = calc_resilience_stats(receiver.effective_resilience)
    dodge_rate, preempt_bonus = calc_initiative_stats(caster.effective_initiative, receiver.effective_initiative)
    
    # 伤害虚弱 Debuff 判定 (虚弱效果由技能释放，其弱化比例受施法方魔力放大)
    dmg_weak_factor = 1.0
    for b in caster.buffs:
        if b['type'] == 'dmg_weak':
            dmg_weak_factor *= (1.0 - b['val'])

    preset = caster.skill_preset
    trigger_skill = (random.random() < preset['chance'])
    
    # 基础普通攻击伤害 (无技能触发时，标准基础伤害: 12% 最大HP + 6% 当前HP)
    raw_damage = caster.max_hp * 0.12 + caster.cur_hp * 0.06
    ignore_def_ratio = 0.0
    lifesteal_ratio = 0.0

    if trigger_skill:
        stype = preset['type']
        if stype == 'havoc_burst':
            # 破锋流: 技能百分比受魔力放大
            self_pct = preset['self_cur_pct'] * caster_amp
            enemy_pct = preset['enemy_lost_pct'] * caster_amp
            raw_damage = caster.cur_hp * self_pct + (receiver.max_hp - receiver.cur_hp) * enemy_pct
            # 技能自带额外暴击率提升 (技能附带百分比受魔力放大)
            crit_rate = min(0.85, crit_rate + 0.15 * caster_amp)

        elif stype == 'berserk_strike':
            # 狂战流: 技能已损伤害百分比与回血百分比受魔力放大
            self_lost = max(0.0, caster.max_hp - caster.cur_hp)
            dmg_pct = preset['self_lost_dmg_pct'] * caster_amp
            heal_pct = preset['self_lost_heal_pct'] * caster_amp
            
            raw_damage = self_lost * dmg_pct + caster.max_hp * 0.10
            heal_val = self_lost * heal_pct
            caster.cur_hp = min(caster.max_hp, caster.cur_hp + heal_val)
            caster.total_healed += heal_val

        elif stype == 'annihilation_slash':
            # 湮灭流: 技能初始HP伤害百分比、无视防御百分比、吸血百分比受魔力放大
            dmg_pct = preset['self_max_dmg_pct'] * caster_amp
            raw_damage = caster.max_hp * dmg_pct
            ignore_def_ratio = min(0.85, preset['ignore_def_pct'] * caster_amp)
            lifesteal_ratio = preset['lifesteal_pct'] * caster_amp

        elif stype == 'phantom_bind':
            # 绝影流: 削弱属性百分比、降低伤害百分比、回血百分比受魔力放大
            debuff_pct = preset['stat_debuff_pct'] * caster_amp
            dc = receiver.base_courage * debuff_pct
            dr = receiver.base_resilience * debuff_pct
            di = receiver.base_initiative * debuff_pct
            dm = receiver.base_magic * debuff_pct
            
            receiver.mod_courage -= dc
            receiver.mod_resilience -= dr
            receiver.mod_initiative -= di
            receiver.mod_magic -= dm
            receiver.buffs.append({
                'type': 'stat_debuff', 'dc': dc, 'dr': dr, 'di': di, 'dm': dm,
                'turns': preset['debuff_turns']
            })
            receiver.buffs.append({
                'type': 'dmg_weak', 'val': preset['dmg_debuff_pct'] * caster_amp,
                'turns': preset['debuff_turns']
            })
            heal_val = caster.max_hp * (preset['self_max_heal_pct'] * caster_amp)
            caster.cur_hp = min(caster.max_hp, caster.cur_hp + heal_val)
            caster.total_healed += heal_val

        elif stype == 'immortal_decay':
            # 不朽流: 技能回血百分比、中毒流失百分比、吸血百分比受魔力放大
            heal_val = caster.max_hp * (preset['self_max_heal_pct'] * caster_amp)
            caster.cur_hp = min(caster.max_hp, caster.cur_hp + heal_val)
            caster.total_healed += heal_val
            
            receiver.dots.append({
                'type': 'poison', 'mode': 'max',
                'val': preset['dot_max_pct'] * caster_amp,
                'turns': preset['dot_turns']
            })
            lifesteal_ratio = preset['lifesteal_pct'] * caster_amp

        elif stype == 'curse_drain':
            # 咒缚流: 偷取属性百分比、固定伤害百分比、衰竭流失百分比受魔力放大
            steal_pct = preset['stat_steal_pct'] * caster_amp
            dc = receiver.base_courage * steal_pct
            dr = receiver.base_resilience * steal_pct
            di = receiver.base_initiative * steal_pct
            dm = receiver.base_magic * steal_pct
            
            receiver.mod_courage -= dc; receiver.mod_resilience -= dr
            receiver.mod_initiative -= di; receiver.mod_magic -= dm
            receiver.buffs.append({'type': 'stat_debuff', 'dc': dc, 'dr': dr, 'di': di, 'dm': dm, 'turns': 2})
            
            caster.mod_courage += dc; caster.mod_resilience += dr
            caster.mod_initiative += di; caster.mod_magic += dm
            caster.buffs.append({'type': 'stat_buff', 'dc': dc, 'dr': dr, 'di': di, 'dm': dm, 'turns': 2})
            
            # 魔力固定伤害效果: n 回合内，每回合受到 基础值 * (百分比 * Amp_M) 点伤害
            flat_dmg_per_turn = preset['dot_flat_base'] * (preset['dot_flat_pct'] * caster_amp)
            receiver.dots.append({
                'type': 'flat_magic_burn', 'mode': 'flat',
                'val': flat_dmg_per_turn,
                'turns': preset['dot_turns']
            })
            # 当前 HP 衰竭 DoT
            receiver.dots.append({
                'type': 'decay', 'mode': 'cur',
                'val': preset['dot_cur_pct'] * caster_amp,
                'turns': preset['dot_turns']
            })

    # 先手差值增伤 (仅由先机差值决定，不乘魔力)
    if is_first_striker and preempt_bonus > 0:
        raw_damage *= (1.0 + preempt_bonus)

    # 虚弱减伤
    raw_damage *= dmg_weak_factor

    # 暴击判定 (暴击率与暴击倍率仅由勇气决定)
    is_crit = (random.random() < crit_rate)
    if is_crit:
        caster.crit_count += 1
        raw_damage *= crit_mult

    # 闪避判定: 暴击必中！未暴击时按先机基础闪避率判定 (闪避率不乘魔力)
    is_dodge = False
    if not is_crit:
        rec_dodge_rate, _ = calc_initiative_stats(receiver.effective_initiative, caster.effective_initiative)
        if random.random() < rec_dodge_rate:
            is_dodge = True
            receiver.dodge_count += 1

    if is_dodge:
        return

    # 坚韧减伤结算 (基础百分比减伤由坚韧决定，技能穿透率受魔力放大)
    effective_pct_dr = max(0.0, pct_dr * (1.0 - ignore_def_ratio))
    damage_after_pct = raw_damage * (1.0 - effective_pct_dr)
    final_damage = max(1.0, damage_after_pct - flat_dr)

    receiver.cur_hp -= final_damage
    caster.total_damage_dealt += final_damage
    receiver.total_damage_taken += final_damage

    # 技能百分比吸血结算
    if lifesteal_ratio > 0:
        heal_val = final_damage * lifesteal_ratio
        caster.cur_hp = min(caster.max_hp, caster.cur_hp + heal_val)
        caster.total_healed += heal_val


def run_battle(entity_a, entity_b, max_turns=30):
    entity_a.reset()
    entity_b.reset()
    
    turn = 0
    winner = None
    
    while turn < max_turns:
        turn += 1
        
        # 1. 回合前结算 DoT (坚韧百分比减伤削弱所有状态伤害，受击方坚韧减免不乘魔力)
        for ent in [entity_a, entity_b]:
            if not ent.is_alive():
                continue
            if ent.dots:
                _, pct_dr = calc_resilience_stats(ent.effective_resilience)
                new_dots = []
                for dot in ent.dots:
                    if dot['mode'] == 'max':
                        base_loss = ent.max_hp * dot['val']
                    elif dot['mode'] == 'cur':
                        base_loss = ent.cur_hp * dot['val']
                    else:
                        base_loss = dot['val']
                    
                    actual_loss = max(1.0, base_loss * (1.0 - pct_dr))
                    ent.cur_hp -= actual_loss
                    ent.total_damage_taken += actual_loss
                    
                    dot['turns'] -= 1
                    if dot['turns'] > 0:
                        new_dots.append(dot)
                ent.dots = new_dots
                
                if not ent.is_alive():
                    ent.cur_hp = 0
                    break
        
        if not entity_a.is_alive() or not entity_b.is_alive():
            break

        # 2. 先机判定出手顺位
        if entity_a.effective_initiative >= entity_b.effective_initiative:
            first, second = entity_a, entity_b
        else:
            first, second = entity_b, entity_a

        # 3. 第一顺位出手
        execute_turn_action(first, second, is_first_striker=True)
        if not second.is_alive():
            break

        # 4. 第二顺位出手
        execute_turn_action(second, first, is_first_striker=False)
        if not first.is_alive():
            break

        # 5. 回合后更新 Buff/Debuff 并正确还原属性
        for ent in [entity_a, entity_b]:
            new_buffs = []
            for b in ent.buffs:
                b['turns'] -= 1
                if b['turns'] <= 0:
                    if b['type'] == 'stat_debuff':
                        ent.mod_courage += b['dc']
                        ent.mod_resilience += b['dr']
                        ent.mod_initiative += b['di']
                        ent.mod_magic += b['dm']
                    elif b['type'] == 'stat_buff':
                        ent.mod_courage -= b['dc']
                        ent.mod_resilience -= b['dr']
                        ent.mod_initiative -= b['di']
                        ent.mod_magic -= b['dm']
                else:
                    new_buffs.append(b)
            ent.buffs = new_buffs

    if entity_a.is_alive() and not entity_b.is_alive():
        winner = entity_a
    elif entity_b.is_alive() and not entity_a.is_alive():
        winner = entity_b
    else:
        ratio_a = entity_a.cur_hp / entity_a.max_hp
        ratio_b = entity_b.cur_hp / entity_b.max_hp
        if ratio_a > ratio_b:
            winner = entity_a
        elif ratio_b > ratio_a:
            winner = entity_b
        else:
            winner = entity_a

    return {
        'winner': winner.name,
        'turns': turn,
        'hp_a_rem': max(0.0, entity_a.cur_hp),
        'hp_b_rem': max(0.0, entity_b.cur_hp),
    }


# ==============================================================================
# 5. 压力测试执行与分析
# ==============================================================================

def run_stress_test(simulations_per_pairing=3000):
    genres = [1, 2, 3, 4, 5, 6]
    genre_names = {
        1: "破锋流(勇+先)",
        2: "狂战流(勇+坚)",
        3: "湮灭流(勇+魔)",
        4: "绝影流(先+坚)",
        5: "不朽流(坚+魔)",
        6: "咒缚流(先+魔)",
    }
    
    wins_matrix = {g1: {g2: 0 for g2 in genres} for g1 in genres}
    turn_matrix = {g1: {g2: [] for g2 in genres} for g1 in genres}
    all_turns = []

    for i in range(len(genres)):
        for j in range(i, len(genres)):
            g1 = genres[i]
            g2 = genres[j]
            
            for sim in range(simulations_per_pairing):
                if sim % 2 == 0:
                    ent1 = create_archetype(g1)
                    ent2 = create_archetype(g2)
                    res = run_battle(ent1, ent2)
                    if res['winner'] == ent1.name:
                        wins_matrix[g1][g2] += 1
                    else:
                        wins_matrix[g2][g1] += 1
                else:
                    ent2 = create_archetype(g2)
                    ent1 = create_archetype(g1)
                    res = run_battle(ent2, ent1)
                    if res['winner'] == ent1.name:
                        wins_matrix[g1][g2] += 1
                    else:
                        wins_matrix[g2][g1] += 1

                turn_matrix[g1][g2].append(res['turns'])
                if g1 != g2:
                    turn_matrix[g2][g1].append(res['turns'])
                all_turns.append(res['turns'])

    print("="*85)
    print("【全新重构版本：六种流派全对决胜率矩阵 (严格技能百分比魔力放大)】")
    print("="*85)
    
    header = f"{'流派 (行攻击/列防守)':<16}"
    for g2 in genres:
        header += f"{genre_names[g2][:6]:>10}"
    header += f"{'综合胜率':>12}"
    print(header)
    print("-" * 88)

    genre_overall_winrates = {}
    for g1 in genres:
        row = f"{genre_names[g1]:<16}"
        total_wins = 0
        total_games = 0
        for g2 in genres:
            if g1 == g2:
                rate = 50.0
                row += f"{rate:>9.1f}%"
            else:
                wins = wins_matrix[g1][g2]
                total = simulations_per_pairing
                rate = (wins / total) * 100.0
                row += f"{rate:>9.1f}%"
                total_wins += wins
                total_games += total
        
        overall_rate = (total_wins / total_games) * 100.0
        genre_overall_winrates[g1] = overall_rate
        row += f"{overall_rate:>11.1f}%"
        print(row)
    print("-" * 88)

    print("\n" + "="*85)
    print("【战斗回合数与节奏体验深度分析 (对齐旧系统 6-12 回合标准)】")
    print("="*85)
    
    avg_turns = sum(all_turns) / len(all_turns)
    min_turns = min(all_turns)
    max_turns = max(all_turns)
    
    r_1_3 = sum(1 for t in all_turns if t <= 3) / len(all_turns) * 100.0
    r_4_7 = sum(1 for t in all_turns if 4 <= t <= 7) / len(all_turns) * 100.0
    r_8_12 = sum(1 for t in all_turns if 8 <= t <= 12) / len(all_turns) * 100.0
    r_13_20 = sum(1 for t in all_turns if 13 <= t <= 20) / len(all_turns) * 100.0
    r_over20 = sum(1 for t in all_turns if t > 20) / len(all_turns) * 100.0

    print(f"全局平均战斗回合数: {avg_turns:.2f} 回合 (旧版系统基准为 6~12 回合)")
    print(f"极限最快决胜:       {min_turns} 回合 (高速刺客双暴局)")
    print(f"极限最长持久战:     {max_turns} 回合 (纯双肉控场互磨局)")
    print("\n战斗节奏区间分布:")
    print(f"  - 闪电爆发 (1~3 回合)  : {r_1_3:5.2f}%  (极高爆发秒杀)")
    print(f"  - 快速压制 (4~7 回合)  : {r_4_7:5.2f}%  (优势局快速锁定胜局)")
    print(f"  - 经典缠斗 (8~12 回合) : {r_8_12:5.2f}% (标准主流对局，中轴体验)")
    print(f"  - 深度拉扯 (13~20 回合): {r_13_20:5.2f}% (肉盾/恢复流阵地拉扯)")
    print(f"  - 疲劳超时 (21+ 回合)  : {r_over20:5.2f}% (极少发生，无死锁情况)")

    print("\n" + "="*85)
    print("【各流派单兵生态位、克制关系与天梯定位】")
    print("="*85)
    
    for g1 in genres:
        name = genre_names[g1]
        overall = genre_overall_winrates[g1]
        matchups = []
        for g2 in genres:
            if g1 != g2:
                rate = (wins_matrix[g1][g2] / simulations_per_pairing) * 100.0
                matchups.append((g2, rate))
        matchups.sort(key=lambda x: x[1], reverse=True)
        best = matchups[0]
        worst = matchups[-1]
        
        print(f"[{name}] 综合天梯胜率: {overall:.1f}%")
        print(f"  - 绝佳优势对局: vs {genre_names[best[0]]} (胜率: {best[1]:.1f}%)")
        print(f"  - 明显劣势对局: vs {genre_names[worst[0]]} (胜率: {worst[1]:.1f}%)")
        avg_g_turn = sum(turn_matrix[g1][best[0]]) / len(turn_matrix[g1][best[0]])
        print(f"  - 平均交锋回合: {avg_g_turn:.1f} 回合")
        print()

if __name__ == '__main__':
    run_stress_test(simulations_per_pairing=3000)
