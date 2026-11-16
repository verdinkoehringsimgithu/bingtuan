#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
角色行走图批量切图与 Unity Meta 生成脚本
执行两项任务：
1. 物理切图：将 1~6、SP 中的所有角色切分为独立单帧 PNG，输出到 D:\\123\\CHARA_SLICED\\{分类}\\{角色名}\\
   帧命名：down_0..3, left_0..3, right_0..3, up_0..3
2. Unity 元数据生成：为原图生成配套的 .png.meta 文件
   - 设置为 Sprite (Multiple)
   - FilterMode = Point, Uncompressed
   - 包含 16 帧切片定义
   - 核心：统一将 Pivot 设置为 Bottom-Center (0.5, 0.0)
严格遵守：不修改、不处理 CHARA\\不合格 目录。
"""

import os
import sys
import time
import hashlib
from PIL import Image

BASE_CHARA = r"D:\123\CHARA"
OUTPUT_SLICED = r"D:\123\CHARA_SLICED"
TARGET_CATS = ["1", "2", "3", "4", "5", "6", "SP"]

def generate_guid(filepath: str) -> str:
    rel = os.path.relpath(filepath, BASE_CHARA).replace('\\', '/').lower()
    return hashlib.md5(rel.encode('utf-8')).hexdigest()

def create_sprite_meta_content(png_path: str, ppu: int = 32) -> str:
    guid = generate_guid(png_path)
    stem = os.path.splitext(os.path.basename(png_path))[0]
    
    with Image.open(png_path) as im:
        w, h = im.size
        
    cols = 4
    rows = 4
    if w % 4 != 0 and w % 3 == 0:
        cols = 3
        
    dir_names = ["down", "left", "right", "up"]
    sprites_yaml = []
    
    for r in range(rows):
        y0 = int(round(r * h / rows))
        y1 = int(round((r + 1) * h / rows))
        cell_h = y1 - y0
        # Unity 纹理坐标系自下而上:
        unity_y = h - y1
        dname = dir_names[r] if r < len(dir_names) else f"row{r}"
        
        for c in range(cols):
            x0 = int(round(c * w / cols))
            x1 = int(round((c + 1) * w / cols))
            cell_w = x1 - x0
            unity_x = x0
            
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
      pivot: {{x: 0.5, y: 0}}
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
    mipBias: 0
    wrapU: 1
    wrapV: 1
    wrapW: 1
  bumpmap:
    convertToNormalMap: 0
    externalNormalMap: 0
    heightScale: 0.25
    normalMapFilter: 0
  isReadable: 0
  streamingMipmaps: 0
  streamingMipmapsPriority: 0
  vTOnly: 0
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
  alignment: 7
  spritePivot: {{x: 0.5, y: 0}}
  spritePixelsToUnits: {ppu}
  spriteBorder: {{x: 0, y: 0, z: 0, w: 0}}
  spriteGenerateFallbackPhysicsShape: 1
  alphaIsTransparency: 1
  spriteColliderType: 1
  compilerAdditionalSpriteData:
    spriteData: []
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
  spritePackingTag: 
  pSDRemoveMatte: 0
  pSDShowRemoveMatteOption: 0
  userData: 
  assetBundleName: 
  assetBundleVariant: 
"""
    return meta_content

def slice_single_image(png_path: str, out_chara_dir: str):
    os.makedirs(out_chara_dir, exist_ok=True)
    with Image.open(png_path) as im:
        w, h = im.size
        cols = 4
        rows = 4
        if w % 4 != 0 and w % 3 == 0:
            cols = 3
        dir_names = ["down", "left", "right", "up"]
        
        for r in range(rows):
            dname = dir_names[r] if r < len(dir_names) else f"row{r}"
            y0 = int(round(r * h / rows))
            y1 = int(round((r + 1) * h / rows))
            for c in range(cols):
                x0 = int(round(c * w / cols))
                x1 = int(round((c + 1) * w / cols))
                frame = im.crop((x0, y0, x1, y1))
                frame_path = os.path.join(out_chara_dir, f"{dname}_{c}.png")
                frame.save(frame_path)

def main():
    t0 = time.time()
    print("开始执行全量切图与 Unity Meta 生成...")
    
    total_sheets = 0
    total_frames = 0
    total_metas = 0
    errors = []
    
    for cat in TARGET_CATS:
        cat_dir = os.path.join(BASE_CHARA, cat)
        if not os.path.exists(cat_dir):
            continue
            
        png_files = sorted([f for f in os.listdir(cat_dir) if f.lower().endswith(".png")])
        print(f"处理分类 [{cat}]：共 {len(png_files)} 个角色...")
        
        for f in png_files:
            png_path = os.path.join(cat_dir, f)
            stem = os.path.splitext(f)[0]
            out_chara_dir = os.path.join(OUTPUT_SLICED, cat, stem)
            meta_path = png_path + ".meta"
            
            try:
                # 1. 物理切图生成单帧 PNG
                slice_single_image(png_path, out_chara_dir)
                total_frames += 16
                
                # 2. 生成 Unity .meta 文件
                meta_content = create_sprite_meta_content(png_path)
                with open(meta_path, "w", encoding="utf-8") as mf:
                    mf.write(meta_content)
                total_metas += 1
                
                total_sheets += 1
            except Exception as e:
                errors.append(f"{png_path}: {e}")
                
    elapsed = time.time() - t0
    print("\n" + "=" * 50)
    print("切图与 Meta 生成全部完成！")
    print(f"处理角色图总数: {total_sheets} 张")
    print(f"切分单帧 PNG 总数: {total_frames} 帧 (位于 D:\\123\\CHARA_SLICED)")
    print(f"生成 Unity .meta 文件数: {total_metas} 份 (位于 D:\\123\\CHARA 各分类目录)")
    print(f"总耗时: {elapsed:.2f} 秒")
    if errors:
        print(f"出现异常数: {len(errors)}")
        for err in errors[:5]:
            print("  ", err)
    print("=" * 50)

if __name__ == "__main__":
    main()
