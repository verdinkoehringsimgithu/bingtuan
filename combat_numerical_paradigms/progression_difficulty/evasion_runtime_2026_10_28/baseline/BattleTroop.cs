using System;
using System.Collections.Generic;

namespace LegionBattle.Battle
{
    [Serializable]
    public class BattleTroop
    {
        public int troopId;
        public string troopName;
        public List<BattleMember> members = new List<BattleMember>();
        public int maxBP, currentBP, shieldBP;
        public int speed, defense, dodge, authority;
        public double alpha = 1, beta = 1, gamma, delta, theta, mu = 1;
        public CombatPersistentLimits persistentLimits;
        public OpeningBondRules openingBonds;
        // Editor reset controls retain these fields; runtime status lives in CombatTeam.
        public List<BattleBuffInstance> buffs = new List<BattleBuffInstance>();
        public int exhaustTurns, resistLethalCount;
        public bool IsDead => currentBP <= 0;
        public float BpRatio => maxBP > 0 ? (float)currentBP / maxBP : 0;
        public float BpPercent => BpRatio * 100;
        public BattleTroop(int id, string name) { troopId = id; troopName = name; }
        public void InitializeFromMembers(List<BattleMember> roster)
        {
            members = roster == null ? new List<BattleMember>() : new List<BattleMember>(roster);
            alpha = beta = mu = 1; gamma = delta = theta = 0;
            buffs.Clear(); exhaustTurns = resistLethalCount = 0;
            Synchronize(CreateRuntime());
        }
        public CombatTeam CreateRuntime()
        {
            var roster = new List<CombatMember>();
            foreach (var m in members)
            {
                if (m == null || m.level < 1 || m.level > BattleRosterStrategy.MaxLevel) throw new ArgumentException("Invalid member level");
                if (m.skills.Count > 1) throw new ArgumentException("One active skill per member");
                roster.Add(new CombatMember { name = m.characterName, bp = m.baseBP, traits = m.traits == null ? null : m.traits.Clone(),
                    stats = new double[] { m.dodge, m.defense, m.speed, m.authority },
                    skill = m.skills.Count == 0 ? null : m.skills[0].combat, item = m.equipment });
            }
            var team = new CombatTeam(roster, persistentLimits, openingBonds); team.Macro(alpha, beta, gamma, delta, theta, mu); return team;
        }
        public void Synchronize(CombatTeam team)
        {
            maxBP = (int)Math.Round(team.maxBP); currentBP = (int)Math.Ceiling(Math.Max(0, team.bp)); shieldBP = (int)Math.Round(team.shield);
            dodge = (int)Math.Round(team.Effective(0)); defense = (int)Math.Round(team.Effective(1));
            speed = (int)Math.Round(team.Effective(2)); authority = (int)Math.Round(team.Effective(3));
        }
    }
}
