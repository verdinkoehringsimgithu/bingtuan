using System.IO;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

namespace HexTerrainStudio
{
    [InitializeOnLoad]
    public static class HexSceneBuilder
    {
        public const string ScenePath = "Assets/HexTerrainStudio/Scenes/HexMapEditorScene.unity";

        static HexSceneBuilder()
        {
            EditorApplication.delayCall += EnsureSceneExists;
        }

        [MenuItem("Tools/Hex Terrain/Create Hex Map Editor Scene")]
        public static void CreateScene()
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            // 1. Main Camera
            var camGo = new GameObject("Main Camera");
            var cam = camGo.AddComponent<Camera>();
            camGo.tag = "MainCamera";
            cam.clearFlags = CameraClearFlags.Skybox;
            cam.fieldOfView = 60f;
            camGo.transform.position = new Vector3(64f, 65f, -20f);
            camGo.transform.rotation = Quaternion.Euler(50f, 0f, 0f);

            // 2. Directional Light
            var lightGo = new GameObject("Directional Light");
            var light = lightGo.AddComponent<Light>();
            light.type = LightType.Directional;
            light.intensity = 1.25f;
            light.shadows = LightShadows.Soft;
            lightGo.transform.rotation = Quaternion.Euler(50f, -30f, 0f);

            // 3. HexMapRoot with Spawner
            var rootGo = new GameObject("HexMapRoot");
            var spawner = rootGo.AddComponent<HexMapSpawner>();
            spawner.EnsureHierarchy();

            // Save Scene
            string dir = Path.GetDirectoryName(ScenePath);
            if (!Directory.Exists(dir)) Directory.CreateDirectory(dir);

            EditorSceneManager.SaveScene(scene, ScenePath);
            AssetDatabase.Refresh();
            Debug.Log("[HexSceneBuilder] Successfully generated scene at: " + ScenePath);
        }

        private static void EnsureSceneExists()
        {
            if (!File.Exists(ScenePath))
            {
                CreateScene();
            }
        }
    }
}
