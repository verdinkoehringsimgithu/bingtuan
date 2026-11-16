# -*- coding: utf-8 -*-
"""
战团技能生成器 (Skill Generator Preview & Audit Engine)
=====================================================
核心设计契约：
1. 四大技能类型与四维属性严格统一为：勇气、坚韧、先机、魔力！
2. 伤害统一表述为“造成 X% 的伤害”，严禁“暴击伤害/精准伤害/直接伤害/斩杀伤害”等名词。
3. 勇气技能：直伤后统一写“有概率暴击”，绝不写死具体概率，不误导玩家，保留勇气属性的暴击增益空间。
4. 先机技能：天生自带“先机等级提高 X”（最低 1 先机，随阶位递增：T1: 1, T2: 2, T3: 4, T4: 7, T5: 10, T6: 15），不占额外特效栏位。严禁任何“对方无法闪避”！
5. 坚韧技能：攻击造成 100% 伤害，并恢复己方总战力/当前战力（T1 保底 4% 总战力恢复）。
6. 魔力技能：天生自带“本次攻击无视目标 X% 的防御”（T1: 20%, T2: 30%, T3: 38%, T4: 50%, T5: 65%, T6: 80%），不占额外特效栏位。
7. T1 技能绝无额外特效，纯白板数值。
"""

import random
import math
import sys
import os

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# ─── 阶位定义 ───
TIERS = {
    1: {"name": "T1", "budget": 18.0, "sub_chance": 0.00, "ini_bonus": 1, "ignore_def": 20},
    2: {"name": "T2", "budget": 24.0, "sub_chance": 0.15, "ini_bonus": 2, "ignore_def": 30},
    3: {"name": "T3", "budget": 32.0, "sub_chance": 0.35, "ini_bonus": 3, "ignore_def": 38},
    4: {"name": "T4", "budget": 48.0, "sub_chance": 0.60, "ini_bonus": 5, "ignore_def": 50},
    5: {"name": "T5", "budget": 68.0, "sub_chance": 0.75, "ini_bonus": 7, "ignore_def": 65},
    6: {"name": "T6", "budget": 92.0, "sub_chance": 0.85, "ini_bonus": 10, "ignore_def": 80},
}

GENRES = ["勇气", "坚韧", "先机", "魔力"]

# ─── 词库与四大构词范式加载 ───
def load_all_affix_data(filepath=r"D:\123\skill_affixes.txt"):
    if not os.path.exists(filepath):
        return None, {}, {}, {}
    affixes = {
        "勇气": {"prefixes": [], "suffixes": []},
        "先机": {"prefixes": [], "suffixes": []},
        "坚韧": {"prefixes": [], "suffixes": []},
        "魔力": {"prefixes": [], "suffixes": []},
        "通用": {"prefixes": [], "suffixes": []}
    }
    mono = {"actions": [], "objects": [], "carriers": [], "modifiers": [], "beasts": []}
    epic = {"verbs": [], "targets": [], "relics": []}
    apex = {"prefixes": [], "actions": [], "fields": []}

    cur = None
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                cur = line[1:-1]
                continue
            if not cur:
                continue

            # Core
            if "Courage" in cur or "Havoc" in cur:
                if cur.endswith("_Prefixes"): affixes["勇气"]["prefixes"].append(line)
                elif cur.endswith("_Suffixes"): affixes["勇气"]["suffixes"].append(line.split(":")[0].strip())
            elif "Initiative" in cur or "Precision" in cur:
                if cur.endswith("_Prefixes"): affixes["先机"]["prefixes"].append(line)
                elif cur.endswith("_Suffixes"): affixes["先机"]["suffixes"].append(line.split(":")[0].strip())
            elif "Resilience" in cur or "Tenacity" in cur:
                if cur.endswith("_Prefixes"): affixes["坚韧"]["prefixes"].append(line)
                elif cur.endswith("_Suffixes"): affixes["坚韧"]["suffixes"].append(line.split(":")[0].strip())
            elif "Magic" in cur or "Utility" in cur:
                if cur.endswith("_Prefixes"): affixes["魔力"]["prefixes"].append(line)
                elif cur.endswith("_Suffixes"): affixes["魔力"]["suffixes"].append(line.split(":")[0].strip())
            elif "Common" in cur:
                if cur.endswith("_Prefixes"): affixes["通用"]["prefixes"].append(line)
                elif cur.endswith("_Suffixes"): affixes["通用"]["suffixes"].append(line.split(":")[0].strip())

            # Mono
            elif cur == "Mono_Actions": mono["actions"].append(line)
            elif cur == "Mono_Objects": mono["objects"].append(line)
            elif cur == "Mono_Carriers": mono["carriers"].append(line)
            elif cur == "Mono_Modifiers": mono["modifiers"].append(line)
            elif cur == "Mono_Beasts": mono["beasts"].append(line)

            # Epic
            elif cur == "Epic_Verbs": epic["verbs"].append(line)
            elif cur == "Epic_Targets": epic["targets"].append(line)
            elif cur == "Epic_Relics": epic["relics"].append(line)

            # Apex
            elif cur == "Apex_Prefixes": apex["prefixes"].append(line)
            elif cur == "Apex_Actions": apex["actions"].append(line)
            elif cur == "Apex_Fields": apex["fields"].append(line)

    return affixes, mono, epic, apex

_loaded_affixes, MONO, EPIC, APEX = load_all_affix_data()
AFFIXES = _loaded_affixes

def generate_mono_name():
    if not (MONO["actions"] and MONO["objects"] and MONO["carriers"]):
        return "斩天剑"
    if random.random() < 0.50 and MONO["modifiers"] and MONO["beasts"]:
        m = random.choice(MONO["modifiers"])
        b = random.choice(MONO["beasts"])
        c = random.choice(MONO["carriers"])
        return f"{m}{b}{c}"
    else:
        a = random.choice(MONO["actions"])
        o = random.choice(MONO["objects"])
        c = random.choice(MONO["carriers"])
        return f"{a}{o}{c}"

def generate_six_char_name():
    if random.random() < 0.50 and EPIC["verbs"] and EPIC["targets"] and EPIC["relics"]:
        ev = random.choice(EPIC["verbs"])
        et = random.choice(EPIC["targets"])
        er = random.choice(EPIC["relics"])
        return f"{ev}{et}{er}"
    elif APEX["prefixes"] and APEX["actions"] and APEX["fields"]:
        ap = random.choice(APEX["prefixes"])
        aa = random.choice(APEX["actions"])
        af = random.choice(APEX["fields"])
        return f"{ap}{aa}{af}"
    elif EPIC["verbs"] and EPIC["targets"] and EPIC["relics"]:
        return f"{random.choice(EPIC['verbs'])}{random.choice(EPIC['targets'])}{random.choice(EPIC['relics'])}"
    return "究极斩击风暴"

def generate_four_char_name(genre):
    data = AFFIXES.get(genre, AFFIXES["勇气"])
    pre_list = data["prefixes"] if data["prefixes"] else ["狂暴"]
    suf_list = data["suffixes"] if data["suffixes"] else ["崩击"]
    for _ in range(25):
        pre = random.choice(pre_list)
        suf = random.choice(suf_list)
        if len(suf) == 1:
            name = f"{pre}之{suf}"
        elif len(suf) == 2:
            name = f"{pre}{suf}"
        else:
            name = f"{pre}{suf}"
        if len(name) == 4 and len(set(name)) == len(name):
            return name
    pre = random.choice(pre_list)
    suf = random.choice(suf_list)
    return f"{pre}之{suf}" if len(suf) == 1 else f"{pre}{suf}"

def generate_skill_name(genre, tier=1):
    # ─── 阶位构词规则 ───
    # 1. T1、T2：100% 用单字组合 (3字，如: 斩天剑、邪龙眼)
    # 2. T6：100% 用 6字 (宏大长句诗意式 + 极境战技风暴式，如: 撕裂天空之剑、究极斩击风暴)
    # 3. T3、T4、T5：四字始终占 75%，从单字更高过渡到多字更高：
    #    - T3: 四字 75%, 单字 20%, 六字 5%   (单字更高)
    #    - T4: 四字 75%, 单字 12.5%, 六字 12.5% (平分过渡)
    #    - T5: 四字 75%, 单字 5%, 六字 20%   (多字更高)
    if tier in [1, 2]:
        return generate_mono_name()
    elif tier == 6:
        return generate_six_char_name()
    elif tier == 3:
        r = random.random()
        if r < 0.75: return generate_four_char_name(genre)
        elif r < 0.95: return generate_mono_name()
        else: return generate_six_char_name()
    elif tier == 4:
        r = random.random()
        if r < 0.75: return generate_four_char_name(genre)
        elif r < 0.875: return generate_mono_name()
        else: return generate_six_char_name()
    elif tier == 5:
        r = random.random()
        if r < 0.75: return generate_four_char_name(genre)
        elif r < 0.80: return generate_mono_name()
        else: return generate_six_char_name()
    else:
        r = random.random()
        if r < 0.75: return generate_four_char_name(genre)
        elif r < 0.875: return generate_mono_name()
        else: return generate_six_char_name()

def sample_normal_clamped(mean, std_dev, min_v, max_v):
    val = random.gauss(mean, std_dev)
    return max(min_v, min(max_v, val))

# ─── 主倍率与发动概率抽取 ───
def get_param_and_chance(genre, tier, is_compensated):
    budget = TIERS[tier]["budget"]
    idx = tier - 1
    
    if genre == "勇气":
        mins = [130, 150, 180, 210, 250, 300]
        maxs = [150, 180, 220, 260, 310, 350]
        mean = (mins[idx] + maxs[idx]) / 2.0
        if is_compensated:
            mean = min(350, mean + budget * 0.45)
            maxs[idx] = min(350, maxs[idx] + 40)
            mins[idx] = min(340, mins[idx] + 30)
        param = int(round(sample_normal_clamped(mean, (maxs[idx] - mins[idx]) * 0.18, mins[idx], maxs[idx])))
        
        eff_weight = param
        base_chance = (budget / eff_weight) * 100.0
        if tier == 1: base_chance *= 1.60
        elif tier == 2: base_chance *= 1.40
        if is_compensated: base_chance += 5.0
        hard_min, hard_max = (19, 57) if tier == 1 else ((16, 50) if tier == 2 else (12, 36))
        chance = int(round(sample_normal_clamped(base_chance, 2.5, hard_min, hard_max)))
        return param, chance

    elif genre == "先机":
        mins = [120, 130, 140, 145, 150, 160]
        maxs = [135, 145, 155, 160, 175, 190]
        mean = (mins[idx] + maxs[idx]) / 2.0
        if is_compensated:
            mean = min(200, mean + budget * 0.25)
            maxs[idx] = min(200, maxs[idx] + 20)
        param = int(round(sample_normal_clamped(mean, (maxs[idx] - mins[idx]) * 0.18, mins[idx], maxs[idx])))
        
        eff_weight = param
        base_chance = (budget / eff_weight) * 100.0 * 1.10
        if tier == 1: base_chance *= 1.60
        elif tier == 2: base_chance *= 1.40
        if is_compensated: base_chance += 5.0
        hard_min, hard_max = (24, 67) if tier == 1 else ((21, 58) if tier == 2 else (15, 42))
        chance = int(round(sample_normal_clamped(base_chance, 2.5, hard_min, hard_max)))
        return param, chance

    elif genre == "坚韧":
        param = 100
        eff_weight = param * 5.5
        base_chance = (budget / eff_weight) * 100.0
        if tier == 1: base_chance *= 1.60
        elif tier == 2: base_chance *= 1.40
        if is_compensated: base_chance += 4.0
        hard_min, hard_max = (24, 60) if tier == 1 else ((21, 53) if tier == 2 else (15, 38))
        chance = int(round(sample_normal_clamped(base_chance, 2.0, hard_min, hard_max)))
        return param, chance

    else:  # 魔力
        mins = [100, 105, 110, 115, 120, 125]
        maxs = [115, 120, 125, 130, 135, 145]
        mean = (mins[idx] + maxs[idx]) / 2.0
        if is_compensated:
            mean = min(180, mean + budget * 0.35)
            maxs[idx] = min(180, maxs[idx] + 25)
        param = int(round(sample_normal_clamped(mean, (maxs[idx] - mins[idx]) * 0.18, mins[idx], maxs[idx])))
        
        eff_weight = param * 0.65
        base_chance = (budget / eff_weight) * 100.0
        if tier == 1: base_chance *= 1.60
        elif tier == 2: base_chance *= 1.40
        if is_compensated: base_chance += 5.0
        hard_min, hard_max = (19, 60) if tier == 1 else ((16, 53) if tier == 2 else (12, 38))
        chance = int(round(sample_normal_clamped(base_chance, 2.5, hard_min, hard_max)))
        return param, chance

# ─── 附加效果抽取 ───
def get_sub_effect(genre, tier):
    idx = tier - 1
    if genre == "勇气":
        pool = [
            ("自身已损反噬", "self_lost", [8, 11, 15, 20, 26, 35][idx], "附带自身已损失战力{v}%伤害"),
            ("敌方当前压制", "enemy_cur", [3, 4, 5, 7, 9, 12][idx], "附带敌方当前战力{v}%伤害"),
            ("敌方已损斩杀", "enemy_lost", [5, 7, 10, 14, 18, 24][idx], "附带敌方已损失战力{v}%伤害"),
        ]
    elif genre == "坚韧":
        pool = [
            ("总战力恢复", "max_heal", [4, 6, 8, 11, 14, 18][idx], "恢复己方总战力{v}%"),
            ("当前战力自愈", "cur_heal", [8, 12, 16, 22, 28, 36][idx], "恢复己方当前战力{v}%"),
        ]
    elif genre == "先机":
        pool = [
            ("四维削弱", "debuff_stats", [10, 14, 18, 22, 28, 35][idx], "降低目标所有属性{v}%，持续2回合"),
            ("虚弱压制", "weak", [15, 20, 25, 30, 38, 48][idx], "降低目标造成的伤害{v}%，持续2回合"),
        ]
    else:  # 魔力
        pool = [
            ("最大流失", "dot_max", [1.5, 2.0, 2.6, 3.2, 4.0, 5.0][idx], "目标2回合内每回合受到目标最大战力{v}%点流失伤害，持续2回合"),
            ("固定流失", "dot_flat", [3000, 5000, 8000, 12000, 18000, 26000][idx], "目标2回合内每回合受到{v}*100%点流失伤害，持续2回合"),
            ("已损流失", "dot_lost", [3.0, 4.2, 5.5, 7.0, 9.0, 12.0][idx], "目标2回合内每回合受到自身已损失战力{v}%点流失伤害，持续2回合"),
            ("战力吸收", "lifesteal", [18, 24, 32, 42, 55, 70][idx], "吸收本次伤害{v}%的战力"),
        ]
    name, code, val, desc_template = random.choice(pool)
    desc = desc_template.format(v=val)
    return name, code, val, desc

# ─── 触发条件与限制 ───
def get_conditions(genre, tier, param, has_sub, sub_code):
    turn_cond = None
    bp_cond = None
    times_limit = 0
    
    if genre == "坚韧":
        threshold = [80, 80, 70, 70, 50, 50][tier - 1]
        bp_cond = f"己方战力低于{threshold}%时"
        times_limit = [0, 0, 3, 2, 1, 1][tier - 1]
        if tier >= 5:
            turn_cond = "第2回合起"
        return turn_cond, bp_cond, times_limit

    if tier <= 2:
        return turn_cond, bp_cond, times_limit
    
    if sub_code in ["self_lost", "dot_lost"] or (param >= 280 and genre == "勇气"):
        bp_cond = "己方战力低于50%时"
        if tier >= 5:
            turn_cond = "第2回合起"
        times_limit = 1 if tier >= 5 else 2
        return turn_cond, bp_cond, times_limit

    if sub_code in ["enemy_lost"]:
        bp_cond = "敌方战力低于50%时"
        times_limit = 1 if tier >= 5 else 2
        return turn_cond, bp_cond, times_limit

    if param >= 300:
        bp_cond = "己方战力低于45%时"
        times_limit = 1
        return turn_cond, bp_cond, times_limit

    if tier == 6:
        times_limit = 1 if param >= 175 else 2
    elif tier == 5:
        times_limit = 1 if param >= 165 else 2
    elif tier == 4:
        times_limit = 2 if param >= 240 else 3
    elif tier == 3:
        times_limit = 3 if param >= 200 else 0

    return turn_cond, bp_cond, times_limit

# ─── 自然语言技能描述拼装 ───
def build_skill_description(genre, trigger_chance, main_param, tier, turn_cond, bp_cond, times_limit, has_sub, sub_desc):
    parts = []
    
    if times_limit and times_limit > 0:
        parts.append(f"每场战斗限{times_limit}次")
    if turn_cond:
        parts.append(turn_cond)
    if bp_cond:
        parts.append(bp_cond)
        
    prefix_cond = "，".join(parts) + "，" if parts else ""
    
    ini_bonus = TIERS[tier]["ini_bonus"]
    ignore_def = TIERS[tier]["ignore_def"]

    dmg_param = 100 if genre == "坚韧" else main_param
    desc = f"{prefix_cond}{trigger_chance}%概率发动，命中后造成{dmg_param}%的伤害"
    
    clean_sub = sub_desc.rstrip("。 \t") if has_sub and sub_desc else ""

    if genre == "坚韧":
        if clean_sub:
            desc += f"，{clean_sub}"
    elif genre == "魔力":
        desc += f"，无视目标{ignore_def}%的防御"
        if clean_sub:
            desc += f"，{clean_sub}"
    elif genre == "先机":
        if clean_sub:
            desc += f"，{clean_sub}"
        desc += f"，先机加{ini_bonus}"
    else:  # 勇气
        if clean_sub:
            desc += f"，{clean_sub}"
        desc += "，有概率暴击"
        
    desc += "。"
    return desc

# ─── 单条技能完整生成 ───
def generate_one_skill(chosen_tier=None, chosen_genre=None):
    tier = chosen_tier if chosen_tier else random.choices([1, 2, 3, 4, 5, 6], weights=[10, 15, 25, 25, 15, 10])[0]
    genre = chosen_genre if chosen_genre else random.choice(GENRES)
    
    tier_info = TIERS[tier]
    sub_chance = tier_info["sub_chance"]
    
    if tier == 1:
        if genre == "坚韧":
            has_sub = True
            sub_name, sub_code, sub_val, sub_desc = ("总战力恢复", "max_heal", 4, "恢复己方总战力4%")
        else:
            has_sub = False
            sub_name, sub_code, sub_val, sub_desc = (None, None, 0, "")
        is_compensated = False
    else:
        has_sub = (random.random() < sub_chance)
        is_compensated = (not has_sub and tier >= 3)
        if has_sub:
            sub_name, sub_code, sub_val, sub_desc = get_sub_effect(genre, tier)
        elif genre == "坚韧":
            has_sub = True
            sub_name, sub_code, sub_val, sub_desc = ("总战力恢复", "max_heal", [4, 6, 8, 11, 14, 18][tier - 1], f"恢复己方总战力{[4, 6, 8, 11, 14, 18][tier - 1]}%")
        else:
            sub_name, sub_code, sub_val, sub_desc = (None, None, 0, "")
        
    main_param, trigger_chance = get_param_and_chance(genre, tier, is_compensated)
    turn_cond, bp_cond, times_limit = get_conditions(genre, tier, main_param, has_sub, sub_code)
    skill_name = generate_skill_name(genre, tier)
    desc = build_skill_description(genre, trigger_chance, main_param, tier, turn_cond, bp_cond, times_limit, has_sub, sub_desc)
    
    return {
        "tier": tier,
        "tier_name": tier_info["name"],
        "genre": genre,
        "name": skill_name,
        "desc": desc,
        "main_param": main_param,
        "trigger_chance": trigger_chance,
        "has_sub": has_sub,
        "sub_name": sub_name,
        "is_compensated": is_compensated,
        "times_limit": times_limit
    }

if __name__ == '__main__':
    print("=" * 70)
    print("【战团技能生成器：全阶位 (T1 ~ T6) 规范样本检阅】")
    print("【四大机制：勇气 | 坚韧 | 先机 | 魔力】")
    print("=" * 70)
    
    for t in [1, 2, 3, 4, 5, 6]:
        print(f"\n>>>>>>>>>>>>>>> 稀有度: {TIERS[t]['name']} <<<<<<<<<<<<<<<")
        for g in GENRES:
            s1 = generate_one_skill(chosen_tier=t, chosen_genre=g)
            print(f"  ● 技能类型: {s1['genre']} | 技能名字: 《{s1['name']}》")
            print(f"    技能效果: {s1['desc']}")
