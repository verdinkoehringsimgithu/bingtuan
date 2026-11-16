import os, sys, glob, shutil, zipfile, io, json
from PIL import Image
from collections import deque

def make_transparent(im_rgba, tolerance=20):
    w, h = im_rgba.size
    pixels = im_rgba.load()
    
    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    corner_colors = [pixels[pt] for pt in corners]
    bg_color = max(set(corner_colors), key=corner_colors.count)
    bg_r, bg_g, bg_b = bg_color[:3]
    
    def is_bg(r, g, b, a):
        if a < 200:
            return True
        return (abs(r - bg_r) <= tolerance and 
                abs(g - bg_g) <= tolerance and 
                abs(b - bg_b) <= tolerance)

    visited = bytearray(w * h)
    queue = deque()
    
    for x in range(w):
        for y in (0, h - 1):
            idx = y * w + x
            if not visited[idx] and is_bg(*pixels[x, y]):
                visited[idx] = 1
                queue.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            idx = y * w + x
            if not visited[idx] and is_bg(*pixels[x, y]):
                visited[idx] = 1
                queue.append((x, y))
                
    cw = max(1, w // 4)
    ch = max(1, h // 4)
    for r in range(4):
        for c in range(4):
            cx = c * cw
            cy = r * ch
            for x in range(cx, min(w, cx + cw)):
                for y in (cy, min(h - 1, cy + ch - 1)):
                    idx = y * w + x
                    if not visited[idx] and is_bg(*pixels[x, y]):
                        visited[idx] = 1
                        queue.append((x, y))
            for y in range(cy, min(h, cy + ch)):
                for x in (cx, min(w - 1, cx + cw)):
                    idx = y * w + x
                    if not visited[idx] and is_bg(*pixels[x, y]):
                        visited[idx] = 1
                        queue.append((x, y))
                        
    while queue:
        x, y = queue.popleft()
        pixels[x, y] = (0, 0, 0, 0)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h:
                nidx = ny * w + nx
                if not visited[nidx]:
                    if is_bg(*pixels[nx, ny]):
                        visited[nidx] = 1
                        queue.append((nx, ny))
                        
    return im_rgba

def fix_issue_1_and_categories():
    print("=== Step 1: 修复分类 1~6 中原始素材的左右晃动（还原原始水平绝对中心） ===")
    chara_dir = r"D:\123\CHARA"
    backup_dir = r"D:\123\CHARA_BACKUP"
    
    backup_files_map = {}
    for root, dirs, files in os.walk(backup_dir):
        for f in files:
            if f.endswith('.png'):
                backup_files_map[f] = os.path.join(root, f)
                
    fixed_count = 0
    categories = ['1', '2', '3', '4', '5', '6', 'SP', '不合格']
    
    for cat in categories:
        cat_dir = os.path.join(chara_dir, cat)
        if not os.path.exists(cat_dir):
            continue
        for f in os.listdir(cat_dir):
            if not f.endswith('.png'):
                continue
            if f in backup_files_map:
                src_path = backup_files_map[f]
                dst_path = os.path.join(cat_dir, f)
                
                # 特殊跳过 908，后续由专门函数高精度对齐
                if '908' in f:
                    continue
                    
                im = Image.open(src_path).convert('RGBA')
                w, h = im.size
                
                # 处理透明背景
                alpha_ext = im.getextrema()[3]
                if alpha_ext[0] == 255:
                    im = make_transparent(im)
                elif alpha_ext[0] > 0:
                    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
                    if any(im.getpixel(pt)[3] == 255 for pt in corners):
                        im = make_transparent(im)
                        
                # 处理尺寸规格：绝不破坏每帧内部的相对 X 坐标！
                if w == 128 and h == 192:
                    im.save(dst_path, 'PNG')
                elif w == 128 and h == 128:
                    # 4 行 32x32，脚底对齐到 y=47，X 坐标完全保持原始 0..32
                    out = Image.new('RGBA', (128, 192), (0, 0, 0, 0))
                    for r in range(4):
                        row_crop = im.crop((0, r * 32, 128, (r + 1) * 32))
                        out.paste(row_crop, (0, r * 48 + 16), row_crop)
                    out.save(dst_path, 'PNG')
                elif 128 <= w <= 132 and 191 <= h <= 194:
                    # 裁剪微小白边至 128x192，不移动内部像素
                    out = Image.new('RGBA', (128, 192), (0, 0, 0, 0))
                    crop_w = min(128, w)
                    crop_h = min(192, h)
                    crop = im.crop((0, 0, crop_w, crop_h))
                    out.paste(crop, (0, 0), crop)
                    out.save(dst_path, 'PNG')
                else:
                    # 按原图尺寸保留（用户指令6：有些不是3帧的就按原来的）
                    im.save(dst_path, 'PNG')
                    
                fixed_count += 1
                
    print(f"已修复 {fixed_count} 个原始分类角色的水平晃动问题。")

def fix_issue_2_and_unpacked():
    print("\n=== Step 2: 修复解包角色左右晃动及 2 帧闪烁问题（Actor/gal 及 split_char） ===")
    chara_dir = r"D:\123\CHARA"
    raw_packs_dir = r"D:\123\CHARA_NEW_RAW_PACKS"
    
    # 2.1 修复 split_char (32 个角色)
    # 原始为 96x128 (3 列 32x32, 4 行 32x32)，直接映射为 4 帧 (0, 1, 2, 1)，X 绝对保持 0..32！
    sprite_split_dir = os.path.join(raw_packs_dir, "sprite_split")
    if os.path.exists(sprite_split_dir):
        for i in range(1, 33):
            p32 = os.path.join(sprite_split_dir, f"character_{i}", f"character_{i}_frame32x32.png")
            if os.path.exists(p32):
                im = Image.open(p32).convert('RGBA')
                out = Image.new('RGBA', (128, 192), (0, 0, 0, 0))
                for row in range(4):
                    frames_3 = [im.crop((c * 32, row * 32, (c + 1) * 32, (row + 1) * 32)) for c in range(3)]
                    frames_4 = [frames_3[0], frames_3[1], frames_3[2], frames_3[1]]
                    for col in range(4):
                        out.paste(frames_4[col], (col * 32, row * 48 + 16), frames_4[col])
                        
                # 寻找当前所在分类目录或根目录
                f_name = f"mini_split_char_{i:02d}.png"
                found_path = None
                for root, dirs, files in os.walk(chara_dir):
                    if f_name in files:
                        found_path = os.path.join(root, f_name)
                        break
                if found_path:
                    out.save(found_path, 'PNG')
                else:
                    out.save(os.path.join(chara_dir, f_name), 'PNG')
        print("已更新 32 个 mini_split_char 角色：绝对 0 晃动。")

    # 2.2 修复 Actor1..3, Evil1, People1..3, AnthroDinos 等多角色大图
    sheets_info = [
        ("Actor1.png", 4, 2, "Actor1"),
        ("Actor1_SD.png", 4, 2, "Actor1_SD"),
        ("Actor1{ISO}.png", 4, 2, "Actor1_ISO"),
        ("Actor2.png", 4, 2, "Actor2"),
        ("Actor3.png", 4, 2, "Actor3"),
        ("AnthroDinos.png", 4, 2, "AnthroDinos"),
        ("Evil1.png", 4, 2, "Evil1"),
        ("Evil1_SD.png", 4, 2, "Evil1_SD"),
        ("Evil1{ISO}.png", 4, 2, "Evil1_ISO"),
        ("NPC Characters-1 (1).png", 4, 4, "NPC_Chars"),
        ("People1.png", 4, 2, "People1"),
        ("People3.png", 4, 2, "People3"),
        ("People3_SD.png", 4, 2, "People3_SD"),
    ]
    
    for fname, char_cols, char_rows, prefix in sheets_info:
        raw_p = os.path.join(raw_packs_dir, fname)
        if not os.path.exists(raw_p):
            continue
        im = Image.open(raw_p).convert('RGBA')
        w, h = im.size
        char_w = w // char_cols
        char_h = h // char_rows
        cell_w = char_w // 3
        cell_h = char_h // 4
        
        for idx in range(char_cols * char_rows):
            cx = (idx % char_cols) * char_w
            cy = (idx // char_cols) * char_h
            char_crop = im.crop((cx, cy, cx + char_w, cy + char_h))
            if not char_crop.split()[3].getbbox():
                continue
                
            out = Image.new('RGBA', (128, 192), (0, 0, 0, 0))
            scale = min(32.0 / cell_w, 48.0 / cell_h)
            if scale > 1.0: scale = 1.0
            
            for row in range(4):
                f0 = char_crop.crop((0 * cell_w, row * cell_h, 1 * cell_w, (row + 1) * cell_h))
                f1 = char_crop.crop((1 * cell_w, row * cell_h, 2 * cell_w, (row + 1) * cell_h))
                f2 = char_crop.crop((2 * cell_w, row * cell_h, 3 * cell_w, (row + 1) * cell_h))
                
                b0 = f0.split()[3].getbbox()
                b1 = f1.split()[3].getbbox()
                b2 = f2.split()[3].getbbox()
                
                # 修复 2 帧闪烁的关键逻辑：如果只有中间站立帧 (Col 1)，4 帧全部复用站立姿态！
                if b1 and not b0 and not b2:
                    frames_4 = [f1, f1, f1, f1]
                elif b0 and b1 and not b2:
                    frames_4 = [f0, f1, f0, f1]
                elif not b0 and not b1 and not b2:
                    continue
                else:
                    frames_4 = [f0, f1, f2 if b2 else f0, f1]
                    
                for col in range(4):
                    cf = frames_4[col]
                    if scale < 0.999:
                        nw = max(1, int(round(cf.width * scale)))
                        nh = max(1, int(round(cf.height * scale)))
                        cf = cf.resize((nw, nh), Image.Resampling.NEAREST)
                        
                    # 水平对齐：基于 cell 槽位绝对居中，不按单帧 bbox 动态偏移，杜绝左右摇晃！
                    dst_x = (32 - cf.width) // 2
                    dst_y = 48 - cf.height
                    out.paste(cf, (col * 32 + dst_x, row * 48 + dst_y), cf)
                    
            f_name = f"{prefix}_{idx+1}.png"
            found_path = None
            for root, dirs, files in os.walk(chara_dir):
                if f_name in files:
                    found_path = os.path.join(root, f_name)
                    break
            if found_path:
                out.save(found_path, 'PNG')
            else:
                out.save(os.path.join(chara_dir, f_name), 'PNG')
    print("已重新生成 Actor/Evil/People 系列角色：彻底消除 2 帧闪烁与左右晃动。")

def fix_issue_3_neuro():
    print("\n=== Step 3: 提取并高精度组装 Neuro 系列 4 方向行走图 ===")
    zip_path = r"C:\Users\Administrator\Downloads\neuro_rpg.zip"
    chara_dir = r"D:\123\CHARA"
    
    neuro_files = [
        ("neuro_rpg_sheet.png", "mini_neuro_rpg_sheet.png"),
        ("neuro_pirate_rpg_sheet.png", "mini_neuro_pirate_rpg_sheet.png"),
        ("evil_rpg_sheet.png", "mini_evil_rpg_sheet.png"),
        ("evil_pirate_rpg_sheet.png", "mini_evil_pirate_rpg_sheet.png")
    ]
    
    # 5x5 网格中对应的 4 个正向行走帧编号:
    # Row 0 (Down/Front): 0, 1, 2, 1
    # Row 1 (Left): 18, 19, 20, 19
    # Row 2 (Right): 6, 7, 8, 7
    # Row 3 (Up/Back): 12, 13, 14, 13
    directions_map = [
        [0, 1, 2, 1],
        [18, 19, 20, 19],
        [6, 7, 8, 7],
        [12, 13, 14, 13]
    ]
    
    with zipfile.ZipFile(zip_path) as z:
        for src_name, out_name in neuro_files:
            data = z.read(src_name)
            sheet = Image.open(io.BytesIO(data)).convert('RGBA')
            
            # 组装为 128x192
            out = Image.new('RGBA', (128, 192), (0, 0, 0, 0))
            
            for row_idx, frame_indices in enumerate(directions_map):
                for col_idx, f_idx in enumerate(frame_indices):
                    scol = f_idx % 5
                    srow = f_idx // 5
                    cell = sheet.crop((scol * 32, srow * 32, (scol + 1) * 32, (srow + 1) * 32))
                    
                    # 放入 32x48 槽位，x=0..32 绝对不变，脚底对齐底部 (y=16..48)
                    out.paste(cell, (col_idx * 32, row_idx * 48 + 16), cell)
                    
            # 移除不合格文件夹中的旧残损文件，放入 CHARA 根目录待重新审核
            bad_path = os.path.join(chara_dir, "不合格", out_name)
            if os.path.exists(bad_path):
                os.remove(bad_path)
            target_path = os.path.join(chara_dir, out_name)
            out.save(target_path, 'PNG')
            print(f"已生成高精度 Neuro 行走图: {out_name}")

def fix_issue_4_three_kingdoms():
    print("\n=== Step 4: 修复三国题材行走图 RTP风格行走图 (908).png ===")
    backup_path = r"D:\123\CHARA_BACKUP\不合格\RTP风格行走图 (908).png"
    chara_dir = r"D:\123\CHARA"
    
    if not os.path.exists(backup_path):
        print("未找到 908 原始备份文件！")
        return
        
    im = Image.open(backup_path).convert('RGBA')
    w, h = im.size
    
    # 1. 白色底色转透明
    pixels = im.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if r > 240 and g > 240 and b > 240:
                pixels[x, y] = (0, 0, 0, 0)
                
    # 2. 真实动作行范围 (消除 19px 顶部空白，按真实边界抽取):
    # Row 0: Down (19..76) h=57
    # Row 1: Left (83..163) h=80
    # Row 2: Right (166..248) h=82
    # Row 3: Up (256..329) h=73
    true_rows = [(19, 76), (83, 163), (166, 248), (256, 329)]
    # 每行 4 列，列宽 91
    col_w = 91
    cell_h = 84
    
    out = Image.new('RGBA', (col_w * 4, cell_h * 4), (0, 0, 0, 0)) # 364 x 336
    
    for r_idx, (y1, y2) in enumerate(true_rows):
        row_h = y2 - y1
        for c_idx in range(4):
            x1 = c_idx * col_w
            x2 = min(w, x1 + col_w)
            cell = im.crop((x1, y1, x2, y2))
            
            # 脚底接地：底部对齐到 cell_h - 1
            dst_y = r_idx * cell_h + (cell_h - row_h)
            dst_x = c_idx * col_w
            out.paste(cell, (dst_x, dst_y), cell)
            
    # 从不合格目录移出并放入 CHARA 根目录待重新审核
    bad_p = os.path.join(chara_dir, "不合格", "RTP风格行走图 (908).png")
    if os.path.exists(bad_p):
        os.remove(bad_p)
        
    target_p = os.path.join(chara_dir, "RTP风格行走图 (908).png")
    out.save(target_p, 'PNG')
    print("已成功对齐并组装三国图: RTP风格行走图 (908).png (364x336, 完整4向4帧)")

def update_chara_tags():
    print("\n=== Step 5: 更新 chara_tags.json ===")
    tags_file = r"D:\123\CHARA\chara_tags.json"
    tags = {}
    if os.path.exists(tags_file):
        try:
            with open(tags_file, 'r', encoding='utf-8') as f:
                tags = json.load(f)
        except:
            tags = {}
            
    # 注册所有 mini_ 开头的文件为 迷你角色
    chara_dir = r"D:\123\CHARA"
    for root, dirs, files in os.walk(chara_dir):
        for f in files:
            if f.startswith("mini_") and f.endswith(".png"):
                tags[f] = "迷你角色"
                
    with open(tags_file, 'w', encoding='utf-8') as f:
        json.dump(tags, f, ensure_ascii=False, indent=2)
    print(f"已更新 chara_tags.json，共标记 {len(tags)} 个迷你角色。")

if __name__ == "__main__":
    fix_issue_1_and_categories()
    fix_issue_2_and_unpacked()
    fix_issue_3_neuro()
    fix_issue_4_three_kingdoms()
    update_chara_tags()
    print("\n所有 4 项问题的图像重构均已全部成功执行！")
