import os, glob
from PIL import Image

chara_dir = r"D:\123\CHARA"
categories = ["1", "2", "3", "4", "5", "6"]

total_categorized = 0
opaque_files = []
non_standard_dims = []
alignment_issues = []

for cat in categories:
    cat_dir = os.path.join(chara_dir, cat)
    if not os.path.exists(cat_dir):
        continue
    files = glob.glob(os.path.join(cat_dir, "*.png"))
    total_categorized += len(files)
    
    for f in files:
        fname = os.path.basename(f)
        try:
            im = Image.open(f)
            w, h = im.size
            
            # 1. Dimension check
            if (w, h) != (128, 192):
                non_standard_dims.append((cat, fname, (w, h)))
                
            # 2. Transparency check
            im_rgba = im.convert('RGBA')
            extrema = im_rgba.getextrema()
            alpha_min, alpha_max = extrema[3]
            if alpha_min == 255:
                # Completely opaque
                corner = im_rgba.getpixel((0, 0))
                opaque_files.append((cat, fname, (w, h), corner))
            else:
                # 3. Check alignment / float / clipping for transparent images
                # Row 0: front-facing walk frames (4 cols)
                fw = w // 4
                fh = h // 4
                
                # Check frame 0 (or all 4 frames in row 0)
                frame_boxes = []
                for col in range(4):
                    cell = im_rgba.crop((col * fw, 0, (col + 1) * fw, fh))
                    # bbox of non-zero alpha
                    alpha_band = cell.split()[3]
                    bbox = alpha_band.getbbox() # (left, upper, right, lower)
                    if bbox:
                        frame_boxes.append(bbox)
                
                if frame_boxes:
                    # check if floating (large gap at bottom across all frames)
                    bottoms = [b[3] for b in frame_boxes]
                    max_bottom = max(bottoms)
                    gap_bottom = fh - max_bottom
                    
                    # check horizontal center
                    widths = [b[2] - b[0] for b in frame_boxes]
                    centers = [(b[0] + b[2]) / 2.0 for b in frame_boxes]
                    expected_center = fw / 2.0
                    max_center_dev = max(abs(c - expected_center) for c in centers)
                    
                    # check if touching borders (clipped)
                    clipped_top = any(b[1] == 0 for b in frame_boxes)
                    clipped_bottom = any(b[3] == fh for b in frame_boxes)
                    clipped_left = any(b[0] == 0 for b in frame_boxes)
                    clipped_right = any(b[2] == fw for b in frame_boxes)
                    
                    if gap_bottom >= 5 or max_center_dev >= 4 or clipped_top or clipped_bottom or clipped_left or clipped_right:
                        alignment_issues.append((cat, fname, (w, h), gap_bottom, max_center_dev, clipped_top, clipped_bottom, clipped_left or clipped_right))
        except Exception as e:
            print(f"Error {f}: {e}")

print(f"Total files in categories 1-6: {total_categorized}")
print(f"Non-standard dimensions: {len(non_standard_dims)}")
for item in non_standard_dims[:15]:
    print(f"  [{item[0]}] {item[1]}: size={item[2]}")

print(f"\nOpaque files (need background removal): {len(opaque_files)}")
for item in opaque_files[:15]:
    print(f"  [{item[0]}] {item[1]}: size={item[2]}, corner={item[3]}")

print(f"\nAlignment issues detected (floating/off-center/clipped): {len(alignment_issues)}")
for item in alignment_issues[:15]:
    print(f"  [{item[0]}] {item[1]}: size={item[2]}, bottom_gap={item[3]}px, center_dev={item[4]:.1f}px, clipped_top={item[5]}, clipped_bottom={item[6]}, clipped_sides={item[7]}")
