#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using LegionBattle.Battle;

namespace LegionBattle.EditorTools
{
    public static class EvasionRuntimeValidation
    {
        public static void Run()
        {
            EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects,NewSceneMode.Single);
            new GameObject("EvasionRuntimeProbe").AddComponent<EvasionRuntimeProbe>();
            EditorApplication.isPlaying=true;
        }
    }
}
#endif
