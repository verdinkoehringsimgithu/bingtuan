#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unity 批量 .meta 文件生成器
直接为所有角色行走图生成标准的 Unity .meta 文件：
1. 设定 TextureImporter 为 Sprite (Multiple)
2. FilterMode = Point (无模糊抗锯齿)
3. 压缩模式 = Uncompressed (保持像素原画质)
4. 精确切分为 16 帧 (4列 x 4行)
5. 核心基准对齐：所有帧统一设置 Pivot = Bottom-Center (0.5, 0.0)，确保游戏内换向行走不抽动不浮空。
"""

import os
import hashlib
from PIL import Image

def generate_guid(filepath: str) -> str:
    rel = os.path.relpath(filepath).replace('\\', '/').lower()
    return hashlib.md5(rel.encode('utf-8')).hexdigest()

def create_sprite_meta(png_path: str, ppu: int = 32) -> str:
    guid = generate_guid(png_path)
    stem = os.path.splitext(os.path.basename(png_path))[0]
    
    with Image.open(png_path) as im:
        w, h = im.size
        
    cols = 4
    rows = 4
    if w % 4 != 0 and w % 3 == 0:
        cols = 3
        
    cw = w // cols
    ch = h // rows
    
    dir_names = ["down", "left", "right", "up"]
    
    sprites_yaml = []
    for r in range(rows):
        # Unity 纹理坐标系原点在左下角，第 r 行(从上至下)对应 Unity Y = (rows - 1 - r) * ch
        unity_y = (rows - 1 - r) * ch
        dname = dir_names[r] if r < len(dir_names) else f"row{r}"
        
        for c in range(cols):
            unity_x = c * cw
            frame_name = f"{stem}_{dname}_{c}"
            frame_id = hashlib.md5(f"{stem}_{r}_{c}".encode('utf-8')).hexdigest()
            
            sprites_yaml.append(f"""    - serializedVersion: 2
      name: {frame_name}
      rect:
        serializedVersion: 2
        x: {unity_x}
        y: {unity_y}
        width: {cw}
        height: {ch}
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

def process_directory(base_dir: str):
    count = 0
    for root, dirs, files in os.walk(base_dir):
        # 排除备份文件夹
        if "CHARA_BACKUP" in root or "CHARA_NEW_RAW_PACKS" in root:
            continue
        for f in files:
            if f.lower().endswith(".png"):
                png_path = os.path.join(root, f)
                meta_path = png_path + ".meta"
                try:
                    meta_text = create_sprite_meta(png_path)
                    with open(meta_path, "w", encoding="utf-8") as mf:
                        mf.write(meta_text)
                    count += 1
                except Exception as e:
                    print(f"Error processing {png_path}: {e}")
    print(f"成功为 {count} 个角色纹理生成 Unity .meta 文件！")

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else r"D:\123\CHARA"
    print(f"正在为目录生成 Unity .meta: {target}")
    process_directory(target)
