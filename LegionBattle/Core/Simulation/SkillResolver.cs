using System;
using LegionBattle.Core.Config;
using LegionBattle.Core.Data;
using LegionBattle.Core.Enums;

namespace LegionBattle.Core.Simulation
{
    /// <summary>
    /// 技能结算执行结果数据
    /// </summary>
    public class SkillResolutionResult
    {
        public ActiveSkillData ExecutedSkill { get; set; }
        public bool IsEvaded { get; set; }
        public long DamageDealt { get; set; }
        public long HealApplied { get; set; }
        public DamageType DamageType { get; set; }
        public bool TriggeredDeathDefy { get; set; }
        public int TurnFixed { get; set; }
    }

    /// <summary>
    /// 17种主动技能效果的具体执行器
    /// </summary>
    public static class SkillResolver
    {
        public static SkillResolutionResult Resolve(
            Legion caster,
            Legion receiver,
            ActiveSkillData skill,
            bool isEvaded,
            int currentTurn,
            FormulaConfig config)
        {
            var result = new SkillResolutionResult
            {
                ExecutedSkill = skill,
                IsEvaded = isEvaded,
                TurnFixed = skill.TurnFixed
            };

            // 精准技能强制不可闪避
            if (skill.IgnoreEvasion || skill.EffectType == SkillEffectType.PrecisionStrike || skill.EffectType == SkillEffectType.TrueDamage)
            {
                result.IsEvaded = false;
            }

            // 处理极意镜像（写轮眼 / 复制技能）
            if (skill.EffectType == SkillEffectType.MirrorArts)
            {
                if (receiver.LastTurnSkill != null && receiver.LastTurnSkill.EffectType != SkillEffectType.MirrorArts)
                {
                    // 递归调用被复制的技能
                    return Resolve(caster, receiver, receiver.LastTurnSkill, isEvaded, currentTurn, config);
                }
                // 若敌方上回合无技能，则降级为基础突袭
                skill = new ActiveSkillData
                {
                    Id = 1,
                    Name = "Strike",
                    EffectType = SkillEffectType.Strike,
                    Param = 100f
                };
            }

            float baseOutput = DamageCalculator.CalcBaseOutput(caster, config);
            float domMult = caster.GetDominanceMultiplierAgainst(receiver, config);

            // 17 种效果分流
            switch (skill.EffectType)
            {
                case SkillEffectType.Strike:
                    ResolveStrike(caster, receiver, skill, result, baseOutput, domMult, currentTurn, config);
                    break;

                case SkillEffectType.HavocStrike:
                    ResolveHavocStrike(caster, receiver, skill, result, baseOutput, domMult, currentTurn, config);
                    break;

                case SkillEffectType.PrecisionStrike:
                    ResolvePrecisionStrike(caster, receiver, skill, result, baseOutput, domMult, currentTurn, config);
                    break;

                case SkillEffectType.FuryStrike:
                    ResolveFuryStrike(caster, receiver, skill, result, domMult, currentTurn, config);
                    break;

                case SkillEffectType.TargetCurrentSiphon:
                    ResolveTargetCurrentSiphon(caster, receiver, skill, result, domMult, currentTurn, config);
                    break;

                case SkillEffectType.TargetMaxSiphon:
                    ResolveTargetMaxSiphon(caster, receiver, skill, result, domMult, currentTurn, config);
                    break;

                case SkillEffectType.TargetWoundSiphon:
                    ResolveTargetWoundSiphon(caster, receiver, skill, result, domMult, currentTurn, config);
                    break;

                case SkillEffectType.VigorDrain:
                    ResolveVigorDrain(caster, receiver, skill, result, baseOutput, domMult, currentTurn, config);
                    break;

                case SkillEffectType.SelfCurrentRestore:
                    ResolveSelfCurrentRestore(caster, receiver, skill, result, baseOutput, domMult, currentTurn, config);
                    break;

                case SkillEffectType.SelfMaxRestore:
                    ResolveSelfMaxRestore(caster, receiver, skill, result, baseOutput, domMult, currentTurn, config);
                    break;

                case SkillEffectType.TargetCurrentRestore:
                    ResolveTargetCurrentRestore(caster, receiver, skill, result, baseOutput, domMult, currentTurn, config);
                    break;

                case SkillEffectType.TargetMaxRestore:
                    ResolveTargetMaxRestore(caster, receiver, skill, result, baseOutput, domMult, currentTurn, config);
                    break;

                case SkillEffectType.TrueDamage:
                    ResolveTrueDamage(caster, receiver, skill, result, baseOutput, domMult, currentTurn, config);
                    break;

                case SkillEffectType.CataclysmA:
                    ResolveCataclysmA(caster, receiver, skill, result, currentTurn, config);
                    break;

                case SkillEffectType.CataclysmB:
                    ResolveCataclysmB(caster, receiver, skill, result, currentTurn, config);
                    break;

                case SkillEffectType.FateSwap:
                    ResolveFateSwap(caster, receiver, skill, result);
                    break;
            }

            return result;
        }

        #region 各具体技能逻辑

        // 1. 基础突袭 (Strike)
        private static void ResolveStrike(Legion caster, Legion receiver, ActiveSkillData skill, SkillResolutionResult res, float baseOutput, float domMult, int turn, FormulaConfig cfg)
        {
            if (res.IsEvaded) return;

            float ratio = (skill.Param > 0 ? skill.Param : 100f) * 0.01f;
            float rawDmg = baseOutput * ratio * receiver.DamageReductionFactor * domMult;

            rawDmg = DamageCalculator.ApplyDiscipline(rawDmg, caster, receiver, 2);
            rawDmg = DamageCalculator.ApplyFrailtyDebuff(rawDmg, caster);
            rawDmg = DamageCalculator.ApplyBerserk(rawDmg, turn, cfg);

            long finalDmg = DamageCalculator.FinalizeDamage(rawDmg, cfg);
            finalDmg = DamageCalculator.ApplyExhaust(finalDmg, caster);

            var (vLoss, sLoss, defy) = receiver.ApplyDamage(finalDmg);
            res.DamageDealt = vLoss + sLoss;
            res.DamageType = DamageType.Physical;
            res.TriggeredDeathDefy = defy;
        }

        // 2. 暴击 (HavocStrike: 先机加伤 + 破防50%)
        private static void ResolveHavocStrike(Legion caster, Legion receiver, ActiveSkillData skill, SkillResolutionResult res, float baseOutput, float domMult, int turn, FormulaConfig cfg)
        {
            if (res.IsEvaded) return;

            // 源码机制实锤：(skill.param/100 + SPEED_FACTOR * caster.speed)
            float ratio = (skill.Param * 0.01f) + (cfg.InitiativeScaling * caster.Initiative);
            if (ratio < 0.2f) ratio = 0.2f;

            // 坚韧穿透 50%
            float drf = DamageCalculator.CalcHavocDamageReductionFactor(receiver, cfg);
            float rawDmg = baseOutput * ratio * drf * domMult;

            rawDmg = DamageCalculator.ApplyDiscipline(rawDmg, caster, receiver, 1);
            rawDmg = DamageCalculator.ApplyFrailtyDebuff(rawDmg, caster);
            rawDmg = DamageCalculator.ApplyBerserk(rawDmg, turn, cfg);

            long finalDmg = DamageCalculator.FinalizeDamage(rawDmg, cfg);
            finalDmg = DamageCalculator.ApplyExhaust(finalDmg, caster);

            var (vLoss, sLoss, defy) = receiver.ApplyDamage(finalDmg);
            res.DamageDealt = vLoss + sLoss;
            res.DamageType = DamageType.Havoc;
            res.TriggeredDeathDefy = defy;
        }

        // 3. 精准制导 (PrecisionStrike: 坚韧次级加成 + 绝对必中 + 王者差值全额转真伤)
        private static void ResolvePrecisionStrike(Legion caster, Legion receiver, ActiveSkillData skill, SkillResolutionResult res, float baseOutput, float domMult, int turn, FormulaConfig cfg)
        {
            // 精准绝对必中，不判定闪避
            res.IsEvaded = false;

            // 坚韧次级加成
            float ratio = (skill.Param * 0.01f) + (cfg.FortitudeScaling * caster.Fortitude);
            if (ratio < 0.2f) ratio = 0.2f;

            // 无视坚韧免伤，全额真实伤害（基础真伤 + 王者差值放大）
            float rawDmg = baseOutput * ratio * domMult;

            rawDmg = DamageCalculator.ApplyDiscipline(rawDmg, caster, receiver, 5);
            rawDmg = DamageCalculator.ApplyFrailtyDebuff(rawDmg, caster);
            rawDmg = DamageCalculator.ApplyBerserk(rawDmg, turn, cfg);

            long finalDmg = DamageCalculator.FinalizeDamage(rawDmg, cfg);
            finalDmg = DamageCalculator.ApplyExhaust(finalDmg, caster);

            var (vLoss, sLoss, defy) = receiver.ApplyDamage(finalDmg);
            res.DamageDealt = vLoss + sLoss;
            res.DamageType = DamageType.Precision;
            res.TriggeredDeathDefy = defy;
        }

        // 4. 逆境狂怒 (FuryStrike: 自身已损精力斩杀)
        private static void ResolveFuryStrike(Legion caster, Legion receiver, ActiveSkillData skill, SkillResolutionResult res, float domMult, int turn, FormulaConfig cfg)
        {
            if (res.IsEvaded) return;

            long lostVigor = Math.Max(0, caster.MaxVigor - caster.CurrentVigor);
            float rawDmg = lostVigor * (skill.Param * 0.01f) * receiver.DamageReductionFactor * domMult;

            rawDmg = DamageCalculator.ApplyDiscipline(rawDmg, caster, receiver, 4);
            rawDmg = DamageCalculator.ApplyFrailtyDebuff(rawDmg, caster);
            rawDmg = DamageCalculator.ApplyBerserk(rawDmg, turn, cfg);

            long finalDmg = DamageCalculator.FinalizeDamage(rawDmg, cfg);
            finalDmg = DamageCalculator.ApplyExhaust(finalDmg, caster);

            var (vLoss, sLoss, defy) = receiver.ApplyDamage(finalDmg);
            res.DamageDealt = vLoss + sLoss;
            res.DamageType = DamageType.Physical;
            res.TriggeredDeathDefy = defy;
        }

        // 5. 目标当前精力抽离
        private static void ResolveTargetCurrentSiphon(Legion caster, Legion receiver, ActiveSkillData skill, SkillResolutionResult res, float domMult, int turn, FormulaConfig cfg)
        {
            if (res.IsEvaded) return;

            float rawDmg = receiver.CurrentVigor * (skill.Param * 0.01f) * receiver.DamageReductionFactor * domMult;
            rawDmg = DamageCalculator.ApplyDiscipline(rawDmg, caster, receiver, 3);
            rawDmg = DamageCalculator.ApplyFrailtyDebuff(rawDmg, caster);
            rawDmg = DamageCalculator.ApplyBerserk(rawDmg, turn, cfg);

            long finalDmg = DamageCalculator.FinalizeDamage(rawDmg, cfg);
            finalDmg = DamageCalculator.ApplyExhaust(finalDmg, caster);

            var (vLoss, sLoss, defy) = receiver.ApplyDamage(finalDmg);
            res.DamageDealt = vLoss + sLoss;
            res.DamageType = DamageType.Physical;
            res.TriggeredDeathDefy = defy;
        }

        // 6. 目标最大精力抽离
        private static void ResolveTargetMaxSiphon(Legion caster, Legion receiver, ActiveSkillData skill, SkillResolutionResult res, float domMult, int turn, FormulaConfig cfg)
        {
            if (res.IsEvaded) return;

            float rawDmg = receiver.MaxVigor * (skill.Param * 0.01f) * receiver.DamageReductionFactor * domMult;
            rawDmg = DamageCalculator.ApplyDiscipline(rawDmg, caster, receiver, 3);
            rawDmg = DamageCalculator.ApplyFrailtyDebuff(rawDmg, caster);
            rawDmg = DamageCalculator.ApplyBerserk(rawDmg, turn, cfg);

            long finalDmg = DamageCalculator.FinalizeDamage(rawDmg, cfg);
            finalDmg = DamageCalculator.ApplyExhaust(finalDmg, caster);

            var (vLoss, sLoss, defy) = receiver.ApplyDamage(finalDmg);
            res.DamageDealt = vLoss + sLoss;
            res.DamageType = DamageType.Physical;
            res.TriggeredDeathDefy = defy;
        }

        // 7. 目标已损精力斩杀
        private static void ResolveTargetWoundSiphon(Legion caster, Legion receiver, ActiveSkillData skill, SkillResolutionResult res, float domMult, int turn, FormulaConfig cfg)
        {
            if (res.IsEvaded) return;

            long enemyLoss = Math.Max(0, receiver.MaxVigor - receiver.CurrentVigor);
            float rawDmg = enemyLoss * (skill.Param * 0.01f) * receiver.DamageReductionFactor * domMult;
            rawDmg = DamageCalculator.ApplyDiscipline(rawDmg, caster, receiver, 4);
            rawDmg = DamageCalculator.ApplyFrailtyDebuff(rawDmg, caster);
            rawDmg = DamageCalculator.ApplyBerserk(rawDmg, turn, cfg);

            long finalDmg = DamageCalculator.FinalizeDamage(rawDmg, cfg);
            finalDmg = DamageCalculator.ApplyExhaust(finalDmg, caster);

            var (vLoss, sLoss, defy) = receiver.ApplyDamage(finalDmg);
            res.DamageDealt = vLoss + sLoss;
            res.DamageType = DamageType.Physical;
            res.TriggeredDeathDefy = defy;
        }

        // 8. 精力虹吸 (VigorDrain)
        private static void ResolveVigorDrain(Legion caster, Legion receiver, ActiveSkillData skill, SkillResolutionResult res, float baseOutput, float domMult, int turn, FormulaConfig cfg)
        {
            if (res.IsEvaded) return;

            float ratio2 = skill.Param2 > 0 ? (skill.Param2 * 0.01f) : 1.0f;
            float rawDmg = baseOutput * receiver.DamageReductionFactor * domMult * ratio2;
            rawDmg = DamageCalculator.ApplyDiscipline(rawDmg, caster, receiver, 2);
            rawDmg = DamageCalculator.ApplyFrailtyDebuff(rawDmg, caster);
            rawDmg = DamageCalculator.ApplyBerserk(rawDmg, turn, cfg);

            long finalDmg = DamageCalculator.FinalizeDamage(rawDmg, cfg);
            finalDmg = DamageCalculator.ApplyExhaust(finalDmg, caster);

            var (vLoss, sLoss, defy) = receiver.ApplyDamage(finalDmg);
            res.DamageDealt = vLoss + sLoss;
            res.DamageType = DamageType.Physical;
            res.TriggeredDeathDefy = defy;

            // 偷取精力回复自身
            long drainHeal = (long)Math.Ceiling(finalDmg * (skill.Param * 0.01f) * caster.HealBonusFactor);
            res.HealApplied = caster.ApplyHeal(drainHeal);
        }

        // 9. 自愈回生·当前比 (SelfCurrentRestore)
        private static void ResolveSelfCurrentRestore(Legion caster, Legion receiver, ActiveSkillData skill, SkillResolutionResult res, float baseOutput, float domMult, int turn, FormulaConfig cfg)
        {
            float rawHeal = caster.CurrentVigor * (skill.Param * 0.01f) * caster.HealBonusFactor;
            rawHeal = DamageCalculator.ApplyDiscipline(rawHeal, caster, receiver, 6);
            long healAmt = (long)Math.Ceiling(rawHeal);
            res.HealApplied = caster.ApplyHeal(healAmt);

            if (res.IsEvaded) return;

            float ratio2 = skill.Param2 > 0 ? (skill.Param2 * 0.01f) : 1.0f;
            float rawDmg = baseOutput * ratio2 * receiver.DamageReductionFactor * domMult;
            rawDmg = DamageCalculator.ApplyFrailtyDebuff(rawDmg, caster);
            rawDmg = DamageCalculator.ApplyBerserk(rawDmg, turn, cfg);

            long finalDmg = DamageCalculator.FinalizeDamage(rawDmg, cfg);
            finalDmg = DamageCalculator.ApplyExhaust(finalDmg, caster);

            var (vLoss, sLoss, defy) = receiver.ApplyDamage(finalDmg);
            res.DamageDealt = vLoss + sLoss;
            res.DamageType = DamageType.Physical;
            res.TriggeredDeathDefy = defy;
        }

        // 10. 自愈回生·最大比 (SelfMaxRestore: 恢复流王牌技能)
        private static void ResolveSelfMaxRestore(Legion caster, Legion receiver, ActiveSkillData skill, SkillResolutionResult res, float baseOutput, float domMult, int turn, FormulaConfig cfg)
        {
            float rawHeal = caster.MaxVigor * (skill.Param * 0.01f) * caster.HealBonusFactor;
            rawHeal = DamageCalculator.ApplyDiscipline(rawHeal, caster, receiver, 6);
            long healAmt = (long)Math.Ceiling(rawHeal);
            res.HealApplied = caster.ApplyHeal(healAmt);

            if (res.IsEvaded) return;

            float ratio2 = skill.Param2 > 0 ? (skill.Param2 * 0.01f) : 1.0f;
            float rawDmg = baseOutput * ratio2 * receiver.DamageReductionFactor * domMult;
            rawDmg = DamageCalculator.ApplyFrailtyDebuff(rawDmg, caster);
            rawDmg = DamageCalculator.ApplyBerserk(rawDmg, turn, cfg);

            long finalDmg = DamageCalculator.FinalizeDamage(rawDmg, cfg);
            finalDmg = DamageCalculator.ApplyExhaust(finalDmg, caster);

            var (vLoss, sLoss, defy) = receiver.ApplyDamage(finalDmg);
            res.DamageDealt = vLoss + sLoss;
            res.DamageType = DamageType.Physical;
            res.TriggeredDeathDefy = defy;
        }

        // 11. 敌势借愈·当前比
        private static void ResolveTargetCurrentRestore(Legion caster, Legion receiver, ActiveSkillData skill, SkillResolutionResult res, float baseOutput, float domMult, int turn, FormulaConfig cfg)
        {
            float rawHeal = receiver.CurrentVigor * (skill.Param * 0.01f) * caster.HealBonusFactor;
            rawHeal = DamageCalculator.ApplyDiscipline(rawHeal, caster, receiver, 6);
            long healAmt = (long)Math.Ceiling(rawHeal);
            res.HealApplied = caster.ApplyHeal(healAmt);

            if (res.IsEvaded) return;

            float ratio2 = skill.Param2 > 0 ? (skill.Param2 * 0.01f) : 1.0f;
            float rawDmg = baseOutput * ratio2 * receiver.DamageReductionFactor * domMult;
            rawDmg = DamageCalculator.ApplyFrailtyDebuff(rawDmg, caster);
            rawDmg = DamageCalculator.ApplyBerserk(rawDmg, turn, cfg);

            long finalDmg = DamageCalculator.FinalizeDamage(rawDmg, cfg);
            finalDmg = DamageCalculator.ApplyExhaust(finalDmg, caster);

            var (vLoss, sLoss, defy) = receiver.ApplyDamage(finalDmg);
            res.DamageDealt = vLoss + sLoss;
            res.DamageType = DamageType.Physical;
            res.TriggeredDeathDefy = defy;
        }

        // 12. 敌势借愈·最大比
        private static void ResolveTargetMaxRestore(Legion caster, Legion receiver, ActiveSkillData skill, SkillResolutionResult res, float baseOutput, float domMult, int turn, FormulaConfig cfg)
        {
            float rawHeal = receiver.MaxVigor * (skill.Param * 0.01f) * caster.HealBonusFactor;
            rawHeal = DamageCalculator.ApplyDiscipline(rawHeal, caster, receiver, 6);
            long healAmt = (long)Math.Ceiling(rawHeal);
            res.HealApplied = caster.ApplyHeal(healAmt);

            if (res.IsEvaded) return;

            float ratio2 = skill.Param2 > 0 ? (skill.Param2 * 0.01f) : 1.0f;
            float rawDmg = baseOutput * ratio2 * receiver.DamageReductionFactor * domMult;
            rawDmg = DamageCalculator.ApplyFrailtyDebuff(rawDmg, caster);
            rawDmg = DamageCalculator.ApplyBerserk(rawDmg, turn, cfg);

            long finalDmg = DamageCalculator.FinalizeDamage(rawDmg, cfg);
            finalDmg = DamageCalculator.ApplyExhaust(finalDmg, caster);

            var (vLoss, sLoss, defy) = receiver.ApplyDamage(finalDmg);
            res.DamageDealt = vLoss + sLoss;
            res.DamageType = DamageType.Physical;
            res.TriggeredDeathDefy = defy;
        }

        // 13. 纯粹真实裁决 (TrueDamage)
        private static void ResolveTrueDamage(Legion caster, Legion receiver, ActiveSkillData skill, SkillResolutionResult res, float baseOutput, float domMult, int turn, FormulaConfig cfg)
        {
            res.IsEvaded = false; // 真实伤害不可被闪避

            float rawDmg = baseOutput * (skill.Param * 0.01f) * domMult;
            rawDmg = DamageCalculator.ApplyDiscipline(rawDmg, caster, receiver, 5);
            rawDmg = DamageCalculator.ApplyFrailtyDebuff(rawDmg, caster);
            rawDmg = DamageCalculator.ApplyBerserk(rawDmg, turn, cfg);

            long finalDmg = DamageCalculator.FinalizeDamage(rawDmg, cfg);
            finalDmg = DamageCalculator.ApplyExhaust(finalDmg, caster);

            var (vLoss, sLoss, defy) = receiver.ApplyDamage(finalDmg);
            res.DamageDealt = vLoss + sLoss;
            res.DamageType = DamageType.True;
            res.TriggeredDeathDefy = defy;
        }

        // 15. 湮灭浩劫·原生 (CataclysmA)
        private static void ResolveCataclysmA(Legion caster, Legion receiver, ActiveSkillData skill, SkillResolutionResult res, int turn, FormulaConfig cfg)
        {
            if (res.IsEvaded) return;

            float casterDmg = caster.CurrentVigor * skill.Param * 0.01f;
            float receiverDmg = receiver.CurrentVigor * skill.Param * 0.01f * receiver.DamageReductionFactor;

            casterDmg = DamageCalculator.ApplyFrailtyDebuff(casterDmg, receiver);
            receiverDmg = DamageCalculator.ApplyFrailtyDebuff(receiverDmg, caster);

            caster.ApplyDamage(DamageCalculator.FinalizeDamage(casterDmg, cfg));
            var (vLoss, sLoss, defy) = receiver.ApplyDamage(DamageCalculator.FinalizeDamage(receiverDmg, cfg));

            res.DamageDealt = vLoss + sLoss;
            res.DamageType = DamageType.Physical;
            res.TriggeredDeathDefy = defy;
        }

        // 16. 湮灭浩劫·护体 (CataclysmB)
        private static void ResolveCataclysmB(Legion caster, Legion receiver, ActiveSkillData skill, SkillResolutionResult res, int turn, FormulaConfig cfg)
        {
            if (res.IsEvaded) return;

            float casterDmg = caster.CurrentVigor * skill.Param * 0.01f * caster.DamageReductionFactor;
            float receiverDmg = receiver.CurrentVigor * skill.Param * 0.01f * receiver.DamageReductionFactor;

            casterDmg = DamageCalculator.ApplyFrailtyDebuff(casterDmg, receiver);
            receiverDmg = DamageCalculator.ApplyFrailtyDebuff(receiverDmg, caster);

            caster.ApplyDamage(DamageCalculator.FinalizeDamage(casterDmg, cfg));
            var (vLoss, sLoss, defy) = receiver.ApplyDamage(DamageCalculator.FinalizeDamage(receiverDmg, cfg));

            res.DamageDealt = vLoss + sLoss;
            res.DamageType = DamageType.Physical;
            res.TriggeredDeathDefy = defy;
        }

        // 17. 宿命互换 (FateSwap)
        private static void ResolveFateSwap(Legion caster, Legion receiver, ActiveSkillData skill, SkillResolutionResult res)
        {
            if (res.IsEvaded) return;

            float casterRatio = (float)caster.CurrentVigor / Math.Max(1, caster.MaxVigor);
            float receiverRatio = (float)receiver.CurrentVigor / Math.Max(1, receiver.MaxVigor);

            caster.CurrentVigor = (long)Math.Ceiling(receiverRatio * caster.MaxVigor);
            receiver.CurrentVigor = (long)Math.Ceiling(casterRatio * receiver.MaxVigor);

            res.DamageType = DamageType.True;
        }

        #endregion
    }
}
