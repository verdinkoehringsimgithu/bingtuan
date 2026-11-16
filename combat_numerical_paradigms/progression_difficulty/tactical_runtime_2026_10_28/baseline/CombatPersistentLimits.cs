using System;

namespace LegionBattle.Battle
{
    // Remaining fractions of the original BP / C / R / I / M budgets.
    // Separate from combat statuses: cleansing cannot remove travel losses.
    [Serializable] public sealed class CombatPersistentLimits
    {
        public double bp = 1, courage = 1, resilience = 1, initiative = 1, magic = 1;

        public CombatPersistentLimits Clone()
        {
            Validate();
            return new CombatPersistentLimits { bp=bp, courage=courage, resilience=resilience, initiative=initiative, magic=magic };
        }
        public void Validate()
        {
            foreach (double value in new[] { bp, courage, resilience, initiative, magic })
                if (double.IsNaN(value) || double.IsInfinity(value) || value <= 0 || value > 1)
                    throw new ArgumentException("Persistent limit fractions must be finite and in (0,1]");
        }
        public double Stat(int axis)
        {
            switch (axis)
            {
                case 0: return courage;
                case 1: return resilience;
                case 2: return initiative;
                case 3: return magic;
                default: throw new ArgumentOutOfRangeException("axis");
            }
        }
    }
}
