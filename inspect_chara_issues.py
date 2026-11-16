import os, glob
from PIL import Image

chara_dir = r"D:\123\CHARA"
files = glob.glob(os.path.join(chara_dir, "*.png"))
print(f"Total PNG files in CHARA root: {len(files)}")

# Also check subdirectories if any
sub_files = glob.glob(os.path.join(chara_dir, "*", "*.png"))
print(f"Total PNG files in CHARA subdirectories: {len(sub_files)}")

all_files = files + sub_files
dim_counts = {}
opaque_files = []
alpha_files = []

for f in all_files:
    try:
        im = Image.open(f)
        dim = im.size
        dim_counts[dim] = dim_counts.get(dim, 0) + 1
        
        im_rgba = im.convert('RGBA')
        extrema = im_rgba.getextrema()
        alpha_min, alpha_max = extrema[3]
        if alpha_min == 255:
            # Entire image is completely opaque
            opaque_files.append((f, im.size, im_rgba.getpixel((0,0))))
        else:
            alpha_files.append((f, im.size, alpha_min, alpha_max))
    except Exception as e:
        print(f"Error reading {f}: {e}")

print("\n--- Dimension counts (top 20) ---")
for dim, count in sorted(dim_counts.items(), key=lambda x: -x[1])[:20]:
    print(f"  {dim}: {count}")

print(f"\nTotal opaque files (need background removal): {len(opaque_files)}")
print(f"Total alpha files (already transparent): {len(alpha_files)}")

print("\nSample opaque files (first 15):")
for item in opaque_files[:15]:
    print(f"  {os.path.basename(item[0])}: size={item[1]}, corner_pixel={item[2]}")
