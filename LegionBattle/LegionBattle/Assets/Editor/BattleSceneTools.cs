#if UNITY_EDITOR
using System;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;
using LegionBattle.Battle;

namespace LegionBattle.EditorTools
{
    public static class BattleSceneTools
    {
        public const string Path="Assets/Scenes/BattleScene.unity";
        [MenuItem("Tools/战斗/创建或更新正式战斗场景")]
        public static void CreateOrUpdate()
        {
            if(AssetDatabase.LoadAssetAtPath<SceneAsset>(Path)==null)
                if(!AssetDatabase.CopyAsset("Assets/Scenes/BattleInspectionScene.unity",Path))throw new InvalidOperationException("Cannot create BattleScene");
            var scene=EditorSceneManager.OpenScene(Path);
            var manager=UnityEngine.Object.FindObjectOfType<BattleInspectionManager>();
            if(manager==null)throw new InvalidOperationException("Battle presentation is missing");
            manager.productionMode=true;
            var controller=UnityEngine.Object.FindObjectOfType<BattleSceneController>();
            if(controller==null)controller=new GameObject("BattleSceneController").AddComponent<BattleSceneController>();
            controller.presentation=manager;
            var serialized=new SerializedObject(manager);
            var next=serialized.FindProperty("btnNextWave").objectReferenceValue as Button;
            var previous=serialized.FindProperty("btnPrevWave").objectReferenceValue as Button;
            var wave=serialized.FindProperty("txtWaveInfo").objectReferenceValue as Text;
            if(controller.leaveButton==null&&next!=null)
            {
                controller.leaveButton=UnityEngine.Object.Instantiate(next,next.transform.parent);
                controller.leaveButton.name="LeaveBattle";controller.leaveButton.gameObject.SetActive(true);
                controller.leaveButton.onClick=new Button.ButtonClickedEvent();
                controller.leaveButton.GetComponentInChildren<Text>().text="离开";
                var rect=(RectTransform)controller.leaveButton.transform;rect.anchorMin=rect.anchorMax=new Vector2(1,0);rect.pivot=new Vector2(1,0);rect.anchoredPosition=new Vector2(-24,24);
            }
            if(next!=null)next.gameObject.SetActive(false);if(previous!=null)previous.gameObject.SetActive(false);
            if(wave!=null)
            {
                wave.gameObject.SetActive(false);
                if(controller.resultText==null){controller.resultText=UnityEngine.Object.Instantiate(wave,wave.transform.parent);controller.resultText.name="BattleResult";controller.resultText.gameObject.SetActive(false);}
            }
            foreach(var text in UnityEngine.Object.FindObjectsOfType<Text>(true))
                if(text.text.Contains("F2配置阶段")||text.text.Contains("四向动画各2秒"))text.gameObject.SetActive(false);
            EditorUtility.SetDirty(manager);EditorUtility.SetDirty(controller);EditorSceneManager.MarkSceneDirty(scene);EditorSceneManager.SaveScene(scene,Path);
            var settings=new System.Collections.Generic.List<EditorBuildSettingsScene>(EditorBuildSettings.scenes);
            if(!settings.Exists(x=>x.path==Path))settings.Add(new EditorBuildSettingsScene(Path,true));
            EditorBuildSettings.scenes=settings.ToArray();AssetDatabase.SaveAssets();
        }
        public static void ValidateLifecycle()
        {
            CreateOrUpdate();
            EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects,NewSceneMode.Single);
            var host=new GameObject("BattleSceneLifecycleProbe");host.AddComponent<BattleSceneLifecycleProbe>();
            new GameObject("CallerCanvas").AddComponent<Canvas>();
            GameObject.CreatePrimitive(PrimitiveType.Cube).name="CallerRenderer";
            EditorApplication.isPlaying=true;
        }
    }
}
#endif
