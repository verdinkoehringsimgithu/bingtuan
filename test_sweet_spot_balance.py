# -*- coding: utf-8 -*-
"""
Realistic Progression & PVE Balance Test
Focusing on:
1. PVE Punching Above Weight: Underdog player (360k BP) vs Boss (720k BP, 2x HP).
   - Resilience reduces percentage damage & DoT as intended.
   - Player must use synergy (True Damage + DoT + Survival) to achieve 25%~45% win rate.
   - Raw physical build fails (0%~5%).
2. Multi-stage Progression (5, 10, 15, 20, 25, 30):
   - Battle length converges to 6~10 turns.
   - Single-skill impact (Swing Ratio) is perceptible (12%~25% for regular, 30%~45% for burst) instead of meek (<8%).
3. Magic playstyles:
   - True Damage vs DoT comparison in both PVE and mirror battles.
"""
import random
import math
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# ------------------------------------------------------------------------------
# 1. 核心数学模型调校
# ------------------------------------------------------------------------------

def calc_resilience_dr(resilience):
    """
    坚韧免伤模型:
    - 坚韧提供全局百分比减伤，对【直接伤害】与【百分比伤害/DoT】全局生效！
    - 公式: pct_dr = 0.25 + (resilience / (resilience + 500.0)) * 0.45 (封顶 68%)
      R=100 -> 32.5%; R=250 -> 40.0%; R=500 -> 47.5%; R=700 -> 51.3%; R=1000 -> 55.0%
    - 固定减伤: flat_dr = resilience * 12.0
    """
    pct_dr = min(0.68, 0.25 + (resilience / (resilience + 500.0)) * 0.45)
    flat_dr = resilience * 12.0
    return flat_dr, pct_dr

def calc_magic_amp_responsive(magic):
    """
    非线性响应式魔力放大:
    前期提供清晰基底增益，中后期平稳收敛:
    M=50 -> 1.25x; M=150 -> 1.60x; M=300 -> 2.00x; M=500 -> 2.45x; M=1000 -> 3.20x
    """
    if magic <= 0: return 1.0
    return 1.0 + (magic / (magic + 280.0)) * 1.5 + (magic / 1400.0) * 0.7

def calc_courage_stats(courage):
    crit_rate = (courage / (courage + 750.0)) * 0.42
    crit_bonus = 0.35 + (courage / (courage + 700.0)) * 0.65
    return crit_rate, crit_bonus

def calc_initiative_stats(initiative, enemy_initiative):
    dodge_rate = min(0.30, (initiative / (initiative + 700.0)) * 0.35)
    diff = max(0.0, initiative - enemy_initiative)
    preempt_bonus = (diff / (diff + 600.0)) * 0.25 if diff > 0 else 0.0
    return dodge_rate, preempt_bonus


# ------------------------------------------------------------------------------
# 2. 实体与战斗执行
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
        self.death_defy = 0
        self.action_swings = []
        self.total_damage = 0.0
        self.true_damage = 0.0
        self.dot_damage = 0.0
        self.crit_damage = 0.0
        self.total_heal = 0.0
        self.dodge_count = 0

    def reset(self):
        self.current_bp = self.max_bp
        self.usage = {}
        self.max_bp_dots = []
        self.turn_end_dots = []
        self.buffs = []
        self.exhaust_turns = 0
        self.death_defy = 0
        self.action_swings = []
        self.total_damage = 0.0
        self.true_damage = 0.0
        self.dot_damage = 0.0
        self.crit_damage = 0.0
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

    def take_damage(self, raw, is_true, def_obj):
        flat_dr, pct_dr = calc_resilience_dr(self.resilience)
        if is_true:
            dmg = raw
        else:
            dmg = max(1.0, raw * (1.0 - pct_dr) - flat_dr)
        
        self.current_bp -= dmg
        if self.current_bp <= 0:
            if self.death_defy > 0:
                self.current_bp = 1.0
                self.death_defy -= 1
            else:
                self.current_bp = 0.0
        return dmg


def execute_turn_action(acting, defender, is_first, turn):
    # 基础战力打击基准: 0.15 MaxBP + 0.08 CurBP (温和基底，拉出 6~10 回合博弈)
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

    # 2. 暴击判定
    crit_boost = 0.10 if skill.genre == "勇气" else 0.0
    is_crit = (random.random() < min(0.95, c_crit_rate + crit_boost))

    # 3. 闪避判定 (暴击必中，未暴击受闪避判定)
    if not is_crit:
        if random.random() < dodge_rate:
            defender.dodge_count += 1
            return

    # 4. 主效果执行
    is_true = skill.is_true_damage or (skill.ignore_def_ratio * m_amp >= 0.90)
    mult = skill.main_param / 100.0
    if is_crit:
        mult += c_crit_bonus

    raw_dmg = base_power * mult * preempt_factor
    if acting.exhaust_turns > 0:
        raw_dmg = 1.0
        acting.exhaust_turns = 0

    if skill.main_type == "Heal":
        heal_val = 0.0
        eff = skill.sub_effect
        if eff == "self_max_heal":
            # 真实可感知的恢复: 基础 12%~18% (危机大急救可达 20%)
            heal_val = acting.max_bp * (skill.sub_param * m_amp)
        elif eff == "self_cur_heal":
            heal_val = acting.current_bp * (skill.sub_param * m_amp)
        acting.heal(heal_val)
        raw_dmg = base_power * 1.0  # 恢复技能附带 100% 普攻反击

    actual_dmg = defender.take_damage(raw_dmg, is_true, defender)
    acting.total_damage += actual_dmg
    if is_true: acting.true_damage += actual_dmg
    if is_crit: acting.crit_damage += actual_dmg

    # 5. 附加效果
    eff = skill.sub_effect
    if eff == "self_lost_dmg":
        lost = max(0.0, acting.max_bp - acting.current_bp)
        extra_raw = lost * (skill.sub_param * m_amp)
        extra_actual = defender.take_damage(extra_raw, is_true=True, def_obj=defender)
        acting.total_damage += extra_actual
        acting.true_damage += extra_actual
    elif eff == "enemy_cur_dmg":
        extra_raw = defender.current_bp * (skill.sub_param * m_amp)
        extra_actual = defender.take_damage(extra_raw, is_true=False, def_obj=defender)
        acting.total_damage += extra_actual
    elif eff == "dot_max":
        # 最大战力流失 (受对方坚韧百分比减免)
        defender.max_bp_dots.append({'val': skill.sub_param * m_amp, 'turns': skill.sub_duration})
    elif eff == "dot_lost":
        defender.turn_end_dots.append({'mode': 'lost', 'val': skill.sub_param * m_amp, 'turns': skill.sub_duration})
    elif eff == "combo_dot":
        defender.max_bp_dots.append({'val': skill.sub_param * m_amp, 'turns': skill.sub_duration})
        defender.turn_end_dots.append({'mode': 'flat', 'val': skill.sub_base * m_amp, 'turns': skill.sub_duration})

    if skill.exhaust_turns > 0:
        defender.exhaust_turns = max(defender.exhaust_turns, skill.exhaust_turns)

    # 记录该次技能造成的战力摆动幅度
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
                    if dot['turns'] > 0:
                        new_dots.append(dot)
                trp.max_bp_dots = new_dots

        if t1.is_dead() or t2.is_dead(): break

        # 交锋
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
                    if dot['turns'] > 0:
                        new_dots.append(dot)
                trp.turn_end_dots = new_dots

        if t1.is_dead() or t2.is_dead(): break

    winner = t1 if (not t1.is_dead() and t2.is_dead()) else (t2 if (not t2.is_dead() and t1.is_dead()) else (t1 if t1.bp_pct >= t2.bp_pct else t2))
    return {'winner': winner, 'turns': turn}


# ------------------------------------------------------------------------------
# 3. 执行全面综合检验
# ------------------------------------------------------------------------------

def test_pve_punching():
    print("=" * 95)
    print("【检验 A: 越级挑战攻坚验证 (15人 36万战力 挑战 72万战力 高防守门巨兽)】")
    print("Boss 特征: 72万战力 (2.0x HP), 600 坚韧 (全局减伤 51.3%), 每击对玩家造成巨大压力")
    print("目标预期: 纯蛮干物理队 0%~5% 惨败; 机制策略队(真伤/侵蚀/控场)获得 20%~40% 策略胜率")
    print("=" * 95)

    def make_boss():
        b = Troop(99, "守门重装巨兽", 15, c=100, r=600, i=100, m=100, max_bp=720000)
        b.skills.append(BattleSkill(9901, "重岩重击", 3, "通用", "Attack", main_param=120.0, trigger_chance=40.0))
        b.skills.append(BattleSkill(9902, "泰山碎地", 4, "通用", "Attack", main_param=135.0, trigger_chance=30.0))
        return b

    # 4 类挑战者
    # 1. 盲目硬碰硬物理队 (纯直伤，无破防无真伤)
    def p_brute():
        p = Troop(1, "纯直伤物理队", 15, c=480, r=60, i=220, m=60, max_bp=360000)
        p.skills.append(BattleSkill(101, "先锋狂斩", 3, "勇气", "Attack", main_param=155.0, trigger_chance=40.0))
        p.skills.append(BattleSkill(102, "绝境重击", 4, "勇气", "Attack", main_param=200.0, trigger_chance=35.0, self_bp_cond2=45))
        return p

    # 2. 魔力直伤穿透流 (纯粹真伤 + 高额破防)
    def p_true():
        p = Troop(2, "魔力真伤穿透队", 15, c=60, r=100, i=180, m=480, max_bp=360000)
        p.skills.append(BattleSkill(201, "奥能贯通炮", 4, "魔力", "Attack", main_param=175.0, trigger_chance=45.0, is_true_damage=True))
        p.skills.append(BattleSkill(202, "虚空穿甲杀", 4, "魔力", "Attack", main_param=160.0, trigger_chance=40.0, ignore_def_ratio=0.75))
        p.skills.append(BattleSkill(203, "常态魔刃", 3, "魔力", "Attack", main_param=135.0, trigger_chance=30.0, is_true_damage=True))
        return p

    # 3. 魔力侵蚀流 (最大战力 DoT 蚕食 Boss + 1次虚弱减伤)
    def p_dot():
        p = Troop(3, "魔力持续侵蚀队", 15, c=60, r=220, i=100, m=480, max_bp=360000)
        # 开局挂 4.5% 最大战力 DoT (Boss 每回合掉 ~3.5万) + 削弱 Boss 伤害
        p.skills.append(BattleSkill(301, "万毒侵蚀", 4, "魔力", "Attack", main_param=115.0, trigger_chance=50.0, turn_cond2=3, times_limit=1, sub_effect="combo_dot", sub_param=0.045, sub_base=18000, sub_duration=3))
        p.skills.append(BattleSkill(302, "腐骨剧毒", 3, "魔力", "Attack", main_param=110.0, trigger_chance=35.0, sub_effect="dot_max", sub_param=0.035, sub_duration=2))
        p.skills.append(BattleSkill(303, "固守急救", 3, "坚韧", "Heal", main_param=100.0, trigger_chance=30.0, self_bp_cond2=60, sub_effect="self_max_heal", sub_param=0.12))
        return p

    # 4. 复合策略抗压队 (真伤 + 侵蚀 + 名刀锁血 1 次 + 虚弱控场)
    def p_strategy():
        p = Troop(4, "全策略攻坚队", 15, c=120, r=200, i=120, m=420, max_bp=360000)
        p.death_defy = 1  # 携带 1 次名刀保命
        p.skills.append(BattleSkill(401, "虚弱穿甲杀", 4, "魔力", "Attack", main_param=150.0, trigger_chance=45.0, turn_cond2=3, times_limit=1, exhaust_turns=1, is_true_damage=True))
        p.skills.append(BattleSkill(402, "剧毒侵蚀", 4, "魔力", "Attack", main_param=120.0, trigger_chance=40.0, sub_effect="combo_dot", sub_param=0.040, sub_base=16000, sub_duration=3))
        p.skills.append(BattleSkill(403, "背水大急救", 4, "坚韧", "Heal", main_param=100.0, trigger_chance=45.0, self_bp_cond2=45, times_limit=1, sub_effect="self_max_heal", sub_param=0.16))
        return p

    challengers = [
        ("1. 纯直伤物理队 (无破防无策略)", p_brute),
        ("2. 魔力真伤穿透队 (纯真伤攻坚)", p_true),
        ("3. 魔力持续侵蚀队 (DoT磨血+续航)", p_dot),
        ("4. 全策略攻坚队 (真伤+侵蚀+控场+名刀)", p_strategy),
    ]

    sims = 2000
    for cname, cmaker in challengers:
        wins = 0
        total_t = 0
        boss_rem = 0.0
        for _ in range(sims):
            player = cmaker()
            boss = make_boss()
            res = run_battle(player, boss, max_turns=25)
            if res['winner'] == player: wins += 1
            total_t += res['turns']
            boss_rem += (boss.current_bp / boss.max_bp) * 100.0
        
        wr = (wins / sims) * 100.0
        avg_t = total_t / sims
        rem = boss_rem / sims
        print(f"\n{cname}:")
        print(f"  * 越级攻坚胜率: {wr:>5.1f}% | 平均存活回合: {avg_t:>4.1f} | 结束时Boss平均剩余血量: {rem:>5.1f}%")


def test_swing_ratio_and_pacing():
    print("\n\n" + "=" * 95)
    print("【检验 B: 节奏基准与单技能摆动幅度 (Swing Ratio) 全周期演化 (5人 ~ 30人)】")
    print("标尺: 平均交锋回合收敛至 6~10 回合 | 单技能摆动 15%~28% (有肉眼可见存在感，不刮痧不暴毙)")
    print("=" * 95)

    scales = [5, 10, 15, 20, 25, 30]
    for sc in scales:
        bp = {5: 60000, 10: 180000, 15: 360000, 20: 600000, 25: 820000, 30: 1000000}[sc]
        t1 = Troop(1, f"勇气队[{sc}]", sc, c=800 if sc>=25 else 400, r=100, i=300, m=100, max_bp=bp)
        t2 = Troop(2, f"坚韧队[{sc}]", sc, c=100, r=800 if sc>=25 else 400, i=100, m=300, max_bp=bp)
        
        t1.skills.append(BattleSkill(101, "核心重击", 3, "勇气", "Attack", main_param=160.0, trigger_chance=35.0))
        t1.skills.append(BattleSkill(102, "常态压制", 2, "勇气", "Attack", main_param=135.0, trigger_chance=30.0))
        
        t2.skills.append(BattleSkill(201, "战地愈合", 3, "坚韧", "Heal", main_param=100.0, trigger_chance=35.0, self_bp_cond2=60, sub_effect="self_max_heal", sub_param=0.14))
        t2.skills.append(BattleSkill(202, "壁垒反制", 3, "坚韧", "Attack", main_param=140.0, trigger_chance=30.0))

        turns = []
        for _ in range(300):
            res = run_battle(t1, t2)
            turns.append(res['turns'])

        avg_t = sum(turns) / len(turns)
        
        # 统计单发技能摆动比
        swings = [x['swing'] for x in t1.action_swings if x['skill'] == "核心重击"]
        avg_sw = sum(swings) / len(swings) if swings else 0.0

        print(f"【{sc:>2} 人阵容】(总战力 {bp:>9,}) -> 平均交锋回合: {avg_t:>4.1f} 回合 | 核心重击平均削减战力: {avg_sw:>5.1f}%")

if __name__ == '__main__':
    test_pve_punching()
    test_swing_ratio_and_pacing()
