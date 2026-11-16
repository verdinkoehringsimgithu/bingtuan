# 五组增益机制已验收，继续推进

用户要求“不用重复确认，一直往前做”。本轮持续实施；学者/剑士之后又完成学生/老师、拜火教、格斗家、侠女、淑女五组，没有结束整体任务。下一组已向用户说明为工程师、贤者、盗贼、杀手。

## 生产实现

项目`D:/123/LegionBattle/LegionBattle`。新增`Assets/Scripts/Battle/CombatAmplificationBonds.cs`，配置/状态/结果摘要默认全部off。请求`left/rightAmplificationBonds`独立Clone传到BattleTroop/CombatTeam；结果同名Summary独立复制。

核心沿用候选：q=n/(n+4)、gain1；Teacher直伤1+.0015×学生等级总和×g，学生XP导出倍率1+.12×老师数×g；Cult直伤1+.035×低于自身技能tier的教徒数×g；Fighter全队Output1+.025q×g×(round−1)；Heroine首次技能结束后每人加一次层，后续侠女技能直伤1+层×.035q×g；Lady前ceil(人数/3)位置技能直伤1+.25q×g。

Direct按Teacher→Cult→Heroine→Lady顺序接原装备因子；Heal技能仍有原生基础攻击，只强化攻击不强化恢复。Fighter回合开始/最大流失前更新，既有源输出流失也受影响。Heroine首次不要求命中，普攻不叠，同一次首次技能不提前享新层。Lady候选仅技能增伤，普攻不加。

新增`CombatMember.level=30`作为纯旧fixture缺省；生产从BattleMember.level复制真实1～30级。没有从四维反推等级，没有修改角色标注阶位或数值预算。XP倍率仅给调用方用于学生，不创建经验奖励/发奖条件/存档系统。

战报`bondDirectMultiplier`、`bondOutputMultiplier`、`heroineFirst`暴露归因。上轮递归播放完成屏障/每次净化/智能恢复继续保留。

## 验证全部完成

证据`combat_numerical_paradigms/progression_difficulty/amplification_runtime_2026_10_28/`。

- 新3360场/58,552次出手原生对照，最大相对误差1.0928757898653885e-15。
- 新29定向不变量；旧9120对照及40+54+11不变量全部通过。
- Unity132新、153学剑、142军忍、71开局、135旅行、73原场景/时序及3698标签全部通过。所有批处理已退出。
- 37,500场综合胜率[53.2,55.6,54.9,47.3,42.7,46.3]，极差12.9pp。
- 标签源JSON、派生人物数据库、正式场景、特效与阵容配置SHA未变。
- README、ps1复测、verify_delivery、最终delivered_sources/delivery_manifest/delivery_checks已冻结，不改旧研究或旧签名。

正式完成11/23。余12：魔法师、猎手、女仆、贤者、工程师、冒险者、帮派、农民、盗贼、富翁、社畜、杀手。

## 下一组实施落点（尚未改生产）

工程师：真实gear基数=显式装备stats+owner_stats的实际贡献；开局先于水手/行商加gear×.25q×g。工程师实际技能发动（命中与否）队列+.035q×g，回合结束/净化后提交gear增量，下回合有效。不要放大装备技能/护盾机制。
贤者：沿用已测范围，原生虚弱/四维削弱/最大、已损、固定流失的幅度×(1+.25q(己方)g)×max(0,1−.25q(敌方)g)，保持时长与原生伤害底数。不要默默扩展到其他羁绊负面。
盗贼：每次攻击（不要求命中）偷有效四维×min(1,.015q×g)，每维不超过敌方原始cur量；从敌方raw stats扣、给己方raw stats加，旅行/临时削弱继续在Effective里生效。本场唯一，不改成员和装备预算。
杀手：命中技能后给敌方待减疗max(现有,min(1,.60q×g))；下一次实际技能选定时消费，普攻不消费，若下一技能被闪避仍消费。该技能的自愈/吸血请求在封顶前缩减；回合宏恢复与免死不受影响。ActiveRecoveryFactor每次Act后清理，防止泄漏。

建议新CombatAugmentationRules/State，开局工程师在OpenRules前，回合工程师提交在Cleanse后。Heal通过状态Filter请求，但只在当前真实技能上下文生效。Thief/Killer/Engineer post hook可在Support后统一处理（单身份使每次只有一个相应角色钩子）。负面sub缩放在装备子效果加成后、魔力应用前。为精确口径记录被阻止的真实恢复请求；原Python当前自愈在Killer统计中有maxBP中间量，物理结果相同但统计应在新适配层修正，别修改冻结源。
