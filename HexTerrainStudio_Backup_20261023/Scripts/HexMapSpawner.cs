using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

#if UNITY_EDITOR
using UnityEditor;
#endif

namespace HexTerrainStudio
{
    [ExecuteInEditMode]
    public class HexMapSpawner : MonoBehaviour
    {
        [Header("Map Configuration")]
        public TextAsset mapJsonAsset;
        public string customJsonPath = "";

        [Header("Hierarchy Roots")]
        public Transform baseRoot;
        public Transform hillRoot;
        public Transform attachmentRoot;

        [HideInInspector]
        public HexMapData currentMapData;

        // Cache for loaded prefabs and materials
        private static Dictionary<string, GameObject> _prefabCache = new Dictionary<string, GameObject>();
        private static Dictionary<string, Material> _materialCache = new Dictionary<string, Material>();

        private static readonly Dictionary<string, string> StandardPrefabPaths = new Dictionary<string, string>
        {
            // Base
            { "Hexagon", "Assets/AssetRaw/GameAssets/Hexagon/Hexagon/Hexagon.prefab" },
            // Hills
            { "Yama1", "Assets/AssetRaw/GameAssets/Hexagon/Prefabs/Yama1.prefab" },
            { "Yama2", "Assets/AssetRaw/GameAssets/Hexagon/Prefabs/Yama2.prefab" },
            { "Yama3", "Assets/AssetRaw/GameAssets/Hexagon/Prefabs/Yama3.prefab" },
            // Mountains
            { "M4", "Assets/AssetRaw/GameAssets/Common/Mountain/MountainCollection1/M4.prefab" },
            { "M4 Variant", "Assets/AssetRaw/GameAssets/Common/Mountain/MountainCollection1/M4 Variant.prefab" },
            { "Snow_mountain_t1_4", "Assets/AssetRaw/GameAssets/Common/Nature/MountainWithShadow/Snow_mountain_t1_4.prefab" },
            { "Snow_mountain_t2_3", "Assets/ALPINE_LAKE/Models/PREFABS/Snow_mountain_t2_3.prefab" },
            { "Mountain_01", "Assets/ANGRY MESH/Nature Pack - Winter Environment/Prefabs/Background/Mountain_01.prefab" },
            { "Mountain_03", "Assets/ANGRY MESH/Nature Pack - Winter Environment/Prefabs/Background/Mountain_03.prefab" },
            // Trees
            { "Pine_01", "Assets/Coniferous forest/Trees/Pine_01.prefab" },
            { "Pine_02", "Assets/Coniferous forest/Trees/Pine_02.prefab" },
            { "Pine_03", "Assets/Coniferous forest/Trees/Pine_03.prefab" },
            { "Pine_04", "Assets/Coniferous forest/Trees/Pine_04.prefab" },
            { "Pine_05", "Assets/Coniferous forest/Trees/Pine_05.prefab" },
            { "Fir_01", "Assets/Coniferous forest/Trees/Fir_01.prefab" },
            { "Spruce_Tree1", "Assets/Coniferous forest/Trees/Spruce_Tree1.prefab" },
            { "Spruce_Tree2", "Assets/Coniferous forest/Trees/Spruce_Tree2.prefab" },
            { "Spruce_Tree3", "Assets/Coniferous forest/Trees/Spruce_Tree3.prefab" },
            { "Tree Birch", "Assets/Visual Design Cafe/Stylized Nature - Grasslands/Universal/Trees/Tree Birch.prefab" },
            { "Tree Maple", "Assets/Visual Design Cafe/Stylized Nature - Grasslands/Universal/Trees/Tree Maple.prefab" },
            { "Acacia", "Assets/Desert Vegetation Pack/Prefabs/Acacia.prefab" },
            // Rocks
            { "Rock_01", "Assets/Coniferous forest/Rocks/Rock_01.prefab" },
            { "Rock_02", "Assets/Coniferous forest/Rocks/Rock_02.prefab" },
            { "Rock_03", "Assets/Coniferous forest/Rocks/Rock_03.prefab" },
            { "Rock_04", "Assets/Coniferous forest/Rocks/Rock_04.prefab" },
            { "Rock_small_01", "Assets/Coniferous forest/Rocks/Rock_small_01.prefab" },
            { "Rock_small_02", "Assets/Coniferous forest/Rocks/Rock_small_02.prefab" },
            { "Rock_small_03", "Assets/Coniferous forest/Rocks/Rock_small_03.prefab" },
            { "Rock_small_04", "Assets/Coniferous forest/Rocks/Rock_small_04.prefab" },
            { "Boulder_Group_1A1", "Assets/Aquarius Fantasy - High Elves/Prefabs/Nature/Rocks/Cliff Chunks/Boulder_Group_1A1.prefab" },
            { "Boulder_Group_1A2", "Assets/Aquarius Fantasy - High Elves/Prefabs/Nature/Rocks/Cliff Chunks/Boulder_Group_1A2.prefab" },
            { "Boulder_Group_1A3", "Assets/Aquarius Fantasy - High Elves/Prefabs/Nature/Rocks/Cliff Chunks/Boulder_Group_1A3.prefab" },
            { "Forest_stone_2", "Assets/ALPINE_LAKE/Models/PREFABS/Forest_stone_2.prefab" },
            { "Forest_stone_4", "Assets/ALPINE_LAKE/Models/PREFABS/Forest_stone_4.prefab" },
            // Crops & Foliage
            { "Wheat_03a", "Assets/FarmCrops/Prefabs/Crops/Wheat_03a.prefab" },
            { "Carrot_03", "Assets/FarmCrops/Prefabs/Crops/Carrot_03.prefab" },
            { "Potato_03", "Assets/FarmCrops/Prefabs/Crops/Potato_03.prefab" },
            { "Fern_A", "Assets/AssetRaw/GameAssets/Common/Nature/grass/Prefabs/Details/Fern_A.prefab" },
            { "Fern_B", "Assets/AssetRaw/GameAssets/Common/Nature/grass/Prefabs/Details/Fern_B.prefab" },
            { "Bush_Red", "Assets/AssetRaw/GameAssets/Common/Nature/grass/Prefabs/Details/Bush_Red.prefab" },
            { "BushDry_B", "Assets/AssetRaw/GameAssets/Common/Nature/grass/Prefabs/Details/BushDry_B.prefab" },
            { "Mushroom_01", "Assets/Coniferous forest/Plants/Mushroom_01.prefab" },
            { "Mushroom_02", "Assets/Coniferous forest/Plants/Mushroom_02.prefab" }
        };

        private static readonly Dictionary<string, string> StandardMaterialPaths = new Dictionary<string, string>
        {
            { "Hexagon", "Assets/AssetRaw/GameAssets/Hexagon/Hexagon/Hexagon.mat" },
            { "Sand", "Assets/AssetRaw/GameAssets/Hexagon/Hexagon/Materail/Sand.mat" },
            { "Hexagon 1", "Assets/AssetRaw/GameAssets/Hexagon/Hexagon/Hexagon 1.mat" },
            { "Hexagon 2", "Assets/AssetRaw/GameAssets/Hexagon/Hexagon/Hexagon 2.mat" },
            { "Hexagon 3", "Assets/AssetRaw/GameAssets/Hexagon/Hexagon/Hexagon 3.mat" },
            { "C", "Assets/AssetRaw/GameAssets/Hexagon/Hexagon/C.mat" }
        };

        public void EnsureHierarchy()
        {
            if (baseRoot == null)
            {
                var tr = transform.Find("Layer1_Base");
                if (tr == null)
                {
                    var go = new GameObject("Layer1_Base");
                    go.transform.SetParent(transform, false);
                    baseRoot = go.transform;
                }
                else baseRoot = tr;
            }

            if (hillRoot == null)
            {
                var tr = transform.Find("Layer2_Hills");
                if (tr == null)
                {
                    var go = new GameObject("Layer2_Hills");
                    go.transform.SetParent(transform, false);
                    hillRoot = go.transform;
                }
                else hillRoot = tr;
            }

            if (attachmentRoot == null)
            {
                var tr = transform.Find("Layer3_Attachments");
                if (tr == null)
                {
                    var go = new GameObject("Layer3_Attachments");
                    go.transform.SetParent(transform, false);
                    attachmentRoot = go.transform;
                }
                else attachmentRoot = tr;
            }
        }

        [ContextMenu("Build Map from JSON File")]
        public void BuildMapFromJson()
        {
            string json = "";
            if (mapJsonAsset != null)
            {
                json = mapJsonAsset.text;
            }
            else if (!string.IsNullOrEmpty(customJsonPath) && File.Exists(customJsonPath))
            {
                json = File.ReadAllText(customJsonPath);
            }
            else
            {
                Debug.LogError("[HexMapSpawner] No JSON file specified!");
                return;
            }

            var mapData = JsonUtility.FromJson<HexMapData>(json);
            if (mapData != null)
            {
                BuildMap(mapData);
            }
            else
            {
                Debug.LogError("[HexMapSpawner] Failed to parse HexMapData JSON.");
            }
        }

        [ContextMenu("Clear Map")]
        public void ClearMap()
        {
            EnsureHierarchy();
            ClearChildren(baseRoot);
            ClearChildren(hillRoot);
            ClearChildren(attachmentRoot);
            currentMapData = null;
        }

        private void ClearChildren(Transform root)
        {
            if (root == null) return;
            for (int i = root.childCount - 1; i >= 0; i--)
            {
                var child = root.GetChild(i).gameObject;
                if (Application.isPlaying)
                    Destroy(child);
                else
                    DestroyImmediate(child);
            }
        }

        public void BuildMap(HexMapData mapData)
        {
            if (mapData == null) return;
            currentMapData = mapData;
            EnsureHierarchy();
            ClearMap();
            currentMapData = mapData;

            // 1. Spawn Layer 1 (Base)
            var tileLookup = new Dictionary<string, GameObject>();
            foreach (var tile in mapData.tiles)
            {
                if (!tile.hasBase) continue;
                Vector3 pos = new Vector3(tile.x, tile.y, tile.z);
                GameObject prefab = ResolvePrefab(tile.basePrefab ?? "Hexagon");
                if (prefab == null) continue;

                GameObject baseGo = Instantiate(prefab, pos, Quaternion.identity, baseRoot);
                baseGo.name = $"Hex_{tile.col}_{tile.row}";

                // Ensure mesh collider exists for raycasting
                if (baseGo.GetComponent<Collider>() == null)
                {
                    var mf = baseGo.GetComponentInChildren<MeshFilter>();
                    if (mf != null && mf.sharedMesh != null)
                    {
                        var mc = baseGo.AddComponent<MeshCollider>();
                        mc.sharedMesh = mf.sharedMesh;
                    }
                }

                // Apply material if specified
                if (!string.IsNullOrEmpty(tile.baseMaterial))
                {
                    Material mat = ResolveMaterial(tile.baseMaterial);
                    if (mat != null)
                    {
                        var rend = baseGo.GetComponentInChildren<Renderer>();
                        if (rend != null) rend.sharedMaterial = mat;
                    }
                }

                tileLookup[$"{tile.col}_{tile.row}"] = baseGo;
            }

            // 2. Spawn Layer 2 (Hills - placed on Base)
            foreach (var tile in mapData.tiles)
            {
                if (!tile.hasHill || string.IsNullOrEmpty(tile.hillPrefab)) continue;
                if (!tileLookup.ContainsKey($"{tile.col}_{tile.row}")) continue; // Hill requires Base

                Vector3 pos = new Vector3(tile.x, tile.y, tile.z);
                GameObject hillPrefab = ResolvePrefab(tile.hillPrefab);
                if (hillPrefab == null) continue;

                Quaternion rot = Quaternion.Euler(0f, tile.hillRotY, 0f);
                GameObject hillGo = Instantiate(hillPrefab, pos, rot, hillRoot);
                hillGo.name = $"Hill_{tile.col}_{tile.row}_{tile.hillPrefab}";
            }

            // 3. Spawn Layer 3 (Attachments & Mountains)
            foreach (var tile in mapData.tiles)
            {
                if (tile.attachments == null || tile.attachments.Count == 0) continue;
                foreach (var att in tile.attachments)
                {
                    if (string.IsNullOrEmpty(att.prefabName)) continue;
                    GameObject attPrefab = ResolvePrefab(att.prefabName);
                    if (attPrefab == null) continue;

                    Vector3 worldPos;
                    if (Mathf.Abs(att.worldX) > 0.0001f || Mathf.Abs(att.worldZ) > 0.0001f)
                    {
                        worldPos = new Vector3(att.worldX, att.worldY, att.worldZ);
                    }
                    else
                    {
                        worldPos = new Vector3(tile.x + att.localX, tile.y + att.localY, tile.z + att.localZ);
                    }
                    Quaternion rot = new Quaternion(att.rotX, att.rotY, att.rotZ, att.rotW);
                    Vector3 scale = new Vector3(att.scaleX, att.scaleY, att.scaleZ);

                    GameObject attGo = Instantiate(attPrefab, worldPos, rot, attachmentRoot);
                    attGo.name = $"Att_{tile.col}_{tile.row}_{att.prefabName}";
                    attGo.transform.localScale = scale;
                }
            }

            Debug.Log($"[HexMapSpawner] Map '{mapData.mapName}' successfully generated! ({mapData.tiles.Count} hex tiles)");
        }

        public static GameObject ResolvePrefab(string key)
        {
            if (string.IsNullOrEmpty(key)) return null;
            if (_prefabCache.TryGetValue(key, out GameObject cached) && cached != null)
                return cached;

#if UNITY_EDITOR
            // 1. Try standard registered path
            if (StandardPrefabPaths.TryGetValue(key, out string path))
            {
                var go = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (go != null)
                {
                    _prefabCache[key] = go;
                    return go;
                }
            }

            // 2. Smart fallback search across the whole project
            string[] guids = AssetDatabase.FindAssets($"{key} t:Prefab");
            foreach (var guid in guids)
            {
                string p = AssetDatabase.GUIDToAssetPath(guid);
                if (Path.GetFileNameWithoutExtension(p).Equals(key, StringComparison.OrdinalIgnoreCase))
                {
                    var go = AssetDatabase.LoadAssetAtPath<GameObject>(p);
                    if (go != null)
                    {
                        _prefabCache[key] = go;
                        return go;
                    }
                }
            }
#endif
            return null;
        }

        public static Material ResolveMaterial(string key)
        {
            if (string.IsNullOrEmpty(key)) return null;
            if (_materialCache.TryGetValue(key, out Material cached) && cached != null)
                return cached;

#if UNITY_EDITOR
            if (StandardMaterialPaths.TryGetValue(key, out string path))
            {
                var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (mat != null)
                {
                    _materialCache[key] = mat;
                    return mat;
                }
            }

            string[] guids = AssetDatabase.FindAssets($"{key} t:Material");
            foreach (var guid in guids)
            {
                string p = AssetDatabase.GUIDToAssetPath(guid);
                if (Path.GetFileNameWithoutExtension(p).Equals(key, StringComparison.OrdinalIgnoreCase))
                {
                    var mat = AssetDatabase.LoadAssetAtPath<Material>(p);
                    if (mat != null)
                    {
                        _materialCache[key] = mat;
                        return mat;
                    }
                }
            }
#endif
            return null;
        }
    }
}
