#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using LegionBattle.Battle;

namespace LegionBattle.EditorTools
{
    public static class AmplificationRuntimeValidation
    {
        public static void Run()
        {
            EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects,NewSceneMode.Single);
            new GameObject("AmplificationRuntimeProbe").AddComponent<AmplificationRuntimeProbe>();
            EditorApplication.isPlaying=true;
        }
    }
}
#endif
