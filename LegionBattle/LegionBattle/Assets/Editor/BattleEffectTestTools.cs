#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using LegionBattle.Battle;

namespace LegionBattle.EditorTools
{
    public static class BattleEffectTestTools
    {
        public const string ScenePath="Assets/Scenes/BattleEffectTestScene.unity";
        [MenuItem("Tools/战斗/打开特效测试模块")]
        public static void Open()
        {
            if(AssetDatabase.LoadAssetAtPath<SceneAsset>(ScenePath)==null)
                AssetDatabase.CopyAsset("Assets/Scenes/BattleInspectionScene.unity",ScenePath);
            var scene=EditorSceneManager.OpenScene(ScenePath);
            var manager=Object.FindObjectOfType<BattleInspectionManager>();manager.productionMode=true;
            var module=manager.GetComponent<BattleEffectTestModule>();if(module==null)module=manager.gameObject.AddComponent<BattleEffectTestModule>();module.presentation=manager;
            foreach(var family in SkillEffectMatcher.AllFamilies)
                foreach(var variant in family.Variants.Values){EffectTimingConfig.For(variant.AnimationId);break;}
            if(!System.IO.File.Exists(EffectTimingConfig.SavePath))EffectTimingConfig.Save();
            var serialized=new SerializedObject(manager);
            foreach(var field in new[]{"btnNextWave","btnPrevWave","txtWaveInfo"}){
                var component=serialized.FindProperty(field).objectReferenceValue as Component;if(component!=null)component.gameObject.SetActive(false);
            }
            foreach(var text in Object.FindObjectsOfType<UnityEngine.UI.Text>(true))
                if(text.text.Contains("F2配置阶段")||text.text.Contains("四向动画各2秒"))text.gameObject.SetActive(false);
            EditorUtility.SetDirty(manager);EditorUtility.SetDirty(module);EditorSceneManager.SaveScene(scene);
            var settings=new System.Collections.Generic.List<EditorBuildSettingsScene>(EditorBuildSettings.scenes);
            if(!settings.Exists(x=>x.path==ScenePath))settings.Add(new EditorBuildSettingsScene(ScenePath,true));EditorBuildSettings.scenes=settings.ToArray();AssetDatabase.SaveAssets();
        }
        public static void Validate()
        {
            Open();new GameObject("EffectTestProbe").AddComponent<BattleEffectTestProbe>();EditorApplication.isPlaying=true;
        }
        public static void BakeAndValidate()
        {
            var slicer=ScriptableObject.CreateInstance<EffectSpriteSheetSlicer>();
            try { slicer.RunBatchSliceAndBuildDatabase(false); } finally { Object.DestroyImmediate(slicer); }
            Validate();
        }
    }
}
#endif
