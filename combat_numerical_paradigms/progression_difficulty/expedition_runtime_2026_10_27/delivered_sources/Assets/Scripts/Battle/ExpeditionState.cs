using System;
using System.Collections.Generic;

namespace LegionBattle.Battle
{
    // Owned and saved by the caller, never by a battle scene. No RNG or region policy here.
    [Serializable] public sealed class ExpeditionState
    {
        public int version = 1;
        public string troopId;
        // Nonnegative log losses, in BP / C / R / I / M order. Remaining fraction = exp(-wear).
        public double[] wear = new double[5];
        public int victoriesSinceRest;
        public List<string> settledOperations = new List<string>();

        public void Validate()
        {
            if (version != 1 || string.IsNullOrWhiteSpace(troopId) || victoriesSinceRest < 0 || settledOperations == null)
                throw new ArgumentException("Invalid expedition state");
            ValidateWear(wear);
            var unique = new HashSet<string>();
            foreach (string id in settledOperations)
                if (string.IsNullOrWhiteSpace(id) || !unique.Add(id)) throw new ArgumentException("Invalid persisted settlement IDs");
        }
        public CombatPersistentLimits BattleLimits()
        {
            Validate();
            return new CombatPersistentLimits { bp=Math.Exp(-wear[0]), courage=Math.Exp(-wear[1]), resilience=Math.Exp(-wear[2]),
                initiative=Math.Exp(-wear[3]), magic=Math.Exp(-wear[4]) };
        }
        // Caller supplies the region's rolled losses. Zeroes record a resolved battle with no loss.
        // Interrupted, failed and unresolved battles cannot silently consume travel distance.
        public bool SettleBattle(string encounterId, BattleSceneResult result, double[] losses)
        {
            if (result == null || !result.initialized || (result.outcome != BattleSceneOutcome.LeftWon &&
                result.outcome != BattleSceneOutcome.RightWon && result.outcome != BattleSceneOutcome.Draw)) return false;
            Validate();
            if (AlreadySettled(encounterId)) return false;
            var after = AfterLoss(losses);
            int victories = result.outcome == BattleSceneOutcome.LeftWon ? checked(victoriesSinceRest+1) : victoriesSinceRest;
            Commit(encounterId, after, victories);
            return true;
        }
        // Travel/dungeon events use the same losses without claiming a battle victory.
        public bool ApplyEventLoss(string operationId, double[] losses)
        {
            Validate();
            if (AlreadySettled(operationId)) return false;
            Commit(operationId, AfterLoss(losses), victoriesSinceRest);
            return true;
        }
        // Restores a fraction of the MISSING cap, not a fraction of log wear.
        // Example: current cap .60, restoration .50 => new cap .80.
        public bool RestoreMissingCaps(string operationId, double[] fractions)
        {
            Validate();
            if (AlreadySettled(operationId)) return false;
            ValidateFractions(fractions, true);
            var after = new double[5];
            for (int i=0; i<5; i++)
            {
                double cap = Math.Exp(-wear[i]);
                after[i] = fractions[i] == 0 ? wear[i] : -Math.Log(cap + fractions[i]*(1-cap));
            }
            Commit(operationId, after, victoriesSinceRest);
            return true;
        }
        // Full rest also starts a new journey count. Ordinary supplies do not.
        public bool Rest(string operationId)
        {
            Validate();
            if (AlreadySettled(operationId)) return false;
            Commit(operationId, new double[5], 0);
            return true;
        }
        private bool AlreadySettled(string id)
        {
            if (string.IsNullOrWhiteSpace(id)) throw new ArgumentException("Settlement ID is required");
            return settledOperations.Contains(id);
        }
        private void Commit(string id, double[] after, int victories)
        {
            ValidateWear(after); // Validate all channels before mutating any state.
            settledOperations.Add(id); wear=after; victoriesSinceRest=victories;
        }
        private double[] AfterLoss(double[] losses)
        {
            ValidateFractions(losses, false);
            var after = new double[5];
            for (int i=0; i<5; i++) after[i] = wear[i] - Math.Log(1-losses[i]);
            return after;
        }
        private static void ValidateWear(double[] values)
        {
            if (values == null || values.Length != 5) throw new ArgumentException("Five wear channels are required");
            foreach (double value in values)
                if (double.IsNaN(value) || double.IsInfinity(value) || value < 0 || Math.Exp(-value) <= 0)
                    throw new ArgumentException("Wear must leave a finite positive cap");
        }
        private static void ValidateFractions(double[] values, bool allowOne)
        {
            if (values == null || values.Length != 5) throw new ArgumentException("Five fractions are required");
            foreach (double value in values)
                if (double.IsNaN(value) || double.IsInfinity(value) || value < 0 || value > 1 || (!allowOne && value == 1))
                    throw new ArgumentException("Invalid loss or restoration fraction");
        }
    }
}
