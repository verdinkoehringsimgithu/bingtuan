using System.Collections.Generic;
using LegionBattle.Core.Enums;

namespace LegionBattle.Core.Simulation
{
    /// <summary>
    /// 单回合战斗切片回放记录（与原版战斗回放五元组数据精准对齐）
    /// </summary>
    public class BattleTurnRecord
    {
        public int TurnIndex { get; set; }
        public bool CasterIsLeft { get; set; }
        public int SkillId { get; set; }
        public bool IsEvaded { get; set; }
        public long DamageDealt { get; set; }
        public long HealApplied { get; set; }
        public DamageType DamageType { get; set; }

        public long LeftVigor { get; set; }
        public long LeftShield { get; set; }
        public long RightVigor { get; set; }
        public long RightShield { get; set; }

        public int BufferId1 { get; set; }
        public int BufferId2 { get; set; }
        public int BufferId3 { get; set; }
    }

    /// <summary>
    /// 全局战斗回放对象
    /// </summary>
    public class BattleRecord
    {
        public BattleResult Result { get; set; }
        public int TotalTurns { get; set; }
        public int Seed { get; set; }

        public long InitialLeftVigor { get; set; }
        public long InitialRightVigor { get; set; }

        public List<BattleTurnRecord> Turns { get; } = new List<BattleTurnRecord>();

        public void AddTurn(BattleTurnRecord turn)
        {
            Turns.Add(turn);
        }
    }
}
