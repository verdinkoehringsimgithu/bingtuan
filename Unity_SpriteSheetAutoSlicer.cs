#if UNITY_EDITOR
using System;
using System.IO;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;

namespace LegionBattle.EditorTools
{
    public class SpriteSheetAutoSlicer : EditorWindow
    {
        private string targetFolder = "Assets/Characters";
        private int pixelsPerUnit = 32;
        private bool generateAnimClips = false;
        private Vector2 scrollPos;

        [MenuItem("Tools/角色行走图批量切图与中心点设置")]
        public static void ShowWindow()
        {
            var win = GetWindow<SpriteSheetAutoSlicer>("角色切图工具");
            win.minSize = new Vector2(460, 320);
            win.Show();
        }

        private void OnEnable()
        {
            if (Selection.activeObject != null)
            {
                string path = AssetDatabase.GetAssetPath(Selection.activeObject);
                if (AssetDatabase.IsValidFolder(path))
                {
                    targetFolder = path;
                }
            }
        }

        private void OnGUI()
        {
            EditorGUILayout.Space(10);
            EditorGUILayout.LabelField("角色行走图批量切图与中心点设置", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox(
                "本工具按分类规则批量完成切图与中心点设置：\n" +
                "1. 最开始的常规角色 (RTP等)：中心点 Y = 0.10\n" +
                "2. gal 格式角色 (Actor/Evil/People等)：中心点 Y = 0.05\n" +
                "3. 迷你 PC 开头角色：中心点 Y = 0.21\n" +
                "4. mini 开头角色：中心点 Y = 0.25\n" +
                "所有切片均设为 Point 像素滤波、无压缩，确保落脚对齐零抽搐。",
                MessageType.Info
            );

            EditorGUILayout.Space(8);
            scrollPos = EditorGUILayout.BeginScrollView(scrollPos);

            EditorGUILayout.BeginHorizontal();
            targetFolder = EditorGUILayout.TextField("目标文件夹", targetFolder);
            if (GUILayout.Button("选择", GUILayout.Width(60)))
            {
                string selected = EditorUtility.OpenFolderPanel("选择角色纹理所在文件夹", "Assets", "");
                if (!string.IsNullOrEmpty(selected))
                {
                    if (selected.StartsWith(Application.dataPath))
                    {
                        targetFolder = "Assets" + selected.Substring(Application.dataPath.Length);
                    }
                    else
                    {
                        targetFolder = selected;
                    }
                }
            }
            EditorGUILayout.EndHorizontal();

            pixelsPerUnit = EditorGUILayout.IntField("Pixels Per Unit", pixelsPerUnit);
            if (pixelsPerUnit < 1) pixelsPerUnit = 1;

            generateAnimClips = EditorGUILayout.Toggle("同步生成 4 方向动画片段", generateAnimClips);

            EditorGUILayout.Space(15);

            if (GUILayout.Button("开始批量切图与中心点设置", GUILayout.Height(38)))
            {
                RunBatchSlice();
            }

            EditorGUILayout.EndScrollView();
        }

        private float GetTargetPivotY(string fileName)
        {
            string lower = fileName.ToLowerInvariant();
            if (lower.StartsWith("pc_") || lower.StartsWith("pc-"))
            {
                return 0.21f;
            }
            else if (lower.StartsWith("mini_") || lower.StartsWith("mini-"))
            {
                return 0.25f;
            }
            else if (lower.StartsWith("actor") || lower.StartsWith("evil") ||
                     lower.StartsWith("people") || lower.StartsWith("anthrodinos") ||
                     lower.StartsWith("vol1") || lower.StartsWith("npc") || lower.Contains("gal"))
            {
                return 0.05f;
            }
            else
            {
                return 0.10f;
            }
        }

        private void RunBatchSlice()
        {
            if (!AssetDatabase.IsValidFolder(targetFolder))
            {
                EditorUtility.DisplayDialog("错误", "请指定有效的 Unity 项目内文件夹路径: " + targetFolder, "确定");
                return;
            }

            string[] guids = AssetDatabase.FindAssets("t:Texture2D", new string[] { targetFolder });
            if (guids.Length == 0)
            {
                EditorUtility.DisplayDialog("提示", "在指定文件夹未找到任何 Texture2D 资源。", "确定");
                return;
            }

            int total = guids.Length;
            int successCount = 0;

            try
            {
                for (int i = 0; i < total; i++)
                {
                    string assetPath = AssetDatabase.GUIDToAssetPath(guids[i]);
                    EditorUtility.DisplayProgressBar("批量处理中...", string.Format("[{0}/{1}] {2}", i + 1, total, Path.GetFileName(assetPath)), (float)i / total);

                    TextureImporter importer = AssetImporter.GetAtPath(assetPath) as TextureImporter;
                    if (importer == null) continue;

                    Texture2D tex = AssetDatabase.LoadAssetAtPath<Texture2D>(assetPath);
                    if (tex == null) continue;

                    int texW = tex.width;
                    int texH = tex.height;

                    int cols = 4;
                    int rows = 4;
                    if (texW % 4 != 0 && texW % 3 == 0)
                    {
                        cols = 3;
                    }

                    int cellW = texW / cols;
                    int cellH = texH / rows;

                    string texName = Path.GetFileNameWithoutExtension(assetPath);
                    float pivotY = GetTargetPivotY(texName);

                    importer.textureType = TextureImporterType.Sprite;
                    importer.spriteImportMode = SpriteImportMode.Multiple;
                    importer.spritePixelsPerUnit = pixelsPerUnit;
                    importer.filterMode = FilterMode.Point;
                    importer.textureCompression = TextureImporterCompression.Uncompressed;
                    importer.alphaIsTransparency = true;

                    string[] dirNames = new string[] { "down", "left", "right", "up" };
                    List<SpriteMetaData> metas = new List<SpriteMetaData>();

                    for (int r = 0; r < rows; r++)
                    {
                        int unityRowY = (rows - 1 - r) * cellH;
                        string dir = r < dirNames.Length ? dirNames[r] : ("row" + r);

                        for (int c = 0; c < cols; c++)
                        {
                            int unityColX = c * cellW;
                            SpriteMetaData meta = new SpriteMetaData();
                            meta.name = string.Format("{0}_{1}_{2}", texName, dir, c);
                            meta.rect = new Rect(unityColX, unityRowY, cellW, cellH);
                            
                            meta.alignment = (int)SpriteAlignment.Custom;
                            meta.pivot = new Vector2(0.5f, pivotY);

                            metas.Add(meta);
                        }
                    }

                    importer.spritesheet = metas.ToArray();
                    EditorUtility.SetDirty(importer);
                    AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceUpdate);

                    if (generateAnimClips)
                    {
                        GenerateDirectionClips(assetPath, texName, dirNames, cols);
                    }

                    successCount++;
                }
            }
            finally
            {
                EditorUtility.ClearProgressBar();
                AssetDatabase.SaveAssets();
                AssetDatabase.Refresh();
            }

            EditorUtility.DisplayDialog("处理完成", string.Format("批量切图与中心点设置完成！\n成功处理: {0} / {1} 个纹理。\n所有中心点已按指定分类规则配置完毕。", successCount, total), "确定");
        }

        private void GenerateDirectionClips(string texturePath, string texName, string[] dirNames, int cols)
        {
            string folder = Path.GetDirectoryName(texturePath) + "/Animations/" + texName;
            if (!Directory.Exists(folder))
            {
                Directory.CreateDirectory(folder);
                AssetDatabase.Refresh();
            }

            UnityEngine.Object[] objects = AssetDatabase.LoadAllAssetsAtPath(texturePath);
            Dictionary<string, Sprite> spriteMap = new Dictionary<string, Sprite>();
            foreach (var obj in objects)
            {
                if (obj is Sprite sp)
                {
                    spriteMap[sp.name] = sp;
                }
            }

            for (int r = 0; r < dirNames.Length; r++)
            {
                string dir = dirNames[r];
                List<Sprite> frames = new List<Sprite>();
                for (int c = 0; c < cols; c++)
                {
                    string frameName = string.Format("{0}_{1}_{2}", texName, dir, c);
                    if (spriteMap.ContainsKey(frameName))
                    {
                        frames.Add(spriteMap[frameName]);
                    }
                }

                if (frames.Count == 0) continue;

                string clipPath = folder + "/" + texName + "_walk_" + dir + ".anim";
                AnimationClip clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(clipPath);
                if (clip == null)
                {
                    clip = new AnimationClip();
                    AssetDatabase.CreateAsset(clip, clipPath);
                }

                clip.frameRate = 6;
                EditorCurveBinding binding = new EditorCurveBinding();
                binding.type = typeof(SpriteRenderer);
                binding.path = "";
                binding.propertyName = "m_Sprite";

                ObjectReferenceKeyframe[] keyframes = new ObjectReferenceKeyframe[frames.Count];
                for (int f = 0; f < frames.Count; f++)
                {
                    keyframes[f] = new ObjectReferenceKeyframe();
                    keyframes[f].time = (float)f / clip.frameRate;
                    keyframes[f].value = frames[f];
                }

                AnimationUtility.SetObjectReferenceCurve(clip, binding, keyframes);
                AnimationClipSettings settings = AnimationUtility.GetAnimationClipSettings(clip);
                settings.loopTime = true;
                AnimationUtility.SetAnimationClipSettings(clip, settings);

                EditorUtility.SetDirty(clip);
            }
        }
    }
}
#endif
