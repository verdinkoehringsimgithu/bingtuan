namespace LegionBattle.Core.Config
{
    /// <summary>
    /// 全局战斗常量定义
    /// </summary>
    public static class BattleConstants
    {
        /// <summary>
        /// 主动技能起始 ID 偏移
        /// </summary>
        public const int ActiveSkillIdOffset = 1000001;

        /// <summary>
        /// 战团最大编制人数（30人阵列）
        /// </summary>
        public const int MaxWarbandCapacity = 30;

        /// <summary>
        /// 战斗最大回合上限
        /// </summary>
        public const int DefaultMaxTurns = 50;

        /// <summary>
        /// 四维属性硬下限（无论任何削弱最低不会跌破 -50）
        /// </summary>
        public const int StatFloor = -50;

        /// <summary>
        /// 超时狂暴触发起始回合数
        /// </summary>
        public const int DefaultBerserkThreshold = 25;

        /// <summary>
        /// 狂暴后每超出一回合的额外增伤比例（+20%/回合）
        /// </summary>
        public const float DefaultBerserkEscalation = 0.20f;

        /// <summary>
        /// 暴击对坚韧的穿透比例（默认无视 50% 坚韧）
        /// </summary>
        public const float HavocFortitudePierceRatio = 0.5f;

        /// <summary>
        /// 概率队列截断总权重（100% 截断）
        /// </summary>
        public const int MaxProbabilityCap = 1000;
    }

    /// <summary>
    /// 可外部注入和配置的数值公式参数集（支持热更、调整和完全解耦脱敏）
    /// </summary>
    public class FormulaConfig
    {
        /// <summary>
        /// 基础攻击力中最大精力值的权重（默认 0.2）
        /// </summary>
        public float MaxVigorWeight { get; set; } = 0.2f;

        /// <summary>
        /// 基础攻击力中当前精力值的权重（默认 0.1）
        /// </summary>
        public float CurVigorWeight { get; set; } = 0.1f;

        /// <summary>
        /// 每点先机对暴击伤害的隐式加成系数（默认 0.005 即每点+0.5%）
        /// </summary>
        public float InitiativeScaling { get; set; } = 0.005f;

        /// <summary>
        /// 每点灵敏对治疗回复的隐式加成系数（默认 0.005 即每点+0.5%）
        /// </summary>
        public float AgilityScaling { get; set; } = 0.005f;

        /// <summary>
        /// 每点坚韧对精准制导的隐式加成系数（默认 0.005 即每点+0.5%）
        /// </summary>
        public float FortitudeScaling { get; set; } = 0.005f;

        /// <summary>
        /// 每点统御差值对最终伤害的放大系数（默认 0.01 即每点+1.0%）
        /// </summary>
        public float DominanceScaling { get; set; } = 0.01f;

        /// <summary>
        /// 双曲基数（默认 100）
        /// </summary>
        public float HyperbolicBase { get; set; } = 100f;

        /// <summary>
        /// 超时狂暴开启回合
        /// </summary>
        public int BerserkThreshold { get; set; } = BattleConstants.DefaultBerserkThreshold;

        /// <summary>
        /// 狂暴伤害递增步长
        /// </summary>
        public float BerserkEscalation { get; set; } = BattleConstants.DefaultBerserkEscalation;

        /// <summary>
        /// 非零命中的保底伤害值
        /// </summary>
        public long MinDamageFloor { get; set; } = 1;

        /// <summary>
        /// 默认单例配置
        /// </summary>
        public static FormulaConfig Default { get; } = new FormulaConfig();
    }
}
