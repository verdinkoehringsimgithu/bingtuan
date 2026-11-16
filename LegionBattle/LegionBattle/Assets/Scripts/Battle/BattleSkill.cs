using System;

namespace LegionBattle.Battle
{
    public enum BattleSkillEffectType
    {
        Melee = 1,                      // 普通攻击
        Critical = 2,                   // 暴击
        IncreaseDamage = 3,             // 伤害加深 / 精准
        Rage = 4,                       // 怒气伤害 (基于自身已损战力)
        TrueDamage = 5,                 // 纯粹伤害 (无视防御)
        DamageByEnemyCurrentBP = 6,     // 反噬敌当
        DamageByEnemyMaxBP = 7,         // 反噬敌初
        DamageByEnemyLossBP = 8,        // 反噬敌损
        BPSteal = 9,                    // 战力吸收 (吸血)
        HealBySelfCurrentBP = 10,       // 战力提升己当
        HealBySelfMaxBP = 11,           // 战力提升己初
        HealByEnemyCurrentBP = 12,      // 战力提升敌当
        HealByEnemyMaxBP = 13,          // 战力提升敌初
        SwapBPPercent = 14              // 战力百分比互换
    }

    [Serializable]
    public class BattleSkill
    {
        public int id, rarityTier=1;
        public string name="普通攻击", desc="";
        public CombatSkill combat=new CombatSkill();
        public int[] levelOneStats, levelThirtyStats;
        // Presentation metadata; numerical behavior is exclusively in combat.
        public BattleSkillEffectType effectType=BattleSkillEffectType.Melee;
        public int bufferId, animationId=1329, hitReactionType=1;
        public string effectCnName="大红圆斩", effectFolder="fx2_slash_large_red";
        public float GetEffectiveTriggerChance(){return (float)Math.Min(100,Math.Max(0,combat.chance));}
        public bool CanTrigger(int round,float self,float enemy,int used){return combat.Eligible(round,self,enemy,used,0);}
        public static BattleSkill CreateDefaultMelee()
        {
            return new BattleSkill { id=1000001,name="普通攻击",combat=new CombatSkill { name="普通攻击",chance=100 },desc="造成基础战力普通伤害。" };
        }
    }
}
