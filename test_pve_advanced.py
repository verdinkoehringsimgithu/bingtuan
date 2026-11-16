# -*- coding: utf-8 -*-
"""
Testing Punching Above Weight with Healing-from-Enemy and FateSwap
"""
import random
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from test_sweet_spot_balance import (
    Troop, BattleSkill, calc_resilience_dr, calc_magic_amp_responsive
)

def test_pve_advanced():
    def make_boss():
        b = Troop(99, "守门重装巨兽", 15, c=100, r=600, i=100, m=100, max_bp=720000)
        b.skills.append(BattleSkill(9901, "重岩猛击", 3, "通用", "Attack", main_param=120.0, trigger_chance=40.0))
        b.skills.append(BattleSkill(9902, "泰山碎地", 4, "通用", "Attack", main_param=135.0, trigger_chance=30.0))
        return b

    # 方案 A: 借力打力吸血流 (基于敌方战力吸取与回复)
    def p_vampire():
        p = Troop(1, "借力吸血流", 15, c=100, r=200, i=150, m=420, max_bp=360000)
        # 命中造成 140% 伤害，吸取造成伤害的 50% 战力
        # 对 72万 Boss: 造成 7万伤害，吸回 3.5万战力 (占自身 10% 血条)
        p.skills.append(BattleSkill(101, "噬魂魔刃", 4, "魔力", "Attack", main_param=150.0, trigger_chance=45.0, is_true_damage=True, sub_effect="lifesteal", sub_param=0.45))
        # 敌当前战力反噬 18%
        p.skills.append(BattleSkill(102, "暗影虹吸", 4, "魔力", "Attack", main_param=100.0, trigger_chance=40.0, sub_effect="enemy_cur_dmg", sub_param=0.18))
        return p

    # 方案 B: 宿命互换刺客 (FateSwap: 自身残血时与 Boss 互换战力百分比 + 斩杀)
    def p_fateswap():
        p = Troop(2, "宿命互换刺客", 15, c=350, r=100, i=200, m=350, max_bp=360000)
        p.death_defy = 1
        # 自身残血反杀互换
        p.skills.append(BattleSkill(201, "宿命互换", 4, "魔力", "Attack", main_param=100.0, trigger_chance=60.0, self_bp_cond2=30, times_limit=1, sub_effect="fate_swap"))
        p.skills.append(BattleSkill(202, "虚空穿刺", 4, "魔力", "Attack", main_param=170.0, trigger_chance=40.0, is_true_damage=True))
        p.skills.append(BattleSkill(203, "残血重劈", 3, "勇气", "Attack", main_param=180.0, trigger_chance=35.0, enemy_bp_cond2=45))
        return p

    # 方案 C: 高闪避持续剧毒流 (先机+魔力: 40% 闪避躲伤害，DoT 持续流失)
    def p_dodge_dot():
        p = Troop(3, "高闪避剧毒流", 15, c=80, r=100, i=480, m=380, max_bp=360000)
        # 480 先机带来 ~26% 基础闪避 + 技能虚弱
        p.skills.append(BattleSkill(301, "迷踪剧毒", 4, "魔力", "Attack", main_param=120.0, trigger_chance=50.0, turn_cond2=3, times_limit=1, exhaust_turns=1, sub_effect="combo_dot", sub_param=0.045, sub_base=18000, sub_duration=3))
        p.skills.append(BattleSkill(302, "迅影虚弱", 4, "先机", "Attack", main_param=130.0, trigger_chance=40.0, exhaust_turns=1))
        p.skills.append(BattleSkill(303, "常态侵蚀", 3, "魔力", "Attack", main_param=110.0, trigger_chance=35.0, sub_effect="dot_max", sub_param=0.035, sub_duration=2))
        return p

    # 执行自定义战斗
    def run_battle_custom(t1, t2, max_turns=25):
        t1.reset()
        t2.reset()
        for turn in range(1, max_turns + 1):
            # 回合前 DoT
            for trp, oppo in [(t1, t2), (t2, t1)]:
                if trp.is_dead(): continue
                if trp.max_bp_dots:
                    _, pct_dr = calc_resilience_dr(trp.resilience)
                    new_dots = []
                    for dot in trp.max_bp_dots:
                        raw = trp.max_bp * dot['val']
                        act = max(1.0, raw * (1.0 - pct_dr))
                        trp.current_bp -= act
                        dot['turns'] -= 1
                        if dot['turns'] > 0: new_dots.append(dot)
                    trp.max_bp_dots = new_dots

            if t1.is_dead() or t2.is_dead(): break

            # 行动
            first, second = (t1, t2) if t1.initiative >= t2.initiative else (t2, t1)
            for acting, defender in [(first, second), (second, first)]:
                if acting.is_dead() or defender.is_dead(): break
                base_pow = acting.max_bp * 0.15 + acting.current_bp * 0.08
                m_amp = calc_magic_amp_responsive(acting.magic)
                dodge_rate, _ = (0.28, 0.0) if acting == t2 and t1.name == "高闪避剧毒流" else (0.05, 0.0)
                
                # 选技
                skill = None
                for s in acting.skills:
                    u = acting.usage.get(s.id, 0)
                    if s.can_trigger(turn, acting.bp_pct, defender.bp_pct, u):
                        if random.random() * 100.0 < s.trigger_chance:
                            skill = s
                            acting.usage[s.id] = u + 1
                            break
                if skill is None:
                    skill = BattleSkill(999, "普攻", 1, "普", "Attack", 100.0)

                # 闪避
                if random.random() < dodge_rate:
                    defender.dodge_count += 1
                    continue

                if skill.sub_effect == "fate_swap":
                    # 宿命战力百分比互换
                    r1 = acting.current_bp / acting.max_bp
                    r2 = defender.current_bp / defender.max_bp
                    acting.current_bp = r2 * acting.max_bp
                    defender.current_bp = r1 * defender.max_bp
                    continue

                raw = base_pow * (skill.main_param / 100.0)
                if acting.exhaust_turns > 0:
                    raw = 1.0
                    acting.exhaust_turns = 0

                act_dmg = defender.take_damage(raw, is_true=skill.is_true_damage, def_obj=defender)
                
                # 附加效果
                if skill.sub_effect == "enemy_cur_dmg":
                    ex = defender.current_bp * (skill.sub_param * m_amp)
                    defender.take_damage(ex, is_true=False, def_obj=defender)
                elif skill.sub_effect == "lifesteal":
                    acting.heal(act_dmg * (skill.sub_param * m_amp))
                elif skill.sub_effect == "combo_dot":
                    defender.max_bp_dots.append({'val': skill.sub_param * m_amp, 'turns': skill.sub_duration})
                elif skill.sub_effect == "dot_max":
                    defender.max_bp_dots.append({'val': skill.sub_param * m_amp, 'turns': skill.sub_duration})

                if skill.exhaust_turns > 0:
                    defender.exhaust_turns = max(defender.exhaust_turns, skill.exhaust_turns)

        winner = t1 if (not t1.is_dead() and t2.is_dead()) else (t2 if (not t2.is_dead() and t1.is_dead()) else (t1 if t1.bp_pct >= t2.bp_pct else t2))
        return {'winner': winner, 'turns': turn}

    builds = [
        ("方案 A: 借力吸血流 (基于敌方战力吸血+反噬)", p_vampire),
        ("方案 B: 宿命互换刺客 (残血互换战力百分比)", p_fateswap),
        ("方案 C: 高闪避持续剧毒流 (闪避+虚弱+持续流失)", p_dodge_dot),
    ]

    print("=" * 85)
    print("【深度攻坚检验：特定战术机制对 2.0x Boss 的越级破局能力】")
    print("=" * 85)
    sims = 2000
    for name, maker in builds:
        wins = 0
        total_t = 0
        for _ in range(sims):
            player = maker()
            boss = make_boss()
            res = run_battle_custom(player, boss)
            if res['winner'] == player: wins += 1
            total_t += res['turns']
        wr = (wins / sims) * 100.0
        avg_t = total_t / sims
        print(f"{name}: 胜率 {wr:>5.1f}% | 平均回合: {avg_t:>4.1f}")

if __name__ == '__main__':
    test_pve_advanced()
