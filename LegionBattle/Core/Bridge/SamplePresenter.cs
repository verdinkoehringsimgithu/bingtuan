using System;
using LegionBattle.Core.Data;
using LegionBattle.Core.Enums;
using LegionBattle.Core.Simulation;

namespace LegionBattle.Core.Bridge
{
    /// <summary>
    /// 轻量级事件总线，方便 Unity 侧各类 UI 组件解耦监听战斗事件
    /// </summary>
    public static class BattleEventBus
    {
        public static event Action<Legion, Legion> OnBattleStart;
        public static event Action<int, Legion, Legion> OnTurnStart;
        public static event Action<Legion, ActiveSkillData> OnSkillCast;
        public static event Action<Legion, long, DamageType> OnDamageDealt;
        public static event Action<Legion, long, bool> OnHealApplied;
        public static event Action<Legion> OnEvasion;
        public static event Action<Legion, string, long> OnBuffTick;
        public static event Action<Legion, int> OnDeathDefy;
        public static event Action<int> OnBerserkActivated;
        public static event Action<BattleResult> OnBattleEnd;

        public static void PublishBattleStart(Legion l, Legion r) => OnBattleStart?.Invoke(l, r);
        public static void PublishTurnStart(int turn, Legion a, Legion d) => OnTurnStart?.Invoke(turn, a, d);
        public static void PublishSkillCast(Legion c, ActiveSkillData s) => OnSkillCast?.Invoke(c, s);
        public static void PublishDamage(Legion t, long d, DamageType type) => OnDamageDealt?.Invoke(t, d, type);
        public static void PublishHeal(Legion t, long h, bool o) => OnHealApplied?.Invoke(t, h, o);
        public static void PublishEvasion(Legion t) => OnEvasion?.Invoke(t);
        public static void PublishBuffTick(Legion t, string b, long d) => OnBuffTick?.Invoke(t, b, d);
        public static void PublishDeathDefy(Legion t, int rem) => OnDeathDefy?.Invoke(t, rem);
        public static void PublishBerserk(int turn) => OnBerserkActivated?.Invoke(turn);
        public static void PublishBattleEnd(BattleResult res) => OnBattleEnd?.Invoke(res);

        public static void ClearAllSubscriptions()
        {
            OnBattleStart = null;
            OnTurnStart = null;
            OnSkillCast = null;
            OnDamageDealt = null;
            OnHealApplied = null;
            OnEvasion = null;
            OnBuffTick = null;
            OnDeathDefy = null;
            OnBerserkActivated = null;
            OnBattleEnd = null;
        }
    }

    /// <summary>
    /// 示例战斗表现层实现（可直接用于控制台输出或 Unity 调试面板显示）
    /// </summary>
    public class SamplePresenter : IBattlePresenter
    {
        public Action<string> LogHandler { get; set; } = Console.WriteLine;

        public void OnBattleStart(Legion left, Legion right)
        {
            LogHandler?.Invoke($"[BATTLE START] {left.Name} (VIG: {left.CurrentVigor:N0}) vs {right.Name} (VIG: {right.CurrentVigor:N0})");
        }

        public void OnTurnStart(int turnNumber, Legion attacker, Legion defender)
        {
            LogHandler?.Invoke($"\n--- Round {turnNumber}: [{attacker.Name}] Turn ---");
        }

        public void OnSkillCast(Legion caster, ActiveSkillData skill)
        {
            LogHandler?.Invoke($"  ★ [{caster.Name}] Casts [{skill.Name}] ({skill.EffectType})");
        }

        public void OnDamageDealt(Legion target, long damage, DamageType type)
        {
            string typeLabel = type switch
            {
                DamageType.Havoc => "CRITICAL HAVOC!!",
                DamageType.Precision => "TRUE PRECISION (Unblockable)!",
                DamageType.True => "PURE TRUE DAMAGE!",
                _ => "Physical Hit"
            };
            LogHandler?.Invoke($"    -> {typeLabel} Hits [{target.Name}] for {damage:N0} damage! (Remaining VIG: {target.CurrentVigor:N0})");
        }

        public void OnHealApplied(Legion target, long heal, bool isOverheal)
        {
            string overTag = isOverheal ? "[OVERHEAL!]" : "";
            LogHandler?.Invoke($"    -> [{target.Name}] Heals {heal:N0} Vigor {overTag}! (Current VIG: {target.CurrentVigor:N0})");
        }

        public void OnEvasion(Legion target)
        {
            LogHandler?.Invoke($"    -> MISS! [{target.Name}] EVADED the attack!");
        }

        public void OnBuffApplied(Legion target, BuffData buff)
        {
            LogHandler?.Invoke($"    -> [{target.Name}] Afflicted by {buff.Name}");
        }

        public void OnBuffTick(Legion target, string buffName, long tickDamage)
        {
            LogHandler?.Invoke($"    -> [DOT {buffName}] ticks [{target.Name}] for {tickDamage:N0} damage!");
        }

        public void OnDeathDefy(Legion target, int remainingCount)
        {
            LogHandler?.Invoke($"    -> [DEATH DEFY TRIGGERED!] [{target.Name}] survives lethal blow! (Remaining Defies: {remainingCount})");
        }

        public void OnShieldBreak(Legion target)
        {
            LogHandler?.Invoke($"    -> [SHIELD BROKEN!] [{target.Name}] shield depleted!");
        }

        public void OnBerserkActivated(int turnNumber)
        {
            LogHandler?.Invoke($"\n  ⚡⚡ [TIMEOUT BERSERK ACTIVATED at Turn {turnNumber}] Damage escalates every turn! ⚡⚡");
        }

        public void OnBattleEnd(BattleResult result)
        {
            LogHandler?.Invoke($"\n[BATTLE END] Result: {result.ToString().ToUpper()}");
        }
    }
}
