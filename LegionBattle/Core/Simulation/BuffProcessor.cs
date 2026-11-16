using System;
using LegionBattle.Core.Config;
using LegionBattle.Core.Data;
using LegionBattle.Core.Enums;

namespace LegionBattle.Core.Simulation
{
    /// <summary>
    /// BUFF 状态效果结算器（时点严格分离：流血前置，剧毒后置）
    /// </summary>
    public static class BuffProcessor
    {
        /// <summary>
        /// 回合行动前结算（Pre-Turn: 流血 Hemorrhage 扣除当前精力百分比）
        /// </summary>
        public static (long damageDealt, bool triggeredDefy) ProcessPreTurnBuffs(Legion legion, FormulaConfig config)
        {
            float bleedFactor = legion.GetBuffFactorSum(BuffType.Hemorrhage);
            if (bleedFactor <= 0 || !legion.IsAlive)
            {
                return (0, false);
            }

            // 源码机制实锤：math_ceil(self.cur_bp * factor)
            long rawDamage = (long)Math.Ceiling(legion.CurrentVigor * bleedFactor);
            if (rawDamage <= 0) rawDamage = config.MinDamageFloor;

            var (vigorLoss, shieldLoss, triggeredDefy) = legion.ApplyDamage(rawDamage);
            return (vigorLoss + shieldLoss, triggeredDefy);
        }

        /// <summary>
        /// 回合行动后结算（Post-Turn: 剧毒 Toxin 扣除最大精力百分比）
        /// </summary>
        public static (long damageDealt, bool triggeredDefy) ProcessPostTurnBuffs(Legion legion, FormulaConfig config)
        {
            float toxinFactor = legion.GetBuffFactorSum(BuffType.Toxin);
            if (toxinFactor <= 0 || !legion.IsAlive)
            {
                return (0, false);
            }

            // 源码机制实锤：math_ceil(self.max_bp * factor)
            long rawDamage = (long)Math.Ceiling(legion.MaxVigor * toxinFactor);
            if (rawDamage <= 0) rawDamage = config.MinDamageFloor;

            var (vigorLoss, shieldLoss, triggeredDefy) = legion.ApplyDamage(rawDamage);
            return (vigorLoss + shieldLoss, triggeredDefy);
        }
    }
}
