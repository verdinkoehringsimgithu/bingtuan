using System;

namespace LegionBattle.Battle
{
    public enum BattleBuffType
    {
        Weak = 1,              // 虚弱: 攻击时伤害削弱 factor%
        SeriouslyInjured = 2,  // 重伤: 回复生命时治疗量削弱 factor%
        Bleed = 3,             // 流血: 回合前扣除当前战力 factor%
        Poison = 4,            // 中毒: 回合前扣除最大战力 factor%
        ResistLethal = 5,      // 受到致命伤保留1战力 (n 回合内有效)
        StatMod = 6            // 临时四维属性修改
    }

    [Serializable]
    public class BattleBuffInstance
    {
        public BattleBuffType type;
        public float factor;          // 系数 (例如 0.20 代表 20%)
        public int remainingTurns;    // 剩余持续回合数
        public string sourceSkill;    // 来源技能名

        public BattleBuffInstance(BattleBuffType type, float factor, int remainingTurns, string sourceSkill = "")
        {
            this.type = type;
            this.factor = factor;
            this.remainingTurns = remainingTurns;
            this.sourceSkill = sourceSkill;
        }
    }
}
