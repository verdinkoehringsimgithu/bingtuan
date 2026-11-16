import os, sys, glob, shutil, hashlib
from PIL import Image
from collections import deque

BASE_CHARA = r"D:\123\CHARA"
BASE_ASSETS = r"D:\123\LegionBattle\LegionBattle\Assets\Characters"
BASE_BACKUP = r"D:\123\CHARA_BACKUP"
BASE_RAW = r"D:\123\CHARA_NEW_RAW_PACKS"
BASE_SLICED = r"D:\123\CHARA_SLICED"

def generate_guid(filepath: str) -> str:
    rel = os.path.relpath(filepath, BASE_CHARA).replace('\\', '/').lower()
    return hashlib.md5(rel.encode('utf-8')).hexdigest()

def create_sprite_meta_content(png_path: str, cell_w: int, cell_h: int, pivot_y: float = 0.05, ppu: int = 100) -> str:
    guid = generate_guid(png_path)
    stem = os.path.splitext(os.path.basename(png_path))[0]
    
    with Image.open(png_path) as im:
        w, h = im.size
        
    cols = 4
    rows = 4
    dir_names = ["down", "left", "right", "up"]
    sprites_yaml = []
    
    for r in range(rows):
        unity_y = (rows - 1 - r) * cell_h
        dname = dir_names[r] if r < len(dir_names) else f"row{r}"
        
        for c in range(cols):
            unity_x = c * cell_w
            frame_name = f"{stem}_{dname}_{c}"
            frame_id = hashlib.md5(f"{stem}_{r}_{c}".encode('utf-8')).hexdigest()
            
            sprites_yaml.append(f"""    - serializedVersion: 2
      name: {frame_name}
      rect:
        serializedVersion: 2
        x: {unity_x}
        y: {unity_y}
        width: {cell_w}
        height: {cell_h}
      alignment: 7
      pivot: {{x: 0.5, y: {pivot_y}}}
      border: {{x: 0, y: 0, z: 0, w: 0}}
      outline: []
      physicsShape: []
      tessellationDetail: 0
      bones: []
      spriteID: {frame_id}
      internalID: {21300000 + r * 10 + c}
      vertices: []
      indices: 
      edges: []
      weights: []""")

    sprites_block = "\n".join(sprites_yaml)
    
    meta_content = f"""fileFormatVersion: 2
guid: {guid}
TextureImporter:
  internalIDToNameTable: []
  externalObjects: {{}}
  serializedVersion: 11
  mipmaps:
    mipMapMode: 0
    enableMipMap: 0
    sRGBTexture: 1
    linearTexture: 0
    fadeOut: 0
    borderMipMap: 0
    mipMapsPreservesCoverage: 0
    alphaTestReferenceValue: 0.5
  bumpMap:
    convertToNormalMap: 0
    externalNormalMap: 0
    heightScale: 0.25
    normalMapFilter: 0
  isReadable: 0
  streamingMipmaps: 0
  streamingMipmapsPriority: 0
  vTOnly: 0
  ignoreMasterTextureLimit: 0
  grayScaleToAlpha: 0
  generateCubemap: 6
  cubemapConvolution: 0
  seamlessCubemap: 0
  textureFormat: 1
  maxTextureSize: 2048
  textureSettings:
    serializedVersion: 2
    filterMode: 0
    aniso: 1
    mipBias: 0
    wrapU: 1
    wrapV: 1
    wrapW: 1
  nPOTScale: 0
  lightmap: 0
  compressionQuality: 50
  spriteMode: 2
  spriteExtrude: 1
  spriteMeshType: 1
  alignment: 0
  spritePivot: {{x: 0.5, y: {pivot_y}}}
  spritePixelsToUnits: {ppu}
  spriteBorder: {{x: 0, y: 0, z: 0, w: 0}}
  spriteGenerateFallbackPhysicsShape: 1
  alphaIsTransparency: 1
  spriteColliderType: 1
  tracks: []
  spriteSheet:
    serializedVersion: 2
    sprites:
{sprites_block}
    outline: []
    physicsShape: []
    bones: []
    spriteID: 
    internalID: 0
    vertices: []
    indices: 
    edges: []
    weights: []
    secondaryTextures: []
    nameFileIdTable: {{}}
  spritePackingTag: 
  pSDRemoveMatte: 0
  pSDShowRemoveMatteOption: 0
  userData: 
  assetBundleName: 
  assetBundleVariant: 
"""
    return meta_content

def update_dual_sync(fn: str, folder: str, img: Image.Image, cell_w: int, cell_h: int, pivot_y: float = 0.05, ppu: int = 100):
    # 1. Save to CHARA/{folder}
    p1 = os.path.join(BASE_CHARA, folder, fn)
    img.save(p1, 'PNG')
    
    # 2. Save to Assets/Characters/{folder}
    p2 = os.path.join(BASE_ASSETS, folder, fn)
    img.save(p2, 'PNG')
    
    # 3. Create meta in both
    meta_text = create_sprite_meta_content(p2, cell_w, cell_h, pivot_y, ppu)
    with open(p1 + '.meta', 'w', encoding='utf-8') as f:
        f.write(meta_text)
    with open(p2 + '.meta', 'w', encoding='utf-8') as f:
        f.write(meta_text)
        
    # 4. Physical slices to CHARA_SLICED
    stem = os.path.splitext(fn)[0]
    out_dir = os.path.join(BASE_SLICED, folder, stem)
    os.makedirs(out_dir, exist_ok=True)
    dir_names = ["down", "left", "right", "up"]
    for r in range(4):
        dname = dir_names[r]
        for c in range(4):
            cell = img.crop((c * cell_w, r * cell_h, (c + 1) * cell_w, (r + 1) * cell_h))
            cell.save(os.path.join(out_dir, f"{dname}_{c}.png"), 'PNG')
            
    print(f"[{folder}] Synced & sliced: {fn} ({img.size}, cell={cell_w}x{cell_h}, pivot={pivot_y})")

def fix_three_kingdoms():
    print("\n=== Fixing Three Kingdoms Characters (NPC Characters-1 (1).png) ===")
    src = os.path.join(BASE_RAW, "NPC Characters-1 (1).png")
    im = Image.open(src).convert('RGBA')
    
    # 4 cols x 2 rows = 8 characters
    # each char: 144w x 384h (cell 48w x 96h)
    for idx in range(8):
        c = idx % 4
        r = idx // 4
        char_crop = im.crop((c * 144, r * 384, (c + 1) * 144, (r + 1) * 384))
        
        # 4-frame cycle [f0, f1, f2, f1] -> 192w x 384h
        out = Image.new('RGBA', (192, 384), (0, 0, 0, 0))
        for row in range(4):
            f0 = char_crop.crop((0 * 48, row * 96, 1 * 48, (row + 1) * 96))
            f1 = char_crop.crop((1 * 48, row * 96, 2 * 48, (row + 1) * 96))
            f2 = char_crop.crop((2 * 48, row * 96, 3 * 48, (row + 1) * 96))
            frames_4 = [f0, f1, f2, f1]
            for col in range(4):
                out.paste(frames_4[col], (col * 48, row * 96), frames_4[col])
                
        fn = f"NPC_Chars_{idx + 1}.png"
        update_dual_sync(fn, "6", out, cell_w=48, cell_h=96, pivot_y=0.05, ppu=100)
        
    # Clean up broken NPC_Chars_1..16 from 不合格
    bad_dir = os.path.join(BASE_CHARA, "不合格")
    for i in range(1, 17):
        bad_f = os.path.join(bad_dir, f"NPC_Chars_{i}.png")
        if os.path.exists(bad_f):
            os.remove(bad_f)
        bad_m = bad_f + ".meta"
        if os.path.exists(bad_m):
            os.remove(bad_m)
    print("Cleaned up 16 broken NPC_Chars from 不合格.")

def fix_20_readded_characters():
    print("\n=== Fixing 20 Re-added Characters ===")
    
    # Remove obsolete files from Assets/Characters/5 that user moved to 6
    obsolete_in_5 = ['45.png', 'RTP风格行走图 (1035).png', 'RTP风格行走图 (1055).png', 
                     'RTP风格行走图 (1282).png', 'RTP风格行走图 (989).png', 
                     'RTP风格行走图 (990).png', 'RTP风格行走图 (991).png']
    for of in obsolete_in_5:
        p = os.path.join(BASE_ASSETS, "5", of)
        if os.path.exists(p):
            os.remove(p)
        if os.path.exists(p + ".meta"):
            os.remove(p + ".meta")
        p_chara = os.path.join(BASE_CHARA, "5", of)
        if os.path.exists(p_chara):
            os.remove(p_chara)
        if os.path.exists(p_chara + ".meta"):
            os.remove(p_chara + ".meta")
            
    # 1. 45.png (Folder 6, 256x256, cell 64x64)
    bp_45 = os.path.join(BASE_BACKUP, "5", "45.png")
    im_45 = Image.open(bp_45).convert('RGBA')
    update_dual_sync("45.png", "6", im_45, cell_w=64, cell_h=64, pivot_y=0.05)
    
    # 2. RTP风格行走图 (1285).png (Folder 5, 160x224, cell 40x56)
    bp_1285 = os.path.join(BASE_BACKUP, "不合格", "RTP风格行走图 (1285).png")
    im_1285 = Image.open(bp_1285).convert('RGBA')
    update_dual_sync("RTP风格行走图 (1285).png", "5", im_1285, cell_w=40, cell_h=56, pivot_y=0.05)
    
    # 3. RTP风格行走图 (421).png (Folder 6, 168x192, cell 42x48)
    bp_421 = os.path.join(BASE_BACKUP, "不合格", "RTP风格行走图 (421).png")
    im_421 = Image.open(bp_421).convert('RGBA')
    update_dual_sync("RTP风格行走图 (421).png", "6", im_421, cell_w=42, cell_h=48, pivot_y=0.05)
    
    # 4. RTP风格行走图 (590).png (Folder 6, 168x192, cell 42x48, white transparentized)
    bp_590 = os.path.join(BASE_BACKUP, "不合格", "RTP风格行走图 (590).png")
    im_590 = Image.open(bp_590).convert('RGBA')
    data_590 = []
    for p in im_590.getdata():
        if p[0] == 255 and p[1] == 255 and p[2] == 255:
            data_590.append((0, 0, 0, 0))
        else:
            data_590.append(p)
    im_590.putdata(data_590)
    update_dual_sync("RTP风格行走图 (590).png", "6", im_590, cell_w=42, cell_h=48, pivot_y=0.05)
    
    # 5. RTP风格行走图 (1035).png (Folder 6, 160x196, cell 40x49, centered)
    bp_1035 = os.path.join(BASE_BACKUP, "5", "RTP风格行走图 (1035).png")
    im_1035_raw = Image.open(bp_1035).convert('RGBA')
    out_1035 = Image.new('RGBA', (160, 196), (0, 0, 0, 0))
    for r in range(4):
        for c in range(4):
            cell = im_1035_raw.crop((c * 37, r * 49, (c + 1) * 37, (r + 1) * 49))
            bb = cell.getbbox()
            if bb:
                crop = cell.crop(bb)
                cw = bb[2] - bb[0]
                dst_x = c * 40 + (40 - cw) // 2
                dst_y = r * 49 + bb[1]
                out_1035.paste(crop, (dst_x, dst_y), crop)
    update_dual_sync("RTP风格行走图 (1035).png", "6", out_1035, cell_w=40, cell_h=49, pivot_y=0.05)
    
    # 6. RTP风格行走图 (217).png (Folder 5, 144x192, cell 36x48, centered)
    bp_217 = os.path.join(BASE_BACKUP, "不合格", "RTP风格行走图 (217).png")
    im_217_raw = Image.open(bp_217).convert('RGBA')
    out_217 = Image.new('RGBA', (144, 192), (0, 0, 0, 0))
    for r in range(4):
        for c in range(4):
            cell = im_217_raw.crop((c * 33, r * 48, (c + 1) * 33, (r + 1) * 48))
            bb = cell.getbbox()
            if bb:
                crop = cell.crop(bb)
                cw = bb[2] - bb[0]
                dst_x = c * 36 + (36 - cw) // 2
                dst_y = r * 48 + bb[1]
                out_217.paste(crop, (dst_x, dst_y), crop)
    update_dual_sync("RTP风格行走图 (217).png", "5", out_217, cell_w=36, cell_h=48, pivot_y=0.1)
    
    # 7. RTP风格行走图 (365).png (Folder 6, 160x192, cell 40x48, connected components)
    bp_365 = os.path.join(BASE_BACKUP, "不合格", "RTP风格行走图 (365).png")
    im_365 = Image.open(bp_365).convert('RGBA')
    out_365 = Image.new('RGBA', (160, 192), (0, 0, 0, 0))
    for r in range(4):
        row_crop = im_365.crop((0, r * 48, 137, (r + 1) * 48))
        visited = set()
        components = []
        for x in range(137):
            for y in range(48):
                if (x, y) not in visited and row_crop.getpixel((x, y))[3] > 0:
                    comp = []
                    q = deque([(x, y)])
                    visited.add((x, y))
                    while q:
                        cx, cy = q.popleft()
                        comp.append((cx, cy))
                        for dx in [-1, 0, 1]:
                            for dy in [-1, 0, 1]:
                                nx, ny = cx + dx, cy + dy
                                if 0 <= nx < 137 and 0 <= ny < 48 and (nx, ny) not in visited:
                                    if row_crop.getpixel((nx, ny))[3] > 0:
                                        visited.add((nx, ny))
                                        q.append((nx, ny))
                    if len(comp) > 50:
                        components.append(comp)
        components.sort(key=lambda c: min(p[0] for p in c))
        for c, comp in enumerate(components):
            min_x = min(p[0] for p in comp)
            max_x = max(p[0] for p in comp)
            min_y = min(p[1] for p in comp)
            max_y = max(p[1] for p in comp)
            cw = max_x - min_x + 1
            ch = max_y - min_y + 1
            sp_img = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
            for px, py in comp:
                sp_img.putpixel((px - min_x, py - min_y), row_crop.getpixel((px, py)))
            dst_x = c * 40 + (40 - cw) // 2
            dst_y = r * 48 + min_y
            out_365.paste(sp_img, (dst_x, dst_y), sp_img)
    update_dual_sync("RTP风格行走图 (365).png", "6", out_365, cell_w=40, cell_h=48, pivot_y=0.05)
    
    # 8. RTP风格行走图 (305).png (Folder 6, 128x192, cell 32x48, centered)
    bp_305 = os.path.join(BASE_BACKUP, "不合格", "RTP风格行走图 (305).png")
    im_305 = Image.open(bp_305).convert('RGBA')
    row_blocks_305 = [(0, 46), (47, 95), (95, 143), (144, 190)]
    out_305 = Image.new('RGBA', (128, 192), (0, 0, 0, 0))
    for r, (y1, y2) in enumerate(row_blocks_305):
        row_crop = im_305.crop((0, y1, 125, y2))
        visited = set()
        components = []
        for x in range(125):
            for y in range(y2 - y1):
                if (x, y) not in visited and row_crop.getpixel((x, y))[3] > 0:
                    comp = []
                    q = deque([(x, y)])
                    visited.add((x, y))
                    while q:
                        cx, cy = q.popleft()
                        comp.append((cx, cy))
                        for dx in [-1, 0, 1]:
                            for dy in [-1, 0, 1]:
                                nx, ny = cx + dx, cy + dy
                                if 0 <= nx < 125 and 0 <= ny < (y2 - y1) and (nx, ny) not in visited:
                                    if row_crop.getpixel((nx, ny))[3] > 0:
                                        visited.add((nx, ny))
                                        q.append((nx, ny))
                    if len(comp) > 50:
                        components.append(comp)
        components.sort(key=lambda c: min(p[0] for p in c))
        for c, comp in enumerate(components):
            min_x = min(p[0] for p in comp)
            max_x = max(p[0] for p in comp)
            min_y = min(p[1] for p in comp)
            max_y = max(p[1] for p in comp)
            cw = max_x - min_x + 1
            ch = max_y - min_y + 1
            sp_img = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
            for px, py in comp:
                sp_img.putpixel((px - min_x, py - min_y), row_crop.getpixel((px, py)))
            dst_x = c * 32 + (32 - cw) // 2
            dst_y = r * 48 + (47 - ch)
            out_305.paste(sp_img, (dst_x, dst_y), sp_img)
    update_dual_sync("RTP风格行走图 (305).png", "6", out_305, cell_w=32, cell_h=48, pivot_y=0.05)
    
    # 9. Evil1_SD_3.png (Folder 6, 96x96, cell 24x24)
    p_evil = os.path.join(BASE_CHARA, "6", "Evil1_SD_3.png")
    im_evil = Image.open(p_evil).convert('RGBA')
    update_dual_sync("Evil1_SD_3.png", "6", im_evil, cell_w=24, cell_h=24, pivot_y=0.05)
    
    # 10. RTP风格行走图 (1055).png (Folder 6, 144x192, cell 36x48, centered)
    bp_1055 = os.path.join(BASE_BACKUP, "5", "RTP风格行走图 (1055).png")
    im_1055 = Image.open(bp_1055).convert('RGBA')
    out_1055 = Image.new('RGBA', (144, 192), (0, 0, 0, 0))
    for r in range(4):
        for c in range(4):
            cell = im_1055.crop((c * 32, r * 48, (c + 1) * 32, (r + 1) * 48))
            bb = cell.getbbox()
            if bb:
                crop = cell.crop(bb)
                cw = bb[2] - bb[0]
                dst_x = c * 36 + (36 - cw) // 2
                dst_y = r * 48 + bb[1]
                out_1055.paste(crop, (dst_x, dst_y), crop)
    update_dual_sync("RTP风格行走图 (1055).png", "6", out_1055, cell_w=36, cell_h=48, pivot_y=0.05)
    
    # 11. RTP风格行走图 (1116).png (Folder 6, 128x192, cell 32x48, centered)
    bp_1116 = os.path.join(BASE_BACKUP, "不合格", "RTP风格行走图 (1116).png")
    im_1116 = Image.open(bp_1116).convert('RGBA')
    out_1116 = Image.new('RGBA', (128, 192), (0, 0, 0, 0))
    for r in range(4):
        for c in range(4):
            cell = im_1116.crop((c * 32, r * 48, (c + 1) * 32, (r + 1) * 48))
            bb = cell.getbbox()
            if bb:
                crop = cell.crop(bb)
                cw = bb[2] - bb[0]
                dst_x = c * 32 + (32 - cw) // 2
                dst_y = r * 48 + bb[1]
                out_1116.paste(crop, (dst_x, dst_y), crop)
    update_dual_sync("RTP风格行走图 (1116).png", "6", out_1116, cell_w=32, cell_h=48, pivot_y=0.05)
    
    # 12. RTP风格行走图 (1284).png (Folder 5, 128x192, cell 32x48, centered)
    bp_1284 = os.path.join(BASE_BACKUP, "不合格", "RTP风格行走图 (1284).png")
    im_1284 = Image.open(bp_1284).convert('RGBA')
    out_1284 = Image.new('RGBA', (128, 192), (0, 0, 0, 0))
    for r in range(4):
        for c in range(4):
            cell = im_1284.crop((c * 32, r * 48, (c + 1) * 32, (r + 1) * 48))
            bb = cell.getbbox()
            if bb:
                crop = cell.crop(bb)
                cw = bb[2] - bb[0]
                dst_x = c * 32 + (32 - cw) // 2
                dst_y = r * 48 + bb[1]
                out_1284.paste(crop, (dst_x, dst_y), crop)
    update_dual_sync("RTP风格行走图 (1284).png", "5", out_1284, cell_w=32, cell_h=48, pivot_y=0.1)
    
    # 13, 14, 15: RTP风格行走图 (989), (990), (991) (Folder 6, 128x192, cell 32x48, white bg transparentized & centered)
    for fn_99x in ["RTP风格行走图 (989).png", "RTP风格行走图 (990).png", "RTP风格行走图 (991).png"]:
        bp_99x = os.path.join(BASE_BACKUP, "5", fn_99x)
        im_99x = Image.open(bp_99x).convert('RGBA')
        d = []
        for p in im_99x.getdata():
            if p[0] == 255 and p[1] == 255 and p[2] == 255:
                d.append((0, 0, 0, 0))
            else:
                d.append(p)
        im_99x.putdata(d)
        out_99x = Image.new('RGBA', (128, 192), (0, 0, 0, 0))
        for r in range(4):
            for c in range(4):
                cell = im_99x.crop((c * 32, r * 48, (c + 1) * 32, (r + 1) * 48))
                bb = cell.getbbox()
                if bb:
                    crop = cell.crop(bb)
                    cw = bb[2] - bb[0]
                    dst_x = c * 32 + (32 - cw) // 2
                    dst_y = r * 48 + bb[1]
                    out_99x.paste(crop, (dst_x, dst_y), crop)
        update_dual_sync(fn_99x, "6", out_99x, cell_w=32, cell_h=48, pivot_y=0.05)
        
    # 16. RTP风格行走图 (1282).png (Folder 6, 128x192)
    bp_1282 = os.path.join(BASE_BACKUP, "5", "RTP风格行走图 (1282).png")
    im_1282 = Image.open(bp_1282).convert('RGBA')
    update_dual_sync("RTP风格行走图 (1282).png", "6", im_1282, cell_w=32, cell_h=48, pivot_y=0.05)
    
    # 17. RTP风格行走图 (354).png (Folder 6, 128x192)
    bp_354 = os.path.join(BASE_BACKUP, "不合格", "RTP风格行走图 (354).png")
    im_354 = Image.open(bp_354).convert('RGBA')
    update_dual_sync("RTP风格行走图 (354).png", "6", im_354, cell_w=32, cell_h=48, pivot_y=0.05)
    
    # 18. RTP风格行走图 (1156).png (Folder 5, 128x192)
    bp_1156 = os.path.join(BASE_BACKUP, "不合格", "RTP风格行走图 (1156).png")
    im_1156 = Image.open(bp_1156).convert('RGBA')
    update_dual_sync("RTP风格行走图 (1156).png", "5", im_1156, cell_w=32, cell_h=48, pivot_y=0.1)
    
    # 19. RTP风格行走图 (1286).png (Folder 5, 128x192)
    bp_1286 = os.path.join(BASE_BACKUP, "不合格", "RTP风格行走图 (1286).png")
    im_1286 = Image.open(bp_1286).convert('RGBA')
    update_dual_sync("RTP风格行走图 (1286).png", "5", im_1286, cell_w=32, cell_h=48, pivot_y=0.1)
    
    # 20. RTP风格行走图 (161).png (Folder 5, 128x192)
    bp_161 = os.path.join(BASE_BACKUP, "不合格", "RTP风格行走图 (161).png")
    im_161 = Image.open(bp_161).convert('RGBA')
    update_dual_sync("RTP风格行走图 (161).png", "5", im_161, cell_w=32, cell_h=48, pivot_y=0.1)

if __name__ == "__main__":
    fix_three_kingdoms()
    fix_20_readded_characters()
    print("\nALL FIXES COMPLETED SUCCESSFULLY!")
