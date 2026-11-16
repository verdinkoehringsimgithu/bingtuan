# 23项身份羁绊运行时接入

2026-10-28。Unity数值核心仍为CombatRuntime，正式入口仍为BattleSceneFlow.Enter。23项机制按七组可选配置传入；身份取真实CharacterTraits.identity，等级取真实1～30级，保持调用方顺位。正常队伍行动仍从前到后检索一个技能，剑士是已确认的追加完整技能例外。

这些配置默认关闭，避免既有调用方在未投放羁绊时改变战斗。生产支持机制与现有候选参数，不代表每个阶段、每种收集阵容都已达到相同平衡收益；强度投放继续参照既有研究的阶段表及适用边界。

## 配置入口

```csharp
var request = new BattleSceneRequest
{
    stage = stage,
    left = playerMembers,
    right = enemyMembers,
    leftOpeningBonds = new OpeningBondRules { sailor = true, merchant = true },
    leftEvasionBonds = new CombatEvasionRules { military = true, ninja = true },
    leftSupportBonds = new CombatSupportRules { scholar = true, sword = true },
    leftAmplificationBonds = new CombatAmplificationRules
    { academy = true, cult = true, fighter = true, heroine = true, lady = true },
    leftAugmentationBonds = new CombatAugmentationRules
    { engineer = true, sage = true, thief = true, killer = true },
    leftTacticalBonds = new CombatTacticalRules
    { mage = true, hunter = true, gang = true, rich = true, worker = true },
    leftCompoundBonds = new CombatCompoundRules
    { maid = true, farmer = true, adventurer = true, maidBudget = .5 },
    autoPlay = true
};
var session = BattleSceneFlow.Enter(request);
```

敌方对应right配置，双方可独立开关与调参。示例maidBudget=.5用于展示已测预算候选，不能将其视为所有阶段统一推荐值。没有自动填充或重排角色；军人按阶段人数上限算占比。每人一件装备、每队最多4件顶级装备继续生效。

## 机制边界

统一候选人数曲线q=n/(n+4)，各组gain控制幅度。除用户明确指定的军人50%占比、女仆长保证发动等规则外，解锁人数与系数均为可调候选。

| 配置组 | 身份与已接入范围 |
|---|---|
| Opening | 水手按身份种类提供开局四维；行商开局给最低属性增加最高属性的一部分 |
| Evasion | 军人技能强制命中克制绝对闪避；忍者给全队绝对闪避，技能增长下回合生效 |
| Support | 学者智能恢复有限技能次数，跳过无限女仆长；剑士追加另一剑士完整技能，独立门槛/次数/装备，概率逐次衰减，最多3次追加 |
| Amplification | 老师依学生等级强化攻击并导出学生经验倍率；拜火教依低阶人数强化高阶技能；格斗家逐回合增长；侠女每人首次技能叠层；淑女强化前部位置 |
| Augmentation | 工程师强化实际装备四维，下回合增长；贤者调整原生负面幅度；盗贼本场等量转移有效四维；杀手削弱敌方下一次技能恢复 |
| Tactical | 魔法师同流派百分比/异流派增伤；猎手折前直伤转延迟真伤；帮派替换普攻；富翁本场金币减伤；社畜本场一次复起 |
| Compound | 女仆长随强度增加复合效果；农民共享成熟、加速、收获果实；冒险者完成实际战斗节点后强化后续技能 |

女仆长替换技能保留其持有者、原技能流派与阶位，先替换数值效果，再应用持有者装备；普通攻击装备不会因女仆长保证发动而转成技能装备。原角色技能不会被永久改写。当前数值核心没有独立封印状态；女仆长绕过全部现有发动门槛，后续接封印系统时应继续通过IsMaidLeader识别其免疫要求。

## 结果与业务边界

BattleSceneResult的left/right七组摘要分别返回人数、层数、次数、装备四维贡献、偷取、减疗、本场金币、果实和冒险首次事件。数组及事件记录都是副本。TurnResolved中的逐次归因字段可用于日志，技能追加仍逐次完整播放。

学生经验倍率只供调用方用于学生经验；本场金币只供调用方决定结算。中断结果也可能包含累计值，不能仅因摘要存在就自动发奖。旅行上限、补给、战后回满到当前有效上限、战利品及退出去向继续由已有接入协议和调用方管理。

## 验证与历史

依次查看各冻结交付目录：identity_runtime_2026_10_28、evasion_runtime_2026_10_28、support_runtime_2026_10_28、amplification_runtime_2026_10_28、augmentation_runtime_2026_10_28、tactical_runtime_2026_10_28、compound_runtime_2026_10_28。

最终一组会复核全部此前数值与Unity场景检查。最新生产签名及实际测试计数以compound_runtime_2026_10_28/delivery_checks.json和delivery_manifest.json为准。旧目录记录各自历史生产快照，后续实现不会重写旧签名。研究源、人物标注、派生数据库、正式场景和用户调校特效/阵容配置的保护状态也在验收记录中。

数值设计继续参考[联测指南](../synergy_research/JOINT_DESIGN_GUIDE.md)、[最优顺位研究](../synergy_research/OPTIMAL_ORDER_DESIGN_GUIDE.md)、[三项复合投放指南](../synergy_research/THREE_BOND_DESIGN_GUIDANCE.md)。本次移植验证使用固定输入和随机数带核对物理一致性，不把这些一致性样本冒充新的玩家分布或最优收益研究。
