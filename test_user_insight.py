# -*- coding: utf-8 -*-
import sys
sys.path.append('d:/123')
import test_30man_combat_simulator as sim

def test_mechanic(debuff_amp_mode='none', true_dmg_amp_mode='none'):
    orig_exec = sim.execute_turn_action

    def custom_exec(acting, defender, is_first, turn):
        eff_c, eff_r, eff_i, eff_m = acting.get_effective_stats()
        def_c, def_r, def_i, def_m = defender.get_effective_stats()

        base_power = acting.max_bp * 0.09 + acting.current_bp * 0.045
        m_amp = sim.calc_magic_amp_responsive(eff_m)
        c_crit_rate, c_crit_bonus = sim.calc_courage_stats(eff_c)
        dodge_rate, preempt_bonus = sim.calc_initiative_stats(eff_i, def_i)
        preempt_factor = (1.0 + preempt_bonus) if (is_first and preempt_bonus > 0) else 1.0

        skill = None
        for s in acting.skills:
            u = acting.usage.get(s.id, 0)
            if s.can_trigger(turn, acting.bp_pct, defender.bp_pct, u):
                if sim.random.random() * 100.0 < s.trigger_chance:
                    skill = s
                    acting.usage[s.id] = u + 1
                    break
        if skill is None:
            skill = sim.BattleSkill(9999, '普通攻击', 1, '通用', 'Attack', main_param=100.0)

        if skill.ini_bonus > 0:
            acting.cur_initiative += skill.ini_bonus

        raw_skill_crit = skill.base_crit_rate
        esc = raw_skill_crit * (1.0 + (m_amp - 1.0) * 0.45) if raw_skill_crit > 0 else 0.0
        total_crit_rate = c_crit_rate + esc
        extra_overflow = (total_crit_rate - 1.0) * 1.5 if total_crit_rate > 1.0 else 0.0
        effective_crit_rate = min(1.0, total_crit_rate)

        is_crit = (sim.random.random() < effective_crit_rate)
        if not is_crit and sim.random.random() < dodge_rate:
            defender.dodge_count += 1
            return

        mult = skill.main_param / 100.0
        if is_crit:
            mult += (c_crit_bonus + extra_overflow)

        raw_dmg = base_power * mult * preempt_factor * acting.get_dmg_output_factor()

        if skill.main_type == 'Heal':
            heal_val = acting.max_bp * skill.sub_param
            acting.heal(heal_val)
            raw_dmg = base_power * 1.0 * acting.get_dmg_output_factor()

        flat_dr, pct_dr = sim.calc_resilience_dr(def_r)
        is_pure_true = (skill.ignore_def_ratio * m_amp >= 0.85)

        if is_pure_true:
            if true_dmg_amp_mode == 'magic_true_bonus':
                # 真实伤害由魔力放大器提供真伤加成
                actual_dmg = raw_dmg * (1.0 + (m_amp - 1.0) * 0.25)
            elif true_dmg_amp_mode == 'preempt_double_on_true':
                actual_dmg = raw_dmg * (1.0 + preempt_bonus)
            else:
                actual_dmg = raw_dmg
        else:
            effective_pct_dr = max(0.0, pct_dr * (1.0 - skill.ignore_def_ratio * m_amp))
            actual_dmg = max(1.0, raw_dmg * (1.0 - effective_pct_dr) - flat_dr)

        defender.current_bp = max(0.0, defender.current_bp - actual_dmg)
        acting.total_damage += actual_dmg

        sub = skill.sub_effect_name
        if sub == '自身已损反噬':
            lost = max(0.0, acting.max_bp - acting.current_bp)
            extra = lost * skill.sub_param
            defender.current_bp = max(0.0, defender.current_bp - max(1.0, extra))
        elif sub == '敌方已损斩杀':
            lost = max(0.0, defender.max_bp - defender.current_bp)
            extra = lost * skill.sub_param * (1.0 - pct_dr)
            defender.current_bp = max(0.0, defender.current_bp - max(1.0, extra))
        elif sub == '战力吸收':
            acting.heal(actual_dmg * (skill.sub_param * m_amp))
        elif sub == '最大流失':
            defender.max_bp_dots.append({'val': skill.sub_param * m_amp, 'turns': skill.sub_duration, 'source': acting})
        elif sub == '已损流失':
            defender.lost_bp_dots.append({'val': skill.sub_param * m_amp, 'turns': skill.sub_duration, 'source': acting})
        elif sub == '虚弱压制':
            pct = skill.sub_param / 100.0
            if debuff_amp_mode == 'magic_amp':
                pct = min(0.65, pct * (1.0 + (m_amp - 1.0) * 0.30))
            elif debuff_amp_mode == 'init_amp':
                pct = min(0.65, pct * (1.0 + preempt_bonus))
            elif debuff_amp_mode == 'both':
                pct = min(0.65, pct * (1.0 + (m_amp - 1.0) * 0.25) * (1.0 + preempt_bonus * 0.5))
            defender.dmg_reduce_debuffs.append({'pct': pct, 'turns': skill.sub_duration})
        elif sub == '四维削弱':
            pct = skill.sub_param / 100.0
            if debuff_amp_mode == 'magic_amp':
                pct = min(0.50, pct * (1.0 + (m_amp - 1.0) * 0.30))
            elif debuff_amp_mode == 'init_amp':
                pct = min(0.50, pct * (1.0 + preempt_bonus))
            elif debuff_amp_mode == 'both':
                pct = min(0.50, pct * (1.0 + (m_amp - 1.0) * 0.25) * (1.0 + preempt_bonus * 0.5))
            defender.stat_reduce_debuffs.append({'pct': pct, 'turns': skill.sub_duration})

    sim.execute_turn_action = custom_exec
    sims = 1000
    genres = ['M_R', 'M_I', 'M_C', 'C_I', 'C_R', 'R_I']
    wm = {g1: {g2: 0 for g2 in genres} for g1 in genres}
    for i in range(len(genres)):
        for j in range(i, len(genres)):
            g1, g2 = genres[i], genres[j]
            if g1 == g2:
                wm[g1][g2] = sims // 2
                continue
            for _ in range(sims):
                t1 = sim.assemble_hybrid_troop(g1)
                t2 = sim.assemble_hybrid_troop(g2)
                res = sim.run_battle(t1, t2)
                if res['winner'].name == t1.name: wm[g1][g2] += 1
                else: wm[g2][g1] += 1
    wr = {g: sum(wm[g][g2] for g2 in genres) / (sims * len(genres)) * 100.0 for g in genres}
    summary = "  ".join(f"{k}:{v:.1f}%" for k, v in wr.items())
    print(f"[{debuff_amp_mode:<9} | {true_dmg_amp_mode:<17}] -> M_I: {wr['M_I']:.1f}% | {summary}")

if __name__ == '__main__':
    print("=== 基准 ===")
    test_mechanic('none', 'none')
    print("\n=== 方向 1: Debuff 百分比受先机 / 魔力增幅 ===")
    test_mechanic('magic_amp', 'none')
    test_mechanic('init_amp', 'none')
    test_mechanic('both', 'none')
    print("\n=== 方向 2: 纯真伤受魔力 / 先机增幅 ===")
    test_mechanic('none', 'magic_true_bonus')
    test_mechanic('none', 'preempt_double_on_true')
    print("\n=== 组合验证 ===")
    test_mechanic('magic_amp', 'magic_true_bonus')
    test_mechanic('init_amp', 'magic_true_bonus')
    test_mechanic('both', 'magic_true_bonus')
