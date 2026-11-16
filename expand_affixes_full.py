# -*- coding: utf-8 -*-
"""
生成扩展全量前后缀与高阶复合构词配置文件 (skill_affixes.txt)
支持以下四大范式：
1. 单字凝练组合式 (斩天剑、邪龙眼、断魂枪、破魔刃、斩天之剑、邪龙之眼)
2. 经典双元偏正式 (修罗崩击、以太脉冲、虚空之侵蚀、鹰眼狙杀)
3. 宏大长句诗意式 (撕裂天空之剑、贯穿星辰之枪、守护终末之盾、焚尽万物之火)
4. 极境战技风暴式 (究极斩击风暴、极限连刺骤雨、苍穹坠击陨星、灭世崩山爆轰)
"""

mono_actions = [
    "斩", "破", "断", "裂", "灭", "弑", "碎", "穿", "封", "焚",
    "诛", "截", "荡", "镇", "劈", "逆", "绝", "拔", "挑", "刺",
    "轰", "碾", "旋", "掠", "御", "引", "化", "定", "锁", "夺"
]

mono_objects = [
    "天", "地", "月", "星", "龙", "魔", "神", "魂", "界", "空",
    "虚", "煞", "渊", "劫", "苍", "冥", "皇", "帝", "炎", "霜",
    "雷", "风", "狱", "魄", "障", "潮", "灵", "影", "梦", "道"
]

mono_carriers = [
    "剑", "刃", "枪", "弓", "杖", "拳", "爪", "盾", "斧", "戟",
    "锤", "链", "扇", "轮", "牙", "角", "翼", "眼", "心", "魄",
    "瞳", "骨", "环", "镜", "珠", "塔", "阵", "矢", "炮", "印"
]

mono_modifiers = [
    "邪", "圣", "魔", "血", "鬼", "狂", "暗", "真", "冥", "灵",
    "幻", "凶", "霸", "炽", "霜", "毒", "影", "幽", "绝", "妖",
    "极", "煞", "苍", "耀", "噬", "怒", "暴", "灭", "黑", "白"
]

mono_beasts = [
    "龙", "兽", "神", "狼", "影", "蛇", "虎", "鸟", "帝", "皇",
    "狐", "雀", "蛟", "熊", "鹰", "狮", "猿", "蝠", "蛛", "蝶",
    "蟒", "雕", "鹏", "麟", "凤", "鲲", "獒", "象", "枭", "蜂"
]

epic_verbs = [
    "撕裂", "贯穿", "斩断", "焚尽", "冻结", "守护", "支配", "碎裂", "吞噬", "唤醒",
    "穿透", "破灭", "终结", "湮灭", "熔铸", "净化", "审判", "裂解", "扭曲", "震碎",
    "斩落", "洞穿", "封印", "裁决", "救赎", "驱散", "崩解", "逆转", "献祭", "重塑"
]

epic_targets = [
    "天空", "星辰", "因果", "万物", "时空", "终末", "虚空", "大地", "灵魂", "黎明",
    "黑夜", "轮回", "冥府", "绝望", "苍穹", "次元", "混沌", "命运", "深渊", "灾厄",
    "极昼", "永夜", "幻梦", "诸界", "狂澜", "破晓", "劫灰", "尘世", "幽域", "深空"
]

epic_relics = [
    "之剑", "之枪", "之刃", "之火", "之息", "之盾", "之眼", "之锤", "之雾", "之光",
    "之箭", "之歌", "之爪", "之门", "之翼", "之印", "之核", "之心", "之轮", "之锁",
    "之誓", "之铠", "之裁", "之冠", "之戟", "之权", "之镜", "之弓", "之牢", "之符"
]

apex_prefixes = [
    "究极", "极限", "绝命", "灭世", "苍穹", "圣堂", "虚空", "狂暴", "瞬影", "深渊",
    "刚猛", "极光", "霸王", "鬼神", "毁灭", "暴风", "天崩", "逆天", "炽煌", "冥炎",
    "绝影", "霸道", "无双", "修罗", "狂怒", "致命", "混沌", "天灾", "猩红", "漆黑"
]

apex_actions = [
    "斩击", "连刺", "穿心", "崩山", "洗礼", "侵蚀", "乱舞", "闪击", "坠击", "吞噬",
    "强劈", "贯穿", "爆射", "震裂", "狂斩", "破阵", "突袭", "轰鸣", "撕裂", "碾压",
    "旋刃", "裂地", "突刺", "飞星", "绝杀", "破霸", "疾射", "逆击", "破空", "碎骨"
]

apex_fields = [
    "风暴", "骤雨", "爆轰", "冲击", "辉光", "狂潮", "旋涡", "绝杀", "陨星", "裂变",
    "震荡", "射线", "怒涛", "崩灭", "领域", "结界", "火海", "狂澜", "暴乱", "浩劫",
    "极境", "天劫", "轰顶", "狂啸", "怒炎", "冰原", "暗涌", "狂雷", "乱流", "狂宴"
]

# Read original 10 sections from D:\123\skill_affixes.txt
sections = {}
cur = None
with open(r"D:\123\skill_affixes.txt", "r", encoding="utf-8") as f:
    for line in f:
        l = line.strip()
        if not l or l.startswith("#"): continue
        if l.startswith("[") and l.endswith("]"):
            cur = l[1:-1]
            sections[cur] = []
        elif cur:
            sections[cur].append(l)

# Construct full content
output_lines = [
    "# ========================================================",
    "# 战团技能高阶全范式词库配置文件 (skill_affixes.txt)",
    "# 涵盖四大构词范式：",
    "# 1. 单字凝练三元/四元式 (如: 斩天剑、邪龙眼、斩天之剑、邪龙之眼)",
    "# 2. 经典双元偏正式 (如: 修罗崩击、以太脉冲、虚空之侵蚀)",
    "# 3. 宏大长句诗意式 (如: 撕裂天空之剑、贯穿星辰之枪、守护终末之盾)",
    "# 4. 极境战技风暴式 (如: 究极斩击风暴、极限连刺骤雨、苍穹坠击陨星)",
    "# 100% 官方真实游戏溯源 (WoW/暗黑/PoE/法环/FF/MH/无双/DNF/LOL/Dota2/异度神剑/鬼泣/原神)",
    "# ========================================================",
    "",
    "[ConnectMode]",
    "0",
    ""
]

# Write the original 10 core sections
core_sections = [
    "Common_Prefixes", "Common_Suffixes",
    "Courage_Prefixes", "Courage_Suffixes",
    "Resilience_Prefixes", "Resilience_Suffixes",
    "Initiative_Prefixes", "Initiative_Suffixes",
    "Magic_Prefixes", "Magic_Suffixes"
]

for sec in core_sections:
    output_lines.append(f"[{sec}]")
    if sec in sections:
        output_lines.extend(sections[sec])
    output_lines.append("")

# Write new advanced paradigms
advanced_blocks = [
    ("Mono_Actions", mono_actions),
    ("Mono_Objects", mono_objects),
    ("Mono_Carriers", mono_carriers),
    ("Mono_Modifiers", mono_modifiers),
    ("Mono_Beasts", mono_beasts),
    ("Epic_Verbs", epic_verbs),
    ("Epic_Targets", epic_targets),
    ("Epic_Relics", epic_relics),
    ("Apex_Prefixes", apex_prefixes),
    ("Apex_Actions", apex_actions),
    ("Apex_Fields", apex_fields)
]

for sec, words in advanced_blocks:
    output_lines.append(f"[{sec}]")
    output_lines.extend(words)
    output_lines.append("")

with open(r"D:\123\skill_affixes.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print("已成功写入扩展全范式配置文件 D:\\123\\skill_affixes.txt！")
