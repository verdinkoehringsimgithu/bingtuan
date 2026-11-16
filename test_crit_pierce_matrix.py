# -*- coding: utf-8 -*-
"""
Testing the impact of Crit Resilience Pierce (暴击破除50%坚韧减伤) on Courage builds.
"""
import random
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from test_hybrid_synergy_and_balance import (
    create_hybrid_roster, Troop, BattleSkill,
    calc_resilience_dr, calc_magic_amp_responsive, calc_courage_stats, calc_initiative_stats
)

def execute_turn_action_with_crit_pierce(acting, defender, is_first, turn):
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

    # 暴击判定
    crit_boost = 0.10 if skill.genre == "勇气" else 0.0
    is_crit = (random.random() < min(0.95, c_crit_rate + crit_boost))

    # 闪避判定 (暴击必定命中)
    if not is_crit:
        if random.random() < dodge_rate:
            defender.dodge_count += 1
            return

    # 主效果结算
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
        acting.heal(heal_val)
        raw_dmg = base_power * 1.0

    # 关键机制: 暴击无视 50% 坚韧减伤 (HavocFortitudePierceRatio = 0.5)
    flat_dr, pct_dr = calc_resilience_dr(defender.resilience)
    is_pure_true = skill.is_true_damage or (skill.ignore_def_ratio * m_amp >= 0.85)

    if is_pure_true:
        actual_dmg = raw_dmg
    else:
        effective_pct_dr = pct_dr * 0.50 if is_crit else pct_dr
        effective_flat_dr = flat_dr * 0.50 if is_crit else flat_dr
        actual_dmg = max(1.0, raw_dmg * (1.0 - effective_pct_dr) - effective_flat_dr)

    defender.current_bp = max(0.0, defender.current_bp - actual_dmg)
    acting.total_damage += actual_dmg

    # 附加效果
    eff = skill.sub_effect
    if eff == "self_lost_dmg":
        lost = max(0.0, acting.max_bp - acting.current_bp)
        extra_raw = lost * (skill.sub_param * m_amp)
        extra_actual = defender.take_damage(extra_raw, is_true=True)
        acting.total_damage += extra_actual
    elif eff == "enemy_lost_dmg":
        lost = max(0.0, defender.max_bp - defender.current_bp)
        extra_raw = lost * (skill.sub_param * m_amp)
        extra_actual = defender.take_damage(extra_raw, is_true=False)
        acting.total_damage += extra_actual
    elif eff == "dot_max":
        defender.max_bp_dots.append({'val': skill.sub_param * m_amp, 'turns': skill.sub_duration})
    elif eff == "dot_lost":
        defender.turn_end_dots.append({'mode': 'lost', 'val': skill.sub_param * m_amp, 'turns': skill.sub_duration})
    elif eff == "combo_dot":
        defender.max_bp_dots.append({'val': skill.sub_param * m_amp, 'turns': skill.sub_duration})
        defender.turn_end_dots.append({'mode': 'flat', 'val': skill.sub_base * m_amp, 'turns': skill.sub_duration})

    if skill.exhaust_turns > 0:
        defender.exhaust_turns = max(defender.exhaust_turns, skill.exhaust_turns)


def run_battle_with_crit_pierce(t1, t2, max_turns=30):
    t1.reset()
    t2.reset()
    turn = 0
    while turn < max_turns:
        turn += 1
        # 回合前 DoT
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
        execute_turn_action_with_crit_pierce(first, second, True, turn)
        if second.is_dead(): break
        execute_turn_action_with_crit_pierce(second, first, False, turn)
        if first.is_dead(): break

        # 回合后 DoT
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


def test_updated_matrix():
    genres = ["M_R", "M_I", "M_C", "C_I", "C_R", "R_I"]
    genre_names = {
        "M_R": "魔力+坚韧(阵地DoT)",
        "M_I": "魔力+先机(灵动真伤)",
        "M_C": "魔力+勇气(暴击真伤)",
        "C_I": "勇气+先机(速攻暴击)",
        "C_R": "勇气+坚韧(残血反噬)",
        "R_I": "坚韧+先机(防守反击)"
    }
    
    sims = 1000
    wins_matrix = {g1: {g2: 0 for g2 in genres} for g1 in genres}
    
    for i in range(len(genres)):
        for j in range(i, len(genres)):
            g1, g2 = genres[i], genres[j]
            if g1 == g2:
                wins_matrix[g1][g2] = sims // 2
                continue
            for _ in range(sims):
                t1 = create_hybrid_roster(30, g1)
                t2 = create_hybrid_roster(30, g2)
                res = run_battle_with_crit_pierce(t1, t2)
                if res['winner'].name.startswith(t1.name[:5]):
                    wins_matrix[g1][g2] += 1
                else:
                    wins_matrix[g2][g1] += 1

    print("=" * 100)
    print("【实装“暴击破除50%坚韧”后的 六大复合流派 对决矩阵 (30 人完全体)】")
    print("=" * 100)
    header = f"{'流派 (行攻击/列防守)':<24}"
    for g in genres: header += f"{genre_names[g][:8]:<11}"
    header += f"{'综合胜率':<8}"
    print(header)
    print("-" * 96)

    for g1 in genres:
        row = f"{genre_names[g1]:<24}"
        tot_wins = 0; tot_matches = 0
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

if __name__ == '__main__':
    test_updated_matrix()
