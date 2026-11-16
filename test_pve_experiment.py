# -*- coding: utf-8 -*-
"""
Experimenting with Punching-Above-Weight (越级挑战) Archetypes:
Player: 15-man troop, 360,000 BP.
Boss: 720,000 BP (2.0x BP), 600 Resilience (High Armor Tank).

Test 4 Different Player Builds against Boss:
1. Standard Direct Damage (Baseline)
2. Pure True Damage Burst (Bypasses Boss Armor)
3. DoT Erosion + Weakness / Exhaust (Bypasses HP & neutralizes Boss turns)
4. Strategic Crisis Counter (Resist Lethal + Fury Strike on lost HP + Dodge)
"""
import random
import math
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from test_progression_balance import (
    BattleSkill, BattleTroop, calc_resilience_dr, calc_initiative_stats, calc_courage_stats
)

def run_pve_experiment(sims=2000):
    # Boss: 720,000 BP, 600 Resilience (54.5% DR, flat DR 9600), 100 Speed
    def make_boss():
        boss = BattleTroop(99, "守关巨兽(72万战力/600坚韧)", 15, courage=100, resilience=600, initiative=100, magic=100, max_bp=720000)
        boss.skills.append(BattleSkill(9901, "巨岩猛击", 3, "通用", "Attack", main_param=120.0, trigger_chance=40.0))
        boss.skills.append(BattleSkill(9902, "泰山压顶", 4, "通用", "Attack", main_param=140.0, trigger_chance=30.0))
        return boss

    # 1. 基准纯物理队 (勇气+先机)
    def make_player_baseline():
        p = BattleTroop(1, "常规物理队", 15, courage=480, resilience=60, initiative=220, magic=60, max_bp=360000)
        p.skills.append(BattleSkill(101, "破阵狂斩", 3, "勇气", "Attack", main_param=165.0, trigger_chance=35.0))
        p.skills.append(BattleSkill(102, "绝境斩", 4, "勇气", "Attack", main_param=220.0, trigger_chance=35.0, self_bp_cond2=45))
        return p

    # 2. 纯真伤穿甲队 (魔力真伤: 100% 破甲与纯粹真伤)
    def make_player_true():
        p = BattleTroop(2, "纯真伤穿透队", 15, courage=60, resilience=60, initiative=220, magic=480, max_bp=360000)
        # 技能带有纯粹真伤 (完全无视 Boss 600坚韧)
        p.skills.append(BattleSkill(201, "奥能贯通炮", 4, "魔力真伤", "Attack", main_param=180.0, trigger_chance=45.0, is_true_damage=True))
        p.skills.append(BattleSkill(202, "纯粹裂魂击", 4, "魔力真伤", "Attack", main_param=160.0, trigger_chance=40.0, is_true_damage=True))
        return p

    # 3. 策略控制流失队 (虚弱/控制争取轮次 + 最大战力 DoT 蚕食 Boss 巨量血条)
    def make_player_control_dot():
        p = BattleTroop(3, "控制侵蚀队", 15, courage=60, resilience=220, initiative=100, magic=480, max_bp=360000)
        # 开局给 Boss 挂 虚弱(降低其50%伤害) + 4.5% 最大战力流失
        p.skills.append(BattleSkill(301, "虚弱侵蚀", 4, "魔力DoT", "Attack", main_param=120.0, trigger_chance=50.0, turn_cond2=3, times_limit=1, sub_effect="combo_dot", sub_param=0.045, sub_base=18000, sub_duration=3))
        # 控场衰弱: 削弱 Boss 伤害 50%
        p.skills.append(BattleSkill(302, "绝力封印", 4, "魔力DoT", "Attack", main_param=110.0, trigger_chance=35.0, sub_effect="weak", sub_param=0.50, sub_duration=2))
        # 常态 3.5% 流失
        p.skills.append(BattleSkill(303, "常态剧毒", 3, "魔力DoT", "Attack", main_param=110.0, trigger_chance=35.0, sub_effect="dot_max", sub_param=0.035, sub_duration=2))
        return p

    # 4. 逆境保命反杀队 (致死保护保留1战力 + 自身已损高额反噬 + 高闪避)
    def make_player_crisis():
        p = BattleTroop(4, "绝境反杀队", 15, courage=480, resilience=220, initiative=100, magic=60, max_bp=360000)
        # 开局挂 1 次致死保护
        # 自身已损 45% 反噬 (在濒死时造成巨大伤害)
        p.skills.append(BattleSkill(401, "背水浴血斩", 4, "勇气", "Attack", main_param=160.0, trigger_chance=50.0, self_bp_cond2=35, sub_effect="self_lost_dmg", sub_param=0.45))
        p.skills.append(BattleSkill(402, "危机大急救", 4, "坚韧", "Heal", main_param=100.0, trigger_chance=40.0, self_bp_cond2=40, sub_effect="self_max_heal", sub_param=0.18))
        p.skills.append(BattleSkill(403, "常态反击", 3, "勇气", "Attack", main_param=150.0, trigger_chance=30.0))
        return p

    builds = [
        ("1. 常规物理队 (无特化机制)", make_player_baseline),
        ("2. 纯真伤穿透队 (破防特化)", make_player_true),
        ("3. 控制侵蚀队 (流失+虚弱特化)", make_player_control_dot),
        ("4. 绝境反杀队 (逆境斩杀+急救)", make_player_crisis),
    ]

    from test_progression_balance import run_single_battle

    print("=" * 90)
    print("【越级挑战 (PVE) 机制有效性验证：15人 (36万战力) VS 72万战力 高防 Boss】")
    print("=" * 90)

    for name, maker in builds:
        wins = 0
        total_turns = 0
        boss_rem_bp = 0.0
        for _ in range(sims):
            player = maker()
            boss = make_boss()
            res = run_single_battle(player, boss, max_turns=25)
            if res['winner'] == player:
                wins += 1
            total_turns += res['turns']
            boss_rem_bp += (boss.current_bp / boss.max_bp) * 100.0

        wr = (wins / sims) * 100.0
        avg_t = total_turns / sims
        avg_rem = boss_rem_bp / sims
        print(f"\n{name}:")
        print(f"  * 胜率: {wr:>5.1f}% | 平均坚持回合: {avg_t:>4.1f} 回合 | 战局结束时Boss平均剩余血量: {avg_rem:>5.1f}%")

if __name__ == '__main__':
    run_pve_experiment(2000)
