#if UNITY_EDITOR
using System;
using System.IO;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using LegionBattle.Battle;

namespace LegionBattle.EditorTools
{
    /// <summary>
    /// Super Pixel Effects Megapack 1 按需精简导入与批量自动切片工具
    /// 1. 仅针对被技能规则命中的 84 个核心家族（共 604 张 large 精灵表）按需读取 spritesheet.txt 坐标
    /// 2. 自动转换左上角像素坐标为 Unity 左下角 SpriteMetaData 坐标 (unityY = texH - y - h)
    /// 3. 批量设置 Point 像素滤波、Uncompressed 无损清晰度、PPU=32、中心锚点 (0.5, 0.5)
    /// 4. 自动构建并保存 Assets/Resources/EffectDatabase.asset 供 30v30 军团战斗零开销调用
    /// </summary>
    public class EffectSpriteSheetSlicer : EditorWindow
    {
        private const string SpritesheetsFolder = "Assets/Effects/Spritesheets";
        private const string DatabaseAssetPath = "Assets/Resources/EffectDatabase.asset";
        private int pixelsPerUnit = 32;
        private string testSkillName = "修罗崩击";
        private string testGenre = "勇气";
        private int testTier = 4;
        private string testResultText = "点击【测试词条匹配】或【随机抽测 10 个技能】查看匹配结果...";
        private Vector2 scrollPos;

        [MenuItem("Tools/特效精灵表按需导入与自动切片工具")]
        public static void ShowWindow()
        {
            var win = GetWindow<EffectSpriteSheetSlicer>("特效批量切图工具");
            win.minSize = new Vector2(540, 480);
            win.Show();
        }

        private void OnGUI()
        {
            EditorGUILayout.Space(8);
            EditorGUILayout.LabelField("Super Pixel Effects 按需导入与自动切片工具 (84家族 / 604变体)", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox(
                "本工具专为 30v30 军团战斗特效设计：\n" +
                "1. 按需精简：仅导入被技能词条规则命中的 84 个核心 large 特效家族（604 张精灵表，仅 11MB，剔除冗余散图与小尺寸）。\n" +
                "2. 自动切片：自动解析每张表配套的 .txt 帧坐标文件，设置 Point 像素滤波、无压缩、PPU=32。\n" +
                "3. 烘焙数据库：自动生成 Assets/Resources/EffectDatabase.asset，绑定唯一 animation_id (1001~1604)。\n" +
                "（注：即使未点击烘焙，运行时 BattleEffectPlayer 也会自动按需实时切帧并缓存，确保 100% 正常播放！）",
                MessageType.Info
            );

            EditorGUILayout.Space(6);
            pixelsPerUnit = EditorGUILayout.IntField("Pixels Per Unit (PPU)", pixelsPerUnit);
            if (pixelsPerUnit < 1) pixelsPerUnit = 32;

            EditorGUILayout.Space(8);
            GUI.backgroundColor = new Color(0.25f, 0.78f, 0.42f, 1f);
            if (GUILayout.Button("一键批量切图并构建 EffectDatabase.asset (604个精灵表)", GUILayout.Height(40)))
            {
                RunBatchSliceAndBuildDatabase();
            }
            GUI.backgroundColor = Color.white;

            EditorGUILayout.Space(14);
            EditorGUILayout.LabelField("技能词条 -> 像素特效 双轴匹配规则实时检视器", EditorStyles.boldLabel);

            EditorGUILayout.BeginHorizontal();
            testSkillName = EditorGUILayout.TextField("测试技能名称", testSkillName);
            testGenre = EditorGUILayout.TextField("流派", testGenre, GUILayout.Width(120));
            testTier = EditorGUILayout.IntSlider("阶位", testTier, 1, 6);
            EditorGUILayout.EndHorizontal();

            EditorGUILayout.BeginHorizontal();
            if (GUILayout.Button("测试当前技能名匹配", GUILayout.Height(28)))
            {
                int aid;
                string cn, folder, cat;
                SkillEffectMatcher.ResolveSkillEffect(testSkillName, testGenre, testTier, "", out aid, out cn, out folder, out cat);
                testResultText = string.Format("技能《{0}》({1} T{2})\n  -> 动画 ID: {3}\n  -> 中文特征名: {4} [{5}]\n  -> 精灵表文件: {6}.png",
                    testSkillName, testGenre, testTier, aid, cn, cat, folder);
            }
            if (GUILayout.Button("随机生成 10 个技能并检视特效匹配", GUILayout.Height(28)))
            {
                System.Text.StringBuilder sb = new System.Text.StringBuilder();
                for (int i = 1; i <= 10; i++)
                {
                    int t = UnityEngine.Random.Range(1, 7);
                    BattleSkill sk = BattleSkillDatabase.GenerateRandomSkill(t);
                    sb.AppendLine(string.Format("[#{0:D2}] T{1} 《{2}》 -> ID:{3} | {4} ({5})",
                        i, sk.rarityTier, sk.name, sk.animationId, sk.effectCnName, sk.effectFolder));
                }
                testResultText = sb.ToString();
            }
            EditorGUILayout.EndHorizontal();

            EditorGUILayout.Space(6);
            scrollPos = EditorGUILayout.BeginScrollView(scrollPos, GUILayout.ExpandHeight(true));
            EditorGUILayout.TextArea(testResultText, GUILayout.ExpandHeight(true));
            EditorGUILayout.EndScrollView();
        }

        public void RunBatchSliceAndBuildDatabase(bool showCompletionDialog = true)
        {
            if (!AssetDatabase.IsValidFolder(SpritesheetsFolder))
            {
                EditorUtility.DisplayDialog("提示", "未找到精灵表目录: " + SpritesheetsFolder + "\n请先运行 build_effect_skill_mapping.py 导入按需精灵表。", "确定");
                return;
            }

            if (!AssetDatabase.IsValidFolder("Assets/Resources"))
            {
                AssetDatabase.CreateFolder("Assets", "Resources");
            }

            EffectDatabase db = AssetDatabase.LoadAssetAtPath<EffectDatabase>(DatabaseAssetPath);
            if (db == null)
            {
                db = ScriptableObject.CreateInstance<EffectDatabase>();
                AssetDatabase.CreateAsset(db, DatabaseAssetPath);
            }
            db.effects.Clear();
            db.visibleFramesCentered=false;

            SkillEffectMatcher.EnsureInitialized();
            int total = 604;
            int processed = 0;

            try
            {
                for (int animId = 1001; animId <= 1604; animId++)
                {
                    SkillEffectMatcher.VariantEntry ve;
                    SkillEffectMatcher.FamilyEntry fe;
                    if (!SkillEffectMatcher.TryGetById(animId, out ve, out fe)) continue;

                    string folder = ve.FolderName;
                    string pngAssetPath = string.Format("{0}/{1}.png", SpritesheetsFolder, folder);
                    string txtAssetPath = string.Format("{0}/{1}.txt", SpritesheetsFolder, folder);
                    string fullTxtPath = Path.Combine(Application.dataPath, string.Format("Effects/Spritesheets/{0}.txt", folder));

                    EditorUtility.DisplayProgressBar(
                        "批量切图并构建特效数据库...",
                        string.Format("[{0}/{1}] ID:{2} {3} ({4})", animId - 1000, total, animId, ve.CnName, folder),
                        (float)(animId - 1001) / total);

                    if (!File.Exists(fullTxtPath)) continue;

                    TextureImporter importer = AssetImporter.GetAtPath(pngAssetPath) as TextureImporter;
                    Texture2D tex = AssetDatabase.LoadAssetAtPath<Texture2D>(pngAssetPath);
                    if (importer == null || tex == null) continue;

                    // Atlas coordinates refer to the original PNG, before importer resizing.
                    byte[] pngBytes = File.ReadAllBytes(Path.Combine(Application.dataPath, "Effects/Spritesheets/" + folder + ".png"));
                    int texW = (pngBytes[16] << 24) | (pngBytes[17] << 16) | (pngBytes[18] << 8) | pngBytes[19];
                    int texH = (pngBytes[20] << 24) | (pngBytes[21] << 16) | (pngBytes[22] << 8) | pngBytes[23];
                    var alphaTexture=new Texture2D(2,2,TextureFormat.RGBA32,false);
                    if(!alphaTexture.LoadImage(pngBytes)){DestroyImmediate(alphaTexture);throw new InvalidOperationException("Cannot read atlas alpha: "+folder);}
                    var pixels=alphaTexture.GetPixels32();DestroyImmediate(alphaTexture);
                    string[] lines = File.ReadAllLines(fullTxtPath);
                    List<SpriteMetaData> metas = new List<SpriteMetaData>();
                    List<EffectFrameRect> rawRects = new List<EffectFrameRect>();
                    int maxDim = 64;

                    for (int i = 0; i < lines.Length; i++)
                    {
                        string line = lines[i].Trim();
                        if (string.IsNullOrEmpty(line)) continue;
                        int eqIdx = line.IndexOf('=');
                        if (eqIdx < 0) continue;

                        string[] nums = line.Substring(eqIdx + 1).Trim().Split(new char[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
                        if (nums.Length < 4) continue;

                        int x = int.Parse(nums[0]);
                        int y = int.Parse(nums[1]);
                        int w = int.Parse(nums[2]);
                        int h = int.Parse(nums[3]);
                        if (w > maxDim) maxDim = w;
                        if (h > maxDim) maxDim = h;

                        int unityY = texH - y - h;
                        SpriteMetaData meta = new SpriteMetaData
                        {
                            name = string.Format("{0}_{1:D2}", folder, metas.Count),
                            rect = new Rect(x, unityY, w, h),
                            alignment = (int)SpriteAlignment.Custom,
                            pivot = EffectFrameAlignment.Pivot(pixels,texW,new Rect(x,unityY,w,h))
                        };
                        metas.Add(meta);
                        rawRects.Add(new EffectFrameRect { x = x, y = y, w = w, h = h });
                    }

                    importer.textureType = TextureImporterType.Sprite;
                    importer.maxTextureSize = Mathf.NextPowerOfTwo(Mathf.Max(texW, texH));
                    importer.npotScale = TextureImporterNPOTScale.None;
                    importer.spriteImportMode = SpriteImportMode.Multiple;
                    importer.spritePixelsPerUnit = pixelsPerUnit;
                    importer.filterMode = FilterMode.Point;
                    importer.textureCompression = TextureImporterCompression.Uncompressed;
                    importer.alphaIsTransparency = true;
                    importer.spritesheet = metas.ToArray();

                    EditorUtility.SetDirty(importer);
                    AssetDatabase.ImportAsset(pngAssetPath, ImportAssetOptions.ForceUpdate);

                    // 加载切好的全部子 Sprite 并按名称排序
                    UnityEngine.Object[] allSubAssets = AssetDatabase.LoadAllAssetsAtPath(pngAssetPath);
                    List<Sprite> sprites = new List<Sprite>();
                    for (int i = 0; i < allSubAssets.Length; i++)
                    {
                        Sprite sp = allSubAssets[i] as Sprite;
                        if (sp != null) sprites.Add(sp);
                    }
                    sprites.Sort((a, b) => string.CompareOrdinal(a.name, b.name));
                    if (sprites.Count != metas.Count)
                        throw new InvalidOperationException(string.Format("Atlas {0}: expected {1} frames, imported {2}", folder, metas.Count, sprites.Count));

                    float recScale = 2.2f;
                    if (maxDim <= 32) recScale = 3.6f;
                    else if (maxDim <= 48) recScale = 3.0f;
                    else if (maxDim <= 64) recScale = 2.4f;
                    else if (maxDim <= 76) recScale = 2.1f;
                    else if (maxDim <= 96) recScale = 1.75f;
                    else if (maxDim <= 128) recScale = 1.40f;
                    else if (maxDim <= 160) recScale = 1.15f;
                    else recScale = 1.00f;

                    bool isDirRight = ve.CnName.Contains("向右") || folder.StartsWith("pj1_") || folder.StartsWith("pj2_") || folder.Contains("boost");

                    EffectEntry entry = new EffectEntry
                    {
                        animationId = animId,
                        baseKey = fe.BaseKey,
                        color = ve.Color,
                        cnName = ve.CnName,
                        categoryCn = fe.CategoryCn,
                        folderName = folder,
                        fps = 15,
                        isDirectionalRight = isDirRight,
                        playOnCaster = fe.PlayOnCaster,
                        recommendedScale = recScale,
                        frames = sprites.ToArray(),
                        rawRects = rawRects
                    };
                    var pivots=new Vector2[metas.Count];for(int i=0;i<metas.Count;i++)pivots[i]=metas[i].pivot;
                    entry.frontFrames=ImportLayer(folder,"front",pivots);
                    entry.backFrames=ImportLayer(folder,"back",pivots);
                    if((entry.frontFrames.Length>0)!=(entry.backFrames.Length>0))throw new InvalidOperationException("Incomplete native layers: "+folder);
                    if(entry.frontFrames.Length>0&&(entry.frontFrames.Length!=entry.frames.Length||entry.backFrames.Length!=entry.frames.Length))throw new InvalidOperationException("Native layer frame mismatch: "+folder);
                    db.effects.Add(entry);
                    processed++;
                }
                db.visibleFramesCentered=true;
            }
            finally
            {
                EditorUtility.ClearProgressBar();
                EditorUtility.SetDirty(db);
                AssetDatabase.SaveAssets();
                AssetDatabase.Refresh();
            }

            if (showCompletionDialog && !Application.isBatchMode) EditorUtility.DisplayDialog(
                "特效自动切图与数据库构建完成",
                string.Format("成功处理并切片 {0} 个特效精灵表！\n已生成数据库：{1}", processed, DatabaseAssetPath),
                "确定");
        }
        private Sprite[] ImportLayer(string folder,string suffix,Vector2[] pivots)
        {
            string assetPath="Assets/Effects/Layers/"+folder+"_"+suffix+".png";
            string textPath=Path.Combine(Application.dataPath,"Effects/Layers/"+folder+"_"+suffix+".txt");
            if(!File.Exists(textPath))return new Sprite[0];
            var importer=AssetImporter.GetAtPath(assetPath) as TextureImporter;
            if(importer==null)throw new InvalidOperationException("Missing layer texture: "+assetPath);
            byte[] png=File.ReadAllBytes(Path.Combine(Application.dataPath,"Effects/Layers/"+folder+"_"+suffix+".png"));
            int width=(png[16]<<24)|(png[17]<<16)|(png[18]<<8)|png[19];int height=(png[20]<<24)|(png[21]<<16)|(png[22]<<8)|png[23];
            var metas=new List<SpriteMetaData>();
            foreach(string raw in File.ReadAllLines(textPath)){
                int equals=raw.IndexOf('=');if(equals<0)continue;
                string[] values=raw.Substring(equals+1).Split(new[]{' ','\t'},StringSplitOptions.RemoveEmptyEntries);if(values.Length!=4)continue;
                int x=int.Parse(values[0]),y=int.Parse(values[1]),w=int.Parse(values[2]),h=int.Parse(values[3]);
                if(metas.Count>=pivots.Length)throw new InvalidOperationException("Native layer pivot mismatch: "+folder);
                metas.Add(new SpriteMetaData {name=folder+"_"+suffix+"_"+metas.Count.ToString("D3"),rect=new Rect(x,height-y-h,w,h),alignment=(int)SpriteAlignment.Custom,pivot=pivots[metas.Count]});
            }
            importer.textureType=TextureImporterType.Sprite;importer.spriteImportMode=SpriteImportMode.Multiple;
            var textureSettings=new TextureImporterSettings();importer.ReadTextureSettings(textureSettings);textureSettings.spriteMeshType=SpriteMeshType.FullRect;importer.SetTextureSettings(textureSettings);
            importer.textureShape=TextureImporterShape.Texture2D;
            importer.maxTextureSize=Mathf.NextPowerOfTwo(Mathf.Max(width,height));importer.npotScale=TextureImporterNPOTScale.None;
            importer.spritePixelsPerUnit=pixelsPerUnit;importer.filterMode=FilterMode.Point;importer.textureCompression=TextureImporterCompression.Uncompressed;importer.alphaIsTransparency=true;importer.spritesheet=metas.ToArray();
            EditorUtility.SetDirty(importer);AssetDatabase.ImportAsset(assetPath,ImportAssetOptions.ForceUpdate);
            var sprites=new List<Sprite>();foreach(var asset in AssetDatabase.LoadAllAssetsAtPath(assetPath)){var sprite=asset as Sprite;if(sprite!=null)sprites.Add(sprite);}
            sprites.Sort((a,b)=>string.CompareOrdinal(a.name,b.name));
            if(sprites.Count!=metas.Count)throw new InvalidOperationException("Native layer import mismatch: "+folder+"_"+suffix+" expected "+metas.Count+" imported "+sprites.Count);
            return sprites.ToArray();
        }
    }
}
#endif
