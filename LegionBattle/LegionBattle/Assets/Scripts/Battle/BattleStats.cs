using System;

namespace LegionBattle.Battle
{
    [Serializable]
    public struct BattleStats
    {
        public int maxBP, currentBP, shieldBP;
        public int speed; // 先机；CSV键
        public int defense; // 坚韧
        public int dodge; // 勇气；CSV键
        public int authority; // 魔力；CSV键
    }
}
