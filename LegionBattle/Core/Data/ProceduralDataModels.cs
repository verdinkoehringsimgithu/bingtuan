using System;
using System.Collections.Generic;
using LegionBattle.Core.Enums;

namespace LegionBattle.Core.Data
{
    /// <summary>
    /// 宝可梦式干员个体值/天资 (Individual Values - IVs)
    /// 用于在程序化生成角色时赋予数值波动与鉴宝乐趣
    /// </summary>
    public class IndividualValues
    {
        /// <summary>
        /// 精力资质乘数 (浮动 0.85 ~ 1.15)
        /// </summary>
        public float VigorGrowthModifier { get; set; } = 1.0f;

        /// <summary>
        /// 技能主倍率个体浮动 (如: 原技能200%，个体值+15%则为230%)
        /// </summary>
        public float SkillParamBonus { get; set; } = 0.0f;

        /// <summary>
        /// 技能触发率个体浮动 (如: 原技能20%，个体值+5%则为25%)
        /// </summary>
        public int SkillChanceBonus { get; set; } = 0;

        /// <summary>
        /// 四维属性天资额外点数 [INI, FRT, AGI, DOM] (浮动 0~5 点)
        /// </summary>
        public int[] StatAptitudes { get; set; } = new int[4];

        /// <summary>
        /// 天资评级 (D, C, B, A, S, SS 类似宝可梦 6V 鉴赏)
        /// </summary>
        public string QualityGrade { get; set; } = "A";
    }

    /// <summary>
    /// 神器词条类型枚举
    /// </summary>
    public enum AffixType
    {
        FlatInitiative = 1,     // 固定先机
        FlatFortitude = 2,      // 固定坚韧
        FlatAgility = 3,        // 固定灵敏
        FlatDominance = 4,      // 固定统御
        HavocCritMultiplier = 5,// 暴击伤害倍率提升 (+X%)
        GlobalLifesteal = 6,    // 攻击吸血转化率 (+X%)
        SkillChanceBonus = 7,   // 技能基础触发概率提升 (+X%)
        FirstTurnGuaranteed = 8,// 核心词条：首轮技能必定释放！(100%首发启动)
        OpeningShield = 9,      // 开场获得相当于自身精力 X% 的护盾
        DeathDefyStack = 10,    // 赋予不屈锁血名刀 +1 次
        EvasionBonus = 11,      // 额外回避率加成
        TrueDamageBonus = 12    // 额外真实伤害加成
    }

    /// <summary>
    /// 神器词条实例
    /// </summary>
    public class AffixData
    {
        public int Id { get; set; }
        public string Name { get; set; }
        public AffixType Type { get; set; }
        public float Value { get; set; }
        public int Tier { get; set; } // 词条阶位 T1~T5
    }

    /// <summary>
    /// 核心神器实例 (每个角色携带1件，最多可配置 10 层词条孔位)
    /// </summary>
    public class RelicInstance
    {
        public string Uid { get; set; } = Guid.NewGuid().ToString("N");
        public string Name { get; set; } = "Ancient Artifact";
        public int BaseTemplateId { get; set; }

        // 基础四维面板
        public int BaseInitiative { get; set; }
        public int BaseFortitude { get; set; }
        public int BaseAgility { get; set; }
        public int BaseDominance { get; set; }

        /// <summary>
        /// 神器词条孔位列表（最多 10 层，通过工坊合成、锻造镶嵌、重铸获得）
        /// </summary>
        public List<AffixData> Sockets { get; set; } = new List<AffixData>();

        /// <summary>
        /// 最大孔位上限 (默认随神器阶位解锁，最高 10 孔)
        /// </summary>
        public int MaxSockets { get; set; } = 10;

        /// <summary>
        /// 检查是否拥有“首轮必发”词条
        /// </summary>
        public bool HasFirstTurnGuaranteedAffix()
        {
            return Sockets.Exists(a => a.Type == AffixType.FirstTurnGuaranteed);
        }
    }

    /// <summary>
    /// 程序化生成的动态干员实例 (Procedural Operative)
    /// 摆脱写死配置，具备宝可梦个体值、动态基因槽位、装备神器与养成经验
    /// </summary>
    public class OperativeInstance
    {
        public string Uid { get; set; } = Guid.NewGuid().ToString("N");
        public string CustomName { get; set; }
        public int SpriteAssetIndex { get; set; } // RPG Maker 4向步行图贴图编号

        public int Tier { get; set; } // 阶位 T1~T6
        public Archetype MainArchetype { get; set; } // 所属主流派
        public string OriginRegion { get; set; } // 出身地域 (沙漠/雪原/沼泽/圣山，提供地域羁绊)

        // 等级与经验双轨制
        public int Level { get; set; } = 1;
        public long CurrentExp { get; set; }

        // 宝可梦个体值 (IVs)
        public IndividualValues IndividualValues { get; set; } = new IndividualValues();

        // 技能配置 (支持从其他卡提取基因替换覆盖！)
        public ActiveSkillData EquippedActiveSkill { get; set; }
        public List<PassiveSkillData> EquippedPassiveSkills { get; set; } = new List<PassiveSkillData>();

        // 动态羁绊标签集合 (地域羁绊 + 种族羁绊 + 专精特性)
        public HashSet<string> SynergyTags { get; set; } = new HashSet<string>();

        // 携带的核心神器 (10孔位)
        public RelicInstance EquippedRelic { get; set; }

        /// <summary>
        /// 战前编译导出完整的技能数据（计算个体值浮动与神器词条加成）
        /// </summary>
        public ActiveSkillData CompileFinalSkill()
        {
            if (EquippedActiveSkill == null) return null;

            // 克隆一份避免污染模板
            var compiled = new ActiveSkillData
            {
                Id = EquippedActiveSkill.Id,
                Name = EquippedActiveSkill.Name,
                EffectType = EquippedActiveSkill.EffectType,
                Param = EquippedActiveSkill.Param + IndividualValues.SkillParamBonus,
                TriggerWeight = EquippedActiveSkill.TriggerWeight + IndividualValues.SkillChanceBonus,
                UseCountLimit = EquippedActiveSkill.UseCountLimit,
                HitReactionType = EquippedActiveSkill.HitReactionType,
                IsFirstTurnGuaranteed = EquippedActiveSkill.IsFirstTurnGuaranteed,
                MinTurn = EquippedActiveSkill.MinTurn,
                MaxTurn = EquippedActiveSkill.MaxTurn,
                MinSelfVigorPct = EquippedActiveSkill.MinSelfVigorPct,
                MaxSelfVigorPct = EquippedActiveSkill.MaxSelfVigorPct,
                MinTargetVigorPct = EquippedActiveSkill.MinTargetVigorPct,
                MaxTargetVigorPct = EquippedActiveSkill.MaxTargetVigorPct,
                Compensation = EquippedActiveSkill.Compensation,
                RelativePowerCond = EquippedActiveSkill.RelativePowerCond,
                IgnoreEvasion = EquippedActiveSkill.IgnoreEvasion,
                IgnoreFortitude = EquippedActiveSkill.IgnoreFortitude
            };

            // 神器词条加成注入
            if (EquippedRelic != null)
            {
                foreach (var affix in EquippedRelic.Sockets)
                {
                    if (affix.Type == AffixType.FirstTurnGuaranteed)
                    {
                        compiled.IsFirstTurnGuaranteed = true; // 词条赋予首轮必发！
                    }
                    else if (affix.Type == AffixType.SkillChanceBonus)
                    {
                        compiled.TriggerWeight += (int)affix.Value;
                    }
                    else if (affix.Type == AffixType.HavocCritMultiplier && compiled.EffectType == SkillEffectType.HavocStrike)
                    {
                        compiled.Param += affix.Value;
                    }
                }
            }

            return compiled;
        }
    }

    /// <summary>
    /// 全局自由分配经验池 (便于玩家获得优质新胚子后瞬间拉满等级)
    /// </summary>
    public class SharedExperiencePool
    {
        public long StoredExperience { get; set; }

        public void AddExp(long amount)
        {
            StoredExperience += Math.Max(0, amount);
        }

        public bool ConsumeExp(long amount)
        {
            if (StoredExperience >= amount)
            {
                StoredExperience -= amount;
                return true;
            }
            return false;
        }
    }

    /// <summary>
    /// 资源驻扎据点状态模型 (安排干员驻扎自动挂机采矿，附带敌袭告急限时防守战)
    /// </summary>
    public class OutpostNode
    {
        public string OutpostId { get; set; }
        public string Name { get; set; }
        public string ResourceType { get; set; } // 铁矿/金矿/神木/精金
        public float ProductionPerMinute { get; set; }

        /// <summary>
        /// 驻扎在该据点的干员 Uid 列表
        /// </summary>
        public List<string> StationedOperativeUids { get; set; } = new List<string>();

        /// <summary>
        /// 是否正在遭受敌袭警报！(需要玩家在限时内带主队前往支援，否则据点失守断产)
        /// </summary>
        public bool IsUnderSiege { get; set; }
        public float SiegeRemainingSeconds { get; set; }
    }
}
