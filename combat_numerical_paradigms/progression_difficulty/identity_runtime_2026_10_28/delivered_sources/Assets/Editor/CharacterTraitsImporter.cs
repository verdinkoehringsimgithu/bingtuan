#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;
using LegionBattle.Battle;

namespace LegionBattle.EditorTools
{
    // Read the external tool's authoritative file; never write it or infer tags from names.
    public static class CharacterTraitsImporter
    {
        public const string LabelsPath="Assets/Characters/character_bond_labels.json";
        public const string DatabasePath="Assets/Characters/CharacterDatabase.asset";
        [Serializable] private sealed class LabelDocument { public int version; public Tag[] tags; public Row[] characters; public Group[] groups; }
        [Serializable] private sealed class Tag { public string id,category,name; }
        [Serializable] private sealed class Row { public string id,path,race,gender; public int rarity; public string[] identities; }
        [Serializable] private sealed class Group { public string id; public string[] members; }

        public static Dictionary<string,CharacterTraits> Parse(string json)
        {
            var document=JsonUtility.FromJson<LabelDocument>(json);
            if(document==null||document.version<1||document.version>4||document.tags==null||document.characters==null)
                throw new ArgumentException("Unsupported character label document");
            var tags=new Dictionary<string,Tag>(StringComparer.Ordinal);
            foreach(var tag in document.tags)
            {
                if(string.IsNullOrWhiteSpace(tag.id)||string.IsNullOrWhiteSpace(tag.name)||tags.ContainsKey(tag.id))
                    throw new ArgumentException("Invalid or duplicate character tag ID");
                tags.Add(tag.id,tag);
            }
            var index=new Dictionary<string,CharacterTraits>(StringComparer.Ordinal);
            foreach(var row in document.characters)
            {
                if(string.IsNullOrWhiteSpace(row.id)||index.ContainsKey(row.id)||row.rarity<0||row.rarity>6)
                    throw new ArgumentException("Invalid or duplicate character record");
                if(row.identities!=null&&row.identities.Length>1)throw new ArgumentException("Resolve multiple identities in the character tool: "+row.id);
                if(!string.IsNullOrEmpty(row.gender)&&Array.IndexOf(new[] {"男","女","无","双"},row.gender)<0)
                    throw new ArgumentException("Invalid character gender: "+row.id);
                string identityId=row.identities==null||row.identities.Length==0?null:row.identities[0];
                var traits=new CharacterTraits {personId=row.id,assetGuid=row.id.StartsWith("unity:",StringComparison.Ordinal)?row.id.Substring(6):null,
                    raceId=row.race,race=Name(tags,row.race,"race"),gender=row.gender,
                    identityId=identityId,identity=Name(tags,identityId,"identity"),markedTier=row.rarity};
                index.Add(row.id,traits);
            }
            var grouped=new HashSet<string>(StringComparer.Ordinal);
            foreach(var group in document.groups??new Group[0])
            {
                if(string.IsNullOrWhiteSpace(group.id)||!index.ContainsKey(group.id)||group.members==null||group.members.Length==0)
                    throw new ArgumentException("Invalid character action group");
                var canonical=index[group.id];
                foreach(string id in group.members)
                {
                    CharacterTraits traits;
                    if(id==null||!index.TryGetValue(id,out traits)||!grouped.Add(id))throw new ArgumentException("Duplicate or missing action group member");
                    if((traits.identityId??"")!=(canonical.identityId??"")||(traits.raceId??"")!=(canonical.raceId??"")||
                        (traits.gender??"")!=(canonical.gender??"")||traits.markedTier!=canonical.markedTier)
                        throw new ArgumentException("Resolve conflicting action-group tags in the character tool: "+group.id);
                    traits.personId=group.id;
                }
            }
            return index;
        }
        private static string Name(Dictionary<string,Tag> tags,string id,string category)
        {
            if(string.IsNullOrEmpty(id))return null;
            Tag tag;
            if(!tags.TryGetValue(id,out tag)||tag.category!=category)throw new ArgumentException("Unknown "+category+" tag: "+id);
            return tag.name;
        }
        public static Dictionary<string,CharacterTraits> Read(out string source)
        {
            var candidates=new List<string>();
            foreach(string path in new[] {LabelsPath,LabelsPath+".bak"})if(File.Exists(path))candidates.Add(path);
            candidates.Sort((a,b)=>File.GetLastWriteTimeUtc(b).CompareTo(File.GetLastWriteTimeUtc(a)));
            Exception failure=null;
            foreach(string path in candidates)
                try{var index=Parse(File.ReadAllText(path));source=path;return index;}catch(Exception ex){failure=ex;}
            throw new InvalidOperationException("No valid character label file; existing database tags are preserved",failure);
        }
        public static int Refresh(CharacterDatabase database)
        {
            if(database==null)throw new ArgumentNullException("database");
            string source;var index=Read(out source);
            var updates=new List<KeyValuePair<CharacterSheetData,CharacterTraits>>();
            Dictionary<string,string> migrationPaths=null;
            foreach(var sheet in database.characters)
            {
                if(sheet==null)continue;
                string guid=sheet.traits==null?null:sheet.traits.assetGuid;
                if(sheet.IsValid)guid=AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(sheet.downFrames[0]));
                // One-time migration of old entries whose Sprite reference is missing. Resolve an
                // exact, unique source texture filename to its actual GUID; never guess its tags.
                if(string.IsNullOrEmpty(guid))
                {
                    if(migrationPaths==null)
                    {
                        migrationPaths=new Dictionary<string,string>(StringComparer.Ordinal);
                        foreach(string candidate in AssetDatabase.FindAssets("t:Texture2D",new[] {"Assets/Characters"}))
                        {
                            string name=Path.GetFileNameWithoutExtension(AssetDatabase.GUIDToAssetPath(candidate));
                            if(migrationPaths.ContainsKey(name))migrationPaths[name]=null;else migrationPaths.Add(name,candidate);
                        }
                    }
                    if(sheet.characterName!=null)migrationPaths.TryGetValue(sheet.characterName,out guid);
                }
                if(string.IsNullOrEmpty(guid))continue;
                string id="unity:"+guid;CharacterTraits traits;
                if(!index.TryGetValue(id,out traits))traits=new CharacterTraits {personId=id,assetGuid=guid};
                if(sheet.traits==null||JsonUtility.ToJson(sheet.traits)!=JsonUtility.ToJson(traits))
                    updates.Add(new KeyValuePair<CharacterSheetData,CharacterTraits>(sheet,traits.Clone()));
            }
            if(updates.Count>0)
            {
                if(EditorUtility.IsDirty(database))throw new InvalidOperationException("Save pending character database edits before synchronizing labels");
                WriteTraitsOnly(database,updates);
            }
            if(source.EndsWith(".bak",StringComparison.Ordinal))Debug.LogWarning("Character traits loaded from backup: "+source);
            return updates.Count;
        }
        [Serializable] private sealed class TextValue {public string value;}
        private static string Quote(string value)
        {
            string json=JsonUtility.ToJson(new TextValue {value=value??""});int colon=json.IndexOf(':');
            return json.Substring(colon+1,json.Length-colon-2);
        }
        private static void WriteTraitsOnly(CharacterDatabase database,List<KeyValuePair<CharacterSheetData,CharacterTraits>> updates)
        {
            string path=AssetDatabase.GetAssetPath(database);
            if(string.IsNullOrEmpty(path))throw new InvalidOperationException("Character database must be a saved asset");
            string original=File.ReadAllText(path),newline=original.Contains("\r\n")?"\r\n":"\n";
            var lines=original.Replace("\r\n","\n").Split('\n');
            int rows=0;foreach(string line in lines)if(line.StartsWith("  - characterName:",StringComparison.Ordinal))rows++;
            if(rows!=database.characters.Count)throw new InvalidOperationException("Save character database structure before synchronizing labels");
            var desired=new Dictionary<CharacterSheetData,CharacterTraits>();foreach(var update in updates)desired.Add(update.Key,update.Value);
            var output=new List<string>();int index=-1;
            for(int line=0;line<lines.Length;line++)
            {
                string text=lines[line];
                if(text.StartsWith("  - characterName:",StringComparison.Ordinal))
                {
                    index++;output.Add(text);var sheet=database.characters[index];CharacterTraits traits;
                    if(!desired.TryGetValue(sheet,out traits))traits=sheet.traits;
                    if(traits!=null)
                    {
                        output.Add("    traits:");
                        output.Add("      personId: "+Quote(traits.personId));output.Add("      assetGuid: "+Quote(traits.assetGuid));
                        output.Add("      raceId: "+Quote(traits.raceId));output.Add("      race: "+Quote(traits.race));
                        output.Add("      gender: "+Quote(traits.gender));output.Add("      identityId: "+Quote(traits.identityId));
                        output.Add("      identity: "+Quote(traits.identity));output.Add("      markedTier: "+traits.markedTier);
                    }
                    continue;
                }
                if(text=="    traits:")
                {while(line+1<lines.Length&&lines[line+1].StartsWith("      ",StringComparison.Ordinal))line++;continue;}
                output.Add(text);
            }
            // Never reserialize the rest of the database: Unity would discard missing Sprite
            // references while saving unrelated labels. Replace the text atomically, then import.
            string temporary=Path.Combine("Temp","CharacterTraits-"+Guid.NewGuid().ToString("N")+".tmp");
            File.WriteAllText(temporary,string.Join(newline,output),new UTF8Encoding(false));
            File.Replace(temporary,path,null);
            AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceUpdate);
        }
        [MenuItem("Tools/战斗/同步人物固有标签")]
        public static void RefreshDatabase()
        {
            var database=AssetDatabase.LoadAssetAtPath<CharacterDatabase>(DatabasePath);
            if(database!=null)Refresh(database);
        }
        [InitializeOnLoadMethod] private static void OnEditorLoad(){EditorApplication.delayCall+=RefreshDatabase;}
    }
    public sealed class CharacterTraitsPostprocessor : AssetPostprocessor
    {
        private static void OnPostprocessAllAssets(string[] imported,string[] deleted,string[] moved,string[] oldPaths)
        {
            foreach(var paths in new[] {imported,deleted,moved,oldPaths})foreach(string path in paths)
                if(path==CharacterTraitsImporter.LabelsPath||path==CharacterTraitsImporter.LabelsPath+".bak")
                {EditorApplication.delayCall+=CharacterTraitsImporter.RefreshDatabase;return;}
        }
    }
    public sealed class CharacterTraitsBuildStep : IPreprocessBuildWithReport
    {
        public int callbackOrder {get{return 0;}}
        public void OnPreprocessBuild(BuildReport report){CharacterTraitsImporter.RefreshDatabase();}
    }
}
#endif
