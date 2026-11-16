# -*- coding: utf-8 -*-
r"""
构建【技能词条 -> 像素特效 (Super Pixel Effects Megapack 1) -> 10大受击物理表现】高精适配与精灵表合成管线 (v3.0)
1. 禁用所有循环类/球珠类特效 (fx1_aura_energy 光球、fx2_fire_burst 火球、fx2_ice_burst 冰球、fanfx2_lightning_spell_loop、fx2_bubble_loop、scifx1_wormhole_loop、scifx2_black_hole_loop 等)
2. 将【黑洞 (scifx2_black_hole)】的 appear + disappear 无缝拼接为完整单次动画精灵表
3. 将【虫洞 (scifx1_wormhole)】的 start + stop 无缝拼接为完整单次动画精灵表
4. 将【泡泡护盾 (fx2_bubble_appear)】的 appear + pop 无缝拼接，并将所有输出文件名统一规范化为 {base_key}_large_{color}.png/.txt，彻底根除找不到图像问题
5. 为全部 67 个核心特效家族绑定 1~10 号受击动力学效果（新增 9=中心聚拢吸附 适配黑洞/虫洞/虹吸/坍缩，10=集体旋转散开 适配漩涡/旋风/波纹）
"""

import os
import sys
import json
import glob
import shutil
from PIL import Image

sys.path.insert(0, r"d:\123")
import pixel_effect_namer as pen

EFFECT_NAMES_JSON = r"d:\123\effect_names.json"
MEGAPACK_ROOT = r"d:\123\Super Pixel Effects Megapack 1"
OUTPUT_MAPPING_JSON = r"d:\123\effect_skill_mapping.json"
ID_REGISTRY_PATH = r"d:/123/effect_animation_ids.json"
UNITY_EFFECTS_DIR = r"d:\123\LegionBattle\LegionBattle\Assets\Effects\Spritesheets"
UNITY_RESOURCES_DIR = r"d:\123\LegionBattle\LegionBattle\Assets\Resources"

COLOR_CN_MAP = {
    "blue": "蓝",
    "green": "绿",
    "orange": "橙",
    "pink": "粉",
    "red": "红",
    "violet": "紫",
    "white": "白",
    "yellow": "黄",
    "black": "黑",
    "gray": "灰",
    "brown": "棕",
    "rainbow": "彩虹",
}

# 需要强制标记为【禁用】的循环/光球/火球/冰球家族
FORCE_DISABLE_BASE_KEYS = {
    "fx1_aura_energy",
    "fx2_bubble_pop", "fx2_magic_swirl", "fx3_lightning_aura", "scifx2_tech_aura",
    "fx2_fire_burst",
    "fx2_ice_burst",
    "fx2_bubble_loop",
    "fanfx2_lightning_spell_loop",
    "fanfx2_lightning_spell_start",
    "fanfx2_lightning_spell_end",
    "fanfx2_lightning_spell_tileable_loop",
    "fanfx2_lightning_spell_tileable_start",
    "fanfx2_lightning_spell_tileable_end",
    "scifx1_wormhole_loop",
    "scifx2_black_hole_loop",
}

# 冗余拆分图层或由合成管线接管的起止片段
REDUNDANT_FRAGMENT_KEYS = {
    "fanfx1_spellcast_B_back",
    "fanfx1_spellcast_B_front",
    "fanfx1_spellcast_C_back",
    "fanfx1_spellcast_C_front",
    "fanfx2_cure_back",
    "fanfx2_cure_front",
    "scifx2_tech_aura_back",
    "scifx2_tech_aura_front",
    "scifx1_wormhole_start",
    "scifx1_wormhole_stop",
    "scifx2_black_hole_appear",
    "scifx2_black_hole_disappear",
}

# 合成动画定义：将起手(Appear/Start)与消散(Disappear/Stop/Pop)拼接为一个完整的非循环精灵表
STITCHED_FAMILIES = {
    "scifx2_black_hole": {
        "pack": "Super Pixel Sci-fi FX Pack 2",
        "part1_pattern": "scifx2_black_hole_appear_large_{color}",
        "part2_pattern": "scifx2_black_hole_disappear_large_{color}",
        "colors": ["blue", "green", "orange", "pink", "red", "violet", "white", "yellow"],
        "cn_template": "大{color_cn}黑洞出现与消散",
        "user_tag": "魔力",
    },
    "scifx1_wormhole": {
        "pack": "Super Pixel Sci-fi FX Pack 1",
        "part1_pattern": "scifx1_wormhole_start_large_{color}",
        "part2_pattern": "scifx1_wormhole_stop_large_{color}",
        "colors": ["blue", "green", "orange", "red", "violet", "yellow"],
        "cn_template": "大{color_cn}虫洞出现与消散",
        "user_tag": "魔力",
    },
    "fx2_bubble_appear": {
        "pack": "Super Pixel Effects Pack 2",
        "part1_pattern": "fx2_bubble_large_{color}_appear",
        "part2_pattern": "fx2_bubble_large_{color}_pop",
        "colors": ["blue", "green", "orange", "red", "violet", "white", "yellow"],
        "cn_template": "大{color_cn}泡泡出现与消散",
        "user_tag": "坚韧",
    },
}

# 67 个核心家族的视觉形态描述、施法锚点、以及绑定的受击动力学效果 (1~10)
# base_key: (category_cn, play_on_caster, hit_reaction_type, hit_reaction_name)
FAMILY_META = {
    # ── 受击类型 9：中心聚拢吸附 (适配黑洞、虫洞、虹吸、坍缩、聚合) ──
    "scifx2_black_hole": ("虚空引力黑洞", False, 9, "中心聚拢吸附"),
    "scifx1_wormhole": ("异界时空虫洞", False, 9, "中心聚拢吸附"),
    "fanfx2_absorb": ("泡沫聚拢星星虹吸", False, 9, "中心聚拢吸附"),
    "scifx1_explosion_A": ("坍缩泡沫收束爆炸", False, 9, "中心聚拢吸附"),
    "expfx1_symmetrical_explosion_C": ("聚拢烟雾对称爆", False, 9, "中心聚拢吸附"),
    "fx3_magic_spawn": ("秘法聚合闪光", False, 9, "中心聚拢吸附"),

    # ── 受击类型 10：集体旋转散开 (适配漩涡、旋风、波纹) ──
    "expfx1_stylized_explosion_B": ("旋风球乱舞爆炸", False, 10, "集体旋转散开"),
    "fanfx2_wind_spell": ("狂风聚拢爆裂", False, 10, "集体旋转散开"),
    "fanfx1_spellcast_A": ("禁锢波纹眩晕星星", False, 10, "集体旋转散开"),
    "fanfx1_spellcast_C": ("诅咒火焰波纹下降", False, 10, "集体旋转散开"),
    "impfx1_toon_impact_D": ("波纹羽毛闪光", False, 10, "集体旋转散开"),

    # ── 针对自身 (PlayOnCaster == True)：受击统一固定为普通击退 (1: 水平震退) ──
    "fanfx1_spellcast_B": ("祈愿波纹星星上升", True, 1, "水平震退"),
    "fanfx1_spellcast_D": ("金星波纹火焰升腾", True, 1, "水平震退"),
    "fx2_magic_swirl": ("圣堂魔法光柱", True, 1, "水平震退"),
    "fanfx1_magic_puff_B": ("灵气烟雾升腾", True, 1, "水平震退"),
    "scifx2_buff": ("战意科技增益上升", True, 1, "水平震退"),
    "scifx2_tech_aura": ("灵气圆圈气泡上升", True, 1, "水平震退"),
    "fanfx2_cure": ("波浪金星治疗", True, 1, "水平震退"),
    "scifx2_hex_shield": ("多边形坚壁护盾", True, 1, "水平震退"),
    "fx2_bubble_appear": ("圣洁泡泡护盾显现", True, 1, "水平震退"),
    "fx2_bubble_pop": ("泡泡护盾反震爆裂", True, 1, "水平震退"),
    "fx3_toon_explosion": ("守护正圆气浪爆", True, 1, "水平震退"),

    # ── 受击类型 1：水平震退 (适配刀剑斩击、利爪撕咬、穿刺寒芒、迅捷闪击) ──
    "fx2_slash": ("刀剑圆斩", False, 1, "水平震退"),
    "fanfx2_claw": ("流光裂空爪斩", False, 1, "水平震退"),
    "fx2_claw": ("利爪撕裂", False, 1, "水平震退"),
    "fx3_bite": ("狂暴利齿咬合", False, 1, "水平震退"),
    "fx1_electric_zap": ("疾电火花闪击", False, 1, "水平震退"),
    "impfx1_toon_impact_B": ("要害刺状闪光", False, 1, "水平震退"),
    "impfx1_quick_impact_D": ("疾闪命中闪光", False, 1, "水平震退"),
    "impfx1_quick_impact_C": ("寒芒冰晶闪光", False, 1, "水平震退"),
    "impfx1_quick_impact_B": ("极速锐芒闪光", False, 1, "水平震退"),
    "impfx1_quick_impact_A": ("迅捷轻微气闪", False, 1, "水平震退"),

    # ── 受击类型 2：垂直击飞 (适配地刺突起、冲天火柱、冲天气柱、升腾烟雾) ──
    "fanfx2_earth_spikes": ("大地冰锥尖刺突起", False, 2, "垂直击飞"),
    "fanfx2_fire_spell": ("冲天烈焰火柱", False, 2, "垂直击飞"),
    "expfx1_epic_explosion_A": ("冲天爆破气柱", False, 2, "垂直击飞"),
    "expfx1_stylized_explosion_C": ("云朵升腾巨爆", False, 2, "垂直击飞"),
    "fanfx2_poison": ("剧毒骷髅烟雾上升", False, 2, "垂直击飞"),

    # ── 受击类型 3：抛物线后仰 (适配重钧圆环重击、星辰闪光轰击、八芒星圣裁) ──
    "fx3_impact_hit": ("重钧圆环打击", False, 3, "抛物线后仰"),
    "impfx1_toon_impact_C": ("圆形气浪复合闪光", False, 3, "抛物线后仰"),
    "fx2_electric_burst": ("八芒星圣裁雷光", False, 3, "抛物线后仰"),
    "fanfx1_magic_burst_A": ("奥术星星爆裂", False, 3, "抛物线后仰"),
    "fanfx1_magic_burst_B": ("璀璨星辰闪光爆裂", False, 3, "抛物线后仰"),

    # ── 受击类型 4：四向旋转翻滚 (适配电弧激荡、次元跃迁、羽毛乱舞) ──
    "impfx1_toon_impact_A": ("弥散羽毛闪光", False, 4, "四向旋转翻滚"),
    "fx3_lightning_aura": ("双半圆雷电激荡", False, 4, "四向旋转翻滚"),
    "scifx1_zap_A": ("繁复电弧爆炸", False, 4, "四向旋转翻滚"),
    "scifx1_zap_B": ("双色高压电弧爆", False, 4, "四向旋转翻滚"),
    "fx3_warp": ("虚空带电跃迁爆炸", False, 4, "四向旋转翻滚"),
    "scifx2_warp": ("次元电弧气环爆炸", False, 4, "四向旋转翻滚"),

    # ── 受击类型 5：波浪状掀飞 (适配激流爆裂、震地气浪冲击) ──
    "scifx1_explosion_B": ("激流带电爆裂", False, 5, "波浪状掀飞"),
    "expfx1_stylized_explosion_A": ("气浪烟雾大爆炸", False, 5, "波浪状掀飞"),
    "impfx1_dust_impact_A": ("震地气浪烟雾爆炸", False, 5, "波浪状掀飞"),
    "impfx1_dust_impact_B": ("裂地分散烟雾爆炸", False, 5, "波浪状掀飞"),

    # ── 受击类型 6：中心炸散复位 (适配史诗巨爆、蘑菇云、镜面破碎、冰晶爆破) ──
    "expfx1_epic_explosion_B": ("史诗毁灭大爆炸", False, 6, "中心炸散复位"),
    "fx2_explosion": ("巨型大爆炸", False, 6, "中心炸散复位"),
    "fx1_explosion": ("毁灭蘑菇云轰炸", False, 6, "中心炸散复位"),
    "fanfx2_shatter": ("镜面次元碎片爆炸", False, 6, "中心炸散复位"),
    "fanfx2_ice_spell": ("史诗冰晶聚拢爆炸", False, 6, "中心炸散复位"),
    "expfx1_symmetrical_explosion_A": ("密集烟雾对称爆", False, 6, "中心炸散复位"),
    "expfx1_symmetrical_explosion_B": ("闪光烟雾对称爆", False, 6, "中心炸散复位"),
    "expfx1_symmetrical_explosion_D": ("分裂烟雾对称爆", False, 6, "中心炸散复位"),

    # ── 受击类型 7：手风琴压缩 (适配重压爆裂、力场下压) ──
    "fx3_toon_impact": ("重压气泡爆裂", False, 7, "手风琴压缩"),
    "scifx2_debuff": ("虚弱压制力场下降", False, 7, "手风琴压缩"),

    # ── 受击类型 8：地震颠簸 (适配死灵骷髅震爆、孢子烟幕、腐蚀爆裂、星辉烟团) ──
    "fanfx1_skull_puff": ("死灵骷髅烟雾爆炸", False, 8, "地震颠簸"),
    "fx3_smoke_bomb": ("暗影孢子烟雾爆炸", False, 8, "地震颠簸"),
    "fx3_splatter": ("腐蚀烟雾泡沫爆炸", False, 8, "地震颠簸"),
    "fanfx1_magic_puff_A": ("秘法星星烟雾爆炸", False, 8, "地震颠簸"),
    "fx1_magic_puff": ("星辉烟团爆炸星星", False, 8, "地震颠簸"),
}


def parse_spritesheet_txt(txt_path):
    frames = []
    if not os.path.exists(txt_path):
        return frames
    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "=" not in line:
                continue
            left, right = line.split("=", 1)
            frame_name = left.strip().split("/")[-1]
            parts = right.strip().split()
            if len(parts) == 4:
                x, y, w, h = map(int, parts)
                frames.append({"name": frame_name, "x": x, "y": y, "w": w, "h": h})
    return frames


def stitch_two_spritesheets(png1, txt1, png2, txt2, dst_png, dst_txt):
    img1 = Image.open(png1).convert("RGBA")
    img2 = Image.open(png2).convert("RGBA")
    rects1 = parse_spritesheet_txt(txt1)
    rects2 = parse_spritesheet_txt(txt2)

    total_w = img1.width + img2.width
    max_h = max(img1.height, img2.height)
    combined = Image.new("RGBA", (total_w, max_h), (0, 0, 0, 0))
    combined.paste(img1, (0, 0))
    combined.paste(img2, (img1.width, 0))
    combined.save(dst_png)

    combined_rects = []
    txt_lines = []
    idx = 0
    for r in rects1:
        fname = f"frame{idx:04d}.png"
        combined_rects.append({"name": fname, "x": r["x"], "y": r["y"], "w": r["w"], "h": r["h"]})
        txt_lines.append(f"{fname} = {r['x']} {r['y']} {r['w']} {r['h']}")
        idx += 1
    for r in rects2:
        fname = f"frame{idx:04d}.png"
        nx = r["x"] + img1.width
        ny = r["y"]
        combined_rects.append({"name": fname, "x": nx, "y": ny, "w": r["w"], "h": r["h"]})
        txt_lines.append(f"{fname} = {nx} {ny} {r['w']} {r['h']}")
        idx += 1

    with open(dst_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines) + "\n")

    fw = combined_rects[0]["w"] if combined_rects else 64
    fh = combined_rects[0]["h"] if combined_rects else 64
    return fw, fh, len(combined_rects), combined_rects


def compute_recommended_scale(width, height):
    max_dim = max(width, height)
    if max_dim <= 64:
        return 2.1
    elif max_dim <= 96:
        return 1.65
    elif max_dim <= 128:
        return 1.35
    elif max_dim <= 160:
        return 1.15
    else:
        return 1.0


def main():
    with open(EFFECT_NAMES_JSON, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    tuning_path = os.path.join(UNITY_RESOURCES_DIR, "EffectTimingConfig.json")
    if os.path.exists(tuning_path):
        with open(tuning_path, encoding="utf-8-sig") as f:
            tuned = json.load(f)
        for profile in tuned.get("profiles", []):
            key = profile.get("familyKey")
            if key in FAMILY_META:
                title, default_self, hit, name = FAMILY_META[key]
                hit = profile.get("reactionType", hit)
                names = ["水平震退", "垂直击飞", "抛物线后仰", "四向旋转翻滚", "波浪状掀飞", "中心炸散复位", "手风琴压缩", "地震颠簸", "中心聚拢吸附", "集体旋转散开"]
                FAMILY_META[key] = (title, profile.get("playOnCaster", default_self), hit, names[hit - 1])

    # 1. 将需要禁用的 loop / 球类特效写回 effect_names.json 标记为【禁用】，并确保 target_self 第二标签已初始化
    json_updated = False
    for full_key, info in raw_data.items():
        folder = info["folder"]
        base_key, size, color = pen.split_full_animation(folder)
        if base_key in FORCE_DISABLE_BASE_KEYS:
            if info.get("category") != "禁用":
                info["category"] = "禁用"
                json_updated = True
        if "target_self" not in info:
            is_self = base_key in pen.DEFAULT_SELF_TARGET_BASE_ACTIONS
            info["target_self"] = is_self
            info["target_tag"] = "针对自身" if is_self else "针对敌方"
            json_updated = True

    if json_updated:
        with open(EFFECT_NAMES_JSON, "w", encoding="utf-8") as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)
        print("Updated effect_names.json: synced loop disables and initialized target_self (第二标签).")

    # 2. 按 base_action 聚合，读取用户第一标签 (category) 与第二标签 (target_self: 是否针对自身)
    families = {}
    family_user_tags = {}
    family_target_self = {}
    for full_key, info in raw_data.items():
        folder = info["folder"]
        base_key, size, color = pen.split_full_animation(folder)
        cat = info.get("category", "").strip()
        if cat and base_key not in family_user_tags:
            family_user_tags[base_key] = cat
        if "target_self" in info and base_key not in family_target_self:
            family_target_self[base_key] = bool(info["target_self"])

        if size != "large":
            continue
        if base_key in REDUNDANT_FRAGMENT_KEYS or base_key in STITCHED_FAMILIES:
            continue
        families.setdefault(base_key, {})[color] = info

    # 严格过滤掉所有被标记为【禁用】的家族
    enabled_base_keys = []
    disabled_base_keys = []
    for base_key in sorted(families.keys()):
        user_tag = family_user_tags.get(base_key, "通用")
        if "禁用" in user_tag or base_key in FORCE_DISABLE_BASE_KEYS:
            disabled_base_keys.append(base_key)
        else:
            enabled_base_keys.append(base_key)

    # 加入合成家族 (scifx2_black_hole, scifx1_wormhole, fx2_bubble_appear)，除非用户在命名工具里将其源片段标为禁用
    active_stitched_keys = []
    for sk in STITCHED_FAMILIES.keys():
        src_key = (
            "scifx2_black_hole_appear"
            if sk == "scifx2_black_hole"
            else ("scifx1_wormhole_start" if sk == "scifx1_wormhole" else "fx2_bubble_appear")
        )
        src_tag = family_user_tags.get(src_key, STITCHED_FAMILIES[sk]["user_tag"])
        if "禁用" in src_tag:
            disabled_base_keys.append(sk)
        else:
            active_stitched_keys.append(sk)

    all_active_keys = sorted(enabled_base_keys + active_stitched_keys)
    print(f"Active families: {len(all_active_keys)} (including {len(active_stitched_keys)} stitched appear+disappear families), {len(disabled_base_keys)} disabled.")

    # Preserve Sprite GUIDs, per-frame pivots and previously allocated IDs.
    os.makedirs(UNITY_EFFECTS_DIR, exist_ok=True)
    os.makedirs(UNITY_RESOURCES_DIR, exist_ok=True)
    registry_path = ID_REGISTRY_PATH
    with open(registry_path, encoding="utf-8") as handle:
        stable_ids = json.load(handle)
    anim_id_counter = max(stable_ids.values(), default=1000) + 1
    def allocate_id(folder):
        nonlocal anim_id_counter
        if folder not in stable_ids:
            stable_ids[folder] = anim_id_counter
            anim_id_counter += 1
        return stable_ids[folder]

    mapping_families = {}
    flat_by_id = {}
    copied_sheets = 0

    for base_key in all_active_keys:
        if base_key in STITCHED_FAMILIES:
            s_cfg = STITCHED_FAMILIES[base_key]
            pack = s_cfg["pack"]
            src_key = (
                "scifx2_black_hole_appear"
                if base_key == "scifx2_black_hole"
                else ("scifx1_wormhole_start" if base_key == "scifx1_wormhole" else "fx2_bubble_appear")
            )
            user_tag = family_user_tags.get(src_key, s_cfg["user_tag"])
            category_cn, default_self, base_hit_type, base_hit_name = FAMILY_META[base_key]
            play_on_caster = bool(family_target_self.get(src_key, default_self))
            # 核心规则：针对自身的特效，对敌人就是普通击退 (1: 水平震退)
            hit_type = 1 if play_on_caster else base_hit_type
            hit_name = "水平震退" if play_on_caster else base_hit_name
            variants_out = {}
            w, h, frames_cnt = 64, 64, 18

            for color in sorted(s_cfg["colors"]):
                p1_folder = s_cfg["part1_pattern"].format(color=color)
                p2_folder = s_cfg["part2_pattern"].format(color=color)
                p1_dir = os.path.join(MEGAPACK_ROOT, pack, "spritesheet", p1_folder)
                p2_dir = os.path.join(MEGAPACK_ROOT, pack, "spritesheet", p2_folder)

                png1 = os.path.join(p1_dir, "spritesheet.png")
                txt1 = os.path.join(p1_dir, "spritesheet.txt")
                png2 = os.path.join(p2_dir, "spritesheet.png")
                txt2 = os.path.join(p2_dir, "spritesheet.txt")

                norm_folder = f"{base_key}_large_{color}"
                dst_png = os.path.join(UNITY_EFFECTS_DIR, f"{norm_folder}.png")
                dst_txt = os.path.join(UNITY_EFFECTS_DIR, f"{norm_folder}.txt")

                w, h, frames_cnt, frame_rects = stitch_two_spritesheets(png1, txt1, png2, txt2, dst_png, dst_txt)
                copied_sheets += 1

                rec_scale = compute_recommended_scale(w, h)
                color_cn = COLOR_CN_MAP.get(color, color)
                custom_name = s_cfg["cn_template"].format(color_cn=color_cn)

                aid = allocate_id(norm_folder)

                variant_entry = {
                    "animation_id": aid,
                    "base_key": base_key,
                    "color": color,
                    "folder": norm_folder,
                    "pack": pack,
                    "custom_name": custom_name,
                    "category_cn": category_cn,
                    "user_tag": user_tag,
                    "target_self": play_on_caster,
                    "hit_reaction_type": hit_type,
                    "hit_reaction_name": hit_name,
                    "base_hit_reaction_type": base_hit_type,
                    "base_hit_reaction_name": base_hit_name,
                    "width": w,
                    "height": h,
                    "frame_count": frames_cnt,
                    "fps": 15,
                    "recommended_scale": rec_scale,
                    "play_on_caster": play_on_caster,
                    "frames": frame_rects,
                }
                variants_out[color] = variant_entry
                flat_by_id[str(aid)] = variant_entry

            mapping_families[base_key] = {
                "base_key": base_key,
                "category_cn": category_cn,
                "user_tag": user_tag,
                "target_self": play_on_caster,
                "hit_reaction_type": hit_type,
                "hit_reaction_name": hit_name,
                "base_hit_reaction_type": base_hit_type,
                "base_hit_reaction_name": base_hit_name,
                "width": w,
                "height": h,
                "frame_count": frames_cnt,
                "fps": 15,
                "recommended_scale": compute_recommended_scale(w, h),
                "play_on_caster": play_on_caster,
                "variants": variants_out,
            }
            continue

        color_dict = families[base_key]
        user_tag = family_user_tags.get(base_key, "通用")
        category_cn, default_self, base_hit_type, base_hit_name = FAMILY_META.get(
            base_key, (user_tag, False, 1, "水平震退")
        )
        play_on_caster = bool(family_target_self.get(base_key, default_self))
        # 核心规则：针对自身的特效，对敌人就是普通击退 (1: 水平震退)
        hit_type = 1 if play_on_caster else base_hit_type
        hit_name = "水平震退" if play_on_caster else base_hit_name

        sample_info = next(iter(color_dict.values()))
        w_str, h_str = sample_info["size"].split("x")
        w, h = int(w_str), int(h_str)
        rec_scale = compute_recommended_scale(w, h)

        variants_out = {}
        for color in sorted(color_dict.keys()):
            info = color_dict[color]
            orig_folder = info["folder"]
            pack = info["pack"]
            custom_name = info.get("custom_name", orig_folder)
            frames_cnt = info.get("frames", 1)

            sheet_dir = os.path.join(MEGAPACK_ROOT, pack, "spritesheet", orig_folder)
            png_src = os.path.join(sheet_dir, "spritesheet.png")
            txt_src = os.path.join(sheet_dir, "spritesheet.txt")

            if not os.path.exists(png_src) or not os.path.exists(txt_src):
                print(f"[ERROR] Missing spritesheet for {orig_folder}")
                continue

            # 统一规范化输出文件名为 {base_key}_large_{color}.png/.txt，确保 100% 零路径偏差
            norm_folder = f"{base_key}_large_{color}"
            png_dst = os.path.join(UNITY_EFFECTS_DIR, f"{norm_folder}.png")
            txt_dst = os.path.join(UNITY_EFFECTS_DIR, f"{norm_folder}.txt")
            shutil.copy2(png_src, png_dst)
            shutil.copy2(txt_src, txt_dst)
            copied_sheets += 1

            frame_rects = parse_spritesheet_txt(txt_src)
            aid = allocate_id(norm_folder)

            variant_entry = {
                "animation_id": aid,
                "base_key": base_key,
                "color": color,
                "folder": norm_folder,
                "pack": pack,
                "custom_name": custom_name,
                "category_cn": category_cn,
                "user_tag": user_tag,
                "target_self": play_on_caster,
                "hit_reaction_type": hit_type,
                "hit_reaction_name": hit_name,
                "base_hit_reaction_type": base_hit_type,
                "base_hit_reaction_name": base_hit_name,
                "width": w,
                "height": h,
                "frame_count": frames_cnt,
                "fps": 15,
                "recommended_scale": rec_scale,
                "play_on_caster": play_on_caster,
                "frames": frame_rects,
            }
            variants_out[color] = variant_entry
            flat_by_id[str(aid)] = variant_entry

        mapping_families[base_key] = {
            "base_key": base_key,
            "category_cn": category_cn,
            "user_tag": user_tag,
            "target_self": play_on_caster,
            "hit_reaction_type": hit_type,
            "hit_reaction_name": hit_name,
            "base_hit_reaction_type": base_hit_type,
            "base_hit_reaction_name": base_hit_name,
            "width": w,
            "height": h,
            "frame_count": sample_info.get("frames", 1),
            "fps": 15,
            "recommended_scale": rec_scale,
            "play_on_caster": play_on_caster,
            "variants": variants_out,
        }

    with open(registry_path, "w", encoding="utf-8") as handle:
        json.dump(stable_ids, handle, ensure_ascii=False, indent=2)

    # 4. 严格校验每一个变体的 .png 和 .txt 是否 100% 存在且有效
    missing_cnt = 0
    for aid_str, ve in flat_by_id.items():
        fn = ve["folder"]
        p_png = os.path.join(UNITY_EFFECTS_DIR, f"{fn}.png")
        p_txt = os.path.join(UNITY_EFFECTS_DIR, f"{fn}.txt")
        if not os.path.exists(p_png) or not os.path.exists(p_txt) or os.path.getsize(p_png) == 0:
            print(f"[FATAL] Missing or empty file for ID {aid_str}: {fn}")
            missing_cnt += 1
    assert missing_cnt == 0, f"Found {missing_cnt} missing spritesheet files!"

    output_payload = {
        "version": "3.1",
        "fps": 15,
        "total_families": len(mapping_families),
        "total_variants": len(flat_by_id),
        "disabled_families_count": len(disabled_base_keys),
        "families": mapping_families,
        "by_id": flat_by_id,
    }

    with open(OUTPUT_MAPPING_JSON, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=2)

    unity_json_path = os.path.join(UNITY_RESOURCES_DIR, "effect_skill_mapping.json")
    with open(unity_json_path, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=2)

    reg_lines = []
    for bk, fam in sorted(mapping_families.items()):
        cat_cn = fam["category_cn"]
        poc = "true" if fam["play_on_caster"] else "false"
        utag = fam.get("user_tag", "通用")
        target_label = "自身" if fam["play_on_caster"] else "对敌"
        htype = fam["hit_reaction_type"]
        hname = fam["hit_reaction_name"]
        vparts = []
        for col, v in sorted(fam["variants"].items()):
            vparts.append(f"{col}:{v['animation_id']}:{v['custom_name']}")
        vstr = "|".join(vparts)
        reg_lines.append(
            f'            Reg("{bk}", "[{utag}|{target_label}] {cat_cn}", "{utag}", {poc}, {htype}, "{hname}", "{vstr}");'
        )

    with open(r"d:\123\generated_reg_lines.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(reg_lines) + "\n")

    print(
        f"Done! Active Families: {len(mapping_families)}, Active Variants: {len(flat_by_id)} "
        f"(ID 1001 ~ {anim_id_counter - 1}), Copied/Stitched sheets: {copied_sheets}, Missing: {missing_cnt}"
    )


if __name__ == "__main__":
    main()
