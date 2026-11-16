# -*- coding: utf-8 -*-
"""
30-Mercenary Formation Battle Simulator & Extreme Balance Stress Test (V11.0 Full Audit Canonical)
Architecture:
- Pure 4-Stat Hybrid System (Zero Stat-Boundary Pollution):
  * 魔力+坚韧流 (阵地持续侵蚀与自愈)
  * 魔力+先机流 (高速破防真伤与吸血身法)
  * 魔力+勇气流 (极限暴击纯真伤核弹)
  * 勇气+先机流 (高速抢攻破闪暴击)
  * 勇气+坚韧流 (残血战神与逆境反噬)
  * 坚韧+先机流 (铁壁防御与防守反击)
- Comprehensive Audit Upgrades:
  1. 勇气：纯高倍率 + 基础暴击率，暴击必中破闪避。超出100%暴击按1:1.5转暴伤。
     【审计修正】：自身已损反噬与斩杀严格接受坚韧减免，严守“勇气绝无穿透”铁律。
  2. 坚韧：固定减伤 + 全局百分比减伤，战力自愈恢复。坚韧治疗本职守恒，绝不被魔力二次翻倍。
  3. 先机：决定顺位，提供身法闪避，先手差值增伤，战斗内动态累加先机 (先机加n)。
     【审计修正】：顺位判定动态读取受Debuff影响的实际先机，平局先手随机交替；百分比Debuff依法受先手优势与魔力放大。
  4. 魔力：纯粹百分比放大器 (放大破防、流失DoT、吸血、基础暴击率)。
     【审计修正】：纯真伤在完全破甲后，超额魔力按本职转化为穿透真伤增幅，打破500封顶天花板。
  5. 基础打击基准: 0.09 MaxBP + 0.045 CurBP，满血基准13.5%，消除开局秒杀，保留一刀奠定胜局的高光。
"""
import random
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def calc_magic_amp_responsive(magic):
    if magic <= 0: return 1.0
    return 1.0 + (magic / (magic + 280.0)) * 1.5 + (magic / 1400.0) * 0.7

def calc_resilience_dr(resilience, flat_scale=0.38):
    pct_dr = min(0.68, 0.25 + (resilience / (resilience + 450.0)) * 0.45)
    flat_dr = resilience * 12.0 * flat_scale
    return flat_dr, pct_dr

def calc_courage_stats(courage):
    crit_rate = (courage / (courage + 750.0)) * 0.45
    crit_bonus = 0.45 + (courage / (courage + 650.0)) * 0.75
    return crit_rate, crit_bonus

def calc_initiative_stats(initiative, enemy_initiative, preempt_cap=0.35, dodge_cap=0.35):
    dodge_rate = min(dodge_cap, (initiative / (initiative + 450.0)) * 0.48)
    diff = max(0.0, initiative - enemy_initiative)
    preempt_bonus = (diff / (diff + 500.0)) * preempt_cap if diff > 0 else 0.0
    return dodge_rate, preempt_bonus


class BattleSkill:
    def __init__(self, sid, name, tier, genre, main_type="Attack", main_param=100.0,
                 trigger_chance=30.0, times_limit=999,
                 turn_cond1=0, turn_cond2=0, self_bp_cond2=0, enemy_bp_cond2=0,
                 base_crit_rate=0.0, ignore_def_ratio=0.0,
                 sub_effect_name="", sub_param=0.0, sub_duration=0,
                 ini_bonus=0):
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
        self.ignore_def_ratio = ignore_def_ratio
        self.sub_effect_name = sub_effect_name
        self.sub_param = sub_param
        self.sub_duration = sub_duration
        self.ini_bonus = ini_bonus

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
        self.base_courage = float(c)
        self.base_resilience = float(r)
        self.base_initiative = float(i)
        self.base_magic = float(m)
        self.skills = []
        self.reset()

    def reset(self):
        self.current_bp = self.max_bp
        self.usage = {}
        self.cur_courage = self.base_courage
        self.cur_resilience = self.base_resilience
        self.cur_initiative = self.base_initiative
        self.cur_magic = self.base_magic
        self.max_bp_dots = []
        self.lost_bp_dots = []
        self.dmg_reduce_debuffs = []
        self.stat_reduce_debuffs = []
        self.dodge_count = 0
        self.total_damage = 0.0

    @property
    def bp_pct(self): return (self.current_bp / self.max_bp) * 100.0
    def is_dead(self): return self.current_bp <= 0.0001

    def heal(self, amount):
        if amount <= 0: return 0.0
        old = self.current_bp
        self.current_bp = min(self.max_bp, self.current_bp + amount)
        return self.current_bp - old

    def get_effective_stats(self):
        stat_factor = 1.0
        for debuff in self.stat_reduce_debuffs:
            stat_factor *= (1.0 - debuff['pct'])
        return (
            self.cur_courage * stat_factor,
            self.cur_resilience * stat_factor,
            self.cur_initiative * stat_factor,
            self.cur_magic * stat_factor
        )

    def get_dmg_output_factor(self):
        factor = 1.0
        for debuff in self.dmg_reduce_debuffs:
            factor *= (1.0 - debuff['pct'])
        return factor


def execute_turn_action(acting, defender, is_first, turn):
    eff_c, eff_r, eff_i, eff_m = acting.get_effective_stats()
    def_c, def_r, def_i, def_m = defender.get_effective_stats()

    base_power = acting.max_bp * 0.09 + acting.current_bp * 0.045
    m_amp = calc_magic_amp_responsive(eff_m)
    c_crit_rate, c_crit_bonus = calc_courage_stats(eff_c)
    dodge_rate, preempt_bonus = calc_initiative_stats(eff_i, def_i)
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

    # 1. 先机动态成长
    if skill.ini_bonus > 0:
        acting.cur_initiative += skill.ini_bonus

    # 2. 暴击判定与魔力增幅 (魔力仅放大技能自带的基础暴击率百分比)
    raw_skill_crit = skill.base_crit_rate
    esc = raw_skill_crit * (1.0 + (m_amp - 1.0) * 0.45) if raw_skill_crit > 0 else 0.0
    total_crit_rate = c_crit_rate + esc

    extra_overflow = (total_crit_rate - 1.0) * 1.5 if total_crit_rate > 1.0 else 0.0
    effective_crit_rate = min(1.0, total_crit_rate)
    is_crit = (random.random() < effective_crit_rate)

    # 3. 闪避判定: 暴击必中破闪避
    if not is_crit:
        if random.random() < dodge_rate:
            defender.dodge_count += 1
            return

    # 4. 主伤害倍率结算
    mult = skill.main_param / 100.0
    if is_crit:
        mult += (c_crit_bonus + extra_overflow)

    raw_dmg = base_power * mult * preempt_factor * acting.get_dmg_output_factor()

    # 5. 坚韧治疗结算 (本职守恒，不被魔力二次翻倍)
    if skill.main_type == "Heal":
        heal_val = acting.max_bp * skill.sub_param
        acting.heal(heal_val)
        raw_dmg = base_power * 1.0 * acting.get_dmg_output_factor()

    # 6. 防御减免与纯真伤穿透
    flat_dr, pct_dr = calc_resilience_dr(def_r)
    is_pure_true = (skill.ignore_def_ratio * m_amp >= 0.85)

    if is_pure_true:
        # 审计修正 2: 纯真伤在破甲之外，享受魔力放大器的穿透真伤增幅 (打破500封顶天花板)
        true_bonus = 1.0 + (m_amp - 1.0) * 0.20
        actual_dmg = raw_dmg * true_bonus
    else:
        effective_pct_dr = max(0.0, pct_dr * (1.0 - skill.ignore_def_ratio * m_amp))
        actual_dmg = max(1.0, raw_dmg * (1.0 - effective_pct_dr) - flat_dr)

    defender.current_bp = max(0.0, defender.current_bp - actual_dmg)
    acting.total_damage += actual_dmg

    # 7. 附加百分比效果结算
    sub = skill.sub_effect_name
    if sub == "自身已损反噬":
        lost = max(0.0, acting.max_bp - acting.current_bp)
        # 审计修正 4: 勇气反噬伤害严格受敌方坚韧减免，严守“勇气绝无穿透”铁律
        extra = lost * skill.sub_param * (1.0 - pct_dr)
        defender.current_bp = max(0.0, defender.current_bp - max(1.0, extra))
        acting.total_damage += max(1.0, extra)
    elif sub == "敌方已损斩杀":
        lost = max(0.0, defender.max_bp - defender.current_bp)
        extra = lost * skill.sub_param * (1.0 - pct_dr)
        defender.current_bp = max(0.0, defender.current_bp - max(1.0, extra))
        acting.total_damage += max(1.0, extra)
    elif sub == "战力吸收":
        acting.heal(actual_dmg * (skill.sub_param * m_amp))
    elif sub == "最大流失":
        defender.max_bp_dots.append({'val': skill.sub_param * m_amp, 'turns': skill.sub_duration, 'source': acting})
    elif sub == "已损流失":
        defender.lost_bp_dots.append({'val': skill.sub_param * m_amp, 'turns': skill.sub_duration, 'source': acting})
    elif sub == "虚弱压制":
        # 严格遵守物理与系统逻辑：先机仅作用于直击伤害，绝不作用于削弱与流失！
        # 百分比削弱与Debuff由魔力放大器(m_amp)平滑放大
        base_pct = skill.sub_param / 100.0
        scaled_pct = min(0.60, base_pct * (1.0 + (m_amp - 1.0) * 0.25))
        defender.dmg_reduce_debuffs.append({'pct': scaled_pct, 'turns': skill.sub_duration})
    elif sub == "四维削弱":
        # 百分比削弱由魔力放大器(m_amp)平滑放大
        base_pct = skill.sub_param / 100.0
        scaled_pct = min(0.40, base_pct * (1.0 + (m_amp - 1.0) * 0.25))
        defender.stat_reduce_debuffs.append({'pct': scaled_pct, 'turns': skill.sub_duration})


def run_battle(t1, t2, max_turns=40):
    t1.reset()
    t2.reset()
    turn = 0
    while turn < max_turns:
        turn += 1

        for trp in [t1, t2]:
            if trp.is_dead(): continue
            _, pdr = calc_resilience_dr(trp.cur_resilience)
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

        # 审计修正 3 & 5: 使用受 Debuff 影响的有效先机判断先手；相同先机随机先后手
        eff_i1 = t1.get_effective_stats()[2]
        eff_i2 = t2.get_effective_stats()[2]
        if eff_i1 > eff_i2:
            first, second = t1, t2
        elif eff_i2 > eff_i1:
            first, second = t2, t1
        else:
            first, second = (t1, t2) if random.random() < 0.5 else (t2, t1)

        execute_turn_action(first, second, True, turn)
        if second.is_dead(): break
        execute_turn_action(second, first, False, turn)
        if first.is_dead(): break

        for trp in [t1, t2]:
            if trp.is_dead(): continue
            _, pdr = calc_resilience_dr(trp.cur_resilience)
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


def assemble_hybrid_troop(genre_code, base_bp=1000000):
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
        troop.skills.append(BattleSkill(1, "灭世剧毒", 6, "魔力", "Attack", main_param=140.0, trigger_chance=35.0, times_limit=1, ignore_def_ratio=0.80, sub_effect_name="最大流失", sub_param=0.015, sub_duration=2))
        troop.skills.append(BattleSkill(2, "神恩涅槃", 6, "坚韧", "Heal", main_param=100.0, trigger_chance=45.0, times_limit=1, self_bp_cond2=50, sub_effect_name="总战力恢复", sub_param=0.14))
        troop.skills.append(BattleSkill(3, "生命剥离", 5, "魔力", "Attack", main_param=130.0, trigger_chance=30.0, ignore_def_ratio=0.65, sub_effect_name="已损流失", sub_param=0.025, sub_duration=2))
        troop.skills.append(BattleSkill(4, "常态愈合", 5, "坚韧", "Heal", main_param=100.0, trigger_chance=25.0, self_bp_cond2=70, sub_effect_name="总战力恢复", sub_param=0.09))

    elif genre_code == "M_I":
        troop.skills.append(BattleSkill(1, "弑神断界斩", 6, "魔力", "Attack", main_param=145.0, trigger_chance=38.0, times_limit=1, ignore_def_ratio=0.80, sub_effect_name="战力吸收", sub_param=0.35, ini_bonus=10))
        troop.skills.append(BattleSkill(2, "瞬影暗袭",   6, "先机", "Attack", main_param=180.0, trigger_chance=36.0, times_limit=1, sub_effect_name="虚弱压制", sub_param=38.0, sub_duration=2, ini_bonus=10))
        troop.skills.append(BattleSkill(3, "纯粹裂魂击", 5, "魔力", "Attack", main_param=135.0, trigger_chance=32.0, ignore_def_ratio=0.65, sub_effect_name="战力吸收", sub_param=0.25, ini_bonus=7))
        troop.skills.append(BattleSkill(4, "疾风影袭",   5, "先机", "Attack", main_param=165.0, trigger_chance=28.0, sub_effect_name="四维削弱", sub_param=22.0, sub_duration=2, ini_bonus=7))

    elif genre_code == "M_C":
        troop.skills.append(BattleSkill(1, "湮灭核弹斩", 6, "魔力", "Attack", main_param=145.0, trigger_chance=36.0, times_limit=1, ignore_def_ratio=0.80, base_crit_rate=0.20))
        troop.skills.append(BattleSkill(2, "终结暴击击", 6, "勇气", "Attack", main_param=340.0, trigger_chance=35.0, times_limit=1, enemy_bp_cond2=55, base_crit_rate=0.30, sub_effect_name="敌方已损斩杀", sub_param=0.20))
        troop.skills.append(BattleSkill(3, "破军重劈",   5, "勇气", "Attack", main_param=260.0, trigger_chance=30.0, base_crit_rate=0.20))
        troop.skills.append(BattleSkill(4, "纯粹裂魂击", 5, "魔力", "Attack", main_param=135.0, trigger_chance=28.0, ignore_def_ratio=0.65, base_crit_rate=0.15))

    elif genre_code == "C_I":
        troop.skills.append(BattleSkill(1, "疾风封脉破", 6, "先机", "Attack", main_param=185.0, trigger_chance=40.0, times_limit=1, sub_effect_name="虚弱压制", sub_param=42.0, sub_duration=2, ini_bonus=10))
        troop.skills.append(BattleSkill(2, "狂雷终结斩", 6, "勇气", "Attack", main_param=340.0, trigger_chance=32.0, times_limit=1, enemy_bp_cond2=50, base_crit_rate=0.25, sub_effect_name="敌方已损斩杀", sub_param=0.18))
        troop.skills.append(BattleSkill(3, "裂地狂劈",   5, "勇气", "Attack", main_param=270.0, trigger_chance=28.0, base_crit_rate=0.20))
        troop.skills.append(BattleSkill(4, "追风影袭",   5, "先机", "Attack", main_param=170.0, trigger_chance=30.0, sub_effect_name="四维削弱", sub_param=22.0, sub_duration=2, ini_bonus=7))

    elif genre_code == "C_R":
        troop.skills.append(BattleSkill(1, "背水浴血斩", 6, "勇气", "Attack", main_param=270.0, trigger_chance=35.0, times_limit=1, self_bp_cond2=50, base_crit_rate=0.25, sub_effect_name="自身已损反噬", sub_param=0.26))
        troop.skills.append(BattleSkill(2, "不坏金身",   5, "坚韧", "Heal", main_param=100.0, trigger_chance=40.0, times_limit=1, self_bp_cond2=50, sub_effect_name="总战力恢复", sub_param=0.13))
        troop.skills.append(BattleSkill(3, "崩山重劈",   5, "勇气", "Attack", main_param=250.0, trigger_chance=26.0, base_crit_rate=0.15))
        troop.skills.append(BattleSkill(4, "常态愈合",   5, "坚韧", "Heal", main_param=100.0, trigger_chance=25.0, self_bp_cond2=70, sub_effect_name="总战力恢复", sub_param=0.08))

    elif genre_code == "R_I":
        troop.skills.append(BattleSkill(1, "神恩涅槃", 6, "坚韧", "Heal", main_param=100.0, trigger_chance=45.0, times_limit=1, self_bp_cond2=50, sub_effect_name="总战力恢复", sub_param=0.15))
        troop.skills.append(BattleSkill(2, "瞬影封脉", 5, "先机", "Attack", main_param=170.0, trigger_chance=35.0, sub_effect_name="虚弱压制", sub_param=35.0, sub_duration=2, ini_bonus=10))
        troop.skills.append(BattleSkill(3, "常态愈合", 5, "坚韧", "Heal", main_param=100.0, trigger_chance=30.0, self_bp_cond2=70, sub_effect_name="总战力恢复", sub_param=0.09))
        troop.skills.append(BattleSkill(4, "追风疾影", 5, "先机", "Attack", main_param=160.0, trigger_chance=28.0, sub_effect_name="四维削弱", sub_param=20.0, sub_duration=2, ini_bonus=7))

    return troop


def run_full_stress_test(sims_per_match=2500):
    genres = ["M_R", "M_I", "M_C", "C_I", "C_R", "R_I"]
    genre_names = {
        "M_R": "魔力+坚韧",
        "M_I": "魔力+先机",
        "M_C": "魔力+勇气",
        "C_I": "勇气+先机",
        "C_R": "勇气+坚韧",
        "R_I": "坚韧+先机"
    }

    win_matrix = {g1: {g2: 0 for g2 in genres} for g1 in genres}
    match_turns = {g1: {g2: [] for g2 in genres} for g1 in genres}

    for i in range(len(genres)):
        for j in range(i, len(genres)):
            g1, g2 = genres[i], genres[j]
            if g1 == g2:
                win_matrix[g1][g2] = sims_per_match // 2
                continue

            for _ in range(sims_per_match):
                t1 = assemble_hybrid_troop(g1)
                t2 = assemble_hybrid_troop(g2)
                res = run_battle(t1, t2)
                match_turns[g1][g2].append(res['turns'])
                match_turns[g2][g1].append(res['turns'])

                if res['winner'].name == t1.name: win_matrix[g1][g2] += 1
                else: win_matrix[g2][g1] += 1

    print("=" * 88)
    print(f"【30人战团六大流派全量对抗实测矩阵 (V11.0 深度审计版)】(每组 {sims_per_match} 局，总计 {sims_per_match*15} 局)")
    print("=" * 88)

    header = f"{'流派 (行攻 / 列防)':<18}"
    for g in genres: header += f"{genre_names[g]:<10}"
    header += f"{'综合胜率':<8}"
    print(header)
    print("-" * 88)

    for g1 in genres:
        row = f"{genre_names[g1]:<18}"
        tot_w = sum(win_matrix[g1][g2] for g2 in genres)
        for g2 in genres:
            pct = (win_matrix[g1][g2] / sims_per_match) * 100.0
            row += f"{pct:>6.1f}%   "
        ovr = (tot_w / (sims_per_match * len(genres))) * 100.0
        row += f"{ovr:>6.1f}%"
        print(row)
    print("-" * 88)

    non_res_pairs = [("M_I","M_C"), ("M_I","C_I"), ("M_C","C_I")]
    nr_turns = []
    for g1, g2 in non_res_pairs: nr_turns.extend(match_turns[g1][g2])
    res_turns = []
    for g1 in genres:
        for g2 in genres:
            if (g1 in {"M_R","C_R","R_I"} or g2 in {"M_R","C_R","R_I"}) and g1 < g2:
                res_turns.extend(match_turns[g1][g2])
    all_turns = [t for row in match_turns.values() for t_list in row.values() for t in t_list]

    print(f"非坚韧对局平均回合: {sum(nr_turns)/len(nr_turns):.2f} 回合")
    print(f"坚韧流对局平均回合: {sum(res_turns)/len(res_turns):.2f} 回合")
    print(f"全局所有对决平均:   {sum(all_turns)/len(all_turns):.2f} 回合")

if __name__ == '__main__':
    run_full_stress_test(2500)
