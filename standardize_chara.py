import os, shutil, glob, time
from PIL import Image
from collections import deque

def make_transparent(im_rgba, tolerance=18):
    """
    Remove solid background by perimeter-seeded floodfill.
    Preserves white/light pixels inside the character body.
    """
    w, h = im_rgba.size
    pixels = im_rgba.load()
    
    # Check 4 corners to determine background color
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
    
    # 1. Seed image outer borders
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
                
    # 2. Seed 4x4 cell borders to catch areas between arms and legs that touch cell grid
    cw = w // 4
    ch = h // 4
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
                for x in (cx, min(w - 1, cx + cell_w if 'cell_w' in dir() else cx + cw)):
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

def standardize_spritesheet(input_path, output_path=None, target_frame_w=32, target_frame_h=48):
    """
    Standardizes any 4-directional 4-frame walk sheet to exactly 128x192:
    - Removes solid background to transparent alpha
    - Crops each frame cleanly
    - Centers character horizontally (x=16)
    - Grounds character feet on bottom baseline (y=47)
    - Scales down oversized characters proportionally so head/feet are never cut off
    Returns (out_image, was_opaque, was_non_standard, was_floating, was_rescaled)
    """
    im = Image.open(input_path)
    im_rgba = im.convert('RGBA')
    w, h = im_rgba.size
    
    was_non_standard = (w != 128 or h != 192)
    was_opaque = False
    
    # 1. Background removal
    alpha_extrema = im_rgba.getextrema()[3]
    if alpha_extrema[0] == 255:
        im_rgba = make_transparent(im_rgba)
        was_opaque = True
    elif alpha_extrema[0] > 0:
        corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
        if any(im_rgba.getpixel(pt)[3] == 255 for pt in corners):
            im_rgba = make_transparent(im_rgba)
            was_opaque = True

    # 2. Determine raw cell grid (4 columns, 4 rows)
    cw = max(1, w // 4)
    ch = max(1, h // 4)
    
    # Target sheet size: 128 x 192 (4 cols * 32, 4 rows * 48)
    out_img = Image.new('RGBA', (target_frame_w * 4, target_frame_h * 4), (0, 0, 0, 0))
    
    was_floating = False
    was_rescaled = False
    
    # For each row (direction: 0=Down/正面, 1=Left, 2=Right, 3=Up)
    for row in range(4):
        frames = []
        bboxes = []
        for col in range(4):
            rx = col * cw
            ry = row * ch
            cell = im_rgba.crop((rx, ry, rx + cw, ry + ch))
            alpha = cell.split()[3]
            bbox = alpha.getbbox()
            frames.append(cell)
            bboxes.append(bbox)
            
        valid_bboxes = [b for b in bboxes if b is not None]
        if not valid_bboxes:
            continue
            
        max_char_h = max(b[3] - b[1] for b in valid_bboxes)
        max_char_w = max(b[2] - b[0] for b in valid_bboxes)
        max_foot_y = max(b[3] for b in valid_bboxes)
        
        # Check floating
        if ch - max_foot_y >= 3:
            was_floating = True
            
        # Check scaling needed (allow 1px margin around 32x48 cell: 30x46 max)
        scale = 1.0
        if max_char_h > (target_frame_h - 2) or max_char_w > (target_frame_w - 2):
            scale_h = (target_frame_h - 2) / float(max_char_h)
            scale_w = (target_frame_w - 2) / float(max_char_w)
            scale = min(scale_h, scale_w)
            was_rescaled = True
            
        # Determine common horizontal anchor across the 4 walk frames
        centers_x = [(b[0] + b[2]) / 2.0 for b in valid_bboxes]
        mean_center_x = sum(centers_x) / len(centers_x)

        # Process each frame in the direction
        for col in range(4):
            bbox = bboxes[col]
            if bbox is None:
                continue
                
            cell = frames[col]
            char_crop = cell.crop(bbox)
            
            if scale < 0.999:
                new_w = max(1, int(round(char_crop.width * scale)))
                new_h = max(1, int(round(char_crop.height * scale)))
                char_crop = char_crop.resize((new_w, new_h), Image.Resampling.NEAREST)
                
            # Alignment:
            # Ground baseline: feet touch target_frame_h - 1 (y = 47)
            # Maintain relative foot stepping height across walk cycle:
            foot_offset = int(round((max_foot_y - bbox[3]) * scale))
            dst_y = (target_frame_h - 1) - char_crop.height - foot_offset
            if dst_y < 0: dst_y = 0
            if dst_y + char_crop.height > target_frame_h:
                dst_y = target_frame_h - char_crop.height
                
            # Horizontal centering:
            # Maintain relative foot stepping lateral shift across walk cycle:
            step_offset = int(round((((bbox[0] + bbox[2]) / 2.0) - mean_center_x) * scale))
            dst_x = (target_frame_w - char_crop.width) // 2 + step_offset
            if dst_x < 0: dst_x = 0
            if dst_x + char_crop.width > target_frame_w:
                dst_x = target_frame_w - char_crop.width
                
            out_x = col * target_frame_w + dst_x
            out_y = row * target_frame_h + dst_y
            out_img.paste(char_crop, (out_x, out_y), char_crop)
            
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        out_img.save(output_path, 'PNG')
        
    return out_img, was_opaque, was_non_standard, was_floating, was_rescaled

def run_batch_standardization(chara_dir=r"D:\123\CHARA", backup_dir=r"D:\123\CHARA_BACKUP"):
    t0 = time.time()
    
    # 1. Backup if not already backed up
    if not os.path.exists(backup_dir):
        print(f"正在创建原始图片完整备份: {backup_dir} ...")
        shutil.copytree(chara_dir, backup_dir)
        print("备份完成。")
    else:
        print(f"备份已存在: {backup_dir}")

    categories = ["1", "2", "3", "4", "5", "6", "SP"]
    
    total_count = 0
    opaque_fixed = 0
    dim_fixed = 0
    floating_fixed = 0
    rescaled_fixed = 0
    
    print("\n开始批量修复与标准化...")
    for cat in categories:
        cat_dir = os.path.join(chara_dir, cat)
        if not os.path.exists(cat_dir):
            continue
            
        files = glob.glob(os.path.join(cat_dir, "*.png"))
        print(f"处理分类 [{cat}]: 共 {len(files)} 张图片...")
        
        for f in files:
            total_count += 1
            try:
                out_img, was_opaque, was_dim, was_float, was_rescale = standardize_spritesheet(f, f)
                if was_opaque: opaque_fixed += 1
                if was_dim: dim_fixed += 1
                if was_float: floating_fixed += 1
                if was_rescale: rescaled_fixed += 1
            except Exception as e:
                print(f"  处理失败 {f}: {e}")
                
    elapsed = time.time() - t0
    print("\n=== 修复标准化处理报告 ===")
    print(f"处理完成总文件数: {total_count} 张")
    print(f"背景透明化修复:   {opaque_fixed} 张 (实心底转透明底)")
    print(f"规格标准化修复:   {dim_fixed} 张 (统一为 128*192 规格)")
    print(f"浮空接地重定线:   {floating_fixed} 张 (脚底贴合 y=47 物理基线)")
    print(f"尺寸防裁切调整:   {rescaled_fixed} 张 (过大角色自适应居中微缩放)")
    print(f"总耗时:           {elapsed:.2f} 秒")
    print(f"原始备份位置:     {backup_dir}")

if __name__ == "__main__":
    run_batch_standardization()
