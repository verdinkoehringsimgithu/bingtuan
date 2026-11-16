# -*- coding: utf-8 -*-
"""
Audited Combat Simulator (V11.0 Full Comprehensive Audit)
Fixing all 5 discovered hidden issues systematically:
1. Debuff percentages lawfully amplified by Magic & Initiative advantage
2. True damage gains lawful penetration scaling with Magic (no 500 cap)
3. Initiative order dynamically checks debuffed effective stats (eff_i)
4. Courage self_lost_dmg strictly mitigated by enemy pct_dr (zero piercing on Courage)
5. Equal initiative coin-flip on turn order
"""
import random, sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from test_30man_combat_simulator import (
    calc_magic_amp_responsive, calc_resilience_dr, calc_courage_stats, calc_initiative_stats,
    BattleSkill, Troop, assemble_hybrid_troop
)

def execute_audited_action(acting, defender, is_first, turn):
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

    if skill.ini_bonus > 0:
        acting.cur_initiative += skill.ini_bonus

    raw_skill_crit = skill.base_crit_rate
    esc = raw_skill_crit * (1.0 + (m_amp - 1.0) * 0.45) if raw_skill_crit > 0 else 0.0
    total_crit_rate = c_crit_rate + esc

    extra_overflow = (total_crit_rate - 1.0) * 1.5 if total_crit_rate > 1.0 else 0.0
    effective_crit_rate = min(1.0, total_crit_rate)
    is_crit = (random.random() < effective_crit_rate)

    if not is_crit and random.random() < dodge_rate:
        defender.dodge_count += 1
        return

    mult = skill.main_param / 100.0
    if is_crit:
        mult += (c_crit_bonus + extra_overflow)

    raw_dmg = base_power * mult * preempt_factor * acting.get_dmg_output_factor()

    if skill.main_type == "Heal":
        heal_val = acting.max_bp * skill.sub_param
        acting.heal(heal_val)
        raw_dmg = base_power * 1.0 * acting.get_dmg_output_factor()

    flat_dr, pct_dr = calc_resilience_dr(def_r)
    is_pure_true = (skill.ignore_def_ratio * m_amp >= 0.85)

    if is_pure_true:
        # 审计修正 2: 纯真伤在破甲之外，享受魔力放大器的真伤穿透增幅 (魔力不封顶)
        true_bonus = 1.0 + (m_amp - 1.0) * 0.20
        actual_dmg = raw_dmg * true_bonus
    else:
        effective_pct_dr = max(0.0, pct_dr * (1.0 - skill.ignore_def_ratio * m_amp))
        actual_dmg = max(1.0, raw_dmg * (1.0 - effective_pct_dr) - flat_dr)

    defender.current_bp = max(0.0, defender.current_bp - actual_dmg)
    acting.total_damage += actual_dmg

    sub = skill.sub_effect_name
    if sub == "自身已损反噬":
        lost = max(0.0, acting.max_bp - acting.current_bp)
        # 审计修正 4: 勇气反噬伤害受敌方坚韧减免！严守'勇气绝不带任何穿透'铁律！
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
        # 审计修正 1: 百分比Debuff依法受魔力放大器平滑放大，并受先手优势赋能
        base_pct = skill.sub_param / 100.0
        scaled_pct = min(0.60, base_pct * (1.0 + (m_amp - 1.0) * 0.20) * (1.0 + preempt_bonus * 0.5))
        defender.dmg_reduce_debuffs.append({'pct': scaled_pct, 'turns': skill.sub_duration})
    elif sub == "四维削弱":
        # 审计修正 1: 四维削弱百分比依法受魔力放大器平滑放大，并受先手优势赋能
        base_pct = skill.sub_param / 100.0
        scaled_pct = min(0.45, base_pct * (1.0 + (m_amp - 1.0) * 0.20) * (1.0 + preempt_bonus * 0.5))
        defender.stat_reduce_debuffs.append({'pct': scaled_pct, 'turns': skill.sub_duration})


def run_audited_battle(t1, t2, max_turns=40):
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

        execute_audited_action(first, second, True, turn)
        if second.is_dead(): break
        execute_audited_action(second, first, False, turn)
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


def run_full_audit_test(sims=2000):
    genres = ["M_R", "M_I", "M_C", "C_I", "C_R", "R_I"]
    names = {
        "M_R": "魔力+坚韧",
        "M_I": "魔力+先机",
        "M_C": "魔力+勇气",
        "C_I": "勇气+先机",
        "C_R": "勇气+坚韧",
        "R_I": "坚韧+先机"
    }

    wm = {g1: {g2: 0 for g2 in genres} for g1 in genres}
    mt = {g1: {g2: [] for g2 in genres} for g1 in genres}

    for i in range(len(genres)):
        for j in range(i, len(genres)):
            g1, g2 = genres[i], genres[j]
            if g1 == g2:
                wm[g1][g2] = sims // 2
                continue
            for _ in range(sims):
                t1 = assemble_hybrid_troop(g1)
                t2 = assemble_hybrid_troop(g2)
                res = run_audited_battle(t1, t2)
                mt[g1][g2].append(res['turns'])
                mt[g2][g1].append(res['turns'])
                if res['winner'].name == t1.name: wm[g1][g2] += 1
                else: wm[g2][g1] += 1

    print("=" * 88)
    print("【全面深度审计修正后真机理实测矩阵 (V11.0)】(每组 2000 局，总计 12,000 局)")
    print("=" * 88)
    header = f"{'流派 (行攻 / 列防)':<18}"
    for g in genres: header += f"{names[g]:<10}"
    header += f"{'综合胜率':<8}"
    print(header)
    print("-" * 88)

    for g1 in genres:
        row = f"{names[g1]:<18}"
        tot_w = sum(wm[g1][g2] for g2 in genres)
        for g2 in genres:
            pct = (wm[g1][g2] / sims) * 100.0
            row += f"{pct:>6.1f}%   "
        ovr = (tot_w / (sims * len(genres))) * 100.0
        row += f"{ovr:>6.1f}%"
        print(row)
    print("-" * 88)

    non_res_pairs = [("M_I","M_C"), ("M_I","C_I"), ("M_C","C_I")]
    nr_turns = []
    for g1, g2 in non_res_pairs: nr_turns.extend(mt[g1][g2])
    res_turns = []
    for g1 in genres:
        for g2 in genres:
            if (g1 in {"M_R","C_R","R_I"} or g2 in {"M_R","C_R","R_I"}) and g1 < g2:
                res_turns.extend(mt[g1][g2])
    all_turns = [t for row in mt.values() for t_list in row.values() for t in t_list]

    print(f"非坚韧对局平均回合: {sum(nr_turns)/len(nr_turns):.2f} 回合")
    print(f"坚韧流对局平均回合: {sum(res_turns)/len(res_turns):.2f} 回合")
    print(f"全局所有对决平均:   {sum(all_turns)/len(all_turns):.2f} 回合")

if __name__ == '__main__':
    run_full_audit_test(2000)
