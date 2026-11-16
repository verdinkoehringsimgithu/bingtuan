# -*- coding: utf-8 -*-
"""
Deep Diagnostic & Experimental Fixes for Combat Balance:
1. Pacing adjustment: Can we reach 6~10 turns by adjusting base strike formula or Resilience scaling?
2. PVE Punching Above Weight: How can Strategy (Debuff, Weak, Dodge, True Damage, DoT) allow 20%~40% win rate against a 2x Boss?
3. Magic Curve: Test non-linear response curve vs linear curve across all scales.
4. Perceived Skill Impact: Test Crisis Healing & Sub-effects.
"""
import random
import math
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from test_progression_balance import (
    BattleSkill, BattleTroop, create_roster_for_scale,
    calc_courage_stats, calc_initiative_stats
)

# ------------------------------------------------------------------------------
# 试验 A: 坚韧减伤与节奏调节试验 (将过快的 3~4 回合拉长到 6~10 回合黄金区间)
# ------------------------------------------------------------------------------
def calc_resilience_dr_improved(resilience, scale=30):
    """
    原版公式: pct_dr = 0.20 + (R / (R + 500)) * 0.45, flat_dr = R * 16
    问题: 在 5~15 人阶段，R 只有 50~220，减伤只有 25%~33%，而基础打击直接吃 30% MaxBP，导致 2~3 刀暴毙。
    改进方案:
    - 基础保底减伤提升至 30%，使早期不至于被普攻 2 刀秒杀
    - 动态成长: pct_dr = 0.30 + (R / (R + 450)) * 0.45 (封顶 70%)
    - 固定减伤 flat_dr 适应阶段比例
    """
    pct_dr = min(0.70, 0.30 + (resilience / (resilience + 450.0)) * 0.45)
    flat_dr = resilience * 20.0
    return flat_dr, pct_dr


def calc_magic_amp_responsive_tuned(magic):
    """
    阶段响应式魔力放大公式:
    早期 (M=50) 给予快速感知 (1.25x)，中期 (M=200) 到达 (1.70x)，后期 (M=1000) 平稳收敛至 (3.0x)
    公式: 1.0 + (M / (M + 250.0)) * 1.5 + (M / 1500.0) * 0.5
    """
    if magic <= 0: return 1.0
    return 1.0 + (magic / (magic + 250.0)) * 1.5 + (magic / 1500.0) * 0.5


# ------------------------------------------------------------------------------
# 试验 B: 越级挑战攻坚支持机制验证
# ------------------------------------------------------------------------------
def test_improved_pve_and_pacing():
    print("=" * 95)
    print("【深度诊断与平衡调优试验】")
    print("=" * 95)

    # 1. 节奏改善验证: 对比原版 vs 调优后的战斗回合数
    print("\n>>> 试验 1: 节奏调优测试 (基础输出权重调整为 0.14 MaxBP + 0.08 CurBP，使交锋进入 6~10 回合)")
    
    # 模拟 30人规模对局
    scales = [5, 15, 30]
    for sc in scales:
        t_courage = create_roster_for_scale(sc, "勇气+先机")
        t_resil = create_roster_for_scale(sc, "坚韧+先机")
        
        # 统计原版
        from test_progression_balance import run_single_battle
        turns_orig = []
        for _ in range(200):
            r = run_single_battle(t_courage, t_resil)
            turns_orig.append(r['turns'])
        avg_orig = sum(turns_orig) / len(turns_orig)

        print(f"  * 【{sc}人规模】当前原版平均回合: {avg_orig:.1f} 回合")

    # 2. 越级挑战攻坚破解分析
    print("\n\n>>> 试验 2: 越级挑战 (15人 36万战力 vs 72万战力 Boss) 破局条件测试")
    print("测试思路: 赋予玩家真实的策略工具 (如: 先手虚弱降低Boss伤害、真伤无视Boss护甲、百分比流失磨血、致死保护)")

    # 增强策略工具后的 15人玩家
    p_true = create_roster_for_scale(15, "魔力真伤")
    p_dot  = create_roster_for_scale(15, "魔力DoT")
    
    # Boss: 72万战力, 600坚韧
    boss = BattleTroop(99, "守门重装巨神", 15, courage=100, resilience=600, initiative=100, magic=100, max_bp=720000)
    boss.skills.append(BattleSkill(9901, "巨岩猛击", 3, "通用", "Attack", main_param=120.0, trigger_chance=40.0))
    boss.skills.append(BattleSkill(9902, "泰山压顶", 4, "通用", "Attack", main_param=140.0, trigger_chance=30.0))

    print("已构建对比试验环境。")

if __name__ == '__main__':
    test_improved_pve_and_pacing()
