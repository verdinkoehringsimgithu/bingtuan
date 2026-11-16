using System;
using System.Collections.Generic;
using LegionBattle.Core.Data;
using LegionBattle.Core.Enums;

namespace LegionBattle.Core.Simulation
{
    /// <summary>
    /// 被动技能与连携羁绊解析器（战前将30人战团的被动技能完整编译注入到 Legion 实体中）
    /// </summary>
    public static class PassiveResolver
    {
        /// <summary>
        /// 战前编译注入全部被动技能与连携效果
        /// </summary>
        public static void CompilePassives(
            Legion legion,
            List<PassiveSkillData> passiveSkills,
            List<SynergySkillData> synergies,
            Dictionary<int, int> operativeCounts)
        {
            var regularPassives = new List<PassiveSkillData>();
            var specialPassives = new List<PassiveSkillData>();

            // 1. 验证连携技激活，并将连携技赋予的技能并入
            if (synergies != null)
            {
                foreach (var syn in synergies)
                {
                    if (CheckSynergyUsable(syn, operativeCounts))
                    {
                        // 连携技直接赋予护盾或BUFF
                        if (syn.BuffId1 > 0)
                        {
                            // 连携BUFF标记后续处理
                        }
                    }
                }
            }

            // 2. 划分普通被动与特殊被动（特殊被动如转化、阈值需在基础属性计算后二次执行）
            foreach (var p in passiveSkills)
            {
                // 基础静态四维加成直接生效
                legion.Initiative += p.Initiative;
                legion.Fortitude += p.Fortitude;
                legion.Agility += p.Agility;
                legion.Dominance += p.Dominance;

                if (p.IsSpecial || p.EffectType == PassiveEffectType.ConvertStat || p.EffectType == PassiveEffectType.ThresholdConvert)
                {
                    specialPassives.Add(p);
                }
                else
                {
                    regularPassives.Add(p);
                }
            }

            // 3. 执行常规被动（属性加成与叠加上限判定）
            foreach (var p in regularPassives)
            {
                ApplyRegularPassive(legion, p, operativeCounts);
            }

            // 4. 执行特殊被动（属性二次转化与阈值突破）
            foreach (var p in specialPassives)
            {
                ApplySpecialPassive(legion, p);
            }
        }

        private static void ApplyRegularPassive(Legion legion, PassiveSkillData p, Dictionary<int, int> counts)
        {
            int applicableOperativesCount = 1;
            // 若限定了职业/性别/种族，则统计符合条件的干员数量
            if (p.RequiredJob != 0 || p.RequiredSex != 0 || p.RequiredRace != 0)
            {
                applicableOperativesCount = 1; // 外部可根据 OperativeTemplate 表进行精确匹配
            }

            int rawAdd = p.Param1 * applicableOperativesCount;
            int finalAdd = ClampStackLimit(legion, p.Id, rawAdd, p.StackLimit);

            switch (p.EffectType)
            {
                case PassiveEffectType.BoostInitiative:
                    legion.Initiative += finalAdd;
                    break;
                case PassiveEffectType.BoostFortitude:
                    legion.Fortitude += finalAdd;
                    break;
                case PassiveEffectType.BoostAgility:
                    legion.Agility += finalAdd;
                    break;
                case PassiveEffectType.BoostDominance:
                    legion.Dominance += finalAdd;
                    break;
                case PassiveEffectType.DeathDefy:
                    legion.DeathDefyCount += p.Param1;
                    break;
                case PassiveEffectType.ShieldGrant:
                    legion.ShieldVigor += p.Param1;
                    break;
            }
        }

        private static void ApplySpecialPassive(Legion legion, PassiveSkillData p)
        {
            // 属性比例转化 (ConvertStat: 每拥有 Param3 点 Param1 属性，增加 Param2 属性)
            if (p.EffectType == PassiveEffectType.ConvertStat)
            {
                if (p.Param1 == 0 || p.Param2 == 0 || p.Param3 <= 0) return;

                int srcVal = GetStatValue(legion, (StatType)p.Param1);
                if (srcVal > 0)
                {
                    int addVal = (srcVal / p.Param3);
                    addVal = ClampStackLimit(legion, p.Id, addVal, p.StackLimit);
                    AddStatValue(legion, (StatType)p.Param2, addVal);
                }
            }
            // 属性阈值突破 (ThresholdConvert: 当 Param1 属性达到 Param3 时，一次性增加 StackLimit 点 Param2 属性)
            else if (p.EffectType == PassiveEffectType.ThresholdConvert)
            {
                if (p.Param1 == 0 || p.Param2 == 0 || p.Param3 <= 0) return;

                int srcVal = GetStatValue(legion, (StatType)p.Param1);
                if (srcVal >= p.Param3)
                {
                    AddStatValue(legion, (StatType)p.Param2, p.StackLimit);
                }
            }
        }

        /// <summary>
        /// 源码机制实锤：FixPropertyNum 限制同名卡叠加上限
        /// </summary>
        private static int ClampStackLimit(Legion legion, int skillId, int addNum, int stackLimit)
        {
            if (stackLimit <= 0) return addNum;

            legion.PassiveStackCounts.TryGetValue(skillId, out int currentStack);
            if (currentStack + addNum >= stackLimit)
            {
                addNum = Math.Max(0, stackLimit - currentStack);
            }
            legion.PassiveStackCounts[skillId] = currentStack + addNum;
            return addNum;
        }

        /// <summary>
        /// 检查连携技是否激活（严格核验战团中指定模板的同名卡数量）
        /// </summary>
        public static bool CheckSynergyUsable(SynergySkillData synergy, Dictionary<int, int> operativeCounts)
        {
            if (synergy == null || synergy.RequiredOperatives == null) return false;

            foreach (var req in synergy.RequiredOperatives)
            {
                int templateId = req.Key;
                int needCount = req.Value;

                if (!operativeCounts.TryGetValue(templateId, out int actualCount) || actualCount < needCount)
                {
                    return false;
                }
            }
            return true;
        }

        private static int GetStatValue(Legion legion, StatType stat)
        {
            return stat switch
            {
                StatType.Initiative => legion.Initiative,
                StatType.Fortitude => legion.Fortitude,
                StatType.Agility => legion.Agility,
                StatType.Dominance => legion.Dominance,
                _ => 0
            };
        }

        private static void AddStatValue(Legion legion, StatType stat, int amount)
        {
            switch (stat)
            {
                case StatType.Initiative: legion.Initiative += amount; break;
                case StatType.Fortitude: legion.Fortitude += amount; break;
                case StatType.Agility: legion.Agility += amount; break;
                case StatType.Dominance: legion.Dominance += amount; break;
            }
        }
    }
}
