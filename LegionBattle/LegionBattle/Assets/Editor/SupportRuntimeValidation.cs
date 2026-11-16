#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using LegionBattle.Battle;

namespace LegionBattle.EditorTools
{
    public static class SupportRuntimeValidation
    {
        public static void Run()
        {
            EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects,NewSceneMode.Single);
            new GameObject("SupportRuntimeProbe").AddComponent<SupportRuntimeProbe>();
            EditorApplication.isPlaying=true;
        }
    }
}
#endif
