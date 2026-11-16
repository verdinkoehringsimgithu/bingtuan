# -*- coding: utf-8 -*-
"""
Canonical Combat Simulation & Balance Engine (V9.0)
Strictly adheres to SkillGenerator.cs specifications and pure 4-stat mechanics:
- No hardcoded individual skill buffs.
- No fake 'exhaust_turns = 1'.
- Uses authentic SkillGenerator SubEffects:
  * 先机: "虚弱压制" (降低目标造成伤害 X%, 持续2回合), "四维削弱" (降低目标所有属性 X%, 持续2回合), "先机加n" (动态累加先机)
  * 勇气: "自身已损反噬" (自身已损战力 X%), "敌方已损斩杀" (敌方已损战力 X%), 暴击必中破闪避
  * 坚韧: "总战力恢复" (恢复己方总战力 X%), 固定减伤与百分比减伤 (本职守恒，不被魔力二次翻倍)
  * 魔力: "无视目标X%防御", "最大流失", "已损流失", 直伤百分比放大
- Experience tempo:
  * base_power = 0.09 MaxBP + 0.045 CurBP (13.5% at full HP) -> Eliminates turn 1 one-shots, preserves decisive 70% strikes
"""
import random, sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# --- 1. 底层四维核心通用公式 ---

def calc_magic_amp_responsive(magic):
    if magic <= 0: return 1.0
    return 1.0 + (magic / (magic + 280.0)) * 1.5 + (magic / 1400.0) * 0.7

def calc_resilience_dr(resilience, flat_dr_scale=0.40):
    pct_dr = min(0.68, 0.25 + (resilience / (resilience + 450.0)) * 0.45)
    flat_dr = resilience * 12.0 * flat_dr_scale
    return flat_dr, pct_dr

def calc_courage_stats(courage):
    crit_rate = (courage / (courage + 750.0)) * 0.45
    crit_bonus = 0.45 + (courage / (courage + 650.0)) * 0.75
    return crit_rate, crit_bonus

def calc_initiative_stats(initiative, enemy_initiative, preempt_cap=0.35, dodge_cap=0.35):
    dodge_rate = min(dodge_cap, (initiative / (initiative + 650.0)) * 0.45)
    diff = max(0.0, initiative - enemy_initiative)
    preempt_bonus = (diff / (diff + 600.0)) * preempt_cap if diff > 0 else 0.0
    return dodge_rate, preempt_bonus


# --- 2. 规范技能数据模型 (完全对照 SkillGenerator.cs 契约) ---

class CanonicalSkill:
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


# --- 3. 战斗单位与状态模型 ---

class CanonicalTroop:
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


# --- 4. 战斗回合动作结算系统 ---

def execute_action(acting, defender, is_first, turn):
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
        skill = CanonicalSkill(9999, "普通攻击", 1, "通用", "Attack", main_param=100.0)

    # 1. 先机动态成长 (技能尾部: 先机加n 真实在战斗内生效)
    if skill.ini_bonus > 0:
        acting.cur_initiative += skill.ini_bonus

    # 2. 暴击判定与魔力增幅 (方向 1 & 2: 魔力增幅技能基础暴击率，超出 100% 转暴伤)
    raw_skill_crit = skill.base_crit_rate
    esc = raw_skill_crit * (1.0 + (m_amp - 1.0) * 0.45) if raw_skill_crit > 0 else 0.0
    total_crit_rate = c_crit_rate + esc

    extra_overflow = 0.0
    if total_crit_rate > 1.0:
        extra_overflow = (total_crit_rate - 1.0) * 1.5
        effective_crit_rate = 1.0
    else:
        effective_crit_rate = min(1.0, total_crit_rate)

    is_crit = (random.random() < effective_crit_rate)

    # 3. 闪避判定: 暴击必定命中破闪避；未暴击受对方闪避判定
    if not is_crit:
        if random.random() < dodge_rate:
            defender.dodge_count += 1
            return

    # 4. 主伤害倍率结算
    mult = skill.main_param / 100.0
    if is_crit:
        mult += (c_crit_bonus + extra_overflow)
    
    # 魔力技能本职直伤放大
    if skill.genre == "魔力":
        mult *= (1.0 + (m_amp - 1.0) * 0.35)

    raw_dmg = base_power * mult * preempt_factor * acting.get_dmg_output_factor()

    # 5. 坚韧治疗技能结算 (坚韧本职守恒，不被魔力二次翻倍)
    if skill.main_type == "Heal":
        heal_val = acting.max_bp * skill.sub_param
        acting.heal(heal_val)
        raw_dmg = base_power * 1.0 * acting.get_dmg_output_factor()

    # 6. 防御减免 (破防与真伤仅由魔力提供；纯净守恒)
    flat_dr, pct_dr = calc_resilience_dr(def_r, 0.40)
    is_pure_true = (skill.ignore_def_ratio * m_amp >= 0.85)

    if is_pure_true:
        actual_dmg = raw_dmg
    else:
        effective_pct_dr = max(0.0, pct_dr * (1.0 - skill.ignore_def_ratio * m_amp))
        actual_dmg = max(1.0, raw_dmg * (1.0 - effective_pct_dr) - flat_dr)

    defender.current_bp = max(0.0, defender.current_bp - actual_dmg)

    # 7. 真实 SkillGenerator 规范附加效果结算
    sub = skill.sub_effect_name
    if sub == "自身已损反噬":
        lost = max(0.0, acting.max_bp - acting.current_bp)
        extra = lost * skill.sub_param
        defender.current_bp = max(0.0, defender.current_bp - max(1.0, extra))
    elif sub == "敌方已损斩杀":
        lost = max(0.0, defender.max_bp - defender.current_bp)
        extra = lost * skill.sub_param * (1.0 - pct_dr)
        defender.current_bp = max(0.0, defender.current_bp - max(1.0, extra))
    elif sub == "战力吸收":
        acting.heal(actual_dmg * (skill.sub_param * m_amp))
    elif sub == "最大流失":
        defender.max_bp_dots.append({'val': skill.sub_param * m_amp, 'turns': skill.sub_duration, 'source': acting})
    elif sub == "已损流失":
        defender.lost_bp_dots.append({'val': skill.sub_param * m_amp, 'turns': skill.sub_duration, 'source': acting})
    elif sub == "虚弱压制":
        defender.dmg_reduce_debuffs.append({'pct': skill.sub_param / 100.0, 'turns': skill.sub_duration})
    elif sub == "四维削弱":
        defender.stat_reduce_debuffs.append({'pct': skill.sub_param / 100.0, 'turns': skill.sub_duration})


# --- 5. 战斗循环与持续效果驱动 ---

def run_canonical_battle(t1, t2, max_turns=40):
    t1.reset()
    t2.reset()
    turn = 0
    while turn < max_turns:
        turn += 1

        # 回合前结算 DoT (坚韧百分比减免全额生效，并受施加者当前的虚弱状态修正)
        for trp in [t1, t2]:
            if trp.is_dead(): continue
            _, pdr = calc_resilience_dr(trp.cur_resilience, 0.40)
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

        first, second = (t1, t2) if t1.cur_initiative >= t2.cur_initiative else (t2, t1)
        execute_action(first, second, True, turn)
        if second.is_dead(): break
        execute_action(second, first, False, turn)
        if first.is_dead(): break

        for trp in [t1, t2]:
            if trp.is_dead(): continue
            _, pdr = calc_resilience_dr(trp.cur_resilience, 0.40)
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


# --- 6. 真实规范阵容工厂 (完全依照 SkillGenerator.cs T5/T6 数值区间生成) ---

def assemble_canonical_troop(genre_code, base_bp=1000000):
    configs = {
        "M_R": ("魔力+坚韧流", 100, 500, 100, 1000),
        "M_I": ("魔力+先机流", 100, 100, 500, 1000),
        "M_C": ("魔力+勇气流", 500, 100, 100, 1000),
        "C_I": ("勇气+先机流", 1000, 100, 500, 100),
        "C_R": ("勇气+坚韧流", 1000, 500, 100, 100),
        "R_I": ("坚韧+先机流", 100, 1000, 500, 100),
    }
    name, c, r, i, m = configs[genre_code]
    troop = CanonicalTroop(1, name, 30, c, r, i, m, base_bp)

    if genre_code == "M_R":
        troop.skills.append(CanonicalSkill(1, "灭世剧毒", 6, "魔力", "Attack", main_param=140.0, trigger_chance=35.0, times_limit=1, ignore_def_ratio=0.80, sub_effect_name="最大流失", sub_param=0.015, sub_duration=2))
        troop.skills.append(CanonicalSkill(2, "神恩涅槃", 6, "坚韧", "Heal", main_param=100.0, trigger_chance=45.0, times_limit=1, self_bp_cond2=50, sub_effect_name="总战力恢复", sub_param=0.14))
        troop.skills.append(CanonicalSkill(3, "生命剥离", 5, "魔力", "Attack", main_param=130.0, trigger_chance=30.0, ignore_def_ratio=0.65, sub_effect_name="已损流失", sub_param=0.025, sub_duration=2))
        troop.skills.append(CanonicalSkill(4, "常态愈合", 5, "坚韧", "Heal", main_param=100.0, trigger_chance=25.0, self_bp_cond2=70, sub_effect_name="总战力恢复", sub_param=0.09))

    elif genre_code == "M_I":
        troop.skills.append(CanonicalSkill(1, "弑神断界斩", 6, "魔力", "Attack", main_param=145.0, trigger_chance=38.0, times_limit=1, ignore_def_ratio=0.80, sub_effect_name="虚弱压制", sub_param=38.0, sub_duration=2, ini_bonus=10))
        troop.skills.append(CanonicalSkill(2, "瞬影暗袭",   6, "先机", "Attack", main_param=180.0, trigger_chance=36.0, times_limit=1, sub_effect_name="四维削弱", sub_param=28.0, sub_duration=2, ini_bonus=10))
        troop.skills.append(CanonicalSkill(3, "纯粹裂魂击", 5, "魔力", "Attack", main_param=135.0, trigger_chance=32.0, ignore_def_ratio=0.65, ini_bonus=7))
        troop.skills.append(CanonicalSkill(4, "常态疾风刃", 5, "先机", "Attack", main_param=165.0, trigger_chance=28.0, sub_effect_name="虚弱压制", sub_param=25.0, sub_duration=2, ini_bonus=7))

    elif genre_code == "M_C":
        troop.skills.append(CanonicalSkill(1, "湮灭核弹斩", 6, "魔力", "Attack", main_param=145.0, trigger_chance=36.0, times_limit=1, ignore_def_ratio=0.80, base_crit_rate=0.15))
        troop.skills.append(CanonicalSkill(2, "终结暴击击", 6, "勇气", "Attack", main_param=340.0, trigger_chance=32.0, times_limit=1, enemy_bp_cond2=50, base_crit_rate=0.25, sub_effect_name="敌方已损斩杀", sub_param=0.18))
        troop.skills.append(CanonicalSkill(3, "纯粹裂魂击", 5, "魔力", "Attack", main_param=135.0, trigger_chance=30.0, ignore_def_ratio=0.65, base_crit_rate=0.12))
        troop.skills.append(CanonicalSkill(4, "破军重劈",   5, "勇气", "Attack", main_param=260.0, trigger_chance=25.0, base_crit_rate=0.18))

    elif genre_code == "C_I":
        troop.skills.append(CanonicalSkill(1, "疾风封脉破", 6, "先机", "Attack", main_param=185.0, trigger_chance=40.0, times_limit=1, sub_effect_name="虚弱压制", sub_param=42.0, sub_duration=2, ini_bonus=10))
        troop.skills.append(CanonicalSkill(2, "狂雷终结斩", 6, "勇气", "Attack", main_param=340.0, trigger_chance=32.0, times_limit=1, enemy_bp_cond2=50, base_crit_rate=0.25, sub_effect_name="敌方已损斩杀", sub_param=0.18))
        troop.skills.append(CanonicalSkill(3, "裂地狂劈",   5, "勇气", "Attack", main_param=270.0, trigger_chance=28.0, base_crit_rate=0.20))
        troop.skills.append(CanonicalSkill(4, "追风影袭",   5, "先机", "Attack", main_param=170.0, trigger_chance=30.0, sub_effect_name="四维削弱", sub_param=22.0, sub_duration=2, ini_bonus=7))

    elif genre_code == "C_R":
        troop.skills.append(CanonicalSkill(1, "背水浴血斩", 6, "勇气", "Attack", main_param=270.0, trigger_chance=35.0, times_limit=1, self_bp_cond2=50, base_crit_rate=0.25, sub_effect_name="自身已损反噬", sub_param=0.35))
        troop.skills.append(CanonicalSkill(2, "不坏金身",   5, "坚韧", "Heal", main_param=100.0, trigger_chance=40.0, times_limit=1, self_bp_cond2=50, sub_effect_name="总战力恢复", sub_param=0.14))
        troop.skills.append(CanonicalSkill(3, "崩山重劈",   5, "勇气", "Attack", main_param=250.0, trigger_chance=26.0, base_crit_rate=0.15))
        troop.skills.append(CanonicalSkill(4, "常态愈合",   5, "坚韧", "Heal", main_param=100.0, trigger_chance=25.0, self_bp_cond2=70, sub_effect_name="总战力恢复", sub_param=0.08))

    elif genre_code == "R_I":
        troop.skills.append(CanonicalSkill(1, "神恩涅槃", 6, "坚韧", "Heal", main_param=100.0, trigger_chance=45.0, times_limit=1, self_bp_cond2=50, sub_effect_name="总战力恢复", sub_param=0.15))
        troop.skills.append(CanonicalSkill(2, "瞬影封脉", 5, "先机", "Attack", main_param=170.0, trigger_chance=35.0, sub_effect_name="虚弱压制", sub_param=35.0, sub_duration=2, ini_bonus=10))
        troop.skills.append(CanonicalSkill(3, "常态愈合", 5, "坚韧", "Heal", main_param=100.0, trigger_chance=30.0, self_bp_cond2=70, sub_effect_name="总战力恢复", sub_param=0.09))
        troop.skills.append(CanonicalSkill(4, "追风疾影", 5, "先机", "Attack", main_param=160.0, trigger_chance=28.0, sub_effect_name="四维削弱", sub_param=20.0, sub_duration=2, ini_bonus=7))

    return troop


# --- 7. 全量对抗矩阵检验 ---

def run_canonical_stress_test(sims_per_match=2000):
    genres = ["M_R", "M_I", "M_C", "C_I", "C_R", "R_I"]
    names = {
        "M_R": "魔力+坚韧流",
        "M_I": "魔力+先机流",
        "M_C": "魔力+勇气流",
        "C_I": "勇气+先机流",
        "C_R": "勇气+坚韧流",
        "R_I": "坚韧+先机流"
    }
    non_res_genres = {"M_I", "M_C", "C_I"}

    wins = {g1: {g2: 0 for g2 in genres} for g1 in genres}
    mt = {g1: {g2: [] for g2 in genres} for g1 in genres}

    for i in range(len(genres)):
        for j in range(i, len(genres)):
            g1, g2 = genres[i], genres[j]
            if g1 == g2:
                wins[g1][g2] = sims_per_match // 2
                continue

            for _ in range(sims_per_match):
                t1 = assemble_canonical_troop(g1)
                t2 = assemble_canonical_troop(g2)
                res = run_canonical_battle(t1, t2)
                t = res['turns']
                mt[g1][g2].append(t)
                mt[g2][g1].append(t)

                if res['winner'].name == t1.name: wins[g1][g2] += 1
                else: wins[g2][g1] += 1

    print("=" * 95)
    print("【真·底层规范重构对决矩阵 (V9.0)】")
    print("【纯净机理: 动态先机叠加 + 真实虚弱压制与四维削弱 + 纯正四维公式】")
    print("=" * 95)
    header = f"{'流派 (行攻 / 列防)':<20}"
    for g in genres: header += f"{names[g]:<11}"
    header += f"{'综合胜率':<8}"
    print(header)
    print("-" * 95)

    for g1 in genres:
        row = f"{names[g1]:<20}"
        tot_w = sum(wins[g1][g2] for g2 in genres)
        for g2 in genres:
            pct = (wins[g1][g2] / sims_per_match) * 100.0
            row += f"{pct:>6.1f}%    "
        ovr = (tot_w / (sims_per_match * len(genres))) * 100.0
        row += f"{ovr:>6.1f}%"
        print(row)
    print("-" * 95)

    non_res_pairs = [("M_I","M_C"), ("M_I","C_I"), ("M_C","C_I")]
    nr_turns = []
    for g1, g2 in non_res_pairs: nr_turns.extend(mt[g1][g2])
    res_turns = []
    for g1 in genres:
        for g2 in genres:
            if (g1 in {"M_R","C_R","R_I"} or g2 in {"M_R","C_R","R_I"}) and g1 < g2:
                res_turns.extend(mt[g1][g2])
    all_turns = [t for row in mt.values() for t_list in row.values() for t in t_list]

    print(f"\n非坚韧对局平均回合: {sum(nr_turns)/len(nr_turns):.2f} 回合 (目标 5~6 回合，消除秒杀，一刀奠定胜局)")
    print(f"坚韧流对局平均回合: {sum(res_turns)/len(res_turns):.2f} 回合 (目标 10~12 回合，防反与拉扯)")
    print(f"全局所有对决平均:   {sum(all_turns)/len(all_turns):.2f} 回合")

if __name__ == '__main__':
    run_canonical_stress_test(2000)
