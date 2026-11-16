using System;
using System.Collections.Generic;

namespace LegionBattle.Battle
{
    // V11 numerical runtime -> existing visual report contract.
    public class BattleEngine
    {
        public BattleTroop leftTroop, rightTroop;
        public int currentRound = 1, currentActingTroopId = 1, winnerTroopId;
        public bool isBattleOver, isCensored;
        public event Action<BattleTurnReport> OnTurnCompleted;
        public CombatRuntime Runtime { get; private set; }
        private BattleTurnReport pendingPresentationReport, publishedPresentationReport;
        public BattleEngine() { }
        public BattleEngine(BattleTroop left, BattleTroop right) { InitBattle(left, right); }
        public void InitBattle(BattleTroop left, BattleTroop right, int? seed = null)
        {
            if (left == null || right == null) throw new ArgumentNullException("troop");
            leftTroop = left; rightTroop = right;
            var rng = seed.HasValue ? new Random(seed.Value) : new Random();
            Runtime = new CombatRuntime(left.CreateRuntime(), right.CreateRuntime(), rng.NextDouble);
            currentRound = 1; isBattleOver = isCensored = false; winnerTroopId = 0;
            left.Synchronize(Runtime.teams[0]); right.Synchronize(Runtime.teams[1]);
            currentActingTroopId = 0; // The numerical runtime chooses order at each round start.
            pendingPresentationReport = publishedPresentationReport = null;
        }
        public BattleTurnReport ExecuteNextTurn() { return ExecuteNextTurn(true); }
        internal BattleTurnReport ExecuteNextTurn(bool publishImmediately)
        {
            if (Runtime == null) throw new InvalidOperationException("Battle is not initialized");
            CombatAction action = Runtime.Next();
            leftTroop.Synchronize(Runtime.teams[0]); rightTroop.Synchronize(Runtime.teams[1]);
            BattleTroop acting = action.side == 0 ? leftTroop : rightTroop;
            BattleTroop defending = action.side == 0 ? rightTroop : leftTroop;
            BattleSkill skill = action.owner >= 0 && !action.normal ? acting.members[action.owner].skills[0] : null;
            if (action.normal) skill = BattleSkill.CreateDefaultMelee();
            currentRound = Runtime.Round; isBattleOver = Runtime.Ended; isCensored = Runtime.Censored;
            winnerTroopId = Runtime.Winner < 0 ? 0 : Runtime.Winner == 0 ? leftTroop.troopId : rightTroop.troopId;
            currentActingTroopId = acting.troopId;
            var report = new BattleTurnReport {
                round = action.round, actingTroopId = acting.troopId, defenderTroopId = defending.troopId,
                actingTroopName = acting.troopName, defenderTroopName = defending.troopName,
                skill = skill, casterMemberName = action.owner >= 0 ? acting.members[action.owner].characterName : acting.troopName,
                isDodge = action.missed, isCrit = action.critical, isTrueDamage = action.pure,isNormalAttack=action.normal,
                isForcedHit=action.forcedHit,isAbsoluteDodge=action.absoluteEvaded,
                damageDealt = (int)Math.Round(action.damage), healDone = (int)Math.Round(action.healing),
                preTurnDamage = (int)Math.Round(action.preDamage), postTurnDamage = (int)Math.Round(action.postDamage),
                actingCurrentBP = acting.currentBP, actingMaxBP = acting.maxBP,
                defenderCurrentBP = defending.currentBP, defenderMaxBP = defending.maxBP,
                isBattleEnd = isBattleOver, winnerTroopId = winnerTroopId, isCensored = isCensored,
                exactLeftBP = Runtime.teams[0].bp, exactRightBP = Runtime.teams[1].bp,
                casterMemberIndex = action.owner,
                chainDepth=action.chainDepth,hasContinuation=action.hasContinuation,scholarTarget=action.scholarTarget,scholarRestored=action.scholarRestored,
                heroineFirst=action.heroineFirst,bondDirectMultiplier=action.bondDirectMultiplier,bondOutputMultiplier=action.bondOutputMultiplier,
                engineerQueued=action.engineerQueued,appliedHealPenalty=action.appliedHealPenalty,healingPrevented=action.healingPrevented,
                stolenStats=action.stolenStats==null?null:(double[])action.stolenStats.Clone(),killerMarked=action.killerMarked,coinsEarned=action.coinsEarned,maidCast=action.maidCast,fruitEvent=action.fruitEvent
            };
            report.logText = action.missed ? $"第 {action.round} 回合：{report.casterMemberName}【{skill?.name}】被闪避。" :
                $"第 {action.round} 回合：{report.casterMemberName}【{skill?.name ?? "持续效果"}】，伤害{report.damageDealt:N0}，恢复{report.healDone:N0}。";
            if (isBattleOver) report.logText += isCensored ? " 达到回合上限，未决。" : winnerTroopId == 0 ? " 双方同时战力耗尽。" : $" { (winnerTroopId == leftTroop.troopId ? leftTroop.troopName : rightTroop.troopName) }获胜。";
            pendingPresentationReport = report;
            if (publishImmediately) PublishPresentationCue(report);
            return report;
        }
        internal void PublishPresentationCue(BattleTurnReport report)
        {
            if (report == publishedPresentationReport) return;
            if (report != pendingPresentationReport) throw new InvalidOperationException("Presentation report is no longer current");
            publishedPresentationReport = report;
            OnTurnCompleted?.Invoke(report);
        }
        public List<BattleTurnReport> SimulateFullBattle(int maxRounds = 120)
        {
            var result = new List<BattleTurnReport>();
            while (!isBattleOver && currentRound <= maxRounds) result.Add(ExecuteNextTurn());
            return result;
        }
    }
}
