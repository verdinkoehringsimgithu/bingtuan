import random
from test_30man_combat_simulator import (
    BattleSkill, Troop, calc_magic_amp_responsive, calc_courage_stats,
    calc_initiative_stats, calc_resilience_dr
)

def run_simulation(power_scale=0.50, flat_dr_scale=0.50, heal_scale=0.70, times_limit_mult=1, max_turns=50, sims=1000):
    # Assemble troops with configurable parameters
    def get_troop(genre_code, base_bp=1000000):
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

        def adjust_limit(lim):
            if lim == 1 and times_limit_mult > 1:
                return times_limit_mult
            return lim

        if genre_code == "M_R":
            troop.skills.append(BattleSkill(1, "灭世剧毒", 6, "魔力", "Attack", 130.0, 50.0, turn_cond2=3, times_limit=adjust_limit(1), sub_effect="combo_dot", sub_param=0.035, sub_base=base_bp*0.03, sub_duration=3))
            troop.skills.append(BattleSkill(2, "神恩涅槃", 6, "坚韧", "Heal", 100.0, 50.0, self_bp_cond2=40, times_limit=adjust_limit(1), sub_effect="self_max_heal", sub_param=0.18*heal_scale))
            troop.skills.append(BattleSkill(3, "生命剥离", 5, "魔力", "Attack", 125.0, 35.0, sub_effect="dot_lost", sub_param=0.055, sub_duration=3))
            troop.skills.append(BattleSkill(4, "常态愈合", 5, "坚韧", "Heal", 100.0, 30.0, self_bp_cond2=65, sub_effect="self_max_heal", sub_param=0.12*heal_scale))

        elif genre_code == "M_I":
            troop.skills.append(BattleSkill(1, "弑神断界斩", 6, "魔力", "Attack", 220.0, 50.0, is_true_damage=True, times_limit=adjust_limit(1)))
            troop.skills.append(BattleSkill(2, "瞬狱虚弱杀", 6, "先机", "Attack", 170.0, 45.0, turn_cond2=3, times_limit=adjust_limit(1), exhaust_turns=1, is_true_damage=True))
            troop.skills.append(BattleSkill(3, "纯粹裂魂击", 5, "魔力", "Attack", 185.0, 35.0, is_true_damage=True))
            troop.skills.append(BattleSkill(4, "常态影刃", 5, "魔力", "Attack", 150.0, 30.0, ignore_def_ratio=0.75))

        elif genre_code == "M_C":
            troop.skills.append(BattleSkill(1, "湮灭核弹斩", 6, "魔力", "Attack", 260.0, 50.0, is_true_damage=True, times_limit=adjust_limit(1), base_crit_rate=0.20))
            troop.skills.append(BattleSkill(2, "终结暴击击", 6, "勇气", "Attack", 384.0, 45.0, enemy_bp_cond2=45, times_limit=adjust_limit(1), base_crit_rate=0.30))
            troop.skills.append(BattleSkill(3, "纯粹裂魂击", 5, "魔力", "Attack", 200.0, 35.0, is_true_damage=True, base_crit_rate=0.15))
            troop.skills.append(BattleSkill(4, "破军重劈",   5, "勇气", "Attack", 216.0, 30.0, base_crit_rate=0.20))

        elif genre_code == "C_I":
            troop.skills.append(BattleSkill(1, "疾风封脉破", 6, "先机", "Attack", 170.0, 50.0, turn_cond2=3, times_limit=adjust_limit(1), exhaust_turns=1))
            troop.skills.append(BattleSkill(2, "狂雷终结斩", 6, "勇气", "Attack", 456.0, 50.0, enemy_bp_cond2=45, times_limit=adjust_limit(1), base_crit_rate=0.25))
            troop.skills.append(BattleSkill(3, "裂地狂劈",   5, "勇气", "Attack", 264.0, 40.0, base_crit_rate=0.20))
            troop.skills.append(BattleSkill(4, "常态影刃",   5, "先机", "Attack", 175.0, 30.0))

        elif genre_code == "C_R":
            troop.skills.append(BattleSkill(1, "背水浴血斩", 6, "勇气", "Attack", 264.0, 50.0, self_bp_cond2=40, times_limit=adjust_limit(1), base_crit_rate=0.25, sub_effect="self_lost_dmg", sub_param=0.35))
            troop.skills.append(BattleSkill(2, "不坏金身",   5, "坚韧", "Heal", 100.0, 45.0, self_bp_cond2=45, times_limit=adjust_limit(1), sub_effect="self_max_heal", sub_param=0.16*heal_scale))
            troop.skills.append(BattleSkill(3, "崩山重劈",   5, "勇气", "Attack", 240.0, 35.0, base_crit_rate=0.15))

        elif genre_code == "R_I":
            troop.skills.append(BattleSkill(1, "神恩涅槃", 6, "坚韧", "Heal", 100.0, 50.0, self_bp_cond2=40, times_limit=adjust_limit(1), sub_effect="self_max_heal", sub_param=0.18*heal_scale))
            troop.skills.append(BattleSkill(2, "瞬影封印", 5, "先机", "Attack", 150.0, 40.0, exhaust_turns=1))
            troop.skills.append(BattleSkill(3, "常态吸血", 5, "坚韧", "Attack", 130.0, 30.0, sub_effect="lifesteal", sub_param=0.35))

        return troop

    def execute_action(acting, defender, is_first, turn):
        base_power = (acting.max_bp * 0.15 + acting.current_bp * 0.08) * power_scale
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

        raw_skill_crit = getattr(skill, 'base_crit_rate', 0.0)
        effective_skill_crit = raw_skill_crit * m_amp if raw_skill_crit > 0 else 0.0
        total_crit_rate = c_crit_rate + effective_skill_crit

        extra_overflow = 0.0
        if total_crit_rate > 1.0:
            extra_overflow = (total_crit_rate - 1.0) * 1.5
            effective_crit_rate = 1.0
        else:
            effective_crit_rate = min(1.0, total_crit_rate)

        is_crit = (random.random() < effective_crit_rate)

        if not is_crit:
            if random.random() < dodge_rate:
                defender.dodge_count += 1
                return

        mult = skill.main_param / 100.0
        if is_crit:
            mult += (c_crit_bonus + extra_overflow)
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

        flat_dr, pct_dr = calc_resilience_dr(defender.resilience)
        flat_dr *= flat_dr_scale
        is_pure_true = skill.is_true_damage or (skill.ignore_def_ratio * m_amp >= 0.85)

        if is_pure_true:
            actual_dmg = raw_dmg
        else:
            actual_dmg = max(1.0, raw_dmg * (1.0 - pct_dr) - flat_dr)

        defender.current_bp = max(0.0, defender.current_bp - actual_dmg)
        acting.total_damage += actual_dmg

        eff = skill.sub_effect
        if eff == "self_lost_dmg":
            lost = max(0.0, acting.max_bp - acting.current_bp)
            extra_raw = lost * (skill.sub_param * m_amp)
            defender.current_bp = max(0.0, defender.current_bp - max(1.0, extra_raw))
        elif eff == "enemy_lost_dmg":
            lost = max(0.0, defender.max_bp - defender.current_bp)
            extra_raw = lost * (skill.sub_param * m_amp) * (1.0 - pct_dr)
            defender.current_bp = max(0.0, defender.current_bp - max(1.0, extra_raw))
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

    def battle(t1, t2):
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
            execute_action(first, second, True, turn)
            if second.is_dead(): break
            execute_action(second, first, False, turn)
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

    genres = ["M_R", "M_I", "M_C", "C_I", "C_R", "R_I"]
    res_genres = {"M_R", "C_R", "R_I"}
    non_res_genres = {"M_I", "M_C", "C_I"}

    wins_matrix = {g1: {g2: 0 for g2 in genres} for g1 in genres}
    non_res_turns = []
    res_turns = []
    all_turns = []

    for i in range(len(genres)):
        for j in range(i, len(genres)):
            g1, g2 = genres[i], genres[j]
            is_non_res_pair = (g1 in non_res_genres and g2 in non_res_genres)
            is_res_involved = (g1 in res_genres or g2 in res_genres)

            if g1 == g2:
                wins_matrix[g1][g2] = sims // 2
                continue
            for _ in range(sims):
                t1 = get_troop(g1)
                t2 = get_troop(g2)
                res = battle(t1, t2)
                all_turns.append(res['turns'])
                if is_non_res_pair: non_res_turns.append(res['turns'])
                if is_res_involved: res_turns.append(res['turns'])

                if res['winner'].name == t1.name:
                    wins_matrix[g1][g2] += 1
                else:
                    wins_matrix[g2][g1] += 1

    win_rates = {}
    for g1 in genres:
        tot_w = sum(wins_matrix[g1][g2] for g2 in genres)
        tot_m = sims * len(genres)
        win_rates[g1] = (tot_w / tot_m) * 100.0

    avg_all = sum(all_turns) / len(all_turns) if all_turns else 0
    avg_nr = sum(non_res_turns) / len(non_res_turns) if non_res_turns else 0
    avg_r = sum(res_turns) / len(res_turns) if res_turns else 0

    return avg_nr, avg_r, avg_all, win_rates

if __name__ == '__main__':
    for p_scale in [0.45, 0.50, 0.55]:
        for d_scale in [0.45, 0.50]:
            for h_scale in [0.80, 1.0, 1.2]:
                nr, r, total, wr = run_simulation(power_scale=p_scale, flat_dr_scale=d_scale, heal_scale=h_scale, sims=300)
                print(f"p={p_scale:.2f}, dr={d_scale:.2f}, heal={h_scale:.2f} | Non-Res: {nr:.2f} 回合, Res: {r:.2f} 回合, 全局: {total:.2f} 回合")
                print("   胜率:", {k: f"{v:.1f}%" for k, v in wr.items()})
