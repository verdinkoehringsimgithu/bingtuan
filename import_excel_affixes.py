# -*- coding: utf-8 -*-
"""
从「游戏全量技能逆向拆解与三特征词库.xlsx」导入全量前缀与后缀词库至 skill_affixes.txt
供 SkillGenerator.exe 与技能生成系统直接调用。
"""
import os
import sys

def sync_affixes():
    try:
        import openpyxl
    except ImportError:
        print("错误: 未安装 openpyxl 库，请运行 pip install openpyxl")
        return False

    base_dir = os.path.dirname(os.path.abspath(__file__))
    xlsx_path = os.path.join(base_dir, "游戏全量技能逆向拆解与三特征词库.xlsx")
    txt_path = os.path.join(base_dir, "skill_affixes.txt")

    if not os.path.exists(xlsx_path):
        # 兼容不同编码/模糊搜索
        cand = [f for f in os.listdir(base_dir) if f.endswith(".xlsx") and ("词库" in f or "拆解" in f)]
        if cand:
            xlsx_path = os.path.join(base_dir, cand[0])
        else:
            print(f"未找到 Excel 词库文件: {xlsx_path}")
            return False

    print(f"正在读取 Excel 词库: {xlsx_path} ...")
    wb = openpyxl.load_workbook(xlsx_path)

    def extract_sheet(sname):
        if sname not in wb.sheetnames:
            print(f"警告: 未找到工作表 {sname}")
            return [], []
        ws = wb[sname]
        p_list = []
        s_list = []
        for r in range(3, ws.max_row + 1):
            p = ws.cell(r, 3).value
            s = ws.cell(r, 8).value
            if p and str(p).strip():
                w = str(p).strip()
                if w not in p_list:
                    p_list.append(w)
            if s and str(s).strip():
                w = str(s).strip()
                if w not in s_list:
                    s_list.append(w)
        return p_list, s_list

    p_h, s_h = extract_sheet("特征一_暴击高伤大范围")
    p_p, s_p = extract_sheet("特征二_精准穿透真实")
    p_t, s_t = extract_sheet("特征三_恢复生命吸取")

    # 通用词库精选
    common_p = [
        "狂暴", "疾风", "烈焰", "冰霜", "雷霆", "暗影", "圣光", "虚空", "以太", "深渊",
        "晨曦", "拂晓", "星界", "混沌", "奥术", "时空", "末日", "极光", "破晓", "暴风",
        "崩山", "裂地", "毁灭", "碎裂", "怒斩", "穿刺", "剔骨", "刺杀", "穿心", "瞬杀",
        "愈合", "汲取", "吸取", "吞噬", "转化", "复苏", "治愈", "守护", "庇护", "净化"
    ]
    common_s = [
        "斩", "刺", "击", "刃", "破", "裂", "射击", "重击", "穿刺", "撕裂",
        "爆破", "冲击", "连击", "狂袭", "裁决", "判决", "贯穿", "礼赞", "庇护", "苏生",
        "吞噬", "低语", "突袭", "逆流", "射线", "风暴", "猛击", "狂攻", "锁链", "回响",
        "愈合", "汲取", "转化", "复苏", "绽放", "惩戒", "圣印", "灵光", "洗礼", "神剑"
    ]

    # 机制流精选
    utility_p = [
        "以太", "虚空", "暗影", "深渊", "魔化", "时空", "奥术", "混沌", "厄运", "灵魂",
        "末日", "星界", "狡黠", "蚀心", "冥界", "暗夜", "镜像", "裂隙", "幻影", "诡术",
        "死灵", "禁忌", "黑巫", "灾厄", "秘法", "幽暗", "命运", "黑炎", "蚀骨", "巫毒",
        "洞悉", "锁魂", "封喉", "匿迹", "潜行", "献祭", "虹吸", "维系", "折跃", "湮灭"
    ]
    utility_s = [
        "爆破", "射线", "吞噬", "冲击", "窃取", "封印", "凝视", "逆流", "低语", "缠绕",
        "回响", "枷锁", "反噬", "突袭", "陷阱", "侵蚀", "突击", "风暴", "撕裂", "汲取",
        "湮灭", "折跃", "之噬", "之触", "之握", "之影", "之锁", "之眼", "之潮", "之歌",
        "之痕", "之契约", "符文", "暗流", "幻象", "禁锢", "心蚀", "同化", "裂变", "降临"
    ]

    out = []
    out.append("# ========================================================")
    out.append("# 战团技能前后字段词库配置文件 (skill_affixes.txt)")
    out.append("# 词库来源：游戏全量技能逆向拆解与三特征词库.xlsx")
    out.append("# 特征一（暴击高伤大范围）-> 破锋流 (Havoc)")
    out.append("# 特征二（精准穿透真实）  -> 精准流 (Precision)")
    out.append("# 特征三（恢复生命吸取）  -> 韧回流 (Tenacity)")
    out.append("# ========================================================")
    out.append("")
    out.append("[ConnectMode]")
    out.append("0")
    out.append("")

    def add_sec(name, items):
        out.append(f"[{name}]")
        for it in items:
            out.append(it)
        out.append("")

    add_sec("Common_Prefixes", common_p)
    add_sec("Common_Suffixes", common_s)

    add_sec("Havoc_Prefixes", p_h)
    add_sec("Havoc_Suffixes", s_h)

    add_sec("Precision_Prefixes", p_p)
    add_sec("Precision_Suffixes", s_p)

    add_sec("Tenacity_Prefixes", p_t)
    add_sec("Tenacity_Suffixes", s_t)

    add_sec("Utility_Prefixes", utility_p)
    add_sec("Utility_Suffixes", utility_s)

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))

    print(f"成功将 Excel 词库同步写入: {txt_path} (共 {len(out)} 行)！")
    print(f"  破锋流 (特征一): 前缀 {len(p_h)} 个, 后缀 {len(s_h)} 个")
    print(f"  精准流 (特征二): 前缀 {len(p_p)} 个, 后缀 {len(s_p)} 个")
    print(f"  韧回流 (特征三): 前缀 {len(p_t)} 个, 后缀 {len(s_t)} 个")
    return True

if __name__ == "__main__":
    sync_affixes()
