namespace LegionBattle.Core.Enums
{
    /// <summary>
    /// 主动技能效果类型（完全脱敏对应原版17种主动效果）
    /// </summary>
    public enum SkillEffectType
    {
        /// <summary>
        /// 1. 基础突袭（常规攻击，受坚韧免伤）
        /// </summary>
        Strike = 1,

        /// <summary>
        /// 2. 暴击（爆发伤害，先机加成，穿透50%坚韧，可闪避）
        /// </summary>
        HavocStrike = 2,

        /// <summary>
        /// 3. 精准制导（稳定伤害，坚韧加成，绝对必中不可闪避，全额真实伤害）
        /// </summary>
        PrecisionStrike = 3,

        /// <summary>
        /// 4. 逆境狂怒（自身已损精力百分比伤害，残血爆发）
        /// </summary>
        FuryStrike = 4,

        /// <summary>
        /// 5. 目标当前精力抽离（按目标当前精力百分比扣减）
        /// </summary>
        TargetCurrentSiphon = 5,

        /// <summary>
        /// 6. 目标最大精力抽离（按目标最大精力百分比扣减）
        /// </summary>
        TargetMaxSiphon = 6,

        /// <summary>
        /// 7. 目标已损精力斩杀（按目标已损精力百分比追加伤害）
        /// </summary>
        TargetWoundSiphon = 7,

        /// <summary>
        /// 8. 精力虹吸（造成伤害并按比例转化为自身精力）
        /// </summary>
        VigorDrain = 8,

        /// <summary>
        /// 9. 自愈回生·当前比（基于自身当前精力回复并附带攻击）
        /// </summary>
        SelfCurrentRestore = 9,

        /// <summary>
        /// 10. 自愈回生·最大比（基于自身最大精力回复并附带攻击，灵敏加成，可过量治疗）
        /// </summary>
        SelfMaxRestore = 10,

        /// <summary>
        /// 11. 敌势借愈·当前比（基于敌方当前精力回复自身并附带攻击）
        /// </summary>
        TargetCurrentRestore = 11,

        /// <summary>
        /// 12. 敌势借愈·最大比（基于敌方最大精力回复自身并附带攻击）
        /// </summary>
        TargetMaxRestore = 12,

        /// <summary>
        /// 13. 纯粹真实裁决（无视坚韧免伤，全额真实伤害）
        /// </summary>
        TrueDamage = 13,

        /// <summary>
        /// 14. 极意镜像（复制目标上一回合施放的技能）
        /// </summary>
        MirrorArts = 14,

        /// <summary>
        /// 15. 湮灭浩劫·原生（双方同扣当前精力百分比，自身承受不受坚韧减免）
        /// </summary>
        CataclysmA = 15,

        /// <summary>
        /// 16. 湮灭浩劫·护体（双方同扣当前精力百分比，各自结算坚韧减免）
        /// </summary>
        CataclysmB = 16,

        /// <summary>
        /// 17. 宿命互换（残血绝境技，双方当前精力百分比直接对调）
        /// </summary>
        FateSwap = 17
    }

    /// <summary>
    /// 被动技能效果类型（脱敏对应原版10种被动机制）
    /// </summary>
    public enum PassiveEffectType
    {
        /// <summary>
        /// 1. 提升先机属性
        /// </summary>
        BoostInitiative = 1,

        /// <summary>
        /// 2. 提升坚韧属性
        /// </summary>
        BoostFortitude = 2,

        /// <summary>
        /// 3. 提升灵敏属性
        /// </summary>
        BoostAgility = 3,

        /// <summary>
        /// 4. 提升统御属性
        /// </summary>
        BoostDominance = 4,

        /// <summary>
        /// 5. 属性比例转化（如：每拥有X点A属性，额外提升Y点B属性）
        /// </summary>
        ConvertStat = 5,

        /// <summary>
        /// 6. 压制敌方回避（降低敌方闪避效果）
        /// </summary>
        NullifyEvasion = 6,

        /// <summary>
        /// 7. 技能效能封印（封印特定流派或效果）
        /// </summary>
        SealEffect = 7,

        /// <summary>
        /// 8. 战团护盾防护（开场赋予吸收护盾池）
        /// </summary>
        ShieldGrant = 8,

        /// <summary>
        /// 9. 不屈致死免疫（致命伤害时保留1点精力免死，有名刀次数）
        /// </summary>
        DeathDefy = 9,

        /// <summary>
        /// 10. 属性阈值激活（当A属性达到阈值X时，一次性激活Y点B属性）
        /// </summary>
        ThresholdConvert = 10
    }

    /// <summary>
    /// 状态效果类型（时点严格分离）
    /// </summary>
    public enum BuffType
    {
        /// <summary>
        /// 重创（降低获得的治疗效果，属于乘区削弱）
        /// </summary>
        Wound = 1,

        /// <summary>
        /// 虚弱（降低造成的输出伤害，属于输出端削弱）
        /// </summary>
        Frailty = 2,

        /// <summary>
        /// 创伤流血（回合开始前结算，扣除当前精力百分比，递减伤害不可致死）
        /// </summary>
        Hemorrhage = 3,

        /// <summary>
        /// 腐蚀剧毒（回合结束后结算，扣除最大精力百分比，恒定斩杀毒害）
        /// </summary>
        Toxin = 4
    }

    /// <summary>
    /// 战团战斗流派
    /// </summary>
    public enum Archetype
    {
        None = 0,
        /// <summary>
        /// 暴击流（先机+暴伤爆发，破除50%坚韧，克制高防精准流）
        /// </summary>
        Havoc = 1,

        /// <summary>
        /// 精准流（坚韧+绝对必中真实伤害，克制高闪恢复流）
        /// </summary>
        Precision = 2,

        /// <summary>
        /// 恢复流（灵敏+双曲高闪避+过量回血，克制暴击流）
        /// </summary>
        Tenacity = 3,

        /// <summary>
        /// 特异战术流（DOT、换血、自爆、控场）
        /// </summary>
        Utility = 4
    }

    /// <summary>
    /// 战斗判定胜负结果
    /// </summary>
    public enum BattleResult
    {
        Ongoing = 0,
        LeftWin = 1,
        RightWin = 2,
        Draw = 3
    }

    /// <summary>
    /// 伤害判定类型
    /// </summary>
    public enum DamageType
    {
        Physical = 1,
        Havoc = 2,       // 暴击
        Precision = 3,   // 精准必中
        True = 4,        // 纯粹真实伤害
        Dot = 5          // 持续伤害
    }

    /// <summary>
    /// 连击与失手补偿类型（原版 turn_cond3 字段）
    /// </summary>
    public enum CompensationType
    {
        None = 0,
        OnHit = 1,         // 上回合成功命中
        OnMiss = 2,        // 上回合未命中/被闪避
        TargetHit = 3,     // 目标上回合命中
        TargetMiss = 4     // 目标上回合失手
    }

    /// <summary>
    /// 四维属性枚举
    /// </summary>
    public enum StatType
    {
        None = 0,
        Initiative = 1, // 先机 (Speed)
        Fortitude = 2,  // 坚韧 (Defense)
        Agility = 3,    // 灵敏 (Dodge)
        Dominance = 4   // 统御 (Authority)
    }
}
