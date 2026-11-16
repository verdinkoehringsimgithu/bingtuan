#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;
using LegionBattle.Battle;

namespace LegionBattle.EditorTools
{
    public class BattleEffectBuildPreparation : IPreprocessBuildWithReport
    {
        public int callbackOrder => 0;
        public void OnPreprocessBuild(BuildReport report)
        {
            // Publish the latest automatic checkpoint into the packaged resource.
            EffectTimingConfig.Save();
            FormationConfig.Load().Save();
            var db=AssetDatabase.LoadAssetAtPath<EffectDatabase>("Assets/Resources/EffectDatabase.asset");
            bool complete=db!=null&&db.visibleFramesCentered;
            foreach(var family in SkillEffectMatcher.AllFamilies)
                foreach(var variant in family.Variants.Values)
                {
                    EffectEntry entry;
                    if(db==null||!db.TryGetEffect(variant.AnimationId,out entry)||!entry.HasValidSprites)complete=false;
                    else if(System.IO.File.Exists(System.IO.Path.Combine(Application.dataPath,"Effects/Layers/"+variant.FolderName+"_back.png"))&&!entry.HasLayerSprites)complete=false;
                }
            if(complete)return;
            var slicer=ScriptableObject.CreateInstance<EffectSpriteSheetSlicer>();
            try {slicer.RunBatchSliceAndBuildDatabase(false);}finally{Object.DestroyImmediate(slicer);}
        }
    }
}
#endif
