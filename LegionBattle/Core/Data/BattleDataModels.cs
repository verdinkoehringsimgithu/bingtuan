using System.Collections.Generic;
using LegionBattle.Core.Enums;

namespace LegionBattle.Core.Data
{
    /// <summary>
    /// 主动技能配置数据（完整保留原版35个技术字段）
    /// </summary>
    public class ActiveSkillData
    {
        public int Id { get; set; }
        public string Name { get; set; }
        public string Description { get; set; }

        // ─── 触发窗口条件 ───
        /// <summary>
        /// 最早可用回合数（turn_cond1，当前回合 <= 此值时不可释放）
        /// </summary>
        public int MinTurn { get; set; }

        /// <summary>
        /// 最晚可用回合数（turn_cond2，0表示无限制，当前回合 >= 此值时不可释放）
        /// </summary>
        public int MaxTurn { get; set; }

        /// <summary>
        /// 自身精力下限百分比（self_bp_cond1，自身精力% <= 此值时不可释放）
        /// </summary>
        public int MinSelfVigorPct { get; set; }

        /// <summary>
        /// 自身精力上限百分比（self_bp_cond2，0表示无限制，自身精力% >= 此值时不可释放）
        /// </summary>
        public int MaxSelfVigorPct { get; set; }

        /// <summary>
        /// 目标精力下限百分比（enemy_bp_cond1）
        /// </summary>
        public int MinTargetVigorPct { get; set; }

        /// <summary>
        /// 目标精力上限百分比（enemy_bp_cond2，0表示无限制）
        /// </summary>
        public int MaxTargetVigorPct { get; set; }

        /// <summary>
        /// 连击与失手补偿机制（turn_cond3）
        /// </summary>
        public CompensationType Compensation { get; set; } = CompensationType.None;

        /// <summary>
        /// 相对战力比较条件（cur_bp_cond: 1=我方大于敌方, 2=我方小于敌方, 3=我方等于敌方）
        /// </summary>
        public int RelativePowerCond { get; set; }

        // ─── 概率与次数控制 ───
        /// <summary>
        /// 触发概率权重（千分比，trigger_chance）
        /// </summary>
        public int TriggerWeight { get; set; }

        /// <summary>
        /// 单场战斗最大释放次数限制（times_limit，达到后无法再次释放）
        /// </summary>
        public int UseCountLimit { get; set; }

        // ─── 核心效果与参数 ───
        /// <summary>
        /// 技能效果分类枚举（effect_type）
        /// </summary>
        public SkillEffectType EffectType { get; set; }

        /// <summary>
        /// 主效果倍率参数（param，通常为百分比）
        /// </summary>
        public float Param { get; set; }

        /// <summary>
        /// 次级效果倍率参数（param2）
        /// </summary>
        public float Param2 { get; set; }

        /// <summary>
        /// 是否必须命中才触发附带效果（need_hit: 1=命中才触发BUFF/属性削弱, 0=未命中也触发）
        /// </summary>
        public bool NeedHit { get; set; } = true;

        // ─── 属性动态削弱/增强 ───
        /// <summary>
        /// 对自身四维的临时增减量 [INI, FRT, AGI, DOM]
        /// </summary>
        public int[] SelfStatModifiers { get; set; } = new int[4];

        /// <summary>
        /// 对敌方四维的临时增减量 [INI, FRT, AGI, DOM]
        /// </summary>
        public int[] TargetStatModifiers { get; set; } = new int[4];

        // ─── 特殊控制技术字段 ───
        /// <summary>
        /// 时钟推进修正值（turn_fixed: 可跳过或增加回合计数）
        /// </summary>
        public int TurnFixed { get; set; }

        /// <summary>
        /// 虚弱回合数（exhaust_turn: 使目标造成伤害降为1点的回合数）
        /// </summary>
        public int ExhaustDuration { get; set; }

        /// <summary>
        /// 无视闪避（绝对必中标记）
        /// </summary>
        public bool IgnoreEvasion { get; set; }

        /// <summary>
        /// 无视坚韧（完全破防标记）
        /// </summary>
        public bool IgnoreFortitude { get; set; }

        /// <summary>
        /// 封印效能
        /// </summary>
        public int SealTurnEffect { get; set; }
        public int SealDuration { get; set; }
        public int SealCondMin { get; set; }
        public int SealCondMax { get; set; }

        /// <summary>
        /// 绑定的动画音效资源标识
        /// </summary>
        public int AnimationId { get; set; }

        /// <summary>
        /// 数据驱动受击动力学类型 (0=按伤害类型自动判定, 1=水平震退, 2=垂直击飞, 3=抛物线后仰, 4=四向旋转翻滚, 5=波浪状掀飞, 6=中心炸散再复位, 7=手风琴压缩, 8=地震颠簸)
        /// </summary>
        public int HitReactionType { get; set; }

        /// <summary>
        /// 是否首轮必定释放 (可通过技能自身、神器词条或先锋印记赋予)
        /// </summary>
        public bool IsFirstTurnGuaranteed { get; set; }

        // ─── 附带触发的 BUFF 列表 ───
        public int BuffId1 { get; set; }
        public int BuffId2 { get; set; }
        public int BuffId3 { get; set; }

        /// <summary>
        /// 技能被动附加的四维属性 [INI, FRT, AGI, DOM]
        /// </summary>
        public int BaseInitiative { get; set; }
        public int BaseFortitude { get; set; }
        public int BaseAgility { get; set; }
        public int BaseDominance { get; set; }
    }

    /// <summary>
    /// 被动技能配置数据
    /// </summary>
    public class PassiveSkillData
    {
        public int Id { get; set; }
        public string Name { get; set; }
        public string Description { get; set; }
        public PassiveEffectType EffectType { get; set; }

        public int Param1 { get; set; }
        public int Param2 { get; set; }
        public int Param3 { get; set; }

        public int RequiredJob { get; set; }
        public int RequiredSex { get; set; }
        public int RequiredRace { get; set; }

        /// <summary>
        /// 叠加上限限制（防止同名卡过度堆叠属性失衡）
        /// </summary>
        public int StackLimit { get; set; }

        public int Initiative { get; set; }
        public int Fortitude { get; set; }
        public int Agility { get; set; }
        public int Dominance { get; set; }

        public bool IsSpecial { get; set; }
    }

    /// <summary>
    /// BUFF / 状态效果配置数据
    /// </summary>
    public class BuffData
    {
        public int Id { get; set; }
        public string Name { get; set; }
        public BuffType Type { get; set; }

        /// <summary>
        /// 目标类型：0=施法者自身, 1=目标敌方
        /// </summary>
        public int TargetType { get; set; }

        public string Description { get; set; }
        public int Chance { get; set; } = 100;

        /// <summary>
        /// 效果强度系数（如：虚弱30%即 30，流血15%即 15）
        /// </summary>
        public float Factor { get; set; }

        /// <summary>
        /// 持续回合数
        /// </summary>
        public int DurationTurns { get; set; }

        /// <summary>
        /// 触发时点："begin" 为回合行动前（流血），"end" 为回合行动后（剧毒）
        /// </summary>
        public string Timing { get; set; }
    }

    /// <summary>
    /// BUFF 运行期实例
    /// </summary>
    public class BuffInstance
    {
        public BuffData Config { get; set; }
        public float Factor { get; set; }
        public int RemainingTurns { get; set; }

        public BuffInstance(BuffData config)
        {
            Config = config;
            Factor = config.Factor * 0.01f;
            RemainingTurns = config.DurationTurns;
        }
    }

    /// <summary>
    /// 战团连携技（原合体技配置）
    /// </summary>
    public class SynergySkillData
    {
        public int Id { get; set; }
        public string Name { get; set; }
        public string Description { get; set; }

        /// <summary>
        /// 触发所需干员模板 ID 及数量要求 [OperativeTemplateId -> RequiredCount]
        /// </summary>
        public Dictionary<int, int> RequiredOperatives { get; set; } = new Dictionary<int, int>();

        /// <summary>
        /// 激活后赠送的技能 ID 列表（包含主动与被动）
        /// </summary>
        public List<int> GrantedSkillIds { get; set; } = new List<int>();

        public int BuffId1 { get; set; }
        public int BuffId2 { get; set; }
        public int BuffId3 { get; set; }
    }

    /// <summary>
    /// 修炼攻守系数配置
    /// </summary>
    public class DisciplineData
    {
        public int DisciplineType { get; set; }
        public int Level { get; set; }
        public int OffensiveCoeff { get; set; } // 进攻增益 +X%
        public int DefensiveCoeff { get; set; } // 防守减免 -X%
    }

    /// <summary>
    /// 干员角色基础原型配置（对应 mercenary.csv）
    /// </summary>
    public class OperativeTemplate
    {
        public int Id { get; set; }
        public string Name { get; set; }
        public int Job { get; set; }
        public int Sex { get; set; }
        public int Race { get; set; }
        public int Tier { get; set; } // 阶位 T1~T6

        public long InitVigor { get; set; }
        public float VigorFactor { get; set; }

        public int ActiveSkillId { get; set; }
        public int PassiveSkillId1 { get; set; }
        public int PassiveSkillId2 { get; set; }

        public int SynergySkillId1 { get; set; }
        public int SynergySkillId2 { get; set; }

        public Archetype PrimaryArchetype { get; set; }

        // 神器附带四维
        public int ArtifactInitiative { get; set; }
        public int ArtifactFortitude { get; set; }
        public int ArtifactAgility { get; set; }
        public int ArtifactDominance { get; set; }
    }

    /// <summary>
    /// 30人战团编队阵容定义
    /// </summary>
    public class WarbandData
    {
        public string WarbandName { get; set; } = "Legion Alpha";
        public List<int> OperativeTemplateIds { get; set; } = new List<int>();
    }
}
