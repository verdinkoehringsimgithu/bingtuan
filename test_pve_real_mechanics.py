# -*- coding: utf-8 -*-
"""
Testing PVE Punching Above Weight with True Game Mechanics:
1. Exhaust (虚弱: 敌方下一次攻击只会造成 1 点伤害)
2. Resist Lethal (受到致命伤保留 1 战力)
3. Percentage Siphon (造成敌方当前战力 20%~30% 伤害)
4. Fate Swap (自身战力 < 20% 且 敌方 > 70% 时，双方当前战力百分比互换)
"""
import random
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def simulate_pve_with_real_mechanics(sims=2000):
    class Troop:
        def __init__(self, name, max_bp, def_val, ddg_val):
            self.name = name
            self.max_bp = float(max_bp)
            self.current_bp = float(max_bp)
            self.defense = def_val
            self.dodge = ddg_val
            self.exhaust_turns = 0
            self.resist_lethal = False
            self.dots = []

        def take_damage(self, dmg, is_true=False):
            if is_true:
                final_dmg = dmg
            else:
                # 原生免伤公式: 100 / (100 + defense)
                dr_factor = 100.0 / (100.0 + max(-50.0, self.defense))
                final_dmg = dmg * dr_factor
            
            final_dmg = max(1.0, final_dmg)
            self.current_bp -= final_dmg
            if self.current_bp <= 0:
                if self.resist_lethal:
                    self.current_bp = 1.0
                    self.resist_lethal = False
                else:
                    self.current_bp = 0.0
            return final_dmg

    # 测试方案: 15人玩家 (36万战力) VS 72万战力 Boss
    # 方案 1: 无策略 (纯普攻)
    # 方案 2: 魔力真伤 (纯粹真伤无视 Boss 护甲)
    # 方案 3: 虚弱控场 (Exhaust: 命中间隔让 Boss 攻击变 1 点)
    # 方案 4: 机制斩杀 (名刀锁血 1 次 + 敌方当前战力反噬 25% + 自身已损战力反噬 45%)
    # 方案 5: 宿命互换 (FateSwap: 自身残血时与 Boss 互换战力百分比)

    strategies = ["1.无策略常规物理", "2.纯粹真伤破防", "3.虚弱控场压制", "4.名刀残血反杀", "5.宿命战力互换"]

    print("=" * 85)
    print("【实装原版真实机制后的 越级挑战 (PVE) 胜率对比】")
    print("玩家: 360,000 战力 | Boss: 720,000 战力 (600 防御)")
    print("=" * 85)

    for strat_idx, strat_name in enumerate(strategies, 1):
        wins = 0
        total_turns = 0
        for _ in range(sims):
            player = Troop("玩家", 360000, def_val=150, ddg_val=80)
            boss = Troop("Boss", 720000, def_val=600, ddg_val=20)
            
            if strat_idx == 4:
                player.resist_lethal = True  # 方案 4 携带 1 次名刀保命
            
            turn = 0
            while turn < 20 and player.current_bp > 0 and boss.current_bp > 0:
                turn += 1
                
                # 玩家行动
                base_power = player.max_bp * 0.20 + player.current_bp * 0.10
                if strat_idx == 1:
                    # 纯常规物理攻击 (130% 伤害，受 Boss 600 防御削减)
                    boss.take_damage(base_power * 1.30, is_true=False)

                elif strat_idx == 2:
                    # 纯粹真伤 (160% 伤害，完全无视防御)
                    boss.take_damage(base_power * 1.60, is_true=True)

                elif strat_idx == 3:
                    # 虚弱控场 (120% 伤害，35% 几率令 Boss 下回合伤害变 1 点)
                    boss.take_damage(base_power * 1.20, is_true=False)
                    if random.random() < 0.35:
                        boss.exhaust_turns = 1

                elif strat_idx == 4:
                    # 名刀残血反杀:
                    # 敌方当前战力反噬 18% + 自身残血时已损战力反噬 45%
                    cur_siphon = boss.current_bp * 0.18
                    lost_self = (player.max_bp - player.current_bp) * 0.45
                    boss.take_damage(cur_siphon + lost_self, is_true=True)

                elif strat_idx == 5:
                    # 宿命战力互换: 自身 < 25% 且 敌方 > 60% 时互换
                    p_ratio = player.current_bp / player.max_bp
                    b_ratio = boss.current_bp / boss.max_bp
                    if p_ratio < 0.25 and b_ratio > 0.60:
                        player.current_bp = b_ratio * player.max_bp
                        boss.current_bp = p_ratio * boss.max_bp
                    else:
                        boss.take_damage(base_power * 1.30, is_true=True)

                if boss.current_bp <= 0:
                    break

                # Boss 行动
                boss_power = boss.max_bp * 0.20 + boss.current_bp * 0.10
                raw_dmg = boss_power * 1.20
                if boss.exhaust_turns > 0:
                    raw_dmg = 1.0
                    boss.exhaust_turns = 0
                
                player.take_damage(raw_dmg, is_true=False)
                if player.current_bp <= 0:
                    break

            if boss.current_bp <= 0 and player.current_bp > 0:
                wins += 1
            total_turns += turn

        wr = (wins / sims) * 100.0
        avg_t = total_turns / sims
        print(f"  * {strat_name:<16}: 胜率 {wr:>5.1f}% | 平均回合: {avg_t:>4.1f}")

if __name__ == '__main__':
    simulate_pve_with_real_mechanics(2000)
