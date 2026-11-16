#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using LegionBattle.Battle;
namespace LegionBattle.EditorTools
{
    public static class CompoundRuntimeValidation
    {
        public static void Run()
        {
            EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects,NewSceneMode.Single);
            new GameObject("CompoundRuntimeProbe").AddComponent<CompoundRuntimeProbe>();EditorApplication.isPlaying=true;
        }
    }
}
#endif
