#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using LegionBattle.Battle;

namespace LegionBattle.EditorTools
{
    public static class ExpeditionValidation
    {
        public static void Run()
        {
            EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects,NewSceneMode.Single);
            new GameObject("ExpeditionRuntimeProbe").AddComponent<ExpeditionRuntimeProbe>();
            EditorApplication.isPlaying=true;
        }
        public static void RunExistingLifecycle()
        {
            // Exercise the saved production scene without re-generating or saving it.
            EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects,NewSceneMode.Single);
            new GameObject("BattleSceneLifecycleProbe").AddComponent<BattleSceneLifecycleProbe>();
            new GameObject("CallerCanvas").AddComponent<Canvas>();
            GameObject.CreatePrimitive(PrimitiveType.Cube).name="CallerRenderer";
            EditorApplication.isPlaying=true;
        }
    }
}
#endif
