#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using LegionBattle.Battle;
namespace LegionBattle.EditorTools
{
    public static class AugmentationRuntimeValidation
    {
        public static void Run()
        {
            EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects,NewSceneMode.Single);
            new GameObject("AugmentationRuntimeProbe").AddComponent<AugmentationRuntimeProbe>();
            EditorApplication.isPlaying=true;
        }
    }
}
#endif
