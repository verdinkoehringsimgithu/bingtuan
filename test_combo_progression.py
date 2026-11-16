# -*- coding: utf-8 -*-
"""
Verify progression across 5 to 30 people under the Ultimate Combo (Dir 1 + 2 + 3)
"""
import sys
if sys.platform == 'win32': sys.stdout.reconfigure(encoding='utf-8')

from test_courage_magic_buffs import (
    Troop, BattleSkill, run_battle_configurable
)

def create_progression_combo_troop(scale, genre_code):
    stage_configs = {
        5:  {'bp': 60000,   'main': 120,  'sub': 50,  'other': 20, 'max_tier': 2},
        10: {'bp': 180000,  'main': 280,  'sub': 130, 'other': 40, 'max_tier': 3},
        15: {'bp': 360000,  'main': 480,  'sub': 220, 'other': 60, 'max_tier': 4},
        20: {'bp': 600000,  'main': 700,  'sub': 340, 'other': 80, 'max_tier': 5},
        25: {'bp': 820000,  'main': 880,  'sub': 430, 'other': 90, 'max_tier': 6},
        30: {'bp': 1000000, 'main': 1000, 'sub': 500, 'other': 100, 'max_tier': 6},
    }
    cfg = stage_configs[scale]
    m_val, s_val, o_val = cfg['main'], cfg['sub'], cfg['other']
    bp = cfg['bp']
    max_t = cfg['max_tier']

    c, r, i, m = o_val, o_val, o_val, o_val
    name_map = {
        "M_R": "魔力+坚韧流",
        "M_I": "魔力+先机流",
        "M_C": "魔力+勇气流",
        "C_I": "勇气+先机流",
        "C_R": "勇气+坚韧流",
        "R_I": "坚韧+先机流"
    }

    if genre_code == "M_R": m = m_val; r = s_val
    elif genre_code == "M_I": m = m_val; i = s_val
    elif genre_code == "M_C": m = m_val; c = s_val
    elif genre_code == "C_I": c = m_val; i = s_val
    elif genre_code == "C_R": c = m_val; r = s_val
    elif genre_code == "R_I": r = m_val; i = s_val

    troop = Troop(1, f"{name_map[genre_code]}[{scale}人]", scale, c, r, i, m, bp)

    # 勇气基础倍率提升 20% (方向 3)
    c_boost = 1.20

    if genre_code == "M_R":
        if max_t <= 2:
            troop.skills.append(BattleSkill(1, "腐蚀毒雾", 1, "魔力", "Attack", 110.0, 35.0, sub_effect="dot_max", sub_param=0.030, sub_duration=2))
            troop.skills.append(BattleSkill(2, "圣佑急救", 2, "坚韧", "Heal", 100.0, 30.0, self_bp_cond2=75, sub_effect="self_max_heal", sub_param=0.08))
        elif max_t <= 4:
            troop.skills.append(BattleSkill(1, "万毒侵蚀", 4, "魔力", "Attack", 120.0, 45.0, turn_cond2=3, times_limit=1, sub_effect="combo_dot", sub_param=0.040, sub_base=bp*0.04, sub_duration=3))
            troop.skills.append(BattleSkill(2, "危机复苏", 4, "坚韧", "Heal", 100.0, 40.0, self_bp_cond2=50, times_limit=1, sub_effect="self_max_heal", sub_param=0.14))
            troop.skills.append(BattleSkill(3, "常态吸血", 3, "魔力", "Attack", 120.0, 25.0, sub_effect="lifesteal", sub_param=0.35))
        else:
            troop.skills.append(BattleSkill(1, "灭世剧毒", 6, "魔力", "Attack", 130.0, 50.0, turn_cond2=3, times_limit=1, sub_effect="combo_dot", sub_param=0.050, sub_base=bp*0.05, sub_duration=3))
            troop.skills.append(BattleSkill(2, "神恩涅槃", 6, "坚韧", "Heal", 100.0, 50.0, self_bp_cond2=40, times_limit=1, sub_effect="self_max_heal", sub_param=0.18))
            troop.skills.append(BattleSkill(3, "生命剥离", 5, "魔力", "Attack", 125.0, 35.0, sub_effect="dot_lost", sub_param=0.075, sub_duration=3))
            troop.skills.append(BattleSkill(4, "常态愈合", 5, "坚韧", "Heal", 100.0, 30.0, self_bp_cond2=65, sub_effect="self_max_heal", sub_param=0.12))

    elif genre_code == "M_I":
        if max_t <= 2:
            troop.skills.append(BattleSkill(1, "透甲穿心刺", 1, "魔力", "Attack", 125.0, 35.0, ignore_def_ratio=0.35))
            troop.skills.append(BattleSkill(2, "迅影突袭", 2, "先机", "Attack", 130.0, 30.0))
        elif max_t <= 4:
            troop.skills.append(BattleSkill(1, "虚弱穿甲杀", 4, "魔力", "Attack", 155.0, 45.0, turn_cond2=3, times_limit=1, exhaust_turns=1, is_true_damage=True))
            troop.skills.append(BattleSkill(2, "奥能贯通炮", 4, "魔力", "Attack", 175.0, 40.0, is_true_damage=True))
            troop.skills.append(BattleSkill(3, "破甲刃", 3, "魔力", "Attack", 140.0, 25.0, ignore_def_ratio=0.60))
        else:
            troop.skills.append(BattleSkill(1, "弑神断界斩", 6, "魔力", "Attack", 220.0, 50.0, is_true_damage=True, times_limit=1))
            troop.skills.append(BattleSkill(2, "瞬狱虚弱杀", 6, "先机", "Attack", 170.0, 45.0, turn_cond2=3, times_limit=1, exhaust_turns=1, is_true_damage=True))
            troop.skills.append(BattleSkill(3, "纯粹裂魂击", 5, "魔力", "Attack", 185.0, 35.0, is_true_damage=True))
            troop.skills.append(BattleSkill(4, "常态影刃", 5, "魔力", "Attack", 150.0, 30.0, ignore_def_ratio=0.75))

    elif genre_code == "M_C":
        # 魔力+勇气流 (享受魔力放大技能暴击率 + 溢出转暴伤 + 勇气倍率提升)
        if max_t <= 2:
            troop.skills.append(BattleSkill(1, "暴烈透甲破", 1, "魔力", "Attack", 130.0, 35.0, ignore_def_ratio=0.35, base_crit_rate=0.15))
            troop.skills.append(BattleSkill(2, "强袭重劈", 2, "勇气", "Attack", 140.0 * c_boost, 30.0, base_crit_rate=0.20))
        elif max_t <= 4:
            troop.skills.append(BattleSkill(1, "暴烈贯通炮", 4, "魔力", "Attack", 180.0, 45.0, is_true_damage=True, base_crit_rate=0.20))
            troop.skills.append(BattleSkill(2, "断头狂斩", 4, "勇气", "Attack", 220.0 * c_boost, 35.0, enemy_bp_cond2=50, base_crit_rate=0.25))
            troop.skills.append(BattleSkill(3, "虚空穿甲杀", 3, "魔力", "Attack", 150.0, 30.0, ignore_def_ratio=0.65, base_crit_rate=0.15))
        else:
            troop.skills.append(BattleSkill(1, "湮灭核弹斩", 6, "魔力", "Attack", 260.0, 50.0, is_true_damage=True, times_limit=1, base_crit_rate=0.20))
            troop.skills.append(BattleSkill(2, "终结暴击击", 6, "勇气", "Attack", 320.0 * c_boost, 45.0, enemy_bp_cond2=45, times_limit=1, base_crit_rate=0.30))
            troop.skills.append(BattleSkill(3, "纯粹裂魂击", 5, "魔力", "Attack", 200.0, 35.0, is_true_damage=True, base_crit_rate=0.15))
            troop.skills.append(BattleSkill(4, "破军重劈", 5, "勇气", "Attack", 180.0 * c_boost, 30.0, base_crit_rate=0.20))

    elif genre_code == "C_I":
        if max_t <= 2:
            troop.skills.append(BattleSkill(1, "迅捷先锋", 1, "先机", "Attack", 125.0, 35.0))
            troop.skills.append(BattleSkill(2, "破阵狂劈", 2, "勇气", "Attack", 145.0 * c_boost, 35.0, base_crit_rate=0.15))
        elif max_t <= 4:
            troop.skills.append(BattleSkill(1, "封脉疾袭", 4, "先机", "Attack", 140.0, 45.0, turn_cond2=3, times_limit=1, exhaust_turns=1))
            troop.skills.append(BattleSkill(2, "绝境致命斩", 4, "勇气", "Attack", 250.0 * c_boost, 40.0, enemy_bp_cond2=45, times_limit=1, base_crit_rate=0.20))
            troop.skills.append(BattleSkill(3, "裂地巨刃", 3, "勇气", "Attack", 160.0 * c_boost, 30.0, base_crit_rate=0.15))
        else:
            troop.skills.append(BattleSkill(1, "瞬狱封穴破", 6, "先机", "Attack", 170.0, 50.0, turn_cond2=3, times_limit=1, exhaust_turns=1))
            troop.skills.append(BattleSkill(2, "狂雷终结斩", 6, "勇气", "Attack", 380.0 * c_boost, 50.0, enemy_bp_cond2=45, times_limit=1, base_crit_rate=0.25))
            troop.skills.append(BattleSkill(3, "裂地狂劈",   5, "勇气", "Attack", 220.0 * c_boost, 40.0, base_crit_rate=0.20))
            troop.skills.append(BattleSkill(4, "常态影刃",   5, "先机", "Attack", 175.0, 30.0))

    elif genre_code == "C_R":
        if max_t <= 2:
            troop.skills.append(BattleSkill(1, "崩山破", 1, "勇气", "Attack", 140.0 * c_boost, 35.0, base_crit_rate=0.15))
            troop.skills.append(BattleSkill(2, "圣佑急救", 2, "坚韧", "Heal", 100.0, 30.0, self_bp_cond2=75, sub_effect="self_max_heal", sub_param=0.08))
        elif max_t <= 4:
            troop.skills.append(BattleSkill(1, "浴血舍身击", 4, "勇气", "Attack", 170.0 * c_boost, 45.0, self_bp_cond2=40, times_limit=1, sub_effect="self_lost_dmg", sub_param=0.30, base_crit_rate=0.20))
            troop.skills.append(BattleSkill(2, "战地苏生", 4, "坚韧", "Heal", 100.0, 40.0, self_bp_cond2=50, times_limit=1, sub_effect="self_max_heal", sub_param=0.14))
            troop.skills.append(BattleSkill(3, "反击重劈", 3, "勇气", "Attack", 150.0 * c_boost, 30.0, base_crit_rate=0.15))
        else:
            troop.skills.append(BattleSkill(1, "背水浴血斩", 6, "勇气", "Attack", 220.0 * c_boost, 50.0, self_bp_cond2=40, times_limit=1, base_crit_rate=0.25, sub_effect="self_lost_dmg", sub_param=0.45))
            troop.skills.append(BattleSkill(2, "不坏金身",   5, "坚韧", "Heal", 100.0, 45.0, self_bp_cond2=45, times_limit=1, sub_effect="self_max_heal", sub_param=0.16))
            troop.skills.append(BattleSkill(3, "崩山重劈",   5, "勇气", "Attack", 200.0 * c_boost, 35.0, base_crit_rate=0.15))

    elif genre_code == "R_I":
        if max_t <= 2:
            troop.skills.append(BattleSkill(1, "圣光急救", 1, "坚韧", "Heal", 100.0, 35.0, self_bp_cond2=80, sub_effect="self_max_heal", sub_param=0.07))
            troop.skills.append(BattleSkill(2, "壁垒盾刺", 2, "坚韧", "Attack", 130.0, 30.0))
        elif max_t <= 4:
            troop.skills.append(BattleSkill(1, "固守苏生", 4, "坚韧", "Heal", 100.0, 45.0, self_bp_cond2=50, times_limit=1, sub_effect="self_max_heal", sub_param=0.15))
            troop.skills.append(BattleSkill(2, "幻影防壁", 4, "先机", "Attack", 145.0, 35.0, exhaust_turns=1))
        else:
            troop.skills.append(BattleSkill(1, "神恩涅槃", 6, "坚韧", "Heal", 100.0, 50.0, self_bp_cond2=40, times_limit=1, sub_effect="self_max_heal", sub_param=0.18))
            troop.skills.append(BattleSkill(2, "瞬影封印", 5, "先机", "Attack", 150.0, 40.0, exhaust_turns=1))
            troop.skills.append(BattleSkill(3, "常态吸血", 5, "坚韧", "Attack", 130.0, 30.0, sub_effect="lifesteal", sub_param=0.35))

    return troop

def test_progression_with_combo():
    scales = [5, 10, 15, 20, 25, 30]
    genres = ["M_R", "M_I", "M_C", "C_I", "C_R", "R_I"]
    genre_names = {
        "M_R": "魔力+坚韧",
        "M_I": "魔力+先机",
        "M_C": "魔力+勇气",
        "C_I": "勇气+先机",
        "C_R": "勇气+坚韧",
        "R_I": "坚韧+先机"
    }

    print("=" * 105)
    print("【实装 终极闭环强化 (方向1+2+3) 后的 全阶梯人数规模 (5~30人) 表现】")
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
                    t1 = create_progression_combo_troop(sc, g1)
                    t2 = create_progression_combo_troop(sc, g2)
                    res = run_battle_configurable(t1, t2,
                                                 enable_magic_amp_crit=True,
                                                 enable_overflow_crit_conv=True,
                                                 overflow_conv_ratio=1.5)
                    all_turns.append(res['turns'])
                    if res['winner'].name.startswith(t1.name[:4]):
                        tot_wins[g1] += 1
                    else:
                        tot_wins[g2] += 1
                    tot_matches[g1] += 1
                    tot_matches[g2] += 1

        avg_turns = sum(all_turns) / len(all_turns)
        row_str = f"【{sc:>2} 人规模 | 平均交锋 {avg_turns:>4.1f} 回合】: "
        for g in genres:
            wr = (tot_wins[g] / tot_matches[g]) * 100.0
            row_str += f"{genre_names[g][:4]}:{wr:>4.1f}%  "
        print(row_str)

if __name__ == '__main__':
    test_progression_with_combo()
