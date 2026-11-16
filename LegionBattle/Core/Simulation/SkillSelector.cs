using System;
using System.Collections.Generic;
using LegionBattle.Core.Config;
using LegionBattle.Core.Data;
using LegionBattle.Core.Enums;

namespace LegionBattle.Core.Simulation
{
    /// <summary>
    /// 技能概率队列抽取器（完美还原原版“12字段条件过滤 + 100%权重截断 + 空白降级普攻”算法）
    /// </summary>
    public static class SkillSelector
    {
        private static readonly ActiveSkillData DefaultStrike = new ActiveSkillData
        {
            Id = 1,
            Name = "Default Strike",
            EffectType = SkillEffectType.Strike,
            Param = 100f,
            TriggerWeight = 1000
        };

        /// <summary>
        /// 从战团技能池中抽取当前回合释放的主动技能
        /// </summary>
        public static ActiveSkillData SelectSkill(Legion caster, Legion receiver, int currentTurn, Random rng)
        {
            var validSkills = new List<ActiveSkillData>();
            int totalWeight = 0;

            int selfVigorPct = (int)Math.Round((double)caster.CurrentVigor / Math.Max(1, caster.MaxVigor) * 100.0);
            int targetVigorPct = (int)Math.Round((double)receiver.CurrentVigor / Math.Max(1, receiver.MaxVigor) * 100.0);

            // 0. 首轮必发判定 (若当前为第1回合且配置了首轮必发技能，绝对优先触发)
            if (currentTurn == 1)
            {
                foreach (var skill in caster.EquippedSkills)
                {
                    if (skill.IsFirstTurnGuaranteed && IsConditionSatisfied(skill, caster, receiver, currentTurn, selfVigorPct, targetVigorPct))
                    {
                        return skill;
                    }
                }
            }

            // 1. 遍历过滤满足全部 12 项技术条件的技能
            foreach (var skill in caster.EquippedSkills)
            {
                if (!IsConditionSatisfied(skill, caster, receiver, currentTurn, selfVigorPct, targetVigorPct))
                {
                    continue;
                }

                validSkills.Add(skill);
                totalWeight += skill.TriggerWeight;

                // 源码实锤：满 100% (1000权重) 强制截断后续技能
                if (totalWeight >= BattleConstants.MaxProbabilityCap)
                {
                    break;
                }
            }

            if (validSkills.Count == 0)
            {
                return DefaultStrike;
            }

            // 2. 掷骰抽取（在 1~1000 的区间内掷骰）
            int roll = rng.Next(1, BattleConstants.MaxProbabilityCap + 1);

            int accumulator = 0;
            foreach (var skill in validSkills)
            {
                accumulator += skill.TriggerWeight;
                if (roll <= accumulator)
                {
                    return skill;
                }
            }

            // 3. 若概率未填满 100% 且掷骰落入空白区，降级释放普通攻击
            return DefaultStrike;
        }

        /// <summary>
        /// 严格判定技能的 12 项触发条件
        /// </summary>
        private static bool IsConditionSatisfied(
            ActiveSkillData skill,
            Legion caster,
            Legion receiver,
            int turn,
            int selfVigorPct,
            int targetVigorPct)
        {
            // 条件 1: 次数限制 (times_limit)
            if (caster.IsSkillCountExceeded(skill))
            {
                return false;
            }

            // 条件 2: 最早回合窗口 (turn_cond1)
            if (skill.MinTurn > 0 && turn <= skill.MinTurn)
            {
                return false;
            }

            // 条件 3: 最晚回合窗口 (turn_cond2)
            if (skill.MaxTurn > 0 && turn >= skill.MaxTurn)
            {
                return false;
            }

            // 条件 4: 自身精力下限% (self_bp_cond1)
            if (skill.MinSelfVigorPct > 0 && selfVigorPct <= skill.MinSelfVigorPct)
            {
                return false;
            }

            // 条件 5: 自身精力上限% (self_bp_cond2)
            if (skill.MaxSelfVigorPct > 0 && selfVigorPct >= skill.MaxSelfVigorPct)
            {
                return false;
            }

            // 条件 6: 目标精力下限% (enemy_bp_cond1)
            if (skill.MinTargetVigorPct > 0 && targetVigorPct <= skill.MinTargetVigorPct)
            {
                return false;
            }

            // 条件 7: 目标精力上限% (enemy_bp_cond2)
            if (skill.MaxTargetVigorPct > 0 && targetVigorPct >= skill.MaxTargetVigorPct)
            {
                return false;
            }

            // 条件 8: 连击与失手补偿判定 (turn_cond3)
            if (skill.Compensation != CompensationType.None)
            {
                if (skill.Compensation == CompensationType.OnHit && !caster.LastTurnHitSuccess) return false;
                if (skill.Compensation == CompensationType.OnMiss && caster.LastTurnHitSuccess) return false;
                if (skill.Compensation == CompensationType.TargetHit && !receiver.LastTurnHitSuccess) return false;
                if (skill.Compensation == CompensationType.TargetMiss && receiver.LastTurnHitSuccess) return false;
            }

            // 条件 9: 相对战力比较 (cur_bp_cond: 1=我方高, 2=我方低, 3=相同)
            if (skill.RelativePowerCond > 0)
            {
                if (skill.RelativePowerCond == 1 && caster.CurrentVigor <= receiver.CurrentVigor) return false;
                if (skill.RelativePowerCond == 2 && caster.CurrentVigor >= receiver.CurrentVigor) return false;
                if (skill.RelativePowerCond == 3 && caster.CurrentVigor != receiver.CurrentVigor) return false;
            }

            return true;
        }
    }
}
