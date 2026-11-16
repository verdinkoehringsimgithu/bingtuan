# -*- coding: utf-8 -*-
"""
PVE Punching Above Weight with Enemy-HP-based mechanics:
Testing how skills based on Enemy HP (敌方当前战力%、敌方最大战力%、吸血) and Exhaust/Dodge
allow an underdog (360k) to strategically defeat a 2.0x Boss (720k).
"""
import random
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from test_sweet_spot_balance import (
    Troop, BattleSkill, run_battle, calc_resilience_dr, calc_magic_amp_responsive
)

def test_pve_with_enemy_scaling():
    def make_boss():
        b = Troop(99, "守门重装巨兽", 15, c=100, r=600, i=100, m=100, max_bp=720000)
        b.skills.append(BattleSkill(9901, "重岩猛击", 3, "通用", "Attack", main_param=120.0, trigger_chance=40.0))
        b.skills.append(BattleSkill(9902, "泰山碎地", 4, "通用", "Attack", main_param=135.0, trigger_chance=30.0))
        return b

    # 1. 纯直伤物理 (对照组)
    def p_brute():
        p = Troop(1, "纯直伤物理队", 15, c=480, r=60, i=220, m=60, max_bp=360000)
        p.skills.append(BattleSkill(101, "狂暴重劈", 3, "勇气", "Attack", main_param=160.0, trigger_chance=40.0))
        p.skills.append(BattleSkill(102, "绝境斩", 4, "勇气", "Attack", main_param=220.0, trigger_chance=35.0, self_bp_cond2=45))
        return p

    # 2. 敌方当前战力反噬流 (根据敌方战力造成伤害)
    def p_siphon():
        p = Troop(2, "敌战力反噬流", 15, c=100, r=100, i=200, m=450, max_bp=360000)
        # 命中后造成对方当前战力 18% 伤害 (受魔力放大后 ~28%)
        p.skills.append(BattleSkill(201, "暗影虹吸", 4, "魔力", "Attack", main_param=100.0, trigger_chance=45.0, sub_effect="enemy_cur_dmg", sub_param=0.18))
        # 纯真伤穿透
        p.skills.append(BattleSkill(202, "奥能贯通炮", 4, "魔力", "Attack", main_param=160.0, trigger_chance=35.0, is_true_damage=True))
        return p

    # 3. 持续侵蚀+虚弱控场流 (DoT + 虚弱令Boss打出1点伤害)
    def p_dot_control():
        p = Troop(3, "侵蚀控场流", 15, c=80, r=200, i=120, m=450, max_bp=360000)
        # 开局挂 4.5% 最大战力 DoT + 虚弱 1 回合
        p.skills.append(BattleSkill(301, "腐蚀封印", 4, "魔力", "Attack", main_param=115.0, trigger_chance=50.0, turn_cond2=3, times_limit=1, exhaust_turns=1, sub_effect="combo_dot", sub_param=0.045, sub_base=18000, sub_duration=3))
        # 虚弱压制 (命中令敌人下一次攻击仅造成1点伤害)
        p.skills.append(BattleSkill(302, "衰弱诅咒", 4, "魔力", "Attack", main_param=120.0, trigger_chance=35.0, exhaust_turns=1))
        # 持续流失
        p.skills.append(BattleSkill(303, "常态剧毒", 3, "魔力", "Attack", main_param=110.0, trigger_chance=35.0, sub_effect="dot_max", sub_param=0.035, sub_duration=2))
        return p

    # 4. 全机制攻坚特化队 (虹吸 + 侵蚀 + 虚弱 + 1次名刀)
    def p_full_strategy():
        p = Troop(4, "全机制攻坚队", 15, c=100, r=180, i=160, m=420, max_bp=360000)
        p.death_defy = 1
        # 开局虚弱 + 侵蚀
        p.skills.append(BattleSkill(401, "天谴之锁", 4, "魔力", "Attack", main_param=130.0, trigger_chance=50.0, turn_cond2=3, times_limit=1, exhaust_turns=1, sub_effect="combo_dot", sub_param=0.040, sub_base=16000, sub_duration=3))
        # 敌当前战力反噬 16%
        p.skills.append(BattleSkill(402, "灵魂抽取", 4, "魔力", "Attack", main_param=100.0, trigger_chance=40.0, sub_effect="enemy_cur_dmg", sub_param=0.16))
        # 自身残血大急救 (恢复 16% MaxBP)
        p.skills.append(BattleSkill(403, "生命复苏", 4, "坚韧", "Heal", main_param=100.0, trigger_chance=40.0, self_bp_cond2=40, times_limit=1, sub_effect="self_max_heal", sub_param=0.16))
        # 常态真伤
        p.skills.append(BattleSkill(404, "奥法冲击", 3, "魔力", "Attack", main_param=135.0, trigger_chance=30.0, is_true_damage=True))
        return p

    challengers = [
        ("1. 纯直伤物理队 (无策略盲目对砍)", p_brute),
        ("2. 敌战力反噬流 (按Boss血量反噬)", p_siphon),
        ("3. 侵蚀控场流   (DoT磨血+虚弱抢轮次)", p_dot_control),
        ("4. 全机制攻坚队 (反噬+侵蚀+控场+名刀)", p_full_strategy),
    ]

    sims = 2000
    print("=" * 90)
    print("【越级攻坚测试：引入敌方战力百分比反噬与虚弱机制 (36万 挑战 72万 Boss)】")
    print("=" * 90)

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
        print(f"  * 越级胜率: {wr:>5.1f}% | 平均回合: {avg_t:>4.1f} | 结束时Boss平均剩余血量: {rem:>5.1f}%")

if __name__ == '__main__':
    test_pve_with_enemy_scaling()
