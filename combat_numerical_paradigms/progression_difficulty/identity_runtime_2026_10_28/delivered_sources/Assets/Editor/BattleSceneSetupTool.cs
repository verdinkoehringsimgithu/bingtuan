#if UNITY_EDITOR
using System;
using System.IO;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.SceneManagement;
using LegionBattle.Battle;

namespace LegionBattle.EditorTools
{
    public static class BattleSceneSetupTool
    {
        private const string ScenePath = "Assets/Scenes/BattleInspectionScene.unity";
        private const string DatabasePath = "Assets/Characters/CharacterDatabase.asset";
        private const string ShadowSpritePath = "Assets/Characters/GroundShadow.png";

        [MenuItem("Tools/一键生成战斗审阅场景")]
        public static void GenerateBattleInspectionScene()
        {
            // 1. 扫描并构建角色数据库 ScriptableObject (零运行时文件查找开销)
            CharacterDatabase db = BuildCharacterDatabase();
            if (db == null || db.characters.Count == 0)
            {
                EditorUtility.DisplayDialog("提示", "未找到任何角色切片资源，请确认 Assets/Characters 目录下已导入角色并完成切图。", "确定");
                return;
            }

            // 加载脚底阴影精灵
            Sprite shadowSprite = AssetDatabase.LoadAssetAtPath<Sprite>(ShadowSpritePath);

            // 2. 创建或重置全新战斗场景
            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            // 3. 配置 16:9 横屏正交摄像机
            GameObject camObj = new GameObject("Main Camera");
            camObj.tag = "MainCamera";
            camObj.transform.position = new Vector3(0, 0, -10f);
            Camera cam = camObj.AddComponent<Camera>();
            cam.orthographic = true;
            cam.orthographicSize = 5.2f;
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.12f, 0.13f, 0.16f, 1f);
            cam.transparencySortMode = TransparencySortMode.CustomAxis;
            cam.transparencySortAxis = new Vector3(0, 1, 0);
            camObj.AddComponent<AudioListener>();

            // 4. 构建左右阵营根节点与 60 个预置点位
            GameObject battleRoot = new GameObject("BattleField");
            GameObject leftRoot = new GameObject("LeftFormation");
            leftRoot.transform.SetParent(battleRoot.transform);

            GameObject rightRoot = new GameObject("RightFormation");
            rightRoot.transform.SetParent(battleRoot.transform);

            BattleCharacterPreview[] leftSlots = new BattleCharacterPreview[30];
            BattleCharacterPreview[] rightSlots = new BattleCharacterPreview[30];

            // 读取已保存的阵列间距与点位配置 (支持游戏模式调节并记录持久化)
            FormationConfig formation = FormationConfig.Load();

            // 预置点位矩阵：5行 x 6列 = 30点位 (左右对称)
            // 第一排第一个位置为基准点，横竖间距分开配置，奇数行交错
            for (int i = 0; i < 30; i++)
            {
                int row = i % 5; // 0..4
                int col = i / 5; // 0..5

                float xOffset = col * formation.spacingX + (row % 2 == 1 ? formation.rowStaggerX : 0f);
                float y = formation.originY - row * formation.spacingY;

                // 越靠下（Y越小）层级越前，每单位 Y 深度划 200 级，同行内加微偏移打破同级
                int baseOrder = Mathf.RoundToInt((10f - y) * 200f);
                int orderL = baseOrder + col * 2;
                int orderR = baseOrder + (5 - col) * 2;

                // --- 左军槽位 ---
                float xL = formation.leftOriginX + xOffset;

                GameObject slotL = new GameObject(string.Format("Slot_L_{0:D2}", i));
                slotL.transform.SetParent(leftRoot.transform);
                slotL.transform.position = new Vector3(xL, y, 0f);

                GameObject shL = null;
                // 脚底接触点阴影标志
                if (shadowSprite != null)
                {
                    shL = new GameObject("Shadow");
                    shL.transform.SetParent(slotL.transform);
                    shL.transform.localPosition = Vector3.zero; // 正好在落地中心点
                    shL.transform.localScale = new Vector3(1.2f, 0.6f, 1f);
                    SpriteRenderer srSh = shL.AddComponent<SpriteRenderer>();
                    srSh.sprite = shadowSprite;
                    srSh.sortingOrder = orderL - 1;
                }

                SpriteRenderer srL = slotL.AddComponent<SpriteRenderer>();
                srL.sortingOrder = orderL;
                BattleCharacterPreview prevL = slotL.AddComponent<BattleCharacterPreview>();
                prevL.Init(srL, shL);
                leftSlots[i] = prevL;

                // --- 右军槽位 ---
                float xR = formation.rightOriginX + xOffset;

                GameObject slotR = new GameObject(string.Format("Slot_R_{0:D2}", i));
                slotR.transform.SetParent(rightRoot.transform);
                slotR.transform.position = new Vector3(xR, y, 0f);

                GameObject shR = null;
                if (shadowSprite != null)
                {
                    shR = new GameObject("Shadow");
                    shR.transform.SetParent(slotR.transform);
                    shR.transform.localPosition = Vector3.zero;
                    shR.transform.localScale = new Vector3(1.2f, 0.6f, 1f);
                    SpriteRenderer srSh = shR.AddComponent<SpriteRenderer>();
                    srSh.sprite = shadowSprite;
                    srSh.sortingOrder = orderR - 1;
                }

                SpriteRenderer srR = slotR.AddComponent<SpriteRenderer>();
                srR.sortingOrder = orderR;
                BattleCharacterPreview prevR = slotR.AddComponent<BattleCharacterPreview>();
                prevR.Init(srR, shR);
                rightSlots[i] = prevR;
            }

            // 5. 构建 UI 界面 (Canvas，适配 1920x1080 横屏)
            GameObject canvasObj = new GameObject("Canvas");
            Canvas canvas = canvasObj.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            CanvasScaler scaler = canvasObj.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920, 1080);
            scaler.matchWidthOrHeight = 0.5f;
            canvasObj.AddComponent<GraphicRaycaster>();

            GameObject esObj = new GameObject("EventSystem");
            UnityEngine.EventSystems.EventSystem es = esObj.AddComponent<UnityEngine.EventSystems.EventSystem>();
            es.sendNavigationEvents = false;
            esObj.AddComponent<UnityEngine.EventSystems.StandaloneInputModule>();

            // 顶部操作栏
            GameObject panelObj = new GameObject("ControlBar");
            panelObj.transform.SetParent(canvasObj.transform, false);
            RectTransform panelRect = panelObj.AddComponent<RectTransform>();
            panelRect.anchorMin = new Vector2(0.5f, 1f);
            panelRect.anchorMax = new Vector2(0.5f, 1f);
            panelRect.pivot = new Vector2(0.5f, 1f);
            panelRect.anchoredPosition = new Vector2(0, -20);
            panelRect.sizeDelta = new Vector2(900, 60);

            Image panelImg = panelObj.AddComponent<Image>();
            panelImg.color = new Color(0.12f, 0.14f, 0.18f, 0.9f);

            Font defaultFont = GetDefaultFont();

            // 上一波按钮
            GameObject btnPrevObj = CreateUIButton("BtnPrev", panelObj.transform, new Vector2(-280, 0), new Vector2(130, 46), "上一波", defaultFont);
            Button btnPrev = btnPrevObj.GetComponent<Button>();

            // 波次文本
            GameObject txtInfoObj = new GameObject("TxtWaveInfo");
            txtInfoObj.transform.SetParent(panelObj.transform, false);
            RectTransform txtInfoRect = txtInfoObj.AddComponent<RectTransform>();
            txtInfoRect.anchoredPosition = new Vector2(0, 0);
            txtInfoRect.sizeDelta = new Vector2(400, 46);
            Text txtInfo = txtInfoObj.AddComponent<Text>();
            if (defaultFont != null) txtInfo.font = defaultFont;
            txtInfo.fontSize = 24;
            txtInfo.alignment = TextAnchor.MiddleCenter;
            txtInfo.color = Color.white;
            txtInfo.text = "第 1 / 21 波";
            txtInfo.raycastTarget = false;

            // 下一波按钮
            GameObject btnNextObj = CreateUIButton("BtnNext", panelObj.transform, new Vector2(280, 0), new Vector2(130, 46), "下一波", defaultFont);
            Button btnNext = btnNextObj.GetComponent<Button>();

            // 底部操作指引文本
            GameObject tipObj = new GameObject("TxtTip");
            tipObj.transform.SetParent(canvasObj.transform, false);
            RectTransform tipRect = tipObj.AddComponent<RectTransform>();
            tipRect.anchorMin = new Vector2(0.5f, 0f);
            tipRect.anchorMax = new Vector2(0.5f, 0f);
            tipRect.pivot = new Vector2(0.5f, 0f);
            tipRect.anchoredPosition = new Vector2(0, 20);
            tipRect.sizeDelta = new Vector2(850, 40);
            Text txtTip = tipObj.AddComponent<Text>();
            if (defaultFont != null) txtTip.font = defaultFont;
            txtTip.fontSize = 20;
            txtTip.alignment = TextAnchor.MiddleCenter;
            txtTip.color = new Color(0.75f, 0.78f, 0.85f, 1f);
            txtTip.text = "空格推进战斗 | F2配置阶段与阵容 | ← 上一波，→ 下一波 (支持 A/D、Q/E)";
            txtTip.raycastTarget = false;

            // 6. 战力与血条系统 UI (BattleHealthBarUI)
            GameObject healthBarObj = new GameObject("BattleHealthBarUI");
            healthBarObj.transform.SetParent(canvasObj.transform, false);
            BattleHealthBarUI healthBarUI = healthBarObj.AddComponent<BattleHealthBarUI>();
            healthBarUI.EnsureUIBuilt();

            // 7. 配置 BattleInspectionManager 控制器
            GameObject managerObj = new GameObject("BattleInspectionManager");
            BattleInspectionManager manager = managerObj.AddComponent<BattleInspectionManager>();
            manager.Configure(db, leftSlots, rightSlots, btnNext, btnPrev, txtInfo, healthBarUI);

            // 在编辑器下直接刷入第 1 波角色，确保无需运行也能在 Scene/Game 视窗立即查看
            manager.ApplyWave(0);

            // 标记脏数据确保场景完全保存
            EditorUtility.SetDirty(manager);
            for (int i = 0; i < 30; i++)
            {
                if (leftSlots[i] != null) EditorUtility.SetDirty(leftSlots[i]);
                if (rightSlots[i] != null) EditorUtility.SetDirty(rightSlots[i]);
            }

            // 7. 保存场景并切换打开
            string scenesDir = Path.GetDirectoryName(ScenePath);
            if (!Directory.Exists(scenesDir))
            {
                Directory.CreateDirectory(scenesDir);
            }

            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene, ScenePath);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();

            EditorSceneManager.OpenScene(ScenePath);

            EditorUtility.DisplayDialog("生成成功", 
                string.Format("战斗审阅场景已成功生成！\n\n场景路径：{0}\n收录角色：{1} 个 (共 {2} 波)\n预置槽位：左30人 + 右30人\n\n已自动保存并打开该场景，点击 Unity 顶部的 Play 按钮即可直接开始审阅。",
                ScenePath, db.characters.Count, manager.TotalWaves), 
                "确定");
        }

        [MenuItem("Tools/重新扫描并构建角色数据库")]
        public static void RebuildCharacterDatabaseMenu()
        {
            BuildCharacterDatabase(true);
            EditorUtility.DisplayDialog("提示", "角色数据库已成功重新扫描构建！", "确定");
        }

        public static CharacterDatabase BuildCharacterDatabase(bool forceRebuild = true)
        {
            string dbFolder = Path.GetDirectoryName(DatabasePath);
            if (!Directory.Exists(dbFolder))
            {
                Directory.CreateDirectory(dbFolder);
            }

            CharacterDatabase db = AssetDatabase.LoadAssetAtPath<CharacterDatabase>(DatabasePath);
            if (!forceRebuild && db != null && db.characters != null && db.characters.Count > 0)
            {
                CharacterTraitsImporter.Refresh(db);
                return db;
            }

            if (db == null)
            {
                db = ScriptableObject.CreateInstance<CharacterDatabase>();
                AssetDatabase.CreateAsset(db, DatabasePath);
            }

            if (forceRebuild)
            {
                AssetDatabase.Refresh();
            }

            db.characters.Clear();

            string[] guids = AssetDatabase.FindAssets("t:Texture2D", new string[] { "Assets/Characters" });
            Array.Sort(guids, (a, b) => string.Compare(AssetDatabase.GUIDToAssetPath(a), AssetDatabase.GUIDToAssetPath(b), StringComparison.OrdinalIgnoreCase));

            for (int i = 0; i < guids.Length; i++)
            {
                string path = AssetDatabase.GUIDToAssetPath(guids[i]);
                if (!path.EndsWith(".png", StringComparison.OrdinalIgnoreCase)) continue;
                if (path.EndsWith("GroundShadow.png", StringComparison.OrdinalIgnoreCase)) continue;

                UnityEngine.Object[] assets = AssetDatabase.LoadAllAssetsAtPath(path);
                if (assets == null || assets.Length <= 1) continue;

                string texName = Path.GetFileNameWithoutExtension(path);
                Dictionary<string, Sprite> map = new Dictionary<string, Sprite>();

                for (int j = 0; j < assets.Length; j++)
                {
                    if (assets[j] is Sprite sp)
                    {
                        map[sp.name] = sp;
                    }
                }

                CharacterSheetData sheet = new CharacterSheetData();
                sheet.characterName = texName;

                string parentDir = Path.GetFileName(Path.GetDirectoryName(path));
                int rVal;
                if (int.TryParse(parentDir, out rVal) && rVal >= 1 && rVal <= 6)
                {
                    sheet.rarity = rVal;
                }
                else
                {
                    sheet.rarity = 3;
                }

                for (int c = 0; c < 4; c++)
                {
                    sheet.downFrames[c] = GetSprite(map, texName, "down", c);
                    sheet.leftFrames[c] = GetSprite(map, texName, "left", c);
                    sheet.rightFrames[c] = GetSprite(map, texName, "right", c);
                    sheet.upFrames[c] = GetSprite(map, texName, "up", c);
                }

                // 3 帧向 4 帧优雅回退处理 (第四帧回退到第二帧 Stand 姿态)
                if (sheet.downFrames[3] == null && sheet.downFrames[1] != null) sheet.downFrames[3] = sheet.downFrames[1];
                if (sheet.leftFrames[3] == null && sheet.leftFrames[1] != null) sheet.leftFrames[3] = sheet.leftFrames[1];
                if (sheet.rightFrames[3] == null && sheet.rightFrames[1] != null) sheet.rightFrames[3] = sheet.rightFrames[1];
                if (sheet.upFrames[3] == null && sheet.upFrames[1] != null) sheet.upFrames[3] = sheet.upFrames[1];

                if (sheet.IsValid)
                {
                    db.characters.Add(sheet);
                }
            }

            EditorUtility.SetDirty(db);
            AssetDatabase.SaveAssetIfDirty(db);
            CharacterTraitsImporter.Refresh(db);
            return db;
        }

        private static Sprite GetSprite(Dictionary<string, Sprite> map, string texName, string dir, int col)
        {
            string key = string.Format("{0}_{1}_{2}", texName, dir, col);
            if (map.ContainsKey(key)) return map[key];

            foreach (var kv in map)
            {
                if (kv.Key.EndsWith("_" + dir + "_" + col))
                {
                    return kv.Value;
                }
            }
            return null;
        }

        private static GameObject CreateUIButton(string name, Transform parent, Vector2 pos, Vector2 size, string textStr, Font font)
        {
            GameObject btnObj = new GameObject(name);
            btnObj.transform.SetParent(parent, false);

            RectTransform rt = btnObj.AddComponent<RectTransform>();
            rt.anchoredPosition = pos;
            rt.sizeDelta = size;

            Image img = btnObj.AddComponent<Image>();
            img.color = new Color(0.24f, 0.28f, 0.36f, 1f);

            Button btn = btnObj.AddComponent<Button>();
            btn.navigation = new Navigation { mode = Navigation.Mode.None };
            ColorBlock cb = btn.colors;
            cb.highlightedColor = new Color(0.35f, 0.42f, 0.55f, 1f);
            cb.pressedColor = new Color(0.18f, 0.22f, 0.30f, 1f);
            btn.colors = cb;

            GameObject txtObj = new GameObject("Text");
            txtObj.transform.SetParent(btnObj.transform, false);
            RectTransform txtRt = txtObj.AddComponent<RectTransform>();
            txtRt.anchorMin = Vector2.zero;
            txtRt.anchorMax = Vector2.one;
            txtRt.sizeDelta = Vector2.zero;

            Text txt = txtObj.AddComponent<Text>();
            if (font != null) txt.font = font;
            txt.fontSize = 20;
            txt.alignment = TextAnchor.MiddleCenter;
            txt.color = Color.white;
            txt.text = textStr;
            txt.raycastTarget = false;

            return btnObj;
        }

        private static Font GetDefaultFont()
        {
            Font font = null;
            try
            {
                font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            }
            catch { }

            if (font == null)
            {
                try
                {
                    font = Resources.GetBuiltinResource<Font>("Arial.ttf");
                }
                catch { }
            }

            if (font == null)
            {
                try
                {
                    font = Font.CreateDynamicFontFromOSFont("Arial", 16);
                }
                catch { }
            }

            return font;
        }
    }
}
#endif
