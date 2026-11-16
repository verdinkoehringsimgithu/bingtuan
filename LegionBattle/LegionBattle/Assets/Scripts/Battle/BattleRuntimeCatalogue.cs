using System;
using System.Collections.Generic;
using UnityEngine;

namespace LegionBattle.Battle
{
    [Serializable] public class RuntimeSkillRecord
    {
        public int tier, sample;
        public string axis, description;
        public CombatSkill skill;
        public int[] start, end;
    }
    [Serializable] public class RuntimeTopItem { public int owner; public string kind; public double value; }
    [Serializable] public class RuntimeGearRule { public string genre; public double points; public RuntimeTopItem[] tops; }
    [Serializable] public class RuntimeStageRule
    {
        public int stage, members, bp, tier, lower, upper;
        public RuntimeGearRule[] gear;
    }
    [Serializable] public class RuntimeEncounter
    {
        public int stage;
        public string difficulty, genre;
        public double alpha, beta, rhoLower, rhoUpper, referenceWinRate;
        public CombatMember[] members;
        public int[] levels;
    }
    [Serializable] public class RuntimeCombatCatalogue
    {
        public RuntimeSkillRecord[] skills;
        public RuntimeStageRule[] stages;
        public RuntimeEncounter[] enemies;
    }
    public static class BattleRuntimeCatalogue
    {
        private static RuntimeCombatCatalogue data;
        public static RuntimeCombatCatalogue Data
        {
            get
            {
                if (data == null)
                {
                    var asset = Resources.Load<TextAsset>("RuntimeCombatCatalogue");
                    if (asset == null) throw new InvalidOperationException("Missing RuntimeCombatCatalogue");
                    data = JsonUtility.FromJson<RuntimeCombatCatalogue>(asset.text);
                    if (data.skills == null || data.stages.Length != 6 || data.enemies.Length != 18) throw new InvalidOperationException("Invalid combat catalogue");
                }
                return data;
            }
        }
        public static RuntimeStageRule Stage(int stage)
        {
            if (stage < 1 || stage > 6) throw new ArgumentOutOfRangeException("stage");
            return Data.stages[stage-1];
        }
        public static RuntimeSkillRecord Source(int tier, string axis, int sample)
        {
            foreach(var row in Data.skills) if(row.tier==tier && row.axis==axis && row.sample==sample)
                return JsonUtility.FromJson<RuntimeSkillRecord>(JsonUtility.ToJson(row));
            throw new InvalidOperationException("Missing fixed encounter skill source");
        }
        public static string Axis(string name)
        {
            switch (name) { case "勇气": case "C": return "C"; case "坚韧": case "R": return "R"; case "先机": case "I": return "I"; case "魔力": case "M": return "M"; default: throw new ArgumentException("Unknown axis"); }
        }
        public static string AxisName(string axis)
        {
            switch (Axis(axis)) { case "C": return "勇气"; case "R": return "坚韧"; case "I": return "先机"; default: return "魔力"; }
        }
        public static RuntimeSkillRecord Pick(int tier, string genre, string role = "filler")
        {
            string axis = Axis(genre); var choices = new List<RuntimeSkillRecord>();
            foreach (var row in Data.skills)
                if (row.tier == tier && row.axis == axis && (role != "backup" || row.skill.limit >= 999 && row.skill.turnLower == 0 && row.skill.turnUpper == 0)) choices.Add(row);
            if (choices.Count == 0 && role == "backup" && tier > 1) return Pick(tier-1, genre, role);
            if (choices.Count == 0) throw new InvalidOperationException("Missing skill tier/axis");
            if (role == "carry")
            {
                choices.Sort((a,b) => (b.skill.mainParam*(1+b.skill.baseCrit)+b.skill.subParam).CompareTo(a.skill.mainParam*(1+a.skill.baseCrit)+a.skill.subParam));
                choices.RemoveRange(Math.Max(8,choices.Count/2), choices.Count-Math.Max(8,choices.Count/2));
            }
            return JsonUtility.FromJson<RuntimeSkillRecord>(JsonUtility.ToJson(choices[UnityEngine.Random.Range(0,choices.Count)]));
        }
        public static RuntimeEncounter Encounter(int stage, string difficulty)
        {
            Stage(stage);
            foreach (var row in Data.enemies) if (row.stage == stage && row.difficulty == difficulty)
                return JsonUtility.FromJson<RuntimeEncounter>(JsonUtility.ToJson(row));
            throw new ArgumentException("Unknown difficulty");
        }
    }
}
