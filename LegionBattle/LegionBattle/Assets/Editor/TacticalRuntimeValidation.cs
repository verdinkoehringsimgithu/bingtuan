#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using LegionBattle.Battle;
namespace LegionBattle.EditorTools
{
    public static class TacticalRuntimeValidation
    {
        public static void Run()
        {
            EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects,NewSceneMode.Single);
            new GameObject("TacticalRuntimeProbe").AddComponent<TacticalRuntimeProbe>();EditorApplication.isPlaying=true;
        }
    }
}
#endif
