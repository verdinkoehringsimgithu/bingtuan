using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEditor;

namespace HexTerrainStudio
{
    public class HexMapEditorWindow : EditorWindow
    {
        private enum ToolMode { Paint, Erase }
        private enum ActiveLayer { Layer1_Base, Layer2_Hill, Layer3_Attachment }

        [SerializeField] private ToolMode _mode = ToolMode.Paint;
        [SerializeField] private ActiveLayer _activeLayer = ActiveLayer.Layer1_Base;

        // Grid Settings (Default 31*35)
        [SerializeField] private int _columns = 35;
        [SerializeField] private int _rows = 31;
        [SerializeField] private float _hexRadius = 2.5f;

        // Brush Settings
        [SerializeField] private int _brushRadius = 1;
        [SerializeField] private bool _randomRotation = true;
        [SerializeField] private Vector2 _scaleRange = new Vector2(0.9f, 1.15f);
        [SerializeField] private int _scatterCount = 2; // attachments per hex

        // Palettes
        private static readonly string[] BaseMaterials = { "Hexagon", "Sand", "Hexagon 1", "Hexagon 2", "Hexagon 3", "C" };
        private static readonly string[] HillPrefabs = { "Yama1", "Yama2", "Yama3" };

        private static readonly string[] TreePrefabs = {
            "Pine_01", "Pine_02", "Pine_03", "Pine_04", "Pine_05", "Fir_01",
            "Spruce_Tree1", "Spruce_Tree2", "Spruce_Tree3", "Tree Birch", "Tree Maple", "Acacia"
        };
        private static readonly string[] RockPrefabs = {
            "Rock_01", "Rock_02", "Rock_03", "Rock_04",
            "Rock_small_01", "Rock_small_02", "Rock_small_03", "Rock_small_04",
            "Boulder_Group_1A1", "Boulder_Group_1A2", "Forest_stone_2", "Forest_stone_4"
        };
        private static readonly string[] CropPrefabs = {
            "Wheat_03a", "Carrot_03", "Potato_03",
            "Fern_A", "Fern_B", "Bush_Red", "BushDry_B", "Mushroom_01", "Mushroom_02"
        };
        private static readonly string[] MountainPrefabs = {
            "M4", "M4 Variant", "Snow_mountain_t1_4", "Snow_mountain_t2_3", "Mountain_01", "Mountain_03"
        };

        private int _selectedBaseMatIndex = 0;
        private int _selectedHillIndex = 0;
        private int _selectedAttachmentCategory = 0; // 0=Tree, 1=Rock, 2=Crops, 3=Mountain
        private int _selectedAttachmentIndex = 0;

        // Procedural Generation Settings
        private bool _showProceduralSection = true;
        private bool _showCapitalGizmos = true;
        private int _procSeed = 12345;
        private int _procFactions = 100;

        private HexMapSpawner _spawner;
        private string _mapFileName = "Map_01";
        private Vector2 _scrollPos;

        private const string MapsFolder = "Assets/HexTerrainStudio/Maps";

        [MenuItem("Tools/Hex Terrain/Hex Map Editor Window")]
        public static void ShowWindow()
        {
            var win = GetWindow<HexMapEditorWindow>("Hex Map Editor");
            win.minSize = new Vector2(360, 600);
            win.Show();
        }

        private void OnEnable()
        {
            SceneView.duringSceneGui += OnSceneGUI;
            FindOrCreateSpawner();
        }

        private void OnDisable()
        {
            SceneView.duringSceneGui -= OnSceneGUI;
        }

        private void FindOrCreateSpawner()
        {
            if (_spawner == null)
            {
                _spawner = FindObjectOfType<HexMapSpawner>();
                if (_spawner == null)
                {
                    var go = new GameObject("HexMapRoot");
                    _spawner = go.AddComponent<HexMapSpawner>();
                    _spawner.EnsureHierarchy();
                    Undo.RegisterCreatedObjectUndo(go, "Create HexMapRoot");
                }
            }
        }

        private void OnGUI()
        {
            FindOrCreateSpawner();
            _scrollPos = EditorGUILayout.BeginScrollView(_scrollPos);

            EditorGUILayout.Space(6);
            EditorGUILayout.LabelField("3-Layer Hex Terrain Studio", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox("31*35 六边形笔刷地形编辑器 (三层架构：基底 -> 丘陵 -> 附着物/山体)", MessageType.Info);

            EditorGUILayout.Space(4);
            DrawProceduralSection();

            EditorGUILayout.Space(6);
            DrawGridSection();

            EditorGUILayout.Space(6);
            DrawToolSection();

            EditorGUILayout.Space(6);
            DrawLayerPaletteSection();

            EditorGUILayout.Space(6);
            DrawBrushSettingsSection();

            EditorGUILayout.Space(8);
            DrawFileIOSection();

            EditorGUILayout.EndScrollView();
        }

        private void DrawProceduralSection()
        {
            _showProceduralSection = EditorGUILayout.Foldout(_showProceduralSection, "★ 程序化宏观沙盘生成 (100阵营 + 河流镂空 + 三山气候)", true, EditorStyles.foldoutHeader);
            if (!_showProceduralSection) return;

            EditorGUILayout.BeginVertical("box");
            EditorGUILayout.HelpBox("管线：1.水系网络(自然划分为7~10个独立陆地板块) -> 2.全图山系(雪山/暗岩/青翠山脊) -> 3.2D相干多频噪声群系(无条纹波浪) -> 4.跨板块均衡100阵营(4~7格) -> 5.聚集生态林与石群", MessageType.None);

            EditorGUILayout.BeginHorizontal();
            _procSeed = EditorGUILayout.IntField("随机种子 (Seed)", _procSeed);
            if (GUILayout.Button("随机", GUILayout.Width(50)))
            {
                _procSeed = UnityEngine.Random.Range(1000, 999999);
            }
            EditorGUILayout.EndHorizontal();

            _procFactions = EditorGUILayout.IntSlider("阵营数量", _procFactions, 10, 100);
            _showCapitalGizmos = EditorGUILayout.Toggle("Scene 视图高亮 100 主城 (★)", _showCapitalGizmos);

            GUI.backgroundColor = new Color(0.3f, 0.85f, 0.45f);
            if (GUILayout.Button("★ 一键运行约束驱动程序化生成 ★", GUILayout.Height(34)))
            {
                RunProceduralGeneration();
            }
            GUI.backgroundColor = Color.white;

            EditorGUILayout.EndVertical();
        }

        private void RunProceduralGeneration()
        {
            FindOrCreateSpawner();
            var config = new HexProceduralGenerator.GenerationConfig
            {
                columns = _columns,
                rows = _rows,
                hexRadius = _hexRadius,
                seed = _procSeed,
                targetFactions = _procFactions,
                minTerritorySize = 4,
                maxTerritorySize = 7
            };

            var mapData = HexProceduralGenerator.Generate(config);
            _spawner.BuildMap(mapData);
            EditorUtility.SetDirty(_spawner);
            FocusMapCenter();
            SceneView.RepaintAll();

            EditorUtility.DisplayDialog("生成成功", $"31*35 沙盘生成完毕！\n- 随机种子: {_procSeed}\n- 阵营数量: {_procFactions}\n- 地表涵盖河流镂空、山脊走向、雪原/荒漠/草原气候带及比例校准后的附着物！", "确定");
        }

        private void DrawGridSection()
        {
            EditorGUILayout.LabelField("1. 网格参数 (31*35)", EditorStyles.boldLabel);
            EditorGUI.BeginChangeCheck();
            _columns = EditorGUILayout.IntField("网格列数 (Columns)", _columns);
            _rows = EditorGUILayout.IntField("网格行数 (Rows)", _rows);
            _hexRadius = EditorGUILayout.FloatField("六角半径 (Radius)", _hexRadius);

            EditorGUILayout.BeginHorizontal();
            if (GUILayout.Button("生成/初始化 31*35 基底网格", GUILayout.Height(28)))
            {
                InitBaseGrid();
            }
            if (GUILayout.Button("清空整张地图", GUILayout.Height(28)))
            {
                if (EditorUtility.DisplayDialog("确认清空", "确定清空当前地图所有模型吗？", "清空", "取消"))
                {
                    _spawner.ClearMap();
                }
            }
            EditorGUILayout.EndHorizontal();

            EditorGUILayout.BeginHorizontal();
            if (GUILayout.Button("视口对焦全图 (Focus Map)", GUILayout.Height(24)))
            {
                FocusMapCenter();
            }
            if (GUILayout.Button("一键配置最佳机位与阳光", GUILayout.Height(24)))
            {
                SetupCameraAndLight();
            }
            EditorGUILayout.EndHorizontal();
        }

        private void DrawToolSection()
        {
            EditorGUILayout.LabelField("2. 笔刷模式", EditorStyles.boldLabel);
            _mode = (ToolMode)GUILayout.Toolbar((int)_mode, new string[] { "笔刷绘制 (Paint)", "橡皮擦除 (Erase)" });

            EditorGUILayout.Space(4);
            EditorGUILayout.LabelField("当前激活图层 (Active Layer):", EditorStyles.boldLabel);
            _activeLayer = (ActiveLayer)GUILayout.Toolbar((int)_activeLayer, new string[] {
                "第1层: 基底", "第2层: 丘陵", "第3层: 附着物/山体"
            });
        }

        private void DrawLayerPaletteSection()
        {
            EditorGUILayout.LabelField("3. 模型与材质画板 (Palette)", EditorStyles.boldLabel);

            switch (_activeLayer)
            {
                case ActiveLayer.Layer1_Base:
                    EditorGUILayout.HelpBox("第 1 层：基底六边形网格地块（可切换材质）", MessageType.None);
                    _selectedBaseMatIndex = EditorGUILayout.Popup("地表材质", _selectedBaseMatIndex, BaseMaterials);
                    break;

                case ActiveLayer.Layer2_Hill:
                    EditorGUILayout.HelpBox("第 2 层：丘陵地貌（规则：只能放置在已有基底上）", MessageType.None);
                    _selectedHillIndex = EditorGUILayout.Popup("丘陵样式", _selectedHillIndex, HillPrefabs);
                    break;

                case ActiveLayer.Layer3_Attachment:
                    EditorGUILayout.HelpBox("第 3 层：附着物与山体（规则：可放置在基底或丘陵上）", MessageType.None);
                    _selectedAttachmentCategory = GUILayout.Toolbar(_selectedAttachmentCategory, new string[] {
                        "树木", "岩石", "作物/灌木", "大型山体"
                    });

                    string[] list = GetCurrentAttachmentList();
                    if (_selectedAttachmentIndex >= list.Length) _selectedAttachmentIndex = 0;
                    _selectedAttachmentIndex = EditorGUILayout.Popup("具体预制体", _selectedAttachmentIndex, list);
                    break;
            }
        }

        private string[] GetCurrentAttachmentList()
        {
            switch (_selectedAttachmentCategory)
            {
                case 0: return TreePrefabs;
                case 1: return RockPrefabs;
                case 2: return CropPrefabs;
                case 3: return MountainPrefabs;
                default: return TreePrefabs;
            }
        }

        private void DrawBrushSettingsSection()
        {
            EditorGUILayout.LabelField("4. 笔刷属性", EditorStyles.boldLabel);
            _brushRadius = EditorGUILayout.IntSlider("笔刷半径 (Radius)", _brushRadius, 1, 5);
            _randomRotation = EditorGUILayout.Toggle("随机 Y 轴旋转", _randomRotation);

            if (_activeLayer == ActiveLayer.Layer3_Attachment)
            {
                EditorGUILayout.MinMaxSlider("随机缩放区间", ref _scaleRange.x, ref _scaleRange.y, 0.5f, 2.0f);
                EditorGUILayout.LabelField($"缩放范围: [{_scaleRange.x:F2} ~ {_scaleRange.y:F2}]");
                if (_selectedAttachmentCategory != 3) // not mountain
                {
                    _scatterCount = EditorGUILayout.IntSlider("单格附着物数量", _scatterCount, 1, 4);
                }
            }
        }

        private void DrawFileIOSection()
        {
            EditorGUILayout.LabelField("5. 地图数据保存与导出 (JSON)", EditorStyles.boldLabel);
            _mapFileName = EditorGUILayout.TextField("地图数据名", _mapFileName);

            EditorGUILayout.BeginHorizontal();
            if (GUILayout.Button("导出当前地图为 JSON", GUILayout.Height(28)))
            {
                ExportCurrentMapToJson();
            }
            if (GUILayout.Button("导入/加载 JSON 地图", GUILayout.Height(28)))
            {
                ImportMapFromJson();
            }
            EditorGUILayout.EndHorizontal();

            EditorGUILayout.Space(4);
            GUI.backgroundColor = new Color(0.25f, 0.75f, 1f);
            if (GUILayout.Button("★ 一键打包导出 HexTerrainStudio (.unitypackage) ★", GUILayout.Height(30)))
            {
                HexPackageExporter.ExportPackage(true);
            }
            GUI.backgroundColor = Color.white;
        }

        private void InitBaseGrid()
        {
            FindOrCreateSpawner();
            var data = new HexMapData
            {
                mapName = _mapFileName,
                columns = _columns,
                rows = _rows,
                hexRadius = _hexRadius,
                tiles = new List<HexTileData>()
            };

            float dx = 1.5f * _hexRadius;
            float dz = Mathf.Sqrt(3f) * _hexRadius;

            for (int c = 0; c < _columns; c++)
            {
                float colOffset = (c % 2 == 1) ? (dz * 0.5f) : 0f;
                for (int r = 0; r < _rows; r++)
                {
                    float x = c * dx;
                    float z = r * dz + colOffset;
                    var tile = new HexTileData
                    {
                        col = c,
                        row = r,
                        x = x,
                        y = 0f,
                        z = z,
                        hasBase = true,
                        basePrefab = "Hexagon",
                        baseMaterial = BaseMaterials[_selectedBaseMatIndex],
                        hasHill = false,
                        attachments = new List<HexAttachmentData>()
                    };
                    data.tiles.Add(tile);
                }
            }

            _spawner.BuildMap(data);
            EditorUtility.SetDirty(_spawner);
            FocusMapCenter();
            SceneView.RepaintAll();
        }

        private void ExportCurrentMapToJson()
        {
            if (_spawner == null || _spawner.currentMapData == null)
            {
                EditorUtility.DisplayDialog("提示", "当前没有正在编辑的地图数据！", "确定");
                return;
            }

            if (!Directory.Exists(MapsFolder))
                Directory.CreateDirectory(MapsFolder);

            string path = Path.Combine(MapsFolder, _mapFileName + ".json");
            string json = JsonUtility.ToJson(_spawner.currentMapData, true);
            File.WriteAllText(path, json);
            AssetDatabase.Refresh();

            EditorUtility.DisplayDialog("导出成功", $"地图数据已导出到:\n{path}\n您可以将此 JSON 文件和 HexMapSpawner.cs 拷贝至其他工程使用！", "确定");
        }

        private void ImportMapFromJson()
        {
            string path = EditorUtility.OpenFilePanel("选择地图 JSON 文件", MapsFolder, "json");
            if (!string.IsNullOrEmpty(path) && File.Exists(path))
            {
                string json = File.ReadAllText(path);
                var data = JsonUtility.FromJson<HexMapData>(json);
                if (data != null)
                {
                    FindOrCreateSpawner();
                    _columns = data.columns;
                    _rows = data.rows;
                    _hexRadius = data.hexRadius;
                    _mapFileName = data.mapName;
                    _spawner.BuildMap(data);
                    FocusMapCenter();
                    SceneView.RepaintAll();
                }
            }
        }

        private void FocusMapCenter()
        {
            float dx = 1.5f * _hexRadius;
            float dz = Mathf.Sqrt(3f) * _hexRadius;
            float centerX = (_columns - 1) * dx * 0.5f;
            float centerZ = (_rows - 1) * dz * 0.5f;
            float sizeX = _columns * dx;
            float sizeZ = _rows * dz;

            Bounds bounds = new Bounds(new Vector3(centerX, 0f, centerZ), new Vector3(sizeX, 25f, sizeZ));
            if (SceneView.lastActiveSceneView != null)
            {
                SceneView.lastActiveSceneView.Frame(bounds, false);
            }
        }

        private void SetupCameraAndLight()
        {
            float dx = 1.5f * _hexRadius;
            float dz = Mathf.Sqrt(3f) * _hexRadius;
            float centerX = (_columns - 1) * dx * 0.5f;
            float centerZ = (_rows - 1) * dz * 0.5f;

            var cam = Camera.main;
            if (cam == null)
            {
                var camGo = new GameObject("Main Camera");
                cam = camGo.AddComponent<Camera>();
                camGo.tag = "MainCamera";
            }
            cam.transform.position = new Vector3(centerX, 70f, centerZ - 55f);
            cam.transform.rotation = Quaternion.Euler(52f, 0f, 0f);

            var light = FindObjectOfType<Light>();
            if (light == null || light.type != LightType.Directional)
            {
                var lightGo = new GameObject("Directional Light");
                light = lightGo.AddComponent<Light>();
                light.type = LightType.Directional;
            }
            light.intensity = 1.25f;
            light.shadows = LightShadows.Soft;
            light.transform.rotation = Quaternion.Euler(50f, -30f, 0f);

            EditorUtility.DisplayDialog("提示", "已为当前场景配置好俯瞰沙盘的最佳机位与阳光！", "确定");
        }

        // ================= SceneView Brush Interaction =================

        private void OnSceneGUI(SceneView sceneView)
        {
            FindOrCreateSpawner();
            if (_spawner == null) return;

            Event e = Event.current;
            Ray ray = HandleUtility.GUIPointToWorldRay(e.mousePosition);

            // Plane at Y=0
            Plane groundPlane = new Plane(Vector3.up, Vector3.zero);
            if (!groundPlane.Raycast(ray, out float enter)) return;
            Vector3 hitPoint = ray.GetPoint(enter);

            // Math to get nearest hex
            GetNearestHex(hitPoint, out int hitCol, out int hitRow);
            if (hitCol < 0 || hitCol >= _columns || hitRow < 0 || hitRow >= _rows) return;

            Vector3 hexCenter = GetHexCenter(hitCol, hitRow);

            // Draw Brush Gizmo in SceneView
            Handles.color = (_mode == ToolMode.Paint) ? new Color(0.2f, 0.9f, 0.3f, 0.6f) : new Color(0.9f, 0.2f, 0.2f, 0.6f);
            float brushVisualRadius = (_brushRadius - 0.5f) * Mathf.Sqrt(3f) * _hexRadius;
            Handles.DrawWireDisc(hexCenter, Vector3.up, Mathf.Max(brushVisualRadius, _hexRadius));

            // Draw Capitals if enabled
            if (_showCapitalGizmos && _spawner.currentMapData != null && _spawner.currentMapData.tiles != null)
            {
                Handles.color = new Color(1f, 0.2f, 0.8f, 0.8f);
                foreach (var t in _spawner.currentMapData.tiles)
                {
                    if (t.isCapital)
                    {
                        Vector3 capPos = new Vector3(t.x, 0.3f, t.z);
                        Handles.DrawWireDisc(capPos, Vector3.up, _hexRadius * 0.45f);
                    }
                }
            }

            // Highlight target hex
            Handles.color = Color.yellow;
            DrawHexWire(hexCenter, _hexRadius);

            // Handle painting on Left Click / Drag
            if ((e.type == EventType.MouseDown || e.type == EventType.MouseDrag) && e.button == 0 && !e.alt)
            {
                ApplyBrush(hitCol, hitRow);
                e.Use();
            }

            // Force repaint to make cursor follow mouse smoothly
            if (e.type == EventType.MouseMove)
            {
                sceneView.Repaint();
            }
        }

        private void ApplyBrush(int centerCol, int centerRow)
        {
            if (_spawner.currentMapData == null)
            {
                InitBaseGrid();
            }

            var mapData = _spawner.currentMapData;
            bool modified = false;

            for (int c = 0; c < _columns; c++)
            {
                for (int r = 0; r < _rows; r++)
                {
                    if (GetHexDistance(centerCol, centerRow, c, r) < _brushRadius)
                    {
                        var tile = mapData.GetTile(c, r);
                        if (tile == null) continue;

                        if (_mode == ToolMode.Paint)
                        {
                            modified |= PaintTile(tile);
                        }
                        else
                        {
                            modified |= EraseTile(tile);
                        }
                    }
                }
            }

            if (modified)
            {
                _spawner.BuildMap(mapData);
                EditorUtility.SetDirty(_spawner);
            }
        }

        private bool PaintTile(HexTileData tile)
        {
            switch (_activeLayer)
            {
                case ActiveLayer.Layer1_Base:
                    tile.hasBase = true;
                    tile.baseMaterial = BaseMaterials[_selectedBaseMatIndex];
                    return true;

                case ActiveLayer.Layer2_Hill:
                    if (!tile.hasBase) return false; // Rule: Hill can only be placed on Base
                    tile.hasHill = true;
                    tile.hillPrefab = HillPrefabs[_selectedHillIndex];
                    tile.hillRotY = _randomRotation ? (UnityEngine.Random.Range(0, 6) * 60f) : 0f;
                    return true;

                case ActiveLayer.Layer3_Attachment:
                    if (!tile.hasBase) return false; // Rule: Attachment can be placed on Base or Hill
                    string prefab = GetCurrentAttachmentList()[_selectedAttachmentIndex];

                    if (_selectedAttachmentCategory == 3) // Mountain
                    {
                        tile.attachments.Clear(); // Mountain dominates hex
                        var att = new HexAttachmentData
                        {
                            prefabName = prefab,
                            attachedLayer = tile.hasHill ? "Hill" : "Base",
                            localX = 0f,
                            localY = tile.hasHill ? 1.0f : 0f,
                            localZ = 0f,
                            worldX = tile.x,
                            worldY = tile.y + (tile.hasHill ? 1.0f : 0f),
                            worldZ = tile.z,
                            rotY = _randomRotation ? UnityEngine.Random.Range(0f, 360f) : 0f,
                            scaleX = 1f, scaleY = 1f, scaleZ = 1f
                        };
                        Quaternion q = Quaternion.Euler(0f, att.rotY, 0f);
                        att.rotX = q.x; att.rotY = q.y; att.rotZ = q.z; att.rotW = q.w;
                        tile.attachments.Add(att);
                    }
                    else // Scatter tree / rock / foliage
                    {
                        if (tile.attachments.Count >= 6) return false;
                        for (int i = 0; i < _scatterCount; i++)
                        {
                            float angle = UnityEngine.Random.Range(0f, Mathf.PI * 2f);
                            float dist = UnityEngine.Random.Range(0.2f, _hexRadius * 0.65f);
                            float lx = Mathf.Cos(angle) * dist;
                            float lz = Mathf.Sin(angle) * dist;
                            float ly = tile.hasHill ? 0.8f : 0f; // Sits on hill or base

                            float scale = UnityEngine.Random.Range(_scaleRange.x, _scaleRange.y);
                            float rotY = _randomRotation ? UnityEngine.Random.Range(0f, 360f) : 0f;
                            Quaternion q = Quaternion.Euler(0f, rotY, 0f);

                            var att = new HexAttachmentData
                            {
                                prefabName = prefab,
                                attachedLayer = tile.hasHill ? "Hill" : "Base",
                                localX = lx,
                                localY = ly,
                                localZ = lz,
                                worldX = tile.x + lx,
                                worldY = tile.y + ly,
                                worldZ = tile.z + lz,
                                rotX = q.x, rotY = q.y, rotZ = q.z, rotW = q.w,
                                scaleX = scale, scaleY = scale, scaleZ = scale
                            };
                            tile.attachments.Add(att);
                        }
                    }
                    return true;
            }
            return false;
        }

        private bool EraseTile(HexTileData tile)
        {
            switch (_activeLayer)
            {
                case ActiveLayer.Layer3_Attachment:
                    if (tile.attachments != null && tile.attachments.Count > 0)
                    {
                        tile.attachments.Clear();
                        return true;
                    }
                    return false;

                case ActiveLayer.Layer2_Hill:
                    if (tile.hasHill)
                    {
                        tile.hasHill = false;
                        tile.hillPrefab = "";
                        return true;
                    }
                    return false;

                case ActiveLayer.Layer1_Base:
                    if (tile.hasBase)
                    {
                        tile.hasBase = false;
                        tile.hasHill = false;
                        tile.attachments.Clear();
                        return true;
                    }
                    return false;
            }
            return false;
        }

        // ================= Coordinate Helper Methods =================

        private Vector3 GetHexCenter(int col, int row)
        {
            float dx = 1.5f * _hexRadius;
            float dz = Mathf.Sqrt(3f) * _hexRadius;
            float colOffset = (col % 2 == 1) ? (dz * 0.5f) : 0f;
            return new Vector3(col * dx, 0f, row * dz + colOffset);
        }

        private void GetNearestHex(Vector3 worldPos, out int col, out int row)
        {
            float dx = 1.5f * _hexRadius;
            float dz = Mathf.Sqrt(3f) * _hexRadius;

            int approxCol = Mathf.RoundToInt(worldPos.x / dx);
            float bestDistSq = float.MaxValue;
            col = 0; row = 0;

            for (int c = approxCol - 1; c <= approxCol + 1; c++)
            {
                if (c < 0 || c >= _columns) continue;
                float colOffset = (c % 2 == 1) ? (dz * 0.5f) : 0f;
                int r = Mathf.RoundToInt((worldPos.z - colOffset) / dz);
                if (r < 0 || r >= _rows) continue;

                Vector3 center = new Vector3(c * dx, 0f, r * dz + colOffset);
                float distSq = (worldPos.x - center.x) * (worldPos.x - center.x) + (worldPos.z - center.z) * (worldPos.z - center.z);
                if (distSq < bestDistSq)
                {
                    bestDistSq = distSq;
                    col = c;
                    row = r;
                }
            }
        }

        private int GetHexDistance(int c1, int r1, int c2, int r2)
        {
            // Axial coordinates conversion for flat-topped odd-q grid
            int q1 = c1;
            int axR1 = r1 - (c1 - (c1 & 1)) / 2;
            int q2 = c2;
            int axR2 = r2 - (c2 - (c2 & 1)) / 2;

            int dq = q1 - q2;
            int dr = axR1 - axR2;
            return (Mathf.Abs(dq) + Mathf.Abs(dq + dr) + Mathf.Abs(dr)) / 2;
        }

        private void DrawHexWire(Vector3 center, float radius)
        {
            Vector3[] points = new Vector3[7];
            for (int i = 0; i < 6; i++)
            {
                float angle = i * 60f * Mathf.Deg2Rad;
                points[i] = center + new Vector3(Mathf.Cos(angle) * radius, 0.05f, Mathf.Sin(angle) * radius);
            }
            points[6] = points[0];
            Handles.DrawPolyLine(points);
        }
    }
}
