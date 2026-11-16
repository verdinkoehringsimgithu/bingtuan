using System;
using System.Collections.Generic;
using LegionBattle.Core.Config;
using LegionBattle.Core.Data;
using LegionBattle.Core.Enums;

namespace LegionBattle.Core.Simulation
{
    /// <summary>
    /// 战团战斗实体（对应原版 troop，汇聚30人战力与四维的完整实体）
    /// </summary>
    public class Legion
    {
        public string Name { get; set; } = "Legion";
        public bool IsLeft { get; set; } = true;

        // ─── 精力（生命池）与护盾 ───
        public long MaxVigor { get; set; }
        public long CurrentVigor { get; set; }
        public long ShieldVigor { get; set; }

        public bool IsAlive => CurrentVigor > 0;

        // ─── 四维属性（动态值，受技能、BUFF、战斗修正） ───
        public int Initiative { get; set; }
        public int Fortitude { get; set; }
        public int Agility { get; set; }
        public int Dominance { get; set; }

        // ─── 基础四维（战前快照） ───
        public int BaseInitiative { get; set; }
        public int BaseFortitude { get; set; }
        public int BaseAgility { get; set; }
        public int BaseDominance { get; set; }

        // ─── 派生因子缓存 ───
        public float DamageReductionFactor { get; private set; } = 1.0f;
        public int EvasionChancePermille { get; private set; } = 0; // 千分比闪避率
        public float HealBonusFactor { get; private set; } = 1.0f;

        // ─── 战斗状态与控制 ───
        public int ExhaustTurns { get; set; }
        public int DeathDefyCount { get; set; }
        public ActiveSkillData LastTurnSkill { get; set; }
        public bool LastTurnHitSuccess { get; set; } = true;

        // 技能已释放次数计数表 [SkillId -> Count]
        public Dictionary<int, int> SkillUseCounts { get; } = new Dictionary<int, int>();

        // 正在生效的 BUFF 集合 [BuffType -> List<BuffInstance>]
        public Dictionary<BuffType, List<BuffInstance>> ActiveBuffs { get; } = new Dictionary<BuffType, List<BuffInstance>>();

        // 携带的主动技能列表（已通过前置被动/羁绊激活的技能池）
        public List<ActiveSkillData> EquippedSkills { get; } = new List<ActiveSkillData>();

        // 修炼系数映射表 [CultivationType -> DisciplineData]
        public Dictionary<int, DisciplineData> Disciplines { get; } = new Dictionary<int, DisciplineData>();

        // 被动堆叠计数缓存 [SpecialIndex -> StackNum]
        public Dictionary<int, int> PassiveStackCounts { get; } = new Dictionary<int, int>();

        public Legion(string name, long maxVigor, int init, int fort, int agi, int dom, bool isLeft = true)
        {
            Name = name;
            MaxVigor = maxVigor;
            CurrentVigor = maxVigor;
            ShieldVigor = 0;
            IsLeft = isLeft;

            BaseInitiative = init;
            BaseFortitude = fort;
            BaseAgility = agi;
            BaseDominance = dom;

            Initiative = init;
            Fortitude = fort;
            Agility = agi;
            Dominance = dom;

            RecalcDerivedStats(FormulaConfig.Default);
        }

        /// <summary>
        /// 重新计算派生乘区（满足下限 -50 约束）
        /// </summary>
        public void RecalcDerivedStats(FormulaConfig config)
        {
            // 四维绝对下限 -50 钳位
            int effectiveFort = Math.Max(BattleConstants.StatFloor, Fortitude);
            int effectiveAgi = Math.Max(BattleConstants.StatFloor, Agility);
            int effectiveInit = Math.Max(BattleConstants.StatFloor, Initiative);

            // 双曲免伤因子: 100 / (100 + Fortitude)
            DamageReductionFactor = config.HyperbolicBase / (config.HyperbolicBase + effectiveFort);

            // 千分比回避率: Agility / (100 + Agility) * 1000
            if (effectiveAgi <= 0)
            {
                EvasionChancePermille = 0;
            }
            else
            {
                EvasionChancePermille = (int)Math.Ceiling((effectiveAgi / (config.HyperbolicBase + effectiveAgi)) * 1000f);
            }

            // 治疗隐式加成乘区: 1 + 0.005 * Agility
            HealBonusFactor = 1.0f + config.AgilityScaling * effectiveAgi;
            if (HealBonusFactor < 0.2f) HealBonusFactor = 0.2f; // 最低保底 20% 治疗量
        }

        /// <summary>
        /// 计算对敌统御相对增伤乘区: 1 + max(0, DOM - EnemyDOM) * DominanceScaling
        /// </summary>
        public float GetDominanceMultiplierAgainst(Legion enemy, FormulaConfig config)
        {
            int diff = Dominance - enemy.Dominance;
            if (diff > 0)
            {
                return 1.0f + diff * config.DominanceScaling;
            }
            return 1.0f; // 源码证实：低于对方时不减伤，保底 1.0
        }

        /// <summary>
        /// 受到伤害结算（护盾池优先吸收，扣完扣精力，触发名刀免死）
        /// </summary>
        public (long actualVigorLoss, long shieldLoss, bool triggeredDefy) ApplyDamage(long damage)
        {
            if (damage <= 0) return (0, 0, false);

            long shieldLoss = 0;
            if (ShieldVigor > 0)
            {
                if (ShieldVigor >= damage)
                {
                    ShieldVigor -= damage;
                    shieldLoss = damage;
                    return (0, shieldLoss, false);
                }
                else
                {
                    shieldLoss = ShieldVigor;
                    damage -= ShieldVigor;
                    ShieldVigor = 0;
                }
            }

            long vigorLoss = damage;
            CurrentVigor -= vigorLoss;
            bool triggeredDefy = false;

            // 名刀致死免疫锁血机制
            if (CurrentVigor <= 0 && DeathDefyCount > 0)
            {
                DeathDefyCount--;
                CurrentVigor = 1;
                triggeredDefy = true;
            }

            if (CurrentVigor < 0) CurrentVigor = 0;

            return (vigorLoss, shieldLoss, triggeredDefy);
        }

        /// <summary>
        /// 受到治疗回复结算（支持无上限过量治疗 Overhealing）
        /// </summary>
        public long ApplyHeal(long heal)
        {
            if (heal <= 0) return 0;

            // 乘算重创 Debuff (Wound) 减益
            float woundFactor = GetBuffFactorSum(BuffType.Wound);
            if (woundFactor > 0)
            {
                long reduction = (long)Math.Ceiling(heal * woundFactor);
                heal = Math.Max(0, heal - reduction);
            }

            // 源码实锤：caster.cur_bp = caster.cur_bp + reply，不被 MaxVigor 截断
            CurrentVigor += heal;
            return heal;
        }

        /// <summary>
        /// 添加或刷新 BUFF
        /// </summary>
        public void AddBuff(BuffData buffData)
        {
            if (!ActiveBuffs.TryGetValue(buffData.Type, out var list))
            {
                list = new List<BuffInstance>();
                ActiveBuffs[buffData.Type] = list;
            }
            list.Add(new BuffInstance(buffData));
        }

        /// <summary>
        /// 获取某类 BUFF 的累积强度因子和
        /// </summary>
        public float GetBuffFactorSum(BuffType type)
        {
            if (!ActiveBuffs.TryGetValue(type, out var list) || list.Count == 0)
                return 0f;

            float sum = 0f;
            for (int i = 0; i < list.Count; i++)
            {
                if (list[i].RemainingTurns > 0)
                {
                    sum += list[i].Factor;
                }
            }
            return sum;
        }

        /// <summary>
        /// 回合结束时递减 BUFF 持续回合
        /// </summary>
        public void DecayBuffs()
        {
            foreach (var kv in ActiveBuffs)
            {
                var list = kv.Value;
                for (int i = list.Count - 1; i >= 0; i--)
                {
                    list[i].RemainingTurns--;
                    if (list[i].RemainingTurns <= 0)
                    {
                        list.RemoveAt(i);
                    }
                }
            }
        }

        /// <summary>
        /// 记录技能已使用次数
        /// </summary>
        public void RecordSkillUse(int skillId)
        {
            if (!SkillUseCounts.TryGetValue(skillId, out int count))
            {
                SkillUseCounts[skillId] = 1;
            }
            else
            {
                SkillUseCounts[skillId] = count + 1;
            }
        }

        /// <summary>
        /// 检查技能是否已达到最大释放次数上限
        /// </summary>
        public bool IsSkillCountExceeded(ActiveSkillData skill)
        {
            if (skill.UseCountLimit <= 0) return false;
            SkillUseCounts.TryGetValue(skill.Id, out int count);
            return count >= skill.UseCountLimit;
        }
    }
}
