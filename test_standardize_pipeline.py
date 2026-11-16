import os, sys
from PIL import Image
from collections import deque

def make_transparent(im_rgba, tolerance=18):
    """
    Remove solid background by perimeter-seeded floodfill.
    """
    w, h = im_rgba.size
    pixels = im_rgba.load()
    
    # Check 4 corners
    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    corner_colors = [pixels[pt] for pt in corners]
    bg_color = max(set(corner_colors), key=corner_colors.count)
    bg_r, bg_g, bg_b = bg_color[:3]
    
    def is_bg(r, g, b, a):
        if a < 200: # already transparent
            return True
        return (abs(r - bg_r) <= tolerance and 
                abs(g - bg_g) <= tolerance and 
                abs(b - bg_b) <= tolerance)

    visited = bytearray(w * h)
    queue = deque()
    
    # Seed image outer border
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
                
    # Also seed 4x4 cell borders
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
                for x in (cx, min(w - 1, cx + cw - 1)):
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
    - Removes background to transparent alpha
    - Crops each frame cleanly
    - Centers character horizontally (x=16)
    - Grounds character feet on bottom baseline (y=47)
    - Scales down large characters proportionally if they exceed 32x48 cell
    """
    im = Image.open(input_path)
    im_rgba = im.convert('RGBA')
    w, h = im_rgba.size
    
    # 1. Background removal if opaque or partially opaque
    alpha_extrema = im_rgba.getextrema()[3]
    if alpha_extrema[0] == 255:
        im_rgba = make_transparent(im_rgba)
    elif alpha_extrema[0] > 0: # some transparency but corners opaque
        corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
        if any(im_rgba.getpixel(pt)[3] == 255 for pt in corners):
            im_rgba = make_transparent(im_rgba)

    # 2. Determine cell grid (usually 4x4)
    # Check if width is roughly divisible by 4, height by 4
    cw = w // 4
    ch = h // 4
    
    # Target sheet size: 128 x 192 (4 cols * 32, 4 rows * 48)
    out_img = Image.new('RGBA', (target_frame_w * 4, target_frame_h * 4), (0, 0, 0, 0))
    
    # For each row (direction: 0=Down, 1=Left, 2=Right, 3=Up)
    for row in range(4):
        frames = []
        bboxes = []
        for col in range(4):
            # Crop raw cell
            rx = col * cw
            ry = row * ch
            cell = im_rgba.crop((rx, ry, rx + cw, ry + ch))
            alpha = cell.split()[3]
            bbox = alpha.getbbox()
            frames.append(cell)
            bboxes.append(bbox)
            
        # Determine baseline and bounding info across the 4 frames of this direction
        valid_bboxes = [b for b in bboxes if b is not None]
        if not valid_bboxes:
            # Completely empty row
            continue
            
        # Max character height across the row
        char_heights = [b[3] - b[1] for b in valid_bboxes]
        max_char_h = max(char_heights)
        char_widths = [b[2] - b[0] for b in valid_bboxes]
        max_char_w = max(char_widths)
        
        # Bottom-most foot coordinate across the row
        max_foot_y = max(b[3] for b in valid_bboxes)
        
        # Check if scaling down is required (if character is too large for 32x48 cell)
        # Margin: 1px top/bottom/sides, so usable is 30x46
        scale = 1.0
        if max_char_h > (target_frame_h - 2) or max_char_w > (target_frame_w - 2):
            scale_h = (target_frame_h - 2) / max_char_h
            scale_w = (target_frame_w - 2) / max_char_w
            scale = min(scale_h, scale_w)
            
        # Determine common horizontal anchor (median center of mass)
        centers_x = [(b[0] + b[2]) / 2.0 for b in valid_bboxes]
        mean_center_x = sum(centers_x) / len(centers_x)

        # Process each frame in the direction
        for col in range(4):
            bbox = bboxes[col]
            if bbox is None:
                continue
                
            cell = frames[col]
            # Crop the character tightly
            char_crop = cell.crop(bbox)
            
            if scale < 0.999:
                new_w = max(1, int(round(char_crop.width * scale)))
                new_h = max(1, int(round(char_crop.height * scale)))
                char_crop = char_crop.resize((new_w, new_h), Image.Resampling.NEAREST)
                
            # Alignment into target 32x48 cell:
            # Ground baseline: foot should rest at target_frame_h - 1 (y = 47)
            # Maintain relative foot height across the 4 walk frames:
            # frame_foot_offset = max_foot_y - bbox[3]
            foot_offset = int(round((max_foot_y - bbox[3]) * scale))
            dst_y = (target_frame_h - 1) - char_crop.height - foot_offset
            if dst_y < 0: dst_y = 0
            if dst_y + char_crop.height > target_frame_h:
                dst_y = target_frame_h - char_crop.height
                
            # Horizontal centering:
            # Maintain relative foot step shift (bbox center vs mean center)
            step_offset = int(round((((bbox[0] + bbox[2]) / 2.0) - mean_center_x) * scale))
            dst_x = (target_frame_w - char_crop.width) // 2 + step_offset
            if dst_x < 0: dst_x = 0
            if dst_x + char_crop.width > target_frame_w:
                dst_x = target_frame_w - char_crop.width
                
            # Paste into target sheet
            out_x = col * target_frame_w + dst_x
            out_y = row * target_frame_h + dst_y
            out_img.paste(char_crop, (out_x, out_y), char_crop)
            
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        out_img.save(output_path, 'PNG')
    return out_img

# Test on 3 problem files
test_samples = [
    r"D:\123\CHARA\1\210-非洲人.png",
    r"D:\123\CHARA\1\RTP风格行走图 (1025).png",
    r"D:\123\CHARA\4\232-人妖铁匠.png"
]

out_test_dir = r"D:\123\test_standardized"
os.makedirs(out_test_dir, exist_ok=True)

for p in test_samples:
    name = os.path.basename(p)
    out_p = os.path.join(out_test_dir, name)
    res = standardize_spritesheet(p, out_p)
    print(f"Processed {name}: Output size={res.size}, Alpha extrema={res.getextrema()[3]}")
