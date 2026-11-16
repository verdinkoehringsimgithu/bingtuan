using System;
using System.IO;
using UnityEngine;

namespace LegionBattle.Battle
{
    [Serializable]
    public class FormationConfig
    {
        [Header("第一排第一位基准点 (行0, 列0)")]
        [Tooltip("左军第1排第1位X坐标")]
        public float leftOriginX = -4.941988f;

        [Tooltip("两军第1排第1位Y坐标")]
        public float originY = 1.4498f;

        [Tooltip("右军第1排第1位X坐标")]
        public float rightOriginX = 0.1764596f;

        [Header("间距配置 (横向与纵向分开调节)")]
        [Tooltip("横向间距 (相邻列之间的距离)")]
        public float spacingX = 0.6536527f;

        [Tooltip("纵向间距 (相邻行之间的距离)")]
        public float spacingY = 0.9947705f;

        [Tooltip("奇数行横向交错偏移量")]
        public float rowStaggerX = 0.0f;

        public float ArmyDistance
        {
            get => rightOriginX - leftOriginX;
            set
            {
                float mid = (leftOriginX + rightOriginX) * 0.5f;
                float half = Mathf.Max(0.5f, value) * 0.5f;
                leftOriginX = mid - half;
                rightOriginX = mid + half;
            }
        }

#if UNITY_EDITOR
        private static string validationDirectory;
        public static void UseValidationDirectory(string path) { validationDirectory = path; }
#endif

        public static string GetConfigFilePath()
        {
#if UNITY_EDITOR
            if (validationDirectory != null) return Path.Combine(validationDirectory, "FormationConfig.json");
            return Path.Combine(Application.dataPath, "Characters/FormationConfig.json");
#else
            return Path.Combine(Application.persistentDataPath, "FormationConfig.json");
#endif
        }

        public static string GetResourcesFilePath()
        {
#if UNITY_EDITOR
            if (validationDirectory != null) return Path.Combine(validationDirectory, "FormationConfig.resources.json");
            return Path.Combine(Application.dataPath, "Resources/FormationConfig.json");
#else
            return Path.Combine(Application.persistentDataPath, "FormationConfig.json");
#endif
        }

        public static string GetAutoSaveFilePath()
        {
#if UNITY_EDITOR
            if (validationDirectory != null) return Path.Combine(validationDirectory, "FormationConfig.autosave.json");
            return Path.Combine(Path.GetDirectoryName(Application.dataPath), "UserSettings/FormationConfig.autosave.json");
#else
            return Path.Combine(Application.persistentDataPath, "FormationConfig.autosave.json");
#endif
        }

        private static string lastPersistedJson;

        public static FormationConfig Load()
        {
            var candidates = new System.Collections.Generic.List<string> {
                GetConfigFilePath(),
                GetAutoSaveFilePath(),
                GetConfigFilePath() + ".bak",
                GetAutoSaveFilePath() + ".bak",
                GetResourcesFilePath()
            };
            candidates.RemoveAll(x => string.IsNullOrEmpty(x) || !File.Exists(x));
            candidates.Sort((a, b) => File.GetLastWriteTimeUtc(b).CompareTo(File.GetLastWriteTimeUtc(a)));
            foreach (var path in candidates)
            {
                try
                {
                    string json = File.ReadAllText(path);
                    FormationConfig cfg = JsonUtility.FromJson<FormationConfig>(json);
                    if (cfg != null && cfg.spacingX > 0f && cfg.spacingY > 0f)
                    {
                        lastPersistedJson = JsonUtility.ToJson(cfg);
                        return cfg;
                    }
                }
                catch (Exception ex)
                {
                    Debug.LogWarning("尝试加载阵列配置副本失败: " + path + " · " + ex.Message);
                }
            }
            try
            {
                TextAsset packaged = Resources.Load<TextAsset>("FormationConfig");
                if (packaged != null)
                {
                    FormationConfig cfg = JsonUtility.FromJson<FormationConfig>(packaged.text);
                    if (cfg != null)
                    {
                        lastPersistedJson = JsonUtility.ToJson(cfg);
                        return cfg;
                    }
                }
            }
            catch { }
            return new FormationConfig();
        }

        public void Save()
        {
            try
            {
                string json = JsonUtility.ToJson(this, true);
                AtomicWrite(GetConfigFilePath(), json);
                string resPath = GetResourcesFilePath();
                if (!string.IsNullOrEmpty(resPath) && resPath != GetConfigFilePath())
                {
                    AtomicWrite(resPath, json);
                }
                AutoSaveIfChanged();
                lastPersistedJson = JsonUtility.ToJson(this);
#if UNITY_EDITOR
                if (validationDirectory == null)
                {
                    UnityEditor.AssetDatabase.Refresh();
                }
#endif
                Debug.Log(string.Format("阵列配置已保存：左X={0:F2}, Y={1:F2}, 右X={2:F2}, 间距={3:F2}, 两军原点差={4:F2}",
                    leftOriginX, originY, rightOriginX, spacingX, ArmyDistance));
            }
            catch (Exception ex)
            {
                Debug.LogError("保存阵列配置失败: " + ex.Message);
            }
        }

        public bool AutoSaveIfChanged()
        {
            try
            {
                string json = JsonUtility.ToJson(this);
                if (json == lastPersistedJson) return false;
                AtomicWrite(GetAutoSaveFilePath(), JsonUtility.ToJson(this, true));
                lastPersistedJson = json;
                return true;
            }
            catch (Exception ex)
            {
                Debug.LogWarning("自动保存阵列配置失败: " + ex.Message);
                return false;
            }
        }

        private static void AtomicWrite(string path, string json)
        {
            if (string.IsNullOrEmpty(path)) return;
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            string temporary = path + ".tmp";
            File.WriteAllText(temporary, json);
            if (File.Exists(path))
            {
                bool valid;
                try
                {
                    var parsed = JsonUtility.FromJson<FormationConfig>(File.ReadAllText(path));
                    valid = parsed != null && parsed.spacingX > 0f;
                }
                catch { valid = false; }
                File.Replace(temporary, path, valid ? path + ".bak" : null);
            }
            else
            {
                File.Move(temporary, path);
            }
        }
    }
}
