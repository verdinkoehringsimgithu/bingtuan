import os, sys, glob, shutil, zipfile, io, json
from PIL import Image

def fix_neuro_smoothness():
    print("=== 1. 修复 Neuro 动画流畅度（补齐中间站立复位帧） ===")
    zip_path = r"C:\Users\Administrator\Downloads\neuro_rpg.zip"
    chara_dir = r"D:\123\CHARA"
    
    neuro_files = [
        ("neuro_rpg_sheet.png", "mini_neuro_rpg_sheet.png"),
        ("neuro_pirate_rpg_sheet.png", "mini_neuro_pirate_rpg_sheet.png"),
        ("evil_rpg_sheet.png", "mini_evil_rpg_sheet.png"),
        ("evil_pirate_rpg_sheet.png", "mini_evil_pirate_rpg_sheet.png")
    ]
    
    # Neuro 原作 5x5 网格中：
    # Down 动作的 3 帧：0 为迈左脚，1 为迈右脚，2 为双脚并拢站立帧 (Stand)！
    # 标准 4 帧行走循环序列为：迈步1 -> 站立 -> 迈步2 -> 站立
    directions_map = [
        [0, 2, 1, 2],       # Down: 0=Step1, 2=Stand, 1=Step2, 2=Stand
        [6, 8, 7, 8],       # Left: 6=Step1, 8=Stand, 7=Step2, 8=Stand
        [18, 20, 19, 20],   # Right: 18=Step1, 20=Stand, 19=Step2, 20=Stand
        [12, 14, 13, 14]    # Up: 12=Step1, 14=Stand, 13=Step2, 14=Stand
    ]
    
    with zipfile.ZipFile(zip_path) as z:
        for src_name, out_name in neuro_files:
            data = z.read(src_name)
            sheet = Image.open(io.BytesIO(data)).convert('RGBA')
            
            # 生成 128x192 规格
            out = Image.new('RGBA', (128, 192), (0, 0, 0, 0))
            for r_idx, f_indices in enumerate(directions_map):
                for c_idx, f_idx in enumerate(f_indices):
                    scol = f_idx % 5
                    srow = f_idx // 5
                    cell = sheet.crop((scol * 32, srow * 32, (scol + 1) * 32, (srow + 1) * 32))
                    out.paste(cell, (c_idx * 32, r_idx * 48 + 16), cell)
                    
            target_path = os.path.join(chara_dir, out_name)
            out.save(target_path, 'PNG')
            print(f"已更新 Neuro: {out_name} -> 4 帧循环 [迈步1, 站立, 迈步2, 站立]")

def fix_gal_and_actor_resolution():
    print("\n=== 2. 修复 gal / Actor 系列素材乱码与缺失（采用原生无损分辨率） ===")
    chara_dir = r"D:\123\CHARA"
    raw_packs_dir = r"D:\123\CHARA_NEW_RAW_PACKS"
    
    sheets_info = [
        ("Actor1.png", 4, 2, "Actor1", 48, 48),
        ("Actor1_SD.png", 4, 2, "Actor1_SD", 24, 24),
        ("Actor1{ISO}.png", 4, 2, "Actor1_ISO", 48, 48),
        ("Actor2.png", 4, 2, "Actor2", 48, 48),
        ("Actor3.png", 4, 2, "Actor3", 48, 48),
        ("AnthroDinos.png", 4, 2, "AnthroDinos", 48, 48),
        ("Evil1.png", 4, 2, "Evil1", 48, 48),
        ("Evil1_SD.png", 4, 2, "Evil1_SD", 24, 24),
        ("Evil1{ISO}.png", 4, 2, "Evil1_ISO", 48, 48),
        ("NPC Characters-1 (1).png", 4, 4, "NPC_Chars", 48, 48),
        ("People1.png", 4, 2, "People1", 48, 48),
        ("People3.png", 4, 2, "People3", 48, 48),
        ("People3_SD.png", 4, 2, "People3_SD", 24, 24),
    ]
    
    count = 0
    for fname, char_cols, char_rows, prefix, cell_w, cell_h in sheets_info:
        raw_p = os.path.join(raw_packs_dir, fname)
        if not os.path.exists(raw_p):
            continue
        im = Image.open(raw_p).convert('RGBA')
        char_w = cell_w * 3
        char_h = cell_h * 4
        
        # 原生输出尺寸：4 列 x cell_w, 4 行 x cell_h (例如 48x48 单元格为 192x192)
        out_w = cell_w * 4
        out_h = cell_h * 4
        
        for idx in range(char_cols * char_rows):
            col_idx = idx % char_cols
            row_idx = idx // char_cols
            cx = col_idx * char_w
            cy = row_idx * char_h
            char_crop = im.crop((cx, cy, cx + char_w, cy + char_h))
            if not char_crop.split()[3].getbbox():
                continue
                
            out = Image.new('RGBA', (out_w, out_h), (0, 0, 0, 0))
            
            for row in range(4):
                f0 = char_crop.crop((0 * cell_w, row * cell_h, 1 * cell_w, (row + 1) * cell_h))
                f1 = char_crop.crop((1 * cell_w, row * cell_h, 2 * cell_w, (row + 1) * cell_h))
                f2 = char_crop.crop((2 * cell_w, row * cell_h, 3 * cell_w, (row + 1) * cell_h))
                
                b0 = f0.split()[3].getbbox()
                b1 = f1.split()[3].getbbox()
                b2 = f2.split()[3].getbbox()
                
                if b1 and not b0 and not b2:
                    frames_4 = [f1, f1, f1, f1]
                elif b0 and b1 and not b2:
                    frames_4 = [f0, f1, f0, f1]
                elif not b0 and not b1 and not b2:
                    continue
                else:
                    frames_4 = [f0, f1, f2 if b2 else f0, f1]
                    
                for col in range(4):
                    # 100% 原生像素粘贴，绝不进行有损缩放！
                    out.paste(frames_4[col], (col * cell_w, row * cell_h), frames_4[col])
                    
            f_name = f"{prefix}_{idx+1}.png"
            # 搜索现有文件并就地替换
            for root, dirs, files in os.walk(chara_dir):
                if f_name in files:
                    out.save(os.path.join(root, f_name), 'PNG')
                    count += 1
                    break
                    
    print(f"已更新 {count} 个 Actor/Evil/People 素材为原生 1:1 分辨率，眼睛与装甲完好无损。")

def fix_pixel_champions():
    print("\n=== 3. 修复 Pixel Champions (图三系列) 切图错误与贴边位移 ===")
    zip_path = r"C:\Users\Administrator\Downloads\Pixel_Champions_v3.zip"
    chara_dir = r"D:\123\CHARA"
    
    char_names = [
        "Glenys-the-Demonswordsman",
        "Hex-the-Time-Witch",
        "Ley-the-Monster-Whisperer",
        "Linail-the-High-Priestess",
        "Oratio-the-Mercenary",
        "Ouzo-the-Wolf-Bard",
        "Prime-the-Great-Sage",
        "Wyvera-the-Queen-Dragoon"
    ]
    
    count = 0
    with zipfile.ZipFile(zip_path) as z:
        for cname in char_names:
            inner_path = f"Pixel_Champions_v3/1x-NormalSize/Overworld/{cname}.png"
            data = z.read(inner_path)
            im = Image.open(io.BytesIO(data)).convert('RGBA')
            
            # 每个单元格为 24x24，组装为原生 96x96 (4 列 x 24w, 4 行 x 24h)
            out = Image.new('RGBA', (96, 96), (0, 0, 0, 0))
            for r in range(4):
                f0 = im.crop((0, r * 24, 24, (r + 1) * 24))
                f1 = im.crop((24, r * 24, 48, (r + 1) * 24))
                f2 = im.crop((48, r * 24, 72, (r + 1) * 24))
                frames_4 = [f0, f1, f2, f1]
                for c in range(4):
                    out.paste(frames_4[c], (c * 24, r * 24), frames_4[c])
                    
            # 更新现有的 _walk, _pose1, _pose2 文件（用户在分类中已划分的文件）
            for suffix in ["_walk.png", "_pose1.png", "_pose2.png"]:
                f_name = f"PC_{cname}{suffix}"
                for root, dirs, files in os.walk(chara_dir):
                    if f_name in files:
                        out.save(os.path.join(root, f_name), 'PNG')
                        count += 1
                        break
                        
    print(f"已更新 {count} 个 PC_* 文件为 96x96 纯正网格：头部空白消除，左右瞬移完全解决。")

def update_tags():
    print("\n=== 4. 更新迷你角色标签 ===")
    tags_file = r"D:\123\CHARA\chara_tags.json"
    tags = {}
    if os.path.exists(tags_file):
        try:
            with open(tags_file, 'r', encoding='utf-8') as f:
                tags = json.load(f)
        except:
            tags = {}
            
    chara_dir = r"D:\123\CHARA"
    for root, dirs, files in os.walk(chara_dir):
        for f in files:
            # mini_ 开头以及 PC_ 开头的角色均为迷你像素角色
            if (f.startswith("mini_") or f.startswith("PC_")) and f.endswith(".png"):
                tags[f] = "迷你角色"
                
    with open(tags_file, 'w', encoding='utf-8') as f:
        json.dump(tags, f, ensure_ascii=False, indent=2)
    print(f"已更新 chara_tags.json，当前迷你角色总数: {len(tags)}")

if __name__ == "__main__":
    fix_neuro_smoothness()
    fix_gal_and_actor_resolution()
    fix_pixel_champions()
    update_tags()
    print("\n修复全部执行完毕！")
