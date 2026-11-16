# -*- coding: utf-8 -*-
"""
Full Progression Stages Evaluation with Tuned Hybrids (5, 10, 15, 20, 25, 30)
"""
import sys
if sys.platform == 'win32': sys.stdout.reconfigure(encoding='utf-8')

from test_tuned_hybrid_matrix import (
    create_hybrid_roster_tuned, run_battle_with_crit_pierce
)

def run_progression_evaluation():
    scales = [5, 10, 15, 20, 25, 30]
    genres = ["M_R", "M_I", "M_C", "C_I", "C_R", "R_I"]
    genre_names = {
        "M_R": "魔力+坚韧(阵地)",
        "M_I": "魔力+先机(灵动)",
        "M_C": "魔力+勇气(核弹)",
        "C_I": "勇气+先机(速攻)",
        "C_R": "勇气+坚韧(反噬)",
        "R_I": "坚韧+先机(防反)"
    }

    print("=" * 105)
    print("【全阶梯人数上限 (5/10/15/20/25/30) 综合平衡演进与节奏全貌 (各阶段 3,000 局抽样)】")
    print("=" * 105)

    for sc in scales:
        tot_wins = {g: 0 for g in genres}
        tot_matches = {g: 0 for g in genres}
        all_turns = []
        sims = 200

        for i in range(len(genres)):
            for j in range(i + 1, len(genres)):
                g1, g2 = genres[i], genres[j]
                for _ in range(sims):
                    t1 = create_hybrid_roster_tuned(sc, g1)
                    t2 = create_hybrid_roster_tuned(sc, g2)
                    res = run_battle_with_crit_pierce(t1, t2)
                    all_turns.append(res['turns'])
                    if res['winner'].name.startswith(t1.name[:5]):
                        tot_wins[g1] += 1
                    else:
                        tot_wins[g2] += 1
                    tot_matches[g1] += 1
                    tot_matches[g2] += 1

        avg_turns = sum(all_turns) / len(all_turns)
        bp_val = create_hybrid_roster_tuned(sc, "M_R").max_bp

        row_str = f"【{sc:>2} 人规模 (战力 {bp_val:>9,}) | 平均交锋 {avg_turns:>4.1f} 回合】: "
        for g in genres:
            wr = (tot_wins[g] / tot_matches[g]) * 100.0
            row_str += f"{genre_names[g][:4]}:{wr:>4.1f}%  "
        print(row_str)

if __name__ == '__main__':
    run_progression_evaluation()
