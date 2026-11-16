using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace LegionBattle.Battle
{
    [Serializable] public class EffectTimingProfile
    {
        public string familyKey;
        public bool playOnCaster;
        public float scale = 1;
        public float offsetX = 0;
        public float offsetY = 0;
        public const float DefaultAdvanceDuration=.30f,DefaultHoldDuration=.50f,DefaultRetreatDuration=.40f;
        public float advanceDuration = DefaultAdvanceDuration;
        public float holdDuration = DefaultHoldDuration;
        public float retreatDuration = DefaultRetreatDuration;
        public bool useFormationSorting = true;
        public int fps = 15;
        public int effectStartFrame;
        public bool autoRotationCount = true;
        public int rotationCount = 1;
        public float secondsPerRotation = 1;
        // Zero-based atlas frame, measured from effect start for enemy effects.
        public int damageFrame;
        public int physicsFrame;
        public int reactionType = 1;
        public float scatterDistanceScale = 0.45f;
        public int healFrame;
        public float DamageDelay => playOnCaster ? 0 : damageFrame/(float)Mathf.Max(1,fps);
        public float PhysicsDelay => playOnCaster ? 0 : physicsFrame/(float)Mathf.Max(1,fps);
        public float HealDelay => healFrame/(float)Mathf.Max(1,fps);
        public void Normalize() { fps=Mathf.Clamp(fps,1,120); scale=Mathf.Clamp(scale,.05f,10); offsetX=Mathf.Clamp(offsetX,-10f,10f); offsetY=Mathf.Clamp(offsetY,-10f,10f); advanceDuration=Duration(advanceDuration,DefaultAdvanceDuration); holdDuration=Duration(holdDuration,DefaultHoldDuration); retreatDuration=Duration(retreatDuration,DefaultRetreatDuration); rotationCount=Mathf.Max(0,rotationCount); secondsPerRotation=Mathf.Max(.05f,secondsPerRotation); reactionType=Mathf.Clamp(reactionType,1,10); if(scatterDistanceScale<=0.001f)scatterDistanceScale=0.45f; scatterDistanceScale=Mathf.Clamp(scatterDistanceScale,0.05f,5f); }
        private static float Duration(float value,float fallback){return float.IsNaN(value)||float.IsInfinity(value)?fallback:Mathf.Max(0,value);}
    }
    [Serializable] public class EffectTimingDocument { public int version=5; public List<EffectTimingProfile> profiles=new List<EffectTimingProfile>(); }
    public static class EffectTimingConfig
    {
        private static EffectTimingDocument document;
        private static string lastPersistedJson;
#if UNITY_EDITOR
        private static string validationDirectory;
        public static void UseValidationDirectory(string path){validationDirectory=path;Reload();}
        [UnityEditor.InitializeOnLoadMethod]
        private static void RegisterSafetySave()
        {
            UnityEditor.AssemblyReloadEvents.beforeAssemblyReload-=SafetySave;
            UnityEditor.AssemblyReloadEvents.beforeAssemblyReload+=SafetySave;
            UnityEditor.EditorApplication.playModeStateChanged-=OnPlayModeChange;
            UnityEditor.EditorApplication.playModeStateChanged+=OnPlayModeChange;
        }
        private static void OnPlayModeChange(UnityEditor.PlayModeStateChange state)
        {
            if(state==UnityEditor.PlayModeStateChange.ExitingPlayMode)SafetySave();
        }
        private static void SafetySave(){try{AutoSaveIfChanged();}catch(Exception e){Debug.LogWarning("特效配置自动保存失败："+e.Message);}}
#endif
        public static string SavePath {
            get {
#if UNITY_EDITOR
                if(validationDirectory!=null)return Path.Combine(validationDirectory,"EffectTimingConfig.json");
                return Path.Combine(Application.dataPath,"Resources/EffectTimingConfig.json");
#else
                return Path.Combine(Application.persistentDataPath,"EffectTimingConfig.json");
#endif
            }
        }
        public static string AutoSavePath {
            get {
#if UNITY_EDITOR
                if(validationDirectory!=null)return Path.Combine(validationDirectory,"EffectTimingConfig.autosave.json");
                return Path.Combine(Path.GetDirectoryName(Application.dataPath),"UserSettings/EffectTimingConfig.autosave.json");
#else
                return Path.Combine(Application.persistentDataPath,"EffectTimingConfig.autosave.json");
#endif
            }
        }
        public static void Reload() { document=null;lastPersistedJson=null; }
        private static EffectTimingDocument Parse(string json)
        {
            if(string.IsNullOrEmpty(json)||!json.Contains("\"profiles\""))throw new InvalidDataException("Invalid effect timing configuration");
            var parsed=JsonUtility.FromJson<EffectTimingDocument>(json);
            if(parsed==null||parsed.profiles==null||parsed.profiles.Exists(x=>x==null||string.IsNullOrEmpty(x.familyKey)))throw new InvalidDataException("Invalid effect timing profiles");
            if(parsed.version<2){foreach(var entry in parsed.profiles)entry.useFormationSorting=true;parsed.version=2;}
            if(parsed.version<3){foreach(var entry in parsed.profiles){entry.autoRotationCount=true;entry.rotationCount=1;entry.secondsPerRotation=1;}parsed.version=3;}
            if(parsed.version<4){foreach(var entry in parsed.profiles){entry.advanceDuration=EffectTimingProfile.DefaultAdvanceDuration;entry.holdDuration=EffectTimingProfile.DefaultHoldDuration;entry.retreatDuration=EffectTimingProfile.DefaultRetreatDuration;}parsed.version=4;}
            if(parsed.version<5){foreach(var entry in parsed.profiles){if(entry.scatterDistanceScale<=0.001f)entry.scatterDistanceScale=0.45f;entry.healFrame=0;}parsed.version=5;}
            foreach(var entry in parsed.profiles)entry.Normalize();
            return parsed;
        }
        private static void Load()
        {
            if(document!=null)return;
            var candidates=new List<string>{SavePath,AutoSavePath,SavePath+".bak",AutoSavePath+".bak"};
            candidates.RemoveAll(x=>!File.Exists(x));
            candidates.Sort((a,b)=>File.GetLastWriteTimeUtc(b).CompareTo(File.GetLastWriteTimeUtc(a)));
            foreach(var path in candidates)
            {
                try{document=Parse(File.ReadAllText(path));break;}
                catch(Exception e){Debug.LogWarning("特效配置读取失败，将尝试恢复副本："+path+" · "+e.Message);}
            }
            if(document==null){var resource=Resources.Load<TextAsset>("EffectTimingConfig");document=resource==null?new EffectTimingDocument():Parse(resource.text);}
            lastPersistedJson=JsonUtility.ToJson(document);
        }
        public static EffectTimingProfile For(int animationId)
        {
            Load(); SkillEffectMatcher.VariantEntry variant; SkillEffectMatcher.FamilyEntry family;
            if(!SkillEffectMatcher.TryGetById(animationId,out variant,out family)||family==null)return new EffectTimingProfile();
            var entry=document.profiles.Find(x=>x.familyKey==family.BaseKey);
            if(entry!=null){ApplySharedMotion(entry);return entry;}
            entry=new EffectTimingProfile {familyKey=family.BaseKey,playOnCaster=family.PlayOnCaster,reactionType=family.HitReactionType};
            entry.Normalize();document.profiles.Add(entry);ApplySharedMotion(entry);return entry;
        }
        public static EffectTimingProfile Motion => For(1001);
        private static void ApplySharedMotion(EffectTimingProfile entry)
        {
            var source=document.profiles.Find(x=>x.familyKey=="expfx1_epic_explosion_A");
            if(source==null||source==entry)return;
            source.Normalize();entry.advanceDuration=source.advanceDuration;entry.holdDuration=source.holdDuration;entry.retreatDuration=source.retreatDuration;
        }
        public static void Save()
        {
            Load();foreach(var entry in document.profiles){entry.Normalize();ApplySharedMotion(entry);}
            AtomicWrite(SavePath,JsonUtility.ToJson(document,true));
            AutoSaveIfChanged();
            lastPersistedJson=JsonUtility.ToJson(document);
#if UNITY_EDITOR
            if(validationDirectory==null)UnityEditor.AssetDatabase.ImportAsset("Assets/Resources/EffectTimingConfig.json");
#endif
        }
        public static bool AutoSaveIfChanged()
        {
            if(document==null)return false;
            foreach(var entry in document.profiles){entry.Normalize();ApplySharedMotion(entry);}
            string json=JsonUtility.ToJson(document);
            if(json==lastPersistedJson)return false;
            AtomicWrite(AutoSavePath,JsonUtility.ToJson(document,true));
            lastPersistedJson=json;return true;
        }
        private static void AtomicWrite(string path,string json)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            string temporary=path+".tmp";File.WriteAllText(temporary,json);
            if(File.Exists(path))
            {
                // Keep the last valid copy even when the current file was corrupted.
                bool valid;try{Parse(File.ReadAllText(path));valid=true;}catch{valid=false;}
                File.Replace(temporary,path,valid?path+".bak":null);
            }
            else File.Move(temporary,path);
        }
        public static float ReactionDuration(int type)
        {
            float[] durations={.50f,.56f,.78f,.90f,.95f,.72f,.60f,.52f,.88f,.92f};
            return durations[Mathf.Clamp(type-1,0,9)];
        }
    }
}
