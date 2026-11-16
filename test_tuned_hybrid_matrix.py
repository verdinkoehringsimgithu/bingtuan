# -*- coding: utf-8 -*-
"""
Fine-tuning hybrid skill compositions to reflect proper Archetype design:
Courage+Initiative (C_I) should utilize Initiative debuffs/weakness to buy time for crit executions!
"""
import random
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from test_crit_pierce_matrix import (
    Troop, BattleSkill, run_battle_with_crit_pierce,
    create_hybrid_roster
)
from test_hybrid_synergy_and_balance import name_prefix

def create_hybrid_roster_tuned(scale, genre_code):
    troop = create_hybrid_roster(scale, genre_code)
    bp = troop.max_bp
    max_t = {5: 2, 10: 3, 15: 4, 20: 5, 25: 6, 30: 6}[scale]

    # 给 C_I (勇气+先机) 赋予合理的先机机制技能 (先手削弱/虚弱控场，契合双属性搭配)
    if genre_code == "C_I":
        troop.skills.clear()
        if max_t <= 2:
            troop.skills.append(BattleSkill(1, "迅捷先锋", 1, "先机", "Attack", 125.0, 35.0))
            troop.skills.append(BattleSkill(2, "破阵狂劈", 2, "勇气", "Attack", 145.0, 35.0))
        elif max_t <= 4:
            # 引入先机开局虚弱控场 (为暴击争取轮次)
            troop.skills.append(BattleSkill(1, "封脉疾袭", 4, "先机", "Attack", 140.0, 45.0, turn_cond2=3, times_limit=1, exhaust_turns=1))
            troop.skills.append(BattleSkill(2, "绝境致命斩", 4, "勇气", "Attack", 250.0, 40.0, enemy_bp_cond2=45, times_limit=1))
            troop.skills.append(BattleSkill(3, "裂地巨刃", 3, "勇气", "Attack", 160.0, 30.0))
            troop.skills.append(BattleSkill(4, "常态影刃", 3, "先机", "Attack", 140.0, 25.0))
        else:
            troop.skills.append(BattleSkill(1, "瞬狱封穴破", 6, "先机", "Attack", 160.0, 50.0, turn_cond2=3, times_limit=1, exhaust_turns=1))
            troop.skills.append(BattleSkill(2, "终极绝命斩", 6, "勇气", "Attack", 340.0, 50.0, enemy_bp_cond2=45, times_limit=1))
            troop.skills.append(BattleSkill(3, "狂风重斩", 5, "勇气", "Attack", 180.0, 35.0))
            troop.skills.append(BattleSkill(4, "死线连刺", 5, "先机", "Attack", 165.0, 30.0))

    return troop

def test_tuned_matrix():
    genres = ["M_R", "M_I", "M_C", "C_I", "C_R", "R_I"]
    genre_names = {
        "M_R": "魔力+坚韧(阵地DoT)",
        "M_I": "魔力+先机(灵动真伤)",
        "M_C": "魔力+勇气(暴击真伤)",
        "C_I": "勇气+先机(速攻暴击)",
        "C_R": "勇气+坚韧(残血反噬)",
        "R_I": "坚韧+先机(防守反击)"
    }
    
    sims = 1500
    wins_matrix = {g1: {g2: 0 for g2 in genres} for g1 in genres}
    
    for i in range(len(genres)):
        for j in range(i, len(genres)):
            g1, g2 = genres[i], genres[j]
            if g1 == g2:
                wins_matrix[g1][g2] = sims // 2
                continue
            for _ in range(sims):
                t1 = create_hybrid_roster_tuned(30, g1)
                t2 = create_hybrid_roster_tuned(30, g2)
                res = run_battle_with_crit_pierce(t1, t2)
                if res['winner'].name.startswith(t1.name[:5]):
                    wins_matrix[g1][g2] += 1
                else:
                    wins_matrix[g2][g1] += 1

    print("=" * 100)
    print("【深度调优后 六大复合流派 终极对决矩阵 (30 人完全体，22,500 局对抗)】")
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
    test_tuned_matrix()
