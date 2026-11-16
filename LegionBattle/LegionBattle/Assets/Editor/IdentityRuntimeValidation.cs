#if UNITY_EDITOR
using System;
using System.IO;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using LegionBattle.Battle;

namespace LegionBattle.EditorTools
{
    public static class IdentityRuntimeValidation
    {
        private static readonly List<string> checks=new List<string>();
        private static void Check(bool condition,string name){if(!condition)throw new Exception(name);checks.Add(name);}
        private static void Reject(string text,string name)
        {bool rejected=false;try{CharacterTraitsImporter.Parse(text);}catch(ArgumentException){rejected=true;}Check(rejected,name);}
        public static void Run()
        {
            checks.Clear();
            VerifyTextOnlyImport();
            var database=AssetDatabase.LoadAssetAtPath<CharacterDatabase>(CharacterTraitsImporter.DatabasePath);
            CharacterTraitsImporter.Refresh(database);
            string source;var index=CharacterTraitsImporter.Read(out source);
            int mapped=0;var people=new HashSet<string>();
            foreach(var sheet in database.characters)
            {
                if(sheet==null)continue;
                string id="unity:"+sheet.traits.assetGuid;
                CharacterTraits traits;
                Check(index.TryGetValue(id,out traits),"Label GUID found: "+id);
                Check(JsonUtility.ToJson(sheet.traits)==JsonUtility.ToJson(traits),"Database label matches source: "+id);
                var member=BattleMember.FromSheetData(sheet);
                string previous=sheet.traits.identity;member.traits.identity="probe-mutation";
                Check(sheet.traits.identity==previous,"Member label is independent: "+id);
                mapped++;people.Add(sheet.traits.personId);
            }
            Check(mapped==1229&&people.Count==1213,"Action variants preserve canonical person IDs without changing portrait count");
            Check(CharacterTraitsImporter.Refresh(database)==0,"Second label synchronization is idempotent");
            string prefix="{\"version\":4,\"tags\":[{\"id\":\"s\",\"name\":\"水手\",\"category\":\"identity\"}],\"characters\":";
            var genders=CharacterTraitsImporter.Parse(prefix+"[{\"id\":\"a\",\"gender\":\"\",\"identities\":[]},{\"id\":\"b\",\"gender\":\"无\",\"identities\":[]}]}");
            Check(genders["a"].gender==""&&genders["b"].gender=="无","Unmarked gender remains distinct from none");
            Reject(prefix+"[{\"id\":\"a\",\"identities\":[\"s\",\"s\"]}]}","Multiple identities require correction in external tool");
            Reject(prefix+"[{\"id\":\"a\",\"identities\":[\"missing\"]}]}","Missing identity dictionary entry rejected");
            Reject(prefix+"[{\"id\":\"a\"},{\"id\":\"a\"}]}","Duplicate person record rejected");
            Reject(prefix+"[{\"id\":\"a\",\"identities\":[\"s\"]},{\"id\":\"b\",\"identities\":[]}],\"groups\":[{\"id\":\"a\",\"members\":[\"a\",\"b\"]}]}","Conflicting action group tags rejected");
            Reject(prefix+"[{\"id\":\"a\",\"gender\":\"invalid\"}]}","Invalid gender rejected");
            File.WriteAllText(Environment.GetEnvironmentVariable("LEGION_IDENTITY_LABEL_VALIDATION"),JsonUtility.ToJson(new LabelResult {
                passed=true,source=source,portraits=mapped,people=people.Count,checks=checks.ToArray()},true));
            EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects,NewSceneMode.Single);
            new GameObject("IdentityRuntimeProbe").AddComponent<IdentityRuntimeProbe>();
            EditorApplication.isPlaying=true;
        }
        private static void VerifyTextOnlyImport()
        {
            const string path="Assets/Editor/IdentityValidationDatabase.asset";
            if(File.Exists(path))throw new InvalidOperationException("Validation asset already exists; refusing to overwrite it");
            string original=File.ReadAllText(CharacterTraitsImporter.DatabasePath);
            string bare=Regex.Replace(original,@"^    traits:\r?\n(?:      .*\r?\n)+","",RegexOptions.Multiline);
            try
            {
                File.WriteAllText(path,bare);AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceUpdate);
                var copy=AssetDatabase.LoadAssetAtPath<CharacterDatabase>(path);
                Check(CharacterTraitsImporter.Refresh(copy)==1229,"Metadata-only import fills every record in disposable copy");
                string after=Regex.Replace(File.ReadAllText(path),@"^    traits:\r?\n(?:      .*\r?\n)+","",RegexOptions.Multiline);
                Check(after==bare,"Metadata-only import preserves all original fields including missing Sprite references");
                string saved=File.ReadAllText(path);copy.characters[0].traits.identity="probe-edit";EditorUtility.SetDirty(copy);
                bool rejected=false;try{CharacterTraitsImporter.Refresh(copy);}catch(InvalidOperationException){rejected=true;}
                Check(rejected&&File.ReadAllText(path)==saved,"Unsaved database edits are preserved by refusing implicit save");
            }
            finally{AssetDatabase.DeleteAsset(path);}
        }
        [Serializable] private sealed class LabelResult {public bool passed;public string source;public int portraits,people;public string[] checks;}
    }
}
#endif
