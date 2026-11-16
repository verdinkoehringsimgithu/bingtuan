# -*- coding: utf-8 -*-
"""
Super Pixel Effects Megapack 1 - 动画检视与极速命名工具 (Pixel Effect Namer v3.1)
核心特性：
1. 【大/小双规格完全合并】：凡是存在大、小对应的特效，绝不展示重复行！列表从 2036 个极致精简至仅 143 个核心动作！
2. 【大/小双规格+全颜色一键同步 (Enter 极速流)】：只命名代表项，Enter 键全自动为大、小双尺寸以及全部颜色变体（每组约12~16个动画）同步推导并保存！
3. 【播放器原地即时切换】：画布下方提供 [大尺寸] [小尺寸] 规格切换与 [蓝] [绿] [橙] [红] [紫] [黄] 颜色切换，原地预览，零翻页负担。
4. 【多格式自动导出】：实时同步保存至 JSON、UTF-8-BOM CSV (Excel兼容) 和快捷查询字典。
"""

import os
import sys
import json
import csv
import glob
import re
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk, ImageDraw

# Windows 高 DPI 适配
try:
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

# ==========================================
# 词典与智能推导规则
# ==========================================
COLORS_ORDERED = [
    'dark_blue', 'dark_brown', 'light_blue', 'light_brown',
    'black', 'blue', 'brown', 'gray', 'green', 'orange',
    'pink', 'rainbow', 'red', 'violet', 'white', 'yellow'
]

SIZES_LIST = ['large', 'medium', 'small']

COLOR_MAP = {
    'blue': '蓝', 'green': '绿', 'orange': '橙', 'red': '红', 'violet': '紫', 'yellow': '黄',
    'black': '黑', 'white': '白', 'gray': '灰', 'brown': '棕',
    'dark_blue': '蓝', 'light_blue': '浅蓝', 'dark_brown': '棕', 'light_brown': '浅棕',
    'pink': '粉', 'rainbow': '彩虹'
}

COLOR_LONG_MAP = {
    'blue': '蓝色', 'green': '绿色', 'orange': '橙色', 'red': '红色', 'violet': '紫色', 'yellow': '黄色',
    'black': '黑色', 'white': '白色', 'gray': '灰色', 'brown': '棕色'
}

COLOR_UI_BUTTONS = {
    'blue': ('#3b82f6', '#ffffff'),
    'green': ('#10b981', '#ffffff'),
    'orange': ('#f97316', '#ffffff'),
    'red': ('#ef4444', '#ffffff'),
    'violet': ('#8b5cf6', '#ffffff'),
    'yellow': ('#eab308', '#000000'),
    'black': ('#27272a', '#ffffff'),
    'white': ('#f4f4f5', '#000000'),
    'gray': ('#6b7280', '#ffffff'),
    'brown': ('#78350f', '#ffffff'),
    'dark_blue': ('#1e3a8a', '#ffffff'),
    'light_blue': ('#60a5fa', '#000000'),
    'dark_brown': ('#451a03', '#ffffff'),
    'light_brown': ('#92400e', '#ffffff'),
    'pink': ('#ec4899', '#ffffff'),
    'rainbow': ('#d946ef', '#ffffff')
}

SIZE_TRANSLATIONS = {
    'large': '大',
    'medium': '中',
    'small': '小'
}

TOKEN_TRANSLATIONS = {
    'absorb': '吸收', 'appear': '显现', 'aura': '光环', 'back': '后层', 'beam': '光束',
    'bite': '撕咬', 'blob': '粘液球', 'blood': '水花', 'bomb': '炸弹', 'boost': '喷射推进',
    'bubble': '泡泡', 'buff': '增益', 'burst': '气浪', 'charge': '蓄力', 'claw': '爪击',
    'cure': '治愈', 'dark': '暗影', 'dash': '冲刺气体', 'debuff': '减益', 'disappear': '消散',
    'dust': '扬尘', 'earth': '大地', 'electric': '电火花', 'electricity': '电弧', 'end': '收招',
    'energy': '光球', 'epic': '大', 'explosion': '爆炸', 'fire': '火焰', 'fireball': '火球',
    'front': '前层', 'ground': '地面', 'hacking': '数据骇入', 'helix': '螺旋', 'hex': '六边形',
    'hit': '击中横向', 'hole': '黑洞', 'ice': '冰晶', 'impact': '向下气浪', 'kunai': '苦无',
    'laser': '激光', 'light': '圣光', 'lightning': '雷电', 'loop': '循环', 'magic': '魔法',
    'meteor': '陨石', 'missile': '飞弹', 'orb': '法球', 'poison': '毒素', 'pop': '爆炸',
    'power': '充能', 'puff': '烟团星星', 'quick': '迅捷', 'rock': '碎石', 'scan': '扫描',
    'scifi': '科幻', 'shatter': '碎裂', 'shield': '气体屏障', 'shock': '向下冲击', 'shockwave': '冲击波',
    'shuriken': '手里剑', 'skull': '骷髅', 'slash': '圆斩', 'smoke': '烟雾', 'sparks': '火花',
    'spawn': '召唤生成', 'spell': '法术', 'spellcast': '施法', 'spike': '地刺', 'spikes': '地刺',
    'splash': '喷溅水花', 'splatter': '爆裂溅射', 'start': '起手', 'stop': '停止', 'stream': '远喷水花',
    'stylized': '风格化', 'swirl': '魔法光柱', 'symmetrical': '对称', 'tech': '科技', 'tileable': '平铺',
    'toon': '卡通', 'trail': '刹车扬尘', 'up': '向上', 'warp': '跃迁', 'wind': '狂风',
    'wormhole': '虫洞', 'zap': '电火花'
}

PREFIX_STRIP = {'bldfx1', 'fx1', 'fx2', 'fx3', 'expfx1', 'fanfx1', 'fanfx2', 'impfx1', 'pj1', 'pj2', 'scifx1', 'scifx2'}

def split_full_animation(anim_name):
    """
    精确使用 _large_ 与 _small_ 剥离尺寸与颜色：
    无论文件夹名如何组织，严格提取：核心动作名、尺寸(大/小)、颜色
    """
    if '_large_' in anim_name:
        parts = anim_name.split('_large_', 1)
        size = 'large'
    elif '_small_' in anim_name:
        parts = anim_name.split('_small_', 1)
        size = 'small'
    else:
        return anim_name, 'large', 'default'
        
    base_prefix = parts[0]
    rest = parts[1]
    
    color = 'default'
    suffix = ''
    for c in COLORS_ORDERED:
        if rest == c:
            color = c
            suffix = ''
            break
        elif rest.startswith(c + '_'):
            color = c
            suffix = rest[len(c) + 1:]
            break
            
    if suffix:
        base_action = f"{base_prefix}_{suffix}"
    else:
        base_action = base_prefix
        
    return base_action, size, color

REF_COLOR_ALIASES = {
    'blue': ['蓝色', '蓝'],
    'dark_blue': ['深蓝色', '深蓝', '蓝色', '蓝'],
    'light_blue': ['浅蓝色', '浅蓝', '蓝色', '蓝'],
    'green': ['绿色', '绿'],
    'orange': ['橙色', '橙'],
    'red': ['红色', '红'],
    'violet': ['紫色', '紫'],
    'yellow': ['黄色', '黄'],
    'black': ['黑色', '黑', '灰色', '灰'],
    'white': ['白色', '白'],
    'gray': ['灰色', '灰'],
    'brown': ['棕色', '棕'],
    'dark_brown': ['深棕色', '深棕', '棕色', '棕'],
    'light_brown': ['浅棕色', '浅棕', '棕色', '棕'],
    'pink': ['粉色', '粉'],
    'rainbow': ['彩虹色', '彩虹']
}

SIZE_PREFIXES = ('大', '小', '中', '巨')

def derive_variant_name(base_custom_name, ref_color, target_color):
    """
    根据颜色精准推导：
    将前缀代表颜色(如大蓝/巨蓝中的'蓝')替换为目标颜色(如'绿'/'红'/'黄'/'紫')，
    严格保留特效自带的双色/附带特征色(如'大蓝紫色' -> '大绿紫色', 不会破坏次要颜色)。
    """
    if not base_custom_name or ref_color == target_color:
        return base_custom_name
        
    tgt_short = COLOR_MAP.get(target_color, '')
    tgt_long = COLOR_LONG_MAP.get(target_color, tgt_short + '色')
    
    # 1. 检查是否以尺寸前缀 (大/小/中/巨) 开头，后面紧跟参考色
    for sz in SIZE_PREFIXES:
        if base_custom_name.startswith(sz):
            rest = base_custom_name[len(sz):]
            aliases = REF_COLOR_ALIASES.get(ref_color, [COLOR_MAP.get(ref_color, '')])
            matched_alias = None
            for alias in aliases:
                if alias and rest.startswith(alias):
                    matched_alias = alias
                    break
            if matched_alias:
                after_color = rest[len(matched_alias):]
                replacement = tgt_long if matched_alias.endswith('色') else tgt_short
                new_name = f"{sz}{replacement}{after_color}"
                # 消除双重同色叠字 (如 大紫+紫色 -> 大紫色, 大黄+黄色 -> 大黄色, 大紫+紫光 -> 大紫光)
                double_pattern_long = f"{sz}{tgt_short}{tgt_short}色"
                if new_name.startswith(double_pattern_long):
                    new_name = f"{sz}{tgt_short}色" + new_name[len(double_pattern_long):]
                double_pattern_opt = f"{sz}{tgt_short}{tgt_short}"
                if new_name.startswith(double_pattern_opt):
                    new_name = f"{sz}{tgt_short}" + new_name[len(double_pattern_opt):]
                return new_name

    # 2. 检查是否无尺寸前缀直接以参考色开头 (如 蓝色火焰 -> 绿色火焰)
    aliases = REF_COLOR_ALIASES.get(ref_color, [COLOR_MAP.get(ref_color, '')])
    for alias in aliases:
        if alias and base_custom_name.startswith(alias):
            after_color = base_custom_name[len(alias):]
            replacement = tgt_long if alias.endswith('色') else tgt_short
            new_name = f"{replacement}{after_color}"
            if new_name.startswith(f"{tgt_short}{tgt_short}色"):
                new_name = f"{tgt_short}色" + new_name[len(f"{tgt_short}{tgt_short}色"):]
            elif new_name.startswith(f"{tgt_short}{tgt_short}"):
                new_name = f"{tgt_short}" + new_name[len(f"{tgt_short}{tgt_short}"):]
            return new_name

    # 3. 如果前缀没匹配，但别名在名称中出现 (仅严格匹配当前参考色的别名，绝不误伤其它颜色)
    for alias in aliases:
        if alias and alias in base_custom_name:
            replacement = tgt_long if alias.endswith('色') else tgt_short
            return base_custom_name.replace(alias, replacement, 1)

    # 4. 若名称中无任何颜色词，则在尺寸后插入目标颜色
    if base_custom_name.startswith(SIZE_PREFIXES):
        return f"{base_custom_name[0]}{tgt_short}{base_custom_name[1:]}"
        
    return f"{base_custom_name}-{tgt_short}"

def derive_family_name(base_custom_name, ref_size, ref_color, target_size, target_color):
    """
    全家族双重自动推导：尺寸 (大/小) + 颜色 (红/绿/蓝/黄/紫...)
    完美支持 巨/大/中 到 小 的规整映射，消除 '小巨' 等冗余前缀。
    """
    name_color = derive_variant_name(base_custom_name, ref_color, target_color)
    if target_size == ref_size:
        return name_color
        
    if target_size == 'small':
        if name_color.startswith(('大', '中', '巨')):
            return '小' + name_color[1:]
        elif not name_color.startswith('小'):
            return '小' + name_color
        return name_color
    elif target_size == 'large':
        if name_color.startswith('小'):
            return '大' + name_color[1:]
        elif not name_color.startswith(('大', '中', '巨')):
            return '大' + name_color
        return name_color
    return name_color

def generate_smart_name(folder_name):
    """根据文件夹名智能生成中文建议"""
    tokens = folder_name.split('_')
    name_parts = []
    color_part = ''
    size_part = ''
    layer_part = ''
    
    for t in tokens:
        if t in PREFIX_STRIP:
            continue
        elif t in COLOR_MAP:
            color_part = COLOR_MAP[t]
        elif t in SIZE_TRANSLATIONS:
            size_part = SIZE_TRANSLATIONS[t]
        elif t in ('front', 'back'):
            layer_part = '前层' if t == 'front' else '后层'
        elif t in TOKEN_TRANSLATIONS:
            name_parts.append(TOKEN_TRANSLATIONS[t])
        elif len(t) == 1 and t.isupper():
            name_parts.append(t)
        else:
            name_parts.append(t)
            
    base = ''.join(name_parts)
    prefix = (size_part if size_part else '大') + (color_part if color_part else '')
    res = f"{prefix}{base}"
    if layer_part:
        res += f"_{layer_part}"
    return res or folder_name

DEFAULT_SELF_TARGET_BASE_ACTIONS = {
    'scifx2_hex_shield',
    'fx2_bubble_appear',
    'fx2_bubble_loop',
    'fanfx2_cure',
    'fanfx2_cure_back',
    'fanfx2_cure_front',
    'scifx2_buff',
    'scifx2_tech_aura',
    'scifx2_tech_aura_back',
    'scifx2_tech_aura_front',
    'fanfx1_spellcast_B',
    'fanfx1_spellcast_B_back',
    'fanfx1_spellcast_B_front',
    'fanfx1_spellcast_D',
    'fx2_magic_swirl',
    'fanfx1_magic_puff_B',
}

# ==========================================
# 数据管理类
# ==========================================
class EffectDataManager:
    def __init__(self, workspace_dir):
        self.workspace_dir = workspace_dir
        self.json_path = os.path.join(workspace_dir, "effect_names.json")
        self.csv_path = os.path.join(workspace_dir, "effect_names.csv")
        self.quick_map_path = os.path.join(workspace_dir, "effect_names_quick_map.json")
        self.data = {}
        self.load_data()
        
    def load_data(self):
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                # 为尚未初始化 target_self 第二标签的历史记录补齐默认值
                changed = False
                for k, v in self.data.items():
                    if 'target_self' not in v:
                        folder = v.get('folder', '')
                        base_act, _, _ = split_full_animation(folder)
                        is_self = (base_act in DEFAULT_SELF_TARGET_BASE_ACTIONS)
                        v['target_self'] = is_self
                        v['target_tag'] = "针对自身" if is_self else "针对敌方"
                        changed = True
                if changed:
                    self.persist()
            except Exception as e:
                print(f"Error loading {self.json_path}: {e}")
                self.data = {}
        else:
            self.data = {}
            
    def get_info(self, anim_key):
        return self.data.get(anim_key, {})
        
    def save_item(self, anim_item, custom_name, category, target_self, notes, persist=True):
        anim_key = anim_item['key']
        is_self = bool(target_self)
        self.data[anim_key] = {
            'pack': anim_item['pack'],
            'folder': anim_item['folder'],
            'rel_path': anim_item['rel_path'],
            'custom_name': custom_name.strip(),
            'category': category.strip(),
            'target_self': is_self,
            'target_tag': "针对自身" if is_self else "针对敌方",
            'notes': notes.strip(),
            'frames': anim_item['frame_count'],
            'size': f"{anim_item['width']}x{anim_item['height']}",
            'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        if persist:
            self.persist()
            
    def batch_update(self, updates_list):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for anim_item, custom_name, category, target_self in updates_list:
            anim_key = anim_item['key']
            existing_notes = self.data.get(anim_key, {}).get('notes', '')
            is_self = bool(target_self)
            self.data[anim_key] = {
                'pack': anim_item['pack'],
                'folder': anim_item['folder'],
                'rel_path': anim_item['rel_path'],
                'custom_name': custom_name.strip(),
                'category': category.strip(),
                'target_self': is_self,
                'target_tag': "针对自身" if is_self else "针对敌方",
                'notes': existing_notes,
                'frames': anim_item['frame_count'],
                'size': f"{anim_item['width']}x{anim_item['height']}",
                'updated_at': now_str
            }
        self.persist()
        
    def persist(self):
        try:
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error writing json: {e}")
            
        try:
            quick_map = {v['folder']: v['custom_name'] for v in self.data.values() if v.get('custom_name')}
            with open(self.quick_map_path, 'w', encoding='utf-8') as f:
                json.dump(quick_map, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error writing quick map: {e}")
            
        try:
            with open(self.csv_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['资源包 (Pack)', '原文件夹名 (Folder)', '中文自定义名称 (Name)', '第一标签:流派定性 (Category)', '第二标签:是否针对自身 (Target)', '帧数 (Frames)', '分辨率 (Size)', '相对路径', '备注', '最后更新时间'])
                for k, v in sorted(self.data.items(), key=lambda x: (x[1].get('pack', ''), x[1].get('folder', ''))):
                    writer.writerow([
                        v.get('pack', ''),
                        v.get('folder', ''),
                        v.get('custom_name', ''),
                        v.get('category', ''),
                        "针对自身" if v.get('target_self', False) else "针对敌方",
                        v.get('frames', ''),
                        v.get('size', ''),
                        v.get('rel_path', ''),
                        v.get('notes', ''),
                        v.get('updated_at', '')
                    ])
        except Exception as e:
            print(f"Error writing csv: {e}")

# ==========================================
# 动画扫描与核心动作分组
# ==========================================
def scan_all_animations(megapack_root):
    items = []
    if not os.path.exists(megapack_root):
        return items
        
    packs = sorted([d for d in os.listdir(megapack_root) if os.path.isdir(os.path.join(megapack_root, d))])
    
    for pack in packs:
        png_dir = os.path.join(megapack_root, pack, "PNG")
        if not os.path.exists(png_dir):
            continue
            
        anims = sorted([a for a in os.listdir(png_dir) if os.path.isdir(os.path.join(png_dir, a))])
        for anim in anims:
            anim_dir = os.path.join(png_dir, anim)
            frames = sorted(glob.glob(os.path.join(anim_dir, "*.png")))
            if not frames:
                continue
                
            width, height = 64, 64
            try:
                with Image.open(frames[0]) as img:
                    width, height = img.size
            except Exception:
                pass
                
            base_action, size, color = split_full_animation(anim)
            key = f"{pack}/{anim}"
            rel_path = f"{pack}/PNG/{anim}"
            
            items.append({
                'key': key,
                'pack': pack,
                'folder': anim,
                'rel_path': rel_path,
                'full_dir': anim_dir,
                'frames': frames,
                'frame_count': len(frames),
                'width': width,
                'height': height,
                'base_action': base_action,
                'size': size,
                'color': color
            })
            
    return items

# ==========================================
# 六大核心技能定性标签配置
# ==========================================
SIX_TAGS = [
    ("先机", "1", "#0284c7", "#38bdf8", "⚡ 先机 [1]"),
    ("坚韧", "2", "#059669", "#34d399", "🛡️ 坚韧 [2]"),
    ("勇气", "3", "#dc2626", "#f87171", "🔥 勇气 [3]"),
    ("魔力", "4", "#7c3aed", "#a78bfa", "🔮 魔力 [4]"),
    ("通用", "5", "#d97706", "#fbbf24", "🌟 通用 [5]"),
    ("禁用", "6", "#4b5563", "#9ca3af", "🚫 禁用 [6]"),
]

TAG_COLOR_MAP = {t[0]: (t[2], t[3]) for t in SIX_TAGS}

# ==========================================
# 主 GUI 界面
# ==========================================
class PixelEffectViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Super Pixel Effects Megapack 1 - 特效流派定性打标与命名工具 v4.0 (先机/坚韧/勇气/魔力/通用/禁用)")
        self.root.geometry("1480x940")
        self.root.minsize(1150, 740)
        
        # 图标
        app_dir = os.path.abspath(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__))
        icon_path = os.path.join(app_dir, "app_icon.ico")
        if not os.path.exists(icon_path):
            icon_path = r"d:\123\app_icon.ico"
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass
        
        # 路径定位
        d123 = r"d:\123"
        default_target = os.path.join(d123, "Super Pixel Effects Megapack 1")
        if os.path.exists(default_target):
            self.megapack_root = default_target
            self.workspace_dir = d123
        elif os.path.exists(os.path.join(app_dir, "Super Pixel Effects Megapack 1")):
            self.megapack_root = os.path.join(app_dir, "Super Pixel Effects Megapack 1")
            self.workspace_dir = app_dir
        else:
            self.megapack_root = default_target
            self.workspace_dir = d123

        self.data_manager = EffectDataManager(self.workspace_dir)
        
        # 核心数据结构
        self.animations = []             # 全部 2036 个动画
        self.action_families = {}        # {(pack, base_action): [item_idx, ...]} (全包仅 143 组)
        self.action_family_keys = []     # 排序后的动作 key 列表 (143 个)
        self.action_representatives = [] # 每组的核心大尺寸主动画 (无任何小尺寸或多余变种)
        
        # 筛选列表
        self.display_anim_indices = []
        self.current_anim_idx = 0
        self.current_frame_idx = 0
        self.is_playing = True
        self.fps = 15
        self.zoom_scale = 4.0
        self.bg_mode = "dark"
        self._loaded_custom_name = ""
        
        # 缓存
        self.cached_anim_key = None
        self.cached_pil_frames = []
        self.cached_tk_frames = []
        
        # 模式控制：默认严格开启隐藏小尺寸与变种，绝不重复展示！
        self.hide_small_and_variants_var = tk.BooleanVar(value=True)
        self.auto_sync_family_var = tk.BooleanVar(value=True)
        self.click_tag_auto_next_var = tk.BooleanVar(value=True)
        self.tag_buttons = {}
        
        # 初始化 UI
        self._setup_styles()
        self._build_ui()
        self.reload_pack_data()
        self._bind_global_shortcuts()
        self._play_loop()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        self.bg_color = "#18181b"
        self.panel_bg = "#27272a"
        self.fg_color = "#f4f4f5"
        
        self.root.configure(bg=self.bg_color)
        
        style.configure("TFrame", background=self.panel_bg)
        style.configure("TLabelframe", background=self.panel_bg, foreground=self.fg_color)
        style.configure("TLabelframe.Label", background=self.panel_bg, foreground="#60a5fa", font=("Microsoft YaHei", 10, "bold"))
        style.configure("TLabel", background=self.panel_bg, foreground=self.fg_color, font=("Microsoft YaHei", 9))
        
        style.configure("Treeview", 
                        background="#111113", 
                        foreground="#f4f4f5", 
                        fieldbackground="#111113",
                        font=("Microsoft YaHei", 9),
                        rowheight=26)
        style.configure("Treeview.Heading", 
                        background="#3f3f46", 
                        foreground="#93c5fd", 
                        font=("Microsoft YaHei", 9, "bold"))
        style.map("Treeview", background=[('selected', '#2563eb')])

    def _build_ui(self):
        # 顶部工具栏
        top_bar = tk.Frame(self.root, bg="#202023", height=50, padx=12, pady=8)
        top_bar.pack(side=tk.TOP, fill=tk.X)
        
        title_lbl = tk.Label(top_bar, text="✨ Super Pixel FX 双标签定性打标与命名工具 (第一标签:流派 | 第二标签:是否针对自身)", bg="#202023", fg="#60a5fa", font=("Microsoft YaHei", 11, "bold"))
        title_lbl.pack(side=tk.LEFT, padx=(0, 12))
        
        self.stats_lbl = tk.Label(top_bar, text="正在加载...", bg="#202023", fg="#fde68a", font=("Microsoft YaHei", 9, "bold"))
        self.stats_lbl.pack(side=tk.LEFT, padx=6)
        
        # 按钮区
        btn_open_folder = tk.Button(top_bar, text="📂 打开保存目录", bg="#3f3f46", fg="#ffffff", relief=tk.FLAT, padx=8, pady=3, font=("Microsoft YaHei", 9), command=self.open_output_folder)
        btn_open_folder.pack(side=tk.RIGHT, padx=4)
        
        btn_export_csv = tk.Button(top_bar, text="📊 导出 Excel/CSV", bg="#059669", fg="#ffffff", relief=tk.FLAT, padx=8, pady=3, font=("Microsoft YaHei", 9, "bold"), command=self.export_csv_prompt)
        btn_export_csv.pack(side=tk.RIGHT, padx=4)
        
        btn_change_dir = tk.Button(top_bar, text="📁 切换特效包路径", bg="#3f3f46", fg="#ffffff", relief=tk.FLAT, padx=8, pady=3, font=("Microsoft YaHei", 9), command=self.choose_custom_pack_dir)
        btn_change_dir.pack(side=tk.RIGHT, padx=4)
        
        # 主体左右分栏
        main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg=self.bg_color, sashrelief=tk.RAISED, sashwidth=4)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # 左侧列表区
        left_frame = tk.Frame(main_paned, bg=self.panel_bg, padx=8, pady=8)
        main_paned.add(left_frame, minsize=540, width=615)
        
        # 模式切换与过滤器
        filter_box = tk.Frame(left_frame, bg=self.panel_bg)
        filter_box.pack(fill=tk.X, pady=(0, 6))
        
        chk_hide_small = tk.Checkbutton(
            filter_box,
            text="⚡ 核心纯享模式 (隐藏小尺寸与同色变体，全包仅 143 个核心动作)",
            variable=self.hide_small_and_variants_var,
            bg=self.panel_bg,
            fg="#fbbf24",
            activebackground=self.panel_bg,
            activeforeground="#fde68a",
            selectcolor="#18181b",
            font=("Microsoft YaHei", 9, "bold"),
            command=self.apply_filter
        )
        chk_hide_small.grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 4))
        
        tk.Label(filter_box, text="资源包:", bg=self.panel_bg, fg="#a1a1aa", font=("Microsoft YaHei", 9)).grid(row=1, column=0, sticky="w", pady=2)
        self.pack_filter_cb = ttk.Combobox(filter_box, state="readonly", width=16)
        self.pack_filter_cb.grid(row=1, column=1, sticky="ew", padx=3, pady=2)
        self.pack_filter_cb.bind("<<ComboboxSelected>>", lambda e: self.apply_filter())

        tk.Label(filter_box, text="第一标签:", bg=self.panel_bg, fg="#fbbf24", font=("Microsoft YaHei", 9, "bold")).grid(row=1, column=2, sticky="w", padx=(4, 0), pady=2)
        self.tag_filter_cb = ttk.Combobox(filter_box, state="readonly", width=9, values=["全部标签", "未打标", "先机", "坚韧", "勇气", "魔力", "通用", "禁用"])
        self.tag_filter_cb.set("全部标签")
        self.tag_filter_cb.grid(row=1, column=3, sticky="ew", padx=3, pady=2)
        self.tag_filter_cb.bind("<<ComboboxSelected>>", lambda e: self.apply_filter())

        tk.Label(filter_box, text="第二标签:", bg=self.panel_bg, fg="#34d399", font=("Microsoft YaHei", 9, "bold")).grid(row=1, column=4, sticky="w", padx=(4, 0), pady=2)
        self.target_filter_cb = ttk.Combobox(filter_box, state="readonly", width=11, values=["全部目标", "🛡️ 针对自身", "⚔️ 针对敌方"])
        self.target_filter_cb.set("全部目标")
        self.target_filter_cb.grid(row=1, column=5, sticky="ew", padx=3, pady=2)
        self.target_filter_cb.bind("<<ComboboxSelected>>", lambda e: self.apply_filter())
        
        tk.Label(filter_box, text="搜索:", bg=self.panel_bg, fg="#a1a1aa", font=("Microsoft YaHei", 9)).grid(row=2, column=0, sticky="w", pady=2)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.apply_filter())
        search_entry = tk.Entry(filter_box, textvariable=self.search_var, bg="#111113", fg="#ffffff", insertbackground="#ffffff", relief=tk.FLAT, font=("Microsoft YaHei", 9))
        search_entry.grid(row=2, column=1, columnspan=5, sticky="ew", padx=4, pady=2)
        
        self.status_filter_var = tk.StringVar(value="all")
        radio_box = tk.Frame(filter_box, bg=self.panel_bg)
        radio_box.grid(row=3, column=0, columnspan=6, sticky="w", pady=(4, 2))
        
        r1 = tk.Radiobutton(radio_box, text="全部 (143)", variable=self.status_filter_var, value="all", bg=self.panel_bg, fg="#e2e8f0", selectcolor="#111113", command=self.apply_filter)
        r_untagged = tk.Radiobutton(radio_box, text="🏷️ 未打标", variable=self.status_filter_var, value="untagged", bg=self.panel_bg, fg="#fde68a", selectcolor="#111113", font=("Microsoft YaHei", 9, "bold"), command=self.apply_filter)
        r_tagged = tk.Radiobutton(radio_box, text="✅ 已打标", variable=self.status_filter_var, value="tagged", bg=self.panel_bg, fg="#6ee7b7", selectcolor="#111113", font=("Microsoft YaHei", 9, "bold"), command=self.apply_filter)
        r_self = tk.Radiobutton(radio_box, text="🛡️ 仅看针对自身", variable=self.status_filter_var, value="self_only", bg=self.panel_bg, fg="#38bdf8", selectcolor="#111113", font=("Microsoft YaHei", 9, "bold"), command=self.apply_filter)
        r2 = tk.Radiobutton(radio_box, text="⚪ 未命名", variable=self.status_filter_var, value="unnamed", bg=self.panel_bg, fg="#a1a1aa", selectcolor="#111113", command=self.apply_filter)
        r1.pack(side=tk.LEFT, padx=4)
        r_untagged.pack(side=tk.LEFT, padx=4)
        r_tagged.pack(side=tk.LEFT, padx=4)
        r_self.pack(side=tk.LEFT, padx=4)
        r2.pack(side=tk.LEFT, padx=4)
        
        filter_box.columnconfigure(1, weight=1)
        filter_box.columnconfigure(3, weight=1)
        filter_box.columnconfigure(5, weight=1)
        
        # 列表 Treeview (包含 第一标签 与 第二标签 列)
        tree_container = tk.Frame(left_frame, bg="#111113")
        tree_container.pack(fill=tk.BOTH, expand=True)
        
        columns = ("status", "tag", "target", "name", "folder", "variants")
        self.tree = ttk.Treeview(tree_container, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("status", text="状态")
        self.tree.heading("tag", text="第一标签(流派)")
        self.tree.heading("target", text="第二标签(自身)")
        self.tree.heading("name", text="中文命名")
        self.tree.heading("folder", text="核心特效动作名")
        self.tree.heading("variants", text="规格信息")
        
        self.tree.column("status", width=38, minwidth=34, anchor="center")
        self.tree.column("tag", width=78, minwidth=64, anchor="center")
        self.tree.column("target", width=72, minwidth=62, anchor="center")
        self.tree.column("name", width=130, minwidth=95)
        self.tree.column("folder", width=175, minwidth=120)
        self.tree.column("variants", width=80, minwidth=60, anchor="center")
        
        tree_scroll = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        
        # 右侧播放与编辑区
        right_frame = tk.Frame(main_paned, bg=self.panel_bg, padx=12, pady=6)
        main_paned.add(right_frame, minsize=620)
        
        # 1. 播放器视口容器
        player_frame = ttk.LabelFrame(right_frame, text=" 动画播放视口 (Pixel Canvas) ")
        player_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))
        
        self.canvas = tk.Canvas(player_frame, bg="#181818", highlightthickness=0, takefocus=1)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        self.canvas.bind("<Configure>", lambda e: self.redraw_current_frame())
        self.canvas.bind("<Button-1>", lambda e: self.canvas.focus_set())
        
        # 变体快速预览双排栏 (尺寸切换 + 颜色切换)
        switcher_box = tk.Frame(player_frame, bg=self.panel_bg)
        switcher_box.pack(fill=tk.X, padx=8, pady=(0, 4))
        
        # 排1：尺寸切换
        row_size = tk.Frame(switcher_box, bg=self.panel_bg)
        row_size.pack(fill=tk.X, pady=(1, 2))
        tk.Label(row_size, text="📏 规格切换:", bg=self.panel_bg, fg="#60a5fa", font=("Microsoft YaHei", 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        self.size_btns_container = tk.Frame(row_size, bg=self.panel_bg)
        self.size_btns_container.pack(side=tk.LEFT, fill=tk.X)
        
        # 排2：颜色切换
        row_color = tk.Frame(switcher_box, bg=self.panel_bg)
        row_color.pack(fill=tk.X, pady=(1, 2))
        tk.Label(row_color, text="🎨 颜色预览:", bg=self.panel_bg, fg="#fbbf24", font=("Microsoft YaHei", 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        self.color_btns_container = tk.Frame(row_color, bg=self.panel_bg)
        self.color_btns_container.pack(side=tk.LEFT, fill=tk.X)
        
        # 控制栏 (播放、帧数、FPS、缩放、背景)
        canvas_bar = tk.Frame(player_frame, bg=self.panel_bg)
        canvas_bar.pack(fill=tk.X, padx=8, pady=(0, 4))
        
        self.btn_play_pause = tk.Button(canvas_bar, text="⏸ 暂停 (Space)", bg="#3f3f46", fg="#ffffff", relief=tk.FLAT, padx=6, font=("Microsoft YaHei", 9), command=self.toggle_play)
        self.btn_play_pause.pack(side=tk.LEFT, padx=2)
        
        btn_prev_frame = tk.Button(canvas_bar, text="⏮ 上一帧", bg="#3f3f46", fg="#ffffff", relief=tk.FLAT, padx=6, font=("Microsoft YaHei", 9), command=self.prev_frame)
        btn_prev_frame.pack(side=tk.LEFT, padx=2)
        
        btn_next_frame = tk.Button(canvas_bar, text="⏭ 下一帧", bg="#3f3f46", fg="#ffffff", relief=tk.FLAT, padx=6, font=("Microsoft YaHei", 9), command=self.next_frame)
        btn_next_frame.pack(side=tk.LEFT, padx=2)
        
        self.frame_lbl = tk.Label(canvas_bar, text="帧: 0/0", bg=self.panel_bg, fg="#e2e8f0", font=("Microsoft YaHei", 9))
        self.frame_lbl.pack(side=tk.LEFT, padx=8)
        
        tk.Label(canvas_bar, text="FPS:", bg=self.panel_bg, fg="#a1a1aa", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(10, 2))
        self.fps_spin = ttk.Spinbox(canvas_bar, from_=1, to=60, width=4, command=self._on_fps_change)
        self.fps_spin.set(15)
        self.fps_spin.pack(side=tk.LEFT, padx=2)
        
        tk.Label(canvas_bar, text="缩放:", bg=self.panel_bg, fg="#a1a1aa", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(12, 2))
        self.zoom_cb = ttk.Combobox(canvas_bar, values=["1x", "2x", "3x", "4x", "6x", "8x", "适应窗口"], width=7, state="readonly")
        self.zoom_cb.set("4x")
        self.zoom_cb.pack(side=tk.LEFT, padx=2)
        self.zoom_cb.bind("<<ComboboxSelected>>", self._on_zoom_change)
        
        tk.Label(canvas_bar, text="背景:", bg=self.panel_bg, fg="#a1a1aa", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(12, 2))
        self.bg_cb = ttk.Combobox(canvas_bar, values=["深灰", "纯黑", "棋盘格", "纯白", "绿幕"], width=6, state="readonly")
        self.bg_cb.set("深灰")
        self.bg_cb.pack(side=tk.LEFT, padx=2)
        self.bg_cb.bind("<<ComboboxSelected>>", self._on_bg_change)

        # ==========================================================
        # 2. 双标签极速打标区 (第一标签:流派定性 1~6 | 第二标签:是否针对自身 Q/W 或 0/7)
        # ==========================================================
        tag_box = ttk.LabelFrame(right_frame, text=" 🎯 特效双标签定性打标 (第一标签:流派 1~6 | 第二标签:是否针对自身 — 针对自身仅【坚韧】可用且对敌固定普通击退) ")
        tag_box.pack(fill=tk.X, pady=(0, 5), padx=2)

        tag_inner = tk.Frame(tag_box, bg=self.panel_bg, padx=8, pady=5)
        tag_inner.pack(fill=tk.X)

        tag_top_row = tk.Frame(tag_inner, bg=self.panel_bg)
        tag_top_row.pack(fill=tk.X, pady=(0, 4))

        self.curr_tag_status_lbl = tk.Label(
            tag_top_row,
            text="第一标签: 【未打标】",
            bg="#18181b",
            fg="#fde68a",
            padx=8,
            pady=2,
            font=("Microsoft YaHei", 9, "bold")
        )
        self.curr_tag_status_lbl.pack(side=tk.LEFT, padx=(0, 6))

        self.curr_target_status_lbl = tk.Label(
            tag_top_row,
            text="第二标签: 【⚔️ 针对敌方】",
            bg="#18181b",
            fg="#a7f3d0",
            padx=8,
            pady=2,
            font=("Microsoft YaHei", 9, "bold")
        )
        self.curr_target_status_lbl.pack(side=tk.LEFT, padx=(0, 10))

        chk_tag_autonext = tk.Checkbutton(
            tag_top_row,
            text="⚡ 点击第一标签(1~6)后自动跳下一个 (Ctrl+点击可多选流派)",
            variable=self.click_tag_auto_next_var,
            bg=self.panel_bg,
            fg="#38bdf8",
            activebackground=self.panel_bg,
            activeforeground="#bae6fd",
            selectcolor="#111113",
            font=("Microsoft YaHei", 9, "bold")
        )
        chk_tag_autonext.pack(side=tk.LEFT)

        # 第一排：第一标签（6大流派定性）
        tag_btn_row = tk.Frame(tag_inner, bg=self.panel_bg)
        tag_btn_row.pack(fill=tk.X, pady=(2, 3))

        for idx_t, (tag_name, shortcut_key, bg_col, active_col, display_text) in enumerate(SIX_TAGS):
            tag_btn_row.columnconfigure(idx_t, weight=1)
            btn = tk.Button(
                tag_btn_row,
                text=display_text,
                bg=bg_col,
                fg="#ffffff",
                activebackground=active_col,
                activeforeground="#ffffff",
                font=("Microsoft YaHei", 10, "bold"),
                relief=tk.RAISED,
                bd=2,
                pady=5,
                cursor="hand2"
            )
            btn.grid(row=0, column=idx_t, sticky="ew", padx=3)
            btn.bind("<Button-1>", lambda event, tn=tag_name: self.on_tag_button_click(tn, event))
            self.tag_buttons[tag_name] = (btn, bg_col, active_col, display_text)

        # 第二排：第二标签（是否针对自身）
        target_btn_row = tk.Frame(tag_inner, bg=self.panel_bg)
        target_btn_row.pack(fill=tk.X, pady=(3, 1))
        target_btn_row.columnconfigure(1, weight=1)
        target_btn_row.columnconfigure(2, weight=1)

        tk.Label(
            target_btn_row,
            text="🎯 第二标签(是否针对自身):",
            bg=self.panel_bg,
            fg="#34d399",
            font=("Microsoft YaHei", 9, "bold")
        ).grid(row=0, column=0, sticky="w", padx=(2, 8))

        self.btn_target_enemy = tk.Button(
            target_btn_row,
            text="⚔️ 针对敌方 (默认：按第一标签流派可用 + 触发专属受击) [快捷键 Q / 0]",
            bg="#3f3f46",
            fg="#ffffff",
            activebackground="#60a5fa",
            activeforeground="#000000",
            font=("Microsoft YaHei", 9, "bold"),
            relief=tk.RAISED,
            bd=2,
            pady=4,
            cursor="hand2",
            command=lambda: self.apply_target_self_tag(False)
        )
        self.btn_target_enemy.grid(row=0, column=1, sticky="ew", padx=3)

        self.btn_target_self = tk.Button(
            target_btn_row,
            text="🛡️ 针对自身 (仅【坚韧】可用 + 施法自身播放 + 敌方普通击退) [快捷键 W / 7]",
            bg="#0f766e",
            fg="#ffffff",
            activebackground="#2dd4bf",
            activeforeground="#000000",
            font=("Microsoft YaHei", 9, "bold"),
            relief=tk.RAISED,
            bd=2,
            pady=4,
            cursor="hand2",
            command=lambda: self.apply_target_self_tag(True)
        )
        self.btn_target_self.grid(row=0, column=2, sticky="ew", padx=3)
        
        # 3. 动画信息与智能推荐
        meta_box = ttk.LabelFrame(right_frame, text=" 动画信息与智能推荐 ")
        meta_box.pack(fill=tk.X, pady=(0, 4), padx=2)
        
        meta_inner = tk.Frame(meta_box, bg=self.panel_bg, padx=8, pady=3)
        meta_inner.pack(fill=tk.X)
        
        self.info_pack_lbl = tk.Label(meta_inner, text="资源包: -", bg=self.panel_bg, fg="#93c5fd", font=("Microsoft YaHei", 9))
        self.info_pack_lbl.pack(anchor="w")
        
        self.info_folder_lbl = tk.Label(meta_inner, text="当前动画: -", bg=self.panel_bg, fg="#e2e8f0", font=("Microsoft YaHei", 9, "bold"))
        self.info_folder_lbl.pack(anchor="w")
        
        self.info_spec_lbl = tk.Label(meta_inner, text="规格: -", bg=self.panel_bg, fg="#a1a1aa", font=("Microsoft YaHei", 9))
        self.info_spec_lbl.pack(anchor="w")
        
        sug_frame = tk.Frame(meta_inner, bg=self.panel_bg)
        sug_frame.pack(fill=tk.X, pady=(2, 0))
        
        tk.Label(sug_frame, text="💡 智能建议:", bg=self.panel_bg, fg="#fbbf24", font=("Microsoft YaHei", 9, "bold")).pack(side=tk.LEFT)
        self.sug_lbl = tk.Label(sug_frame, text="-", bg=self.panel_bg, fg="#fde68a", font=("Microsoft YaHei", 10, "bold"))
        self.sug_lbl.pack(side=tk.LEFT, padx=8)
        
        btn_apply_sug = tk.Button(sug_frame, text="填入建议 (Alt+R)", bg="#d97706", fg="#ffffff", relief=tk.FLAT, padx=6, pady=1, font=("Microsoft YaHei", 9, "bold"), command=self.apply_smart_suggestion)
        btn_apply_sug.pack(side=tk.LEFT, padx=6)
        
        # 4. 命名录入区
        edit_box = ttk.LabelFrame(right_frame, text=" 命名与双标签微调 (支持 Enter 键保存大/小双规格及全颜色变体) ")
        edit_box.pack(fill=tk.X, pady=(0, 4), padx=2)
        
        edit_inner = tk.Frame(edit_box, bg=self.panel_bg, padx=8, pady=4)
        edit_inner.pack(fill=tk.X)
        
        chk_autosync = tk.Checkbutton(
            edit_inner,
            text="✨ 自动将【第一标签】【第二标签(是否针对自身)】与中文名同步保存至本特效全尺寸、全颜色所有变体",
            variable=self.auto_sync_family_var,
            bg=self.panel_bg,
            fg="#6ee7b7",
            activebackground=self.panel_bg,
            activeforeground="#a7f3d0",
            selectcolor="#111113",
            font=("Microsoft YaHei", 9, "bold")
        )
        chk_autosync.grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 4))
        
        tk.Label(edit_inner, text="动画中文命名 *:", bg=self.panel_bg, fg="#60a5fa", font=("Microsoft YaHei", 10, "bold")).grid(row=1, column=0, sticky="w", pady=3)
        self.name_entry = tk.Entry(edit_inner, font=("Microsoft YaHei", 11), bg="#111113", fg="#ffffff", insertbackground="#ffffff", relief=tk.FLAT)
        self.name_entry.grid(row=1, column=1, columnspan=5, sticky="ew", padx=8, pady=3)
        self.name_entry.bind("<Return>", lambda e: self.save_and_next())
        
        tk.Label(edit_inner, text="第一标签(流派):", bg=self.panel_bg, fg="#fbbf24", font=("Microsoft YaHei", 9, "bold")).grid(row=2, column=0, sticky="w", pady=3)
        self.category_entry = ttk.Combobox(edit_inner, values=["先机", "坚韧", "勇气", "魔力", "通用", "禁用"], font=("Microsoft YaHei", 9, "bold"), width=12)
        self.category_entry.grid(row=2, column=1, sticky="ew", padx=6, pady=3)
        self.category_entry.bind("<Return>", lambda e: self.save_and_next())
        self.category_entry.bind("<<ComboboxSelected>>", lambda e: self._refresh_tag_buttons_highlight(self.category_entry.get().strip(), self._get_current_target_self_bool()))

        tk.Label(edit_inner, text="第二标签(自身):", bg=self.panel_bg, fg="#34d399", font=("Microsoft YaHei", 9, "bold")).grid(row=2, column=2, sticky="w", padx=(6, 0), pady=3)
        self.target_entry = ttk.Combobox(edit_inner, state="readonly", values=["针对敌方", "针对自身"], font=("Microsoft YaHei", 9, "bold"), width=10)
        self.target_entry.set("针对敌方")
        self.target_entry.grid(row=2, column=3, sticky="ew", padx=6, pady=3)
        self.target_entry.bind("<Return>", lambda e: self.save_and_next())
        self.target_entry.bind("<<ComboboxSelected>>", lambda e: (self._refresh_tag_buttons_highlight(self.category_entry.get().strip(), self._get_current_target_self_bool()), self.save_current_only()))
        
        tk.Label(edit_inner, text="备注:", bg=self.panel_bg, fg="#e2e8f0", font=("Microsoft YaHei", 9)).grid(row=2, column=4, sticky="w", padx=(6, 0), pady=3)
        self.notes_entry = tk.Entry(edit_inner, font=("Microsoft YaHei", 9), bg="#111113", fg="#ffffff", insertbackground="#ffffff", relief=tk.FLAT)
        self.notes_entry.grid(row=2, column=5, sticky="ew", padx=6, pady=3)
        self.notes_entry.bind("<Return>", lambda e: self.save_and_next())
        
        edit_inner.columnconfigure(1, weight=1)
        edit_inner.columnconfigure(3, weight=1)
        edit_inner.columnconfigure(5, weight=2)
        
        # 底部操作栏
        btn_action_box = tk.Frame(right_frame, bg=self.panel_bg)
        btn_action_box.pack(fill=tk.X, pady=(4, 2))
        
        btn_save_next = tk.Button(btn_action_box, text="💾 保存并切下一个动作 (Enter)", bg="#2563eb", fg="#ffffff", font=("Microsoft YaHei", 10, "bold"), relief=tk.FLAT, padx=14, pady=5, command=self.save_and_next)
        btn_save_next.pack(side=tk.LEFT, padx=(0, 8))
        
        btn_save_curr = tk.Button(btn_action_box, text="仅保存 (Ctrl+S)", bg="#3f3f46", fg="#ffffff", font=("Microsoft YaHei", 9), relief=tk.FLAT, padx=10, pady=5, command=self.save_current_only)
        btn_save_curr.pack(side=tk.LEFT, padx=4)
        
        btn_prev = tk.Button(btn_action_box, text="◀ 上一个 (Alt+← / ↑)", bg="#3f3f46", fg="#ffffff", font=("Microsoft YaHei", 9), relief=tk.FLAT, padx=8, pady=5, command=self.go_prev_anim)
        btn_prev.pack(side=tk.RIGHT, padx=4)
        
        btn_next = tk.Button(btn_action_box, text="下一个 ▶ (Alt+→ / ↓)", bg="#3f3f46", fg="#ffffff", font=("Microsoft YaHei", 9), relief=tk.FLAT, padx=8, pady=5, command=self.go_next_anim)
        btn_next.pack(side=tk.RIGHT, padx=4)

    def _bind_global_shortcuts(self):
        self.root.bind("<space>", lambda e: self._handle_space(e))
        self.root.bind("<Control-s>", lambda e: (self.save_current_only(), "break")[1])
        self.root.bind("<Alt-Left>", lambda e: (self.go_prev_anim(), "break")[1])
        self.root.bind("<Alt-Right>", lambda e: (self.go_next_anim(), "break")[1])
        self.root.bind("<Alt-r>", lambda e: (self.apply_smart_suggestion(), "break")[1])

        # 绑定数字键 1~6、小键盘 1~6、F1~F6、Alt+1~6 极速打第一标签
        for idx_t, (tag_name, key_num, _, _, _) in enumerate(SIX_TAGS):
            self.root.bind(f"<Key-{key_num}>", lambda e, tn=tag_name: self._handle_number_hotkey(e, tn))
            self.root.bind(f"<KP_{key_num}>", lambda e, tn=tag_name: self._handle_number_hotkey(e, tn))
            self.root.bind(f"<F{key_num}>", lambda e, tn=tag_name: (self.apply_quick_tag(tn, toggle_multi=False), "break")[1])
            self.root.bind(f"<Alt-Key-{key_num}>", lambda e, tn=tag_name: (self.apply_quick_tag(tn, toggle_multi=False), "break")[1])

        # 绑定第二标签快捷键: 0 / Q = 针对敌方, 7 / W = 针对自身
        self.root.bind("<Key-0>", lambda e: self._handle_target_hotkey(e, False))
        self.root.bind("<KP_0>", lambda e: self._handle_target_hotkey(e, False))
        self.root.bind("<Key-q>", lambda e: self._handle_target_hotkey(e, False))
        self.root.bind("<Key-Q>", lambda e: self._handle_target_hotkey(e, False))
        self.root.bind("<Key-7>", lambda e: self._handle_target_hotkey(e, True))
        self.root.bind("<KP_7>", lambda e: self._handle_target_hotkey(e, True))
        self.root.bind("<Key-w>", lambda e: self._handle_target_hotkey(e, True))
        self.root.bind("<Key-W>", lambda e: self._handle_target_hotkey(e, True))

    def _get_current_target_self_bool(self):
        return self.target_entry.get().strip() == "针对自身"

    def _handle_target_hotkey(self, event, is_self):
        widget = self.root.focus_get()
        if isinstance(widget, (tk.Entry, ttk.Combobox, ttk.Spinbox)):
            return
        self.apply_target_self_tag(is_self)
        return "break"

    def apply_target_self_tag(self, is_self):
        self.target_entry.set("针对自身" if is_self else "针对敌方")
        self._refresh_tag_buttons_highlight(self.category_entry.get().strip(), is_self)
        self.save_current_only()

    def _handle_number_hotkey(self, event, tag_name):
        widget = self.root.focus_get()
        if isinstance(widget, (tk.Entry, ttk.Combobox, ttk.Spinbox)):
            return
        self.apply_quick_tag(tag_name, toggle_multi=False)
        return "break"

    def _handle_space(self, event):
        widget = self.root.focus_get()
        if isinstance(widget, (tk.Entry, ttk.Combobox)):
            return
        self.toggle_play()
        return "break"

    def on_tag_button_click(self, tag_name, event=None):
        # 按住 Ctrl 点击可多选组合标签 (例如 勇气,先机)
        ctrl_pressed = bool(event and (event.state & 0x0004))
        self.apply_quick_tag(tag_name, toggle_multi=ctrl_pressed)
        return "break"

    def apply_quick_tag(self, tag_name, toggle_multi=False):
        curr_cat = self.category_entry.get().strip()
        is_self = self._get_current_target_self_bool()
        if toggle_multi:
            parts = [p.strip() for p in curr_cat.replace("，", ",").replace("/", ",").split(",") if p.strip()]
            if tag_name == "禁用":
                new_cat = "禁用"
            else:
                if "禁用" in parts:
                    parts.remove("禁用")
                if tag_name in parts:
                    parts.remove(tag_name)
                else:
                    parts.append(tag_name)
                new_cat = ",".join(parts) if parts else tag_name
            self.category_entry.set(new_cat)
            self._refresh_tag_buttons_highlight(new_cat, is_self)
            self.save_current_only()
        else:
            self.category_entry.set(tag_name)
            self._refresh_tag_buttons_highlight(tag_name, is_self)
            if self.click_tag_auto_next_var.get():
                self.save_and_next()
            else:
                self.save_current_only()

    def _refresh_tag_buttons_highlight(self, cat_text, is_self=None):
        cat_text = (cat_text or "").strip()
        if is_self is None:
            is_self = self._get_current_target_self_bool()

        active_tags = {p.strip() for p in cat_text.replace("，", ",").replace("/", ",").split(",") if p.strip()}

        if active_tags:
            first_tag = next(iter(active_tags))
            bg_c, _ = TAG_COLOR_MAP.get(first_tag, ("#2563eb", "#60a5fa"))
            self.curr_tag_status_lbl.config(text=f"第一标签: 【{cat_text}】", bg=bg_c, fg="#ffffff")
        else:
            self.curr_tag_status_lbl.config(text="第一标签: 【未打标】", bg="#18181b", fg="#fde68a")

        for tag_name, (btn, bg_col, active_col, display_text) in self.tag_buttons.items():
            if tag_name in active_tags:
                btn.config(
                    text=f"✔ {display_text}",
                    bg=active_col,
                    fg="#000000" if tag_name in ("通用", "坚韧", "先机") else "#ffffff",
                    relief=tk.SUNKEN,
                    bd=4
                )
            else:
                btn.config(
                    text=display_text,
                    bg=bg_col,
                    fg="#ffffff",
                    relief=tk.RAISED,
                    bd=2
                )

        if hasattr(self, 'btn_target_self') and hasattr(self, 'btn_target_enemy'):
            if is_self:
                self.curr_target_status_lbl.config(text="第二标签: 【🛡️ 针对自身 (仅坚韧·敌普通击退)】", bg="#0f766e", fg="#ffffff")
                self.btn_target_self.config(
                    text="✔ 🛡️ 针对自身 (仅【坚韧】可用 + 施法自身播放 + 敌方普通击退) [W / 7]",
                    bg="#2dd4bf",
                    fg="#000000",
                    relief=tk.SUNKEN,
                    bd=4
                )
                self.btn_target_enemy.config(
                    text="⚔️ 针对敌方 (默认：按第一标签流派可用 + 触发专属受击) [Q / 0]",
                    bg="#3f3f46",
                    fg="#ffffff",
                    relief=tk.RAISED,
                    bd=2
                )
            else:
                self.curr_target_status_lbl.config(text="第二标签: 【⚔️ 针对敌方】", bg="#18181b", fg="#a7f3d0")
                self.btn_target_enemy.config(
                    text="✔ ⚔️ 针对敌方 (默认：按第一标签流派可用 + 触发专属受击) [Q / 0]",
                    bg="#60a5fa",
                    fg="#000000",
                    relief=tk.SUNKEN,
                    bd=4
                )
                self.btn_target_self.config(
                    text="🛡️ 针对自身 (仅【坚韧】可用 + 施法自身播放 + 敌方普通击退) [W / 7]",
                    bg="#0f766e",
                    fg="#ffffff",
                    relief=tk.RAISED,
                    bd=2
                )

    def choose_custom_pack_dir(self):
        folder = filedialog.askdirectory(title="选择 Super Pixel Effects Megapack 1 文件夹", initialdir=self.workspace_dir)
        if folder:
            self.megapack_root = folder
            self.reload_pack_data()

    # ==========================================
    # 数据加载、分组构建与过滤
    # ==========================================
    def reload_pack_data(self):
        self.animations = scan_all_animations(self.megapack_root)
        
        # 构建核心动作分组映射 (合并大、小以及所有颜色，全包精确 143 组)
        self.action_families = {}
        for idx, item in enumerate(self.animations):
            fam_key = (item['pack'], item['base_action'])
            if fam_key not in self.action_families:
                self.action_families[fam_key] = []
            self.action_families[fam_key].append(idx)
            
        self.action_family_keys = sorted(list(self.action_families.keys()), key=lambda x: (x[0], x[1]))
        
        # 计算每组的主代表动画 (大尺寸、首选蓝色/黑色，绝无小尺寸)
        self.action_representatives = []
        for fam_key in self.action_family_keys:
            indices = self.action_families[fam_key]
            # 严格筛选出大尺寸动画
            large_candidates = [i for i in indices if self.animations[i]['size'] == 'large']
            if not large_candidates:
                large_candidates = indices
                
            rep_idx = large_candidates[0]
            for idx in large_candidates:
                item = self.animations[idx]
                if item['color'] == 'blue':
                    rep_idx = idx
                    break
                elif item['color'] in ('black', 'dark_blue') and self.animations[rep_idx]['color'] not in ('blue', 'black'):
                    rep_idx = idx
            self.action_representatives.append(rep_idx)
            
        packs = sorted(list({item['pack'] for item in self.animations}))
        cb_values = ["全部资源包"] + packs
        self.pack_filter_cb['values'] = cb_values
        self.pack_filter_cb.set("全部资源包")
        
        self.apply_filter()

    def _get_family_name_and_tag(self, item, siblings):
        info = self.data_manager.get_info(item['key'])
        custom_name = info.get('custom_name', '').strip()
        cat_tag = info.get('category', '').strip()
        has_target_key = ('target_self' in info)
        target_self = bool(info.get('target_self', item['base_action'] in DEFAULT_SELF_TARGET_BASE_ACTIONS))
        if not custom_name or not cat_tag or not has_target_key:
            for s_idx in siblings:
                s_info = self.data_manager.get_info(self.animations[s_idx]['key'])
                if not custom_name and s_info.get('custom_name'):
                    custom_name = s_info.get('custom_name').strip()
                if not cat_tag and s_info.get('category'):
                    cat_tag = s_info.get('category').strip()
                if not has_target_key and ('target_self' in s_info):
                    target_self = bool(s_info.get('target_self', False))
                    has_target_key = True
                if custom_name and cat_tag and has_target_key:
                    break
        return custom_name, cat_tag, target_self

    def apply_filter(self):
        sel_pack = self.pack_filter_cb.get()
        sel_tag = self.tag_filter_cb.get() if hasattr(self, 'tag_filter_cb') else "全部标签"
        sel_target = self.target_filter_cb.get() if hasattr(self, 'target_filter_cb') else "全部目标"
        search_kw = self.search_var.get().strip().lower()
        status_mode = self.status_filter_var.get()
        hide_variants = self.hide_small_and_variants_var.get()
        
        curr_key = None
        if 0 <= self.current_anim_idx < len(self.animations):
            curr_key = self.animations[self.current_anim_idx]['key']
            
        self.display_anim_indices = []
        
        for row in self.tree.get_children():
            self.tree.delete(row)
            
        # 候选列表：hide_variants 时绝对只有 143 个代表项，不含任何小尺寸或变种
        candidate_indices = self.action_representatives if hide_variants else list(range(len(self.animations)))
        
        for idx in candidate_indices:
            item = self.animations[idx]
            fam_key = (item['pack'], item['base_action'])
            siblings = self.action_families.get(fam_key, [idx])
            
            if hide_variants:
                custom_name, cat_tag, target_self = self._get_family_name_and_tag(item, siblings)
            else:
                info = self.data_manager.get_info(item['key'])
                custom_name = info.get('custom_name', '').strip()
                cat_tag = info.get('category', '').strip()
                target_self = bool(info.get('target_self', item['base_action'] in DEFAULT_SELF_TARGET_BASE_ACTIONS))
                
            has_name = bool(custom_name)
            has_tag = bool(cat_tag)
                        
            if sel_pack and sel_pack != "全部资源包" and item['pack'] != sel_pack:
                continue

            if sel_tag and sel_tag != "全部标签":
                if sel_tag == "未打标":
                    if has_tag:
                        continue
                else:
                    if sel_tag not in cat_tag:
                        continue

            if sel_target and sel_target != "全部目标":
                if "针对自身" in sel_target and not target_self:
                    continue
                if "针对敌方" in sel_target and target_self:
                    continue
                
            if status_mode == "unnamed" and has_name:
                continue
            if status_mode == "named" and not has_name:
                continue
            if status_mode == "untagged" and has_tag:
                continue
            if status_mode == "tagged" and not has_tag:
                continue
            if status_mode == "self_only" and not target_self:
                continue
                
            if search_kw:
                target_kw = "针对自身" if target_self else "针对敌方"
                match = (search_kw in item['folder'].lower() or 
                         search_kw in custom_name.lower() or 
                         search_kw in cat_tag.lower() or
                         search_kw in target_kw.lower() or
                         search_kw in item['pack'].lower() or
                         search_kw in item['base_action'].lower())
                if not match:
                    continue
                    
            self.display_anim_indices.append(idx)
            if "禁用" in cat_tag:
                status_icon = "🚫"
            elif has_tag:
                status_icon = "✅"
            elif has_name:
                status_icon = "🏷️"
            else:
                status_icon = "⚪"

            tag_display = f"【{cat_tag}】" if cat_tag else "未打标"
            target_display = "🛡️自身" if target_self else "⚔️敌方"
            
            if hide_variants:
                display_folder = f"{item['base_action']}"
                spec_info = f"共{len(siblings)}变体 {item['frame_count']}F"
            else:
                display_folder = item['folder']
                spec_info = f"{item['size']}_{item['color']} {item['frame_count']}F"
                
            self.tree.insert("", tk.END, iid=str(idx), values=(status_icon, tag_display, target_display, custom_name, display_folder, spec_info))
            
        self._update_stats_label()
            
        if self.display_anim_indices:
            target_idx = self.display_anim_indices[0]
            if curr_key:
                for f_idx in self.display_anim_indices:
                    if self.animations[f_idx]['key'] == curr_key:
                        target_idx = f_idx
                        break
            self.select_animation_by_index(target_idx)
        else:
            self._clear_editor()

    def select_animation_by_index(self, anim_index):
        if not (0 <= anim_index < len(self.animations)):
            return
            
        self.current_anim_idx = anim_index
        item = self.animations[anim_index]
        
        fam_key = (item['pack'], item['base_action'])
        siblings = self.action_families.get(fam_key, [anim_index])
        
        # 查找在树形表格中显示的行 ID
        target_iid = str(anim_index)
        if not self.tree.exists(target_iid) and self.hide_small_and_variants_var.get():
            for s_idx in siblings:
                if self.tree.exists(str(s_idx)):
                    target_iid = str(s_idx)
                    break
                    
        if self.tree.exists(target_iid):
            self.tree.selection_set(target_iid)
            self.tree.see(target_iid)
            
        self._load_animation_frames(item)
        
        info = self.data_manager.get_info(item['key'])
        
        size_cn = '大尺寸' if item['size'] == 'large' else ('小尺寸' if item['size'] == 'small' else item['size'])
        color_cn = COLOR_MAP.get(item['color'], item['color'])
        
        self.info_pack_lbl.config(text=f"资源包: {item['pack']}")
        self.info_folder_lbl.config(text=f"当前动画: {item['folder']}  (核心动作: {item['base_action']}，全组共 {len(siblings)} 个大小/颜色变体)")
        self.info_spec_lbl.config(text=f"规格: {item['width']}x{item['height']} 像素 | 帧数: {item['frame_count']} 帧 | 当前预览: 【{size_cn} / {color_cn}】")
        
        smart_sug = generate_smart_name(item['folder'])
        self.sug_lbl.config(text=smart_sug)
        
        custom_name = info.get('custom_name', '').strip()
        cat_tag = info.get('category', '').strip()
        has_target_key = ('target_self' in info)
        target_self = bool(info.get('target_self', item['base_action'] in DEFAULT_SELF_TARGET_BASE_ACTIONS))
        if not custom_name or not cat_tag or not has_target_key:
            for s_idx in siblings:
                s_info = self.data_manager.get_info(self.animations[s_idx]['key'])
                if not custom_name and s_info.get('custom_name'):
                    custom_name = derive_family_name(s_info['custom_name'], self.animations[s_idx]['size'], self.animations[s_idx]['color'], item['size'], item['color'])
                if not cat_tag and s_info.get('category'):
                    cat_tag = s_info.get('category', '').strip()
                if not has_target_key and ('target_self' in s_info):
                    target_self = bool(s_info.get('target_self', False))
                    has_target_key = True
                if custom_name and cat_tag and has_target_key:
                    break
                    
        self._loaded_custom_name = custom_name
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, custom_name)
        
        self.category_entry.set(cat_tag)
        self.target_entry.set("针对自身" if target_self else "针对敌方")
        self._refresh_tag_buttons_highlight(cat_tag, target_self)

        self.notes_entry.delete(0, tk.END)
        self.notes_entry.insert(0, info.get('notes', ''))
        
        # 刷新尺寸与颜色快速切换栏
        self._refresh_family_switchers(siblings, anim_index)
        
        # 如果已经有中文名，默认把焦点放在画布上，方便直接按键盘数字键 1~6 / Q / W 极速打标签！
        if custom_name:
            self.canvas.focus_set()
        else:
            self.name_entry.focus_set()
            self.name_entry.select_range(0, tk.END)

    def _refresh_family_switchers(self, sibling_indices, active_idx):
        active_item = self.animations[active_idx]
        
        # 1. 刷新规格/尺寸切换按钮 (大 / 小)
        for child in self.size_btns_container.winfo_children():
            child.destroy()
            
        sizes_in_family = sorted(list({self.animations[i]['size'] for i in sibling_indices}), reverse=True)
        for s in sizes_in_family:
            is_active = (s == active_item['size'])
            s_label = '● 大尺寸 (Large)' if (s == 'large' and is_active) else ('大尺寸 (Large)' if s == 'large' else ('● 小尺寸 (Small)' if (s == 'small' and is_active) else '小尺寸 (Small)'))
            btn_bg = '#2563eb' if is_active else '#3f3f46'
            
            # 找到对应同颜色的目标索引
            target_idx = None
            for idx in sibling_indices:
                if self.animations[idx]['size'] == s and self.animations[idx]['color'] == active_item['color']:
                    target_idx = idx
                    break
            if target_idx is None:
                for idx in sibling_indices:
                    if self.animations[idx]['size'] == s:
                        target_idx = idx
                        break
                        
            btn = tk.Button(
                self.size_btns_container,
                text=s_label,
                bg=btn_bg,
                fg='#ffffff',
                font=("Microsoft YaHei", 8, "bold" if is_active else "normal"),
                relief=tk.SUNKEN if is_active else tk.FLAT,
                bd=2 if is_active else 0,
                padx=8,
                pady=1,
                command=lambda t=target_idx: self.select_animation_by_index(t) if t is not None else None
            )
            btn.pack(side=tk.LEFT, padx=3)
            
        # 2. 刷新颜色切换按钮
        for child in self.color_btns_container.winfo_children():
            child.destroy()
            
        colors_in_family = [i for i in sibling_indices if self.animations[i]['size'] == active_item['size']]
        if not colors_in_family:
            colors_in_family = sibling_indices
            
        for s_idx in colors_in_family:
            sib_item = self.animations[s_idx]
            c_name = sib_item['color']
            c_cn = COLOR_MAP.get(c_name, c_name)
            
            is_active = (s_idx == active_idx)
            btn_bg, btn_fg = COLOR_UI_BUTTONS.get(c_name, ('#4b5563', '#ffffff'))
            
            btn = tk.Button(
                self.color_btns_container,
                text=f"{'● ' if is_active else ''}{c_cn}",
                bg=btn_bg,
                fg=btn_fg,
                font=("Microsoft YaHei", 8, "bold" if is_active else "normal"),
                relief=tk.SUNKEN if is_active else tk.FLAT,
                bd=2 if is_active else 0,
                padx=6,
                pady=1,
                command=lambda target_i=s_idx: self.select_animation_by_index(target_i)
            )
            btn.pack(side=tk.LEFT, padx=3)

    def _clear_editor(self):
        self.cached_pil_frames = []
        self.cached_tk_frames = []
        self.canvas.delete("all")
        self.info_pack_lbl.config(text="资源包: -")
        self.info_folder_lbl.config(text="当前动画: -")
        self.info_spec_lbl.config(text="规格: -")
        self.sug_lbl.config(text="-")
        self.name_entry.delete(0, tk.END)
        self.category_entry.set("")
        self.target_entry.set("针对敌方")
        self._refresh_tag_buttons_highlight("", False)
        self.notes_entry.delete(0, tk.END)
        self.frame_lbl.config(text="帧: 0/0")
        for child in self.size_btns_container.winfo_children():
            child.destroy()
        for child in self.color_btns_container.winfo_children():
            child.destroy()

    def _on_tree_select(self, event):
        sel = self.tree.selection()
        if sel:
            idx = int(sel[0])
            if idx != self.current_anim_idx:
                self.select_animation_by_index(idx)

    # ==========================================
    # 动画帧加载与渲染
    # ==========================================
    def _load_animation_frames(self, item):
        self.cached_anim_key = item['key']
        self.cached_pil_frames = []
        self.cached_tk_frames = []
        self.current_frame_idx = 0
        
        for frame_file in item['frames']:
            try:
                img = Image.open(frame_file).convert("RGBA")
                self.cached_pil_frames.append(img)
            except Exception as e:
                print(f"Failed to load frame {frame_file}: {e}")
                
        self._rebuild_scaled_tk_frames()
        self.redraw_current_frame()

    def _rebuild_scaled_tk_frames(self):
        self.cached_tk_frames = []
        if not self.cached_pil_frames:
            return
            
        c_width = self.canvas.winfo_width() or 400
        c_height = self.canvas.winfo_height() or 300
        
        orig_w, orig_h = self.cached_pil_frames[0].size
        
        if self.zoom_scale == "fit":
            scale_w = max(1, c_width / orig_w)
            scale_h = max(1, c_height / orig_h)
            actual_scale = max(1.0, min(scale_w, scale_h) * 0.9)
        else:
            actual_scale = float(self.zoom_scale)
            
        new_w = max(1, int(orig_w * actual_scale))
        new_h = max(1, int(orig_h * actual_scale))
        
        for pil_img in self.cached_pil_frames:
            scaled = pil_img.resize((new_w, new_h), Image.Resampling.NEAREST)
            self.cached_tk_frames.append(ImageTk.PhotoImage(scaled))

    def redraw_current_frame(self):
        if not self.cached_tk_frames:
            self.canvas.delete("all")
            return
            
        if self.current_frame_idx >= len(self.cached_tk_frames):
            self.current_frame_idx = 0
            
        c_w = self.canvas.winfo_width()
        c_h = self.canvas.winfo_height()
        cx = c_w // 2
        cy = c_h // 2
        
        self.canvas.delete("all")
        
        if self.bg_mode == "grid":
            self.canvas.config(bg="#1e1e24")
            cell = 20
            for x in range(0, c_w, cell):
                for y in range(0, c_h, cell):
                    if ((x // cell) + (y // cell)) % 2 == 1:
                        self.canvas.create_rectangle(x, y, x + cell, y + cell, fill="#2b2b36", outline="")
        elif self.bg_mode == "black":
            self.canvas.config(bg="#000000")
        elif self.bg_mode == "white":
            self.canvas.config(bg="#ffffff")
        elif self.bg_mode == "green":
            self.canvas.config(bg="#00e676")
        else:
            self.canvas.config(bg="#181818")
            
        tk_img = self.cached_tk_frames[self.current_frame_idx]
        self.canvas.create_image(cx, cy, image=tk_img, anchor="center")
        
        self.frame_lbl.config(text=f"帧: {self.current_frame_idx + 1} / {len(self.cached_tk_frames)}")

    def _play_loop(self):
        if self.is_playing and self.cached_tk_frames:
            self.current_frame_idx = (self.current_frame_idx + 1) % len(self.cached_tk_frames)
            self.redraw_current_frame()
            
        delay_ms = max(10, int(1000 / max(1, self.fps)))
        self.root.after(delay_ms, self._play_loop)

    def toggle_play(self):
        self.is_playing = not self.is_playing
        self.btn_play_pause.config(text="▶ 播放 (Space)" if not self.is_playing else "⏸ 暂停 (Space)")

    def prev_frame(self):
        self.is_playing = False
        self.btn_play_pause.config(text="▶ 播放 (Space)")
        if self.cached_tk_frames:
            self.current_frame_idx = (self.current_frame_idx - 1) % len(self.cached_tk_frames)
            self.redraw_current_frame()

    def next_frame(self):
        self.is_playing = False
        self.btn_play_pause.config(text="▶ 播放 (Space)")
        if self.cached_tk_frames:
            self.current_frame_idx = (self.current_frame_idx + 1) % len(self.cached_tk_frames)
            self.redraw_current_frame()

    def _on_fps_change(self):
        try:
            self.fps = int(self.fps_spin.get())
        except ValueError:
            self.fps = 15

    def _on_zoom_change(self, event):
        val = self.zoom_cb.get()
        if val == "适应窗口":
            self.zoom_scale = "fit"
        else:
            self.zoom_scale = float(val.replace("x", ""))
        self._rebuild_scaled_tk_frames()
        self.redraw_current_frame()

    def _on_bg_change(self, event):
        val = self.bg_cb.get()
        mapping = {"深灰": "dark", "棋盘格": "grid", "纯黑": "black", "纯白": "white", "绿幕": "green"}
        self.bg_mode = mapping.get(val, "dark")
        self.redraw_current_frame()

    # ==========================================
    # 极速定性打标与全家族 (大/小+全颜色) 自动同步
    # ==========================================
    def apply_smart_suggestion(self):
        sug = self.sug_lbl.cget("text")
        if sug and sug != "-":
            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, sug)
            self.name_entry.focus_set()

    def save_current_only(self):
        if not (0 <= self.current_anim_idx < len(self.animations)):
            return
            
        item = self.animations[self.current_anim_idx]
        name = self.name_entry.get().strip()
        cat = self.category_entry.get().strip()
        target_self = self._get_current_target_self_bool()
        notes = self.notes_entry.get().strip()
        name_changed = (name != self._loaded_custom_name)
        
        # 1. 保存当前项
        self.data_manager.save_item(item, name, cat, target_self, notes, persist=False)
        self._loaded_custom_name = name
        
        # 2. 如果开启了自动同步全家族 (大/小全规格 + 全颜色变体)
        if self.auto_sync_family_var.get():
            fam_key = (item['pack'], item['base_action'])
            siblings = self.action_families.get(fam_key, [self.current_anim_idx])
            batch_updates = []
            for s_idx in siblings:
                if s_idx == self.current_anim_idx:
                    continue
                s_item = self.animations[s_idx]
                s_existing_name = self.data_manager.get_info(s_item['key']).get('custom_name', '').strip()
                # 如果用户没有改动中文名且变体已有名字，严格保留变体原有中文名（保护双色定制命名），仅同步第一标签 cat 与第二标签 target_self
                if not name_changed and s_existing_name:
                    var_name = s_existing_name
                elif name:
                    var_name = derive_family_name(name, item['size'], item['color'], s_item['size'], s_item['color'])
                else:
                    var_name = s_existing_name
                batch_updates.append((s_item, var_name, cat, target_self))
            if batch_updates:
                self.data_manager.batch_update(batch_updates)
                
        self.data_manager.persist()
        self._refresh_tag_buttons_highlight(cat, target_self)
        
        # 更新树行
        has_name = bool(name)
        has_tag = bool(cat)
        if "禁用" in cat:
            status_icon = "🚫"
        elif has_tag:
            status_icon = "✅"
        elif has_name:
            status_icon = "🏷️"
        else:
            status_icon = "⚪"

        tag_display = f"【{cat}】" if cat else "未打标"
        target_display = "🛡️自身" if target_self else "⚔️敌方"
        fam_key = (item['pack'], item['base_action'])
        siblings = self.action_families.get(fam_key, [self.current_anim_idx])
        
        display_folder = f"{item['base_action']}" if self.hide_small_and_variants_var.get() else item['folder']
        spec_info = f"共{len(siblings)}变体 {item['frame_count']}F" if self.hide_small_and_variants_var.get() else f"{item['size']}_{item['color']} {item['frame_count']}F"
        
        target_iid = str(self.current_anim_idx)
        if not self.tree.exists(target_iid) and self.hide_small_and_variants_var.get():
            for s_idx in siblings:
                if self.tree.exists(str(s_idx)):
                    target_iid = str(s_idx)
                    break
        if self.tree.exists(target_iid):
            self.tree.item(target_iid, values=(status_icon, tag_display, target_display, name, display_folder, spec_info))
            
        self._update_stats_label()

    def save_and_next(self):
        """核心极速流水线：保存当前并自动跳入下一个动作"""
        self.save_current_only()
        self.go_next_anim()

    def go_prev_anim(self):
        if not self.display_anim_indices:
            return
        try:
            curr_pos = self.display_anim_indices.index(self.current_anim_idx)
            prev_pos = (curr_pos - 1) % len(self.display_anim_indices)
            self.select_animation_by_index(self.display_anim_indices[prev_pos])
        except ValueError:
            self.select_animation_by_index(self.display_anim_indices[0])

    def go_next_anim(self):
        if not self.display_anim_indices:
            return
        try:
            curr_pos = self.display_anim_indices.index(self.current_anim_idx)
            next_pos = (curr_pos + 1) % len(self.display_anim_indices)
            self.select_animation_by_index(self.display_anim_indices[next_pos])
        except ValueError:
            self.select_animation_by_index(self.display_anim_indices[0])

    def _update_stats_label(self):
        total_actions = len(self.action_family_keys)
        tagged_actions_count = 0
        self_target_count = 0
        tag_counts = {t[0]: 0 for t in SIX_TAGS}

        for fam_key in self.action_family_keys:
            fam_indices = self.action_families[fam_key]
            fam_cat = ""
            fam_self = False
            for i in fam_indices:
                info = self.data_manager.get_info(self.animations[i]['key'])
                c = info.get('category', '').strip()
                if c and not fam_cat:
                    fam_cat = c
                if info.get('target_self', False):
                    fam_self = True
            if fam_self:
                self_target_count += 1
            if fam_cat:
                tagged_actions_count += 1
                for tn in tag_counts:
                    if tn in fam_cat:
                        tag_counts[tn] += 1

        tag_pct = (tagged_actions_count / total_actions * 100) if total_actions > 0 else 0
        breakdown = " | ".join(f"{k}:{v}" for k, v in tag_counts.items())
        self.stats_lbl.config(
            text=f"🏷️ 第一标签: {tagged_actions_count}/{total_actions} ({tag_pct:.0f}%) [{breakdown}]  |  🛡️ 第二标签(针对自身): {self_target_count} 个"
        )

    def open_output_folder(self):
        os.startfile(self.workspace_dir)

    def export_csv_prompt(self):
        self.data_manager.persist()
        messagebox.showinfo("导出成功", f"命名与双标签数据（第一标签:流派定性 + 第二标签:是否针对自身）已成功导出！\n\n• JSON配置: {self.data_manager.json_path}\n• Excel表格: {self.data_manager.csv_path}\n• 极简映射: {self.data_manager.quick_map_path}")


def main():
    root = tk.Tk()
    app = PixelEffectViewerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
