using System;

namespace LegionBattle.Battle
{
    /// <summary>
    /// 单回合战斗战报 (纯数据驱动，完全解耦 UI 与视图渲染)
    /// </summary>
    [Serializable]
    public class BattleTurnReport
    {
        public int round;
        public int casterMemberIndex = -1;
        public int postTurnDamage;
        public bool isCensored;
        public double exactLeftBP, exactRightBP;
        public int actingTroopId;       // 1: 左军, 2: 右军
        public int defenderTroopId;     // 受击方

        public string actingTroopName;
        public string defenderTroopName;

        public BattleSkill skill;
        public string casterMemberName; // 发动技能的角色名字

        public bool isDodge;            // 对方是否闪避
        public bool isForcedHit,isAbsoluteDodge;
        public bool isCrit;             // 是否暴击
        public bool isTrueDamage;       // 是否纯粹伤害
        public int damageDealt;         // 造成的实际伤害
        public int healDone;            // 恢复的战力值

        public int preTurnDamage;       // 回合前结算的异常掉血 (流血/中毒)
        public string preTurnDesc;

        public bool isResistLethal;     // 是否触发名刀锁战力

        public int actingCurrentBP;
        public int actingMaxBP;
        public int defenderCurrentBP;
        public int defenderMaxBP;

        public string logText;          // 自然语言战报条目

        public bool isBattleEnd;        // 战斗是否分出胜负
        public int winnerTroopId;       // 获胜方 ID (0 表示战斗仍在进行)
    }
}
