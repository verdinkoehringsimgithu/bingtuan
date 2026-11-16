using System;
using System.Collections.Generic;
using UnityEngine;

namespace LegionBattle.Battle
{
    public static class BattleRosterStrategy
    {
        public class DraftResult
        {
            public List<BattleMember> selected30 = new List<BattleMember>();
            public float specialConditionChanceTotal, normalConditionChanceTotal;
            public double totalBP;
            public BattleStats totalStats;
        }
        public static DraftResult BuildStrategyRoster(CharacterDatabase database, string teamName = "策略军团", int stage = 6, string genre = "C_I", bool fullLevel = true, bool topEquipment = false)
        {
            if (database == null || database.characters == null || database.characters.Count == 0) throw new ArgumentException("Missing character database");
            if (Array.IndexOf(new[] { "C_I", "C_R", "M_I", "M_R", "M_C", "R_I" }, genre) < 0) throw new ArgumentException("Unknown flow");
            var rule = BattleRuntimeCatalogue.Stage(stage);
            RuntimeGearRule gear = Array.Find(rule.gear, x => x.genre == genre);
            var result = new DraftResult();
            int carry = Math.Min(2, rule.members), backup = Math.Min(4, rule.members-carry);
            int mainCount = (int)Math.Round(rule.members*.7);
            var axes = new List<string>();
            for (int i=0;i<rule.members;i++) axes.Add(i<mainCount ? genre.Substring(0,1) : genre.Substring(2,1));
            for (int i=axes.Count-1;i>0;i--) { int j=UnityEngine.Random.Range(0,i+1); string axis=axes[i]; axes[i]=axes[j]; axes[j]=axis; }
            for (int pos=0;pos<rule.members;pos++)
            {
                string role = pos<carry ? "carry" : pos<carry+backup ? "backup" : "filler";
                int tier = role=="carry" ? rule.tier : role=="backup" ? Math.Min(3,Math.Max(1,rule.tier-1)) : Math.Max(1,rule.tier-1-UnityEngine.Random.Range(0,2));
                var appearances = database.characters.FindAll(x => x != null && x.rarity == tier);
                if (appearances.Count==0) appearances = database.characters.FindAll(x => x != null);
                if (appearances.Count==0) throw new ArgumentException("Character database contains no valid entries");
                var member = BattleMember.FromSheetData(appearances[UnityEngine.Random.Range(0,appearances.Count)],pos);
                var skill = BattleSkillDatabase.GenerateRandomSkill(tier,axes[pos],role);
                member.rarityTier = skill.rarityTier;
                member.skills.Clear(); member.skills.Add(skill);
                InitializeTierBaseStats(member,skill);
                SetLevel(member, fullLevel ? MaxLevel : UnityEngine.Random.Range(rule.lower,rule.upper+1));
                member.baseBP = rule.bp/(double)rule.members;
                member.equipment = new CombatItem { kind = "basic" };
                int first = AxisIndex(genre[0]), second=AxisIndex(genre[2]);
                member.equipment.stats[first] = gear.points*.67;
                member.equipment.stats[second] = gear.points*.33;
                if (topEquipment)
                    foreach (var top in gear.tops)
                        if (top.owner==pos) { member.equipment.kind=top.kind; member.equipment.value=top.value; member.equipment.top=true; }
                result.selected30.Add(member);
                result.totalBP += member.baseBP;
                result.totalStats.dodge+=member.dodge; result.totalStats.defense+=member.defense;
                result.totalStats.speed+=member.speed; result.totalStats.authority+=member.authority;
            }
            return result;
        }
        private static int AxisIndex(char axis) { return axis=='C' ? 0 : axis=='R' ? 1 : axis=='I' ? 2 : 3; }
        public static void ConfigureReferenceMember(BattleMember member, BattleSkill skill, int stage, string genre, int level, bool topEquipment)
        {
            var rule=BattleRuntimeCatalogue.Stage(stage); var gear=Array.Find(rule.gear,x=>x.genre==genre);
            InitializeTierBaseStats(member,skill); SetLevel(member,level); member.baseBP=rule.bp/(double)rule.members;
            member.equipment=new CombatItem { kind="basic" };
            member.equipment.stats[AxisIndex(genre[0])]=gear.points*.67;
            member.equipment.stats[AxisIndex(genre[2])]=gear.points*.33;
            if(topEquipment) foreach(var top in gear.tops) if(top.owner==member.memberIndex)
                { member.equipment.kind=top.kind; member.equipment.value=top.value; member.equipment.top=true; }
        }
        public static DraftResult BuildEncounterRoster(CharacterDatabase database, int stage, string difficulty)
        {
            var encounter=BattleRuntimeCatalogue.Encounter(stage,difficulty); var result=new DraftResult();
            if (database==null || database.characters==null || database.characters.Count==0) throw new ArgumentException("Missing character database");
            for (int i=0;i<encounter.members.Length;i++)
            {
                var source=encounter.members[i];
                var appearances=database.characters.FindAll(x => x!=null && x.rarity==source.skill.tier);
                if(appearances.Count==0) appearances=database.characters.FindAll(x=>x!=null);
                var appearance=appearances[i%appearances.Count];
                var member=BattleMember.FromSheetData(appearance,i);
                member.level=encounter.levels[i]; member.baseBP=source.bp;
                member.rarityTier=source.skill.tier;
                member.dodge=(int)source.stats[0]; member.defense=(int)source.stats[1]; member.speed=(int)source.stats[2]; member.authority=(int)source.stats[3];
                // The name/effect pipeline remains owned by BattleSkillDatabase.
                var record=BattleRuntimeCatalogue.Source(source.skill.tier,source.skill.axis,source.sample);
                var skill=BattleSkillDatabase.GenerateRandomSkill(source.skill.tier,source.skill.axis,"filler",record);
                skill.combat=source.skill; skill.combat.name=skill.name;
                member.skills.Clear(); member.skills.Add(skill); member.equipment=source.item;
                result.selected30.Add(member); result.totalBP+=member.baseBP;
            }
            return result;
        }
        // 1级沿用原投放，30级采用实测预算；四维顺序 C/R/I/M。
        public const int MaxLevel = 30;
        private static readonly int[] StartMin = { 0, 1, 3, 5, 8, 12 };
        private static readonly int[] StartMax = { 0, 2, 4, 7, 11, 16 };
        private static readonly int[] EndMin = { 36, 54, 54, 54, 55, 62 };
        private static readonly int[] EndMax = { 44, 66, 66, 67, 68, 75 };

        public static void InitializeTierBaseStats(BattleMember member, BattleSkill skill = null)
        {
            if (member == null) return;
            if (skill != null && skill.levelOneStats != null && skill.levelThirtyStats != null)
            {
                member.levelOneStats = (int[])skill.levelOneStats.Clone();
                member.levelThirtyStats = (int[])skill.levelThirtyStats.Clone();
                SetLevel(member, 1);
                return;
            }
            int t = Mathf.Clamp(member.rarityTier, 1, 6) - 1;
            int primary = skill == null ? 3 : AxisIndex(skill.combat.axis[0]);
            member.levelOneStats = AllocateBudget(UnityEngine.Random.Range(StartMin[t], StartMax[t] + 1), primary, false);
            member.levelThirtyStats = AllocateBudget(UnityEngine.Random.Range(EndMin[t], EndMax[t] + 1), primary, true);
            SetLevel(member, 1);
        }

        private static int[] AllocateBudget(int budget, int primary, bool endpoint)
        {
            int secondary = primary == 0 ? 3 : primary == 3 ? 1 : 0;
            int third = primary == 2 ? 3 : 2;
            int remaining = 6 - primary - secondary - third;
            int[] stats = new int[4];
            double p = endpoint ? 0.6931515783314715 : 0.6;
            double q = endpoint ? 0.10771411490803917 : 0.2;
            stats[primary] = (int)Math.Round(budget * p);
            stats[secondary] = (int)Math.Round(budget * q);
            stats[third] = (int)Math.Round(budget * (1 - p - q) / 2);
            stats[remaining] = budget - stats[primary] - stats[secondary] - stats[third];
            return stats;
        }

        // 与 progression_difficulty/model.py 同步：逐级按最大缺口分配整数增量。
        public static int[] GrowthStats(int level, int[] start, int[] end, double power = 1.0)
        {
            if (level < 1 || level > MaxLevel) throw new ArgumentOutOfRangeException("level");
            if (start == null || end == null || start.Length != 4 || end.Length != 4 ||
                power <= 0 || double.IsNaN(power) || double.IsInfinity(power))
                throw new ArgumentException("Invalid growth endpoints or power");
            int[] current = (int[])start.Clone();
            int first = 0, last = 0;
            for (int i = 0; i < 4; i++)
            {
                if (start[i] < 0 || end[i] < start[i]) throw new ArgumentException("Growth must be nondecreasing");
                first += start[i]; last += end[i];
            }
            for (int step = 2; step <= level; step++)
            {
                double fraction = Math.Pow((step - 1) / 29.0, power);
                int target = (int)Math.Round(first + (last - first) * fraction);
                int total = 0; for (int i = 0; i < 4; i++) total += current[i];
                while (total < target)
                {
                    int axis = 0;
                    for (int i = 1; i < 4; i++)
                        if (start[i] + (end[i] - start[i]) * fraction - current[i] >
                            start[axis] + (end[axis] - start[axis]) * fraction - current[axis]) axis = i;
                    current[axis]++; total++;
                }
            }
            return current;
        }

        public static void SetLevel(BattleMember member, int level)
        {
            if (member == null) return;
            int[] stats = GrowthStats(level, member.levelOneStats, member.levelThirtyStats);
            member.level = level;
            member.dodge = stats[0]; member.defense = stats[1];
            member.speed = stats[2]; member.authority = stats[3];
        }

        public static void UpgradeToMaxLevel(BattleMember member)
        {
            if (member == null) return;
            if (member.levelOneStats == null || member.levelThirtyStats == null)
                InitializeTierBaseStats(member, member.skills.Count > 0 ? member.skills[0] : null);
            SetLevel(member, MaxLevel);
        }
    }
}
