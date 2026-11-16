import os, glob
from PIL import Image
from collections import deque

def remove_background_floodfill(im_rgba, tolerance=15):
    """
    Flood-fill from image perimeter to turn background transparent.
    """
    w, h = im_rgba.size
    pixels = im_rgba.load()
    
    # Check corners to get bg color
    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    corner_colors = [pixels[pt] for pt in corners]
    
    # Choose most common corner color as bg color
    bg_color = max(set(corner_colors), key=corner_colors.count)
    bg_r, bg_g, bg_b = bg_color[:3]
    
    def color_match(r, g, b):
        return (abs(r - bg_r) <= tolerance and 
                abs(g - bg_g) <= tolerance and 
                abs(b - bg_b) <= tolerance)

    visited = bytearray(w * h)
    queue = deque()
    
    # Initialize queue with border pixels matching bg_color
    for x in range(w):
        for y in [0, h - 1]:
            idx = y * w + x
            r, g, b, a = pixels[x, y]
            if not visited[idx] and color_match(r, g, b):
                visited[idx] = 1
                queue.append((x, y))
    for y in range(h):
        for x in [0, w - 1]:
            idx = y * w + x
            r, g, b, a = pixels[x, y]
            if not visited[idx] and color_match(r, g, b):
                visited[idx] = 1
                queue.append((x, y))
                
    # Also check cell perimeter for 4x4 grid (to catch regions between legs/arms that touch cell borders)
    cell_w = w // 4
    cell_h = h // 4
    for row in range(4):
        for col in range(4):
            cx = col * cell_w
            cy = row * cell_h
            for x in range(cx, min(w, cx + cell_w)):
                for y in [cy, min(h - 1, cy + cell_h - 1)]:
                    idx = y * w + x
                    r, g, b, a = pixels[x, y]
                    if not visited[idx] and color_match(r, g, b):
                        visited[idx] = 1
                        queue.append((x, y))
            for y in range(cy, min(h, cy + cell_h)):
                for x in [cx, min(w - 1, cx + cell_w - 1)]:
                    idx = y * w + x
                    r, g, b, a = pixels[x, y]
                    if not visited[idx] and color_match(r, g, b):
                        visited[idx] = 1
                        queue.append((x, y))
                        
    while queue:
        x, y = queue.popleft()
        pixels[x, y] = (0, 0, 0, 0)
        
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h:
                nidx = ny * w + nx
                if not visited[nidx]:
                    r, g, b, a = pixels[nx, ny]
                    if color_match(r, g, b):
                        visited[nidx] = 1
                        queue.append((nx, ny))
                        
    return im_rgba

# Test on 210
f = glob.glob(r"D:\123\CHARA\1\210-*.png")[0]
im = Image.open(f).convert("RGBA")
print("Original 210 alpha extrema:", im.getextrema()[3])

im_trans = remove_background_floodfill(im)
print("After floodfill alpha extrema:", im_trans.getextrema()[3])

# Check how many transparent pixels
alphas = [p[3] for p in im_trans.getdata()]
transparent_count = sum(1 for a in alphas if a == 0)
opaque_count = sum(1 for a in alphas if a > 0)
print(f"Transparent pixels: {transparent_count}, Opaque character pixels: {opaque_count}")
