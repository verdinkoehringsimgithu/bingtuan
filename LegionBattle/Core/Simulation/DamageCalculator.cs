using System;
using LegionBattle.Core.Config;
using LegionBattle.Core.Data;
using LegionBattle.Core.Enums;

namespace LegionBattle.Core.Simulation
{
    /// <summary>
    /// 核心战斗伤害公式引擎
    /// </summary>
    public static class DamageCalculator
    {
        /// <summary>
        /// 1. 计算进攻方基础输出基数 B = 0.2 * MaxVigor + 0.1 * CurVigor
        /// </summary>
        public static float CalcBaseOutput(Legion caster, FormulaConfig config)
        {
            return caster.MaxVigor * config.MaxVigorWeight + caster.CurrentVigor * config.CurVigorWeight;
        }

        /// <summary>
        /// 2. 应用修炼心法攻守增减乘区 (1 + OffCoeff% + DefCoeff%)
        /// </summary>
        public static float ApplyDiscipline(float rawDamage, Legion caster, Legion receiver, int disciplineType)
        {
            float offCoeff = 0f;
            float defCoeff = 0f;

            if (caster.Disciplines.TryGetValue(disciplineType, out var cData))
            {
                offCoeff = cData.OffensiveCoeff * 0.01f;
            }
            if (receiver.Disciplines.TryGetValue(disciplineType, out var rData))
            {
                defCoeff = rData.DefensiveCoeff * 0.01f;
            }

            float multiplier = 1.0f + offCoeff + defCoeff;
            if (multiplier < 0.1f) multiplier = 0.1f; // 保证有至少 10% 底线

            return rawDamage * multiplier;
        }

        /// <summary>
        /// 3. 应用虚弱 Debuff (Frailty) 削弱
        /// </summary>
        public static float ApplyFrailtyDebuff(float rawDamage, Legion caster)
        {
            float frailtyFactor = caster.GetBuffFactorSum(BuffType.Frailty);
            if (frailtyFactor > 0)
            {
                float reduction = rawDamage * frailtyFactor;
                return Math.Max(0f, rawDamage - reduction);
            }
            return rawDamage;
        }

        /// <summary>
        /// 4. 应用力竭状态 (ExhaustTurns: 攻击伤害强制降为 1)
        /// </summary>
        public static long ApplyExhaust(long calculatedDamage, Legion caster)
        {
            if (caster.ExhaustTurns > 0)
            {
                return 1;
            }
            return calculatedDamage;
        }

        /// <summary>
        /// 5. 应用超时狂暴增伤乘区
        /// </summary>
        public static float ApplyBerserk(float rawDamage, int currentTurn, FormulaConfig config)
        {
            if (currentTurn > config.BerserkThreshold)
            {
                int overTurns = currentTurn - config.BerserkThreshold;
                float berserkMult = 1.0f + overTurns * config.BerserkEscalation;
                return rawDamage * berserkMult;
            }
            return rawDamage;
        }

        /// <summary>
        /// 6. 最终伤害收尾（向上取整与非零保底 1 点）
        /// </summary>
        public static long FinalizeDamage(float rawDamage, FormulaConfig config)
        {
            long dmg = (long)Math.Ceiling(rawDamage);
            if (dmg <= 0) dmg = config.MinDamageFloor;
            return dmg;
        }

        /// <summary>
        /// 计算暴击技能穿透后的坚韧免伤因子（无视 50% 坚韧）
        /// </summary>
        public static float CalcHavocDamageReductionFactor(Legion receiver, FormulaConfig config)
        {
            // 坚韧穿透 50%
            float piercedFort = receiver.Fortitude * (1.0f - BattleConstants.HavocFortitudePierceRatio);
            float effectiveFort = Math.Max(BattleConstants.StatFloor, piercedFort);
            return config.HyperbolicBase / (config.HyperbolicBase + effectiveFort);
        }
    }
}
