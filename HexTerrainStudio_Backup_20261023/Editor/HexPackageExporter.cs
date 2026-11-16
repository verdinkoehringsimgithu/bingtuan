using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace HexTerrainStudio
{
    /// <summary>
    /// HexTerrainStudio 独立发布与一键打包工具
    /// 自动追踪核心算法脚本、编辑器扩展、沙盘预设、JSON 地图数据及六角底板/三山核心模型资产
    /// </summary>
    public static class HexPackageExporter
    {
        private const string TriggerFile = "Assets/HexTerrainStudio/Editor/.trigger_export";

        [InitializeOnLoadMethod]
        private static void OnEditorLoad()
        {
            if (File.Exists(TriggerFile))
            {
                try
                {
                    File.Delete(TriggerFile);
                }
                catch {}
                EditorApplication.delayCall += () => ExportPackage(false);
            }
        }

        [MenuItem("Tools/Hex Terrain/★ 打包导出 HexTerrainStudio (.unitypackage) ★", priority = 300)]
        public static void MenuExport()
        {
            ExportPackage(true);
        }

        public static string ExportPackage(bool showDialog = true)
        {
            // 1. 核心导出资产目录
            var assetPaths = new List<string>
            {
                "Assets/HexTerrainStudio",
                "Assets/AssetRaw/GameAssets/Hexagon"
            };

            // 2. 校验路径存在性
            var validPaths = new List<string>();
            foreach (var p in assetPaths)
            {
                if (AssetDatabase.IsValidFolder(p) || File.Exists(p))
                {
                    validPaths.Add(p);
                }
            }

            // 3. 确定导出目标路径（优先输出到工作区 D:\123）
            string packageFileName = "HexTerrainStudio_v1.0.unitypackage";
            string targetDir = @"D:\123";
            if (!Directory.Exists(targetDir))
            {
                targetDir = Path.GetFullPath(Path.Combine(Application.dataPath, "../../"));
            }

            string primaryPath = Path.Combine(targetDir, packageFileName);
            string backupPath = Path.GetFullPath(Path.Combine(Application.dataPath, "../" + packageFileName));

            // 4. 执行 UnityPackage 打包 (递归 + 包含依赖)
            ExportPackageOptions options = ExportPackageOptions.Recurse | ExportPackageOptions.IncludeDependencies;
            AssetDatabase.ExportPackage(validPaths.ToArray(), primaryPath, options);

            // 5. 双重备份
            try
            {
                if (Path.GetFullPath(primaryPath) != Path.GetFullPath(backupPath))
                {
                    File.Copy(primaryPath, backupPath, true);
                }
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[HexPackageExporter] 备份至工程目录失败: {ex.Message}");
            }

            Debug.Log($"[HexPackageExporter] ★ 打包完成！UnityPackage 成功生成至:\n- 主路径: {primaryPath}\n- 备份路径: {backupPath}");

            if (showDialog)
            {
                EditorUtility.RevealInFinder(primaryPath);
                EditorUtility.DisplayDialog(
                    "打包导出成功",
                    $"HexTerrainStudio 已成功打包为 UnityPackage！\n\n文件保存路径:\n{primaryPath}\n\n包含内容:\n- 31*35 平顶六角宏观沙盘生成器全套代码\n- 地幔板块构造河流 + 12座旋转山脉 + 惠特克双变量气候\n- 100 阵营均衡分布与 4~7 格区域生长算法\n- 三层笔刷与关卡地图编辑器窗口及预设场景\n- 完整六角底板、Yama1/2/3模型与PBR材质\n- 详细使用说明文档 (使用说明.md)",
                    "确定"
                );
            }
            else
            {
                EditorUtility.RevealInFinder(primaryPath);
            }

            return primaryPath;
        }
    }
}
