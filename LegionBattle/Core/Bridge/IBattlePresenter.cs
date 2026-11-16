using LegionBattle.Core.Data;
using LegionBattle.Core.Enums;
using LegionBattle.Core.Simulation;

namespace LegionBattle.Core.Bridge
{
    /// <summary>
    /// 战斗演出表现层接口（留给 Unity MonoBehaviour / UI 控制器实现）
    /// </summary>
    public interface IBattlePresenter
    {
        void OnBattleStart(Legion left, Legion right);
        void OnTurnStart(int turnNumber, Legion attacker, Legion defender);
        void OnSkillCast(Legion caster, ActiveSkillData skill);
        void OnDamageDealt(Legion target, long damage, DamageType type);
        void OnHealApplied(Legion target, long heal, bool isOverheal);
        void OnEvasion(Legion target);
        void OnBuffApplied(Legion target, BuffData buff);
        void OnBuffTick(Legion target, string buffName, long tickDamage);
        void OnDeathDefy(Legion target, int remainingCount);
        void OnShieldBreak(Legion target);
        void OnBerserkActivated(int turnNumber);
        void OnBattleEnd(BattleResult result);
    }

    /// <summary>
    /// 音效触发接口
    /// </summary>
    public interface IBattleAudio
    {
        void PlaySkillVoice(int skillAnimationId);
        void PlayHitSound(DamageType type);
        void PlayEvasionSound();
        void PlayHealSound();
        void PlayWinJingle();
        void PlayDefeatJingle();
    }
}
