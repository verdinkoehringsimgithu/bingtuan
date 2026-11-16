# 人物标签与首批开局羁绊接入

2026-10-28。本轮完成外部人物资料进入Unity的链路，以及水手、行商两项完整的开局效果。其余21项身份机制继续沿用既有设计与研究档案，尚未整体移植至Unity。

## 已可使用

- 外部工具的`Assets/Characters/character_bond_labels.json`仍是标签权威文件。Unity读取种族、性别、单个身份、手工阶级标记与动作分组；不反写标注文件。
- `CharacterSheetData.traits → BattleMember.traits → CombatMember.traits`传递资料，进入战斗时独立复制；战斗中修改不反写人物数据库。
- `CharacterTraits.personId`标识人物，`assetGuid`标识当前动作素材。8组walk/pose素材保持同一个人物ID；原数据库1229条素材仍保留，对应1213个人物。
- 种族与性别作为固有资料传递，没有自动转为属性羁绊。“未填写”与性别“无”保持不同。
- `markedTier`保留外部1～6阶标记；本次没有用它覆盖现有数值阶位、角色属性或培养等级。
- 编辑器启动、标签文件导入、数据库重建和构建前同步资料。也可使用菜单`Tools → 战斗 → 同步人物固有标签`。

读取主标注和`.bak`中最新有效文件；两份均不可用时拒绝清空已有资料。多身份、未知词条ID、动作组冲突会给出需要在标注工具中修正的错误，不自动挑选其中一个身份。

标签同步只原子替换人物数据库文本中的`traits`字段，再让Unity重新导入；不调用整库重新序列化。这样可保留原有Sprite引用、未显式序列化的默认数值及其他字段。数据库有未保存的人工修改时拒绝隐式保存，先保留这些修改。临时副本测试覆盖了这一行为。

旧数据库有9条记录的首帧Sprite引用失效。本轮没有改其帧引用；资料迁移时以**精确且唯一的源图片文件名定位实际GUID，再查标注ID**，未根据人物外观或名字推断身份。GUID写入派生资料后，后续同步继续按GUID关联。存在同名素材、无法唯一定位时不猜测。最终全部1229条记录都核对到了其源标签。

## 水手与行商

实现沿用既有`synergy_research/settings.py`和`joint_core.Team`的开局候选，保留显式开关。默认关闭；已有战斗不会仅因导入标签就改变属性。调用方可分别启用双方、分别设置系数。

令`q(n)=n/(n+k)`，候选`k=4`，`g`为调用方指定的强度倍率，候选为1。

| 机制 | 本轮实现 |
|---|---|
| 水手 | 每项四维增加`成员自身四维总和 / 实际人数 × 不同已填写身份数 × sailorCoefficient × q(水手数) × g`，候选系数0.006 |
| 行商 | 最低一项四维增加`最高一项四维 × merchantCoefficient × q(行商数) × g`，候选系数0.30 |

水手的平均角色预算不含装备；装备属性、`owner_stats`仍正常计入战团。不同身份包括其他已填写身份，不只限于本次已实现效果的身份；未填写不凭空算一种身份。

结算顺序：**角色+装备汇总 → 水手 → 行商 → 遭遇先机差 → 战斗内有效属性中的旅行比例/临时削弱**。行商以水手增加后的原始四维选最高/最低，最低并列按勇气、坚韧、先机、魔力顺序选择一项。两种效果只结算一次，不需要对应成员发动技能，不随回合重复增加。

旅行限制不参与行商开局“最低属性”的重选，与已有旅行研究层顺序一致。战力回满、免死、治疗、技能限次及表现时序继续走既有管线。

```csharp
var session = BattleSceneFlow.Enter(new BattleSceneRequest
{
    stage = stage,
    left = playerMembers,      // 从BattleMember.FromSheetData生成时自动复制标签。
    right = enemyMembers,      // 顺位仍由调用方决定。
    playerLimits = travel.BattleLimits(),
    leftOpeningBonds = new OpeningBondRules { sailor = true, merchant = true },
    autoPlay = true
});
```

调用方手工创建成员时可传`new CharacterTraits { identity="水手" }`；真实角色应保留其GUID标签资料。右侧开关是`rightOpeningBonds`。开启规则不代表重新排阵或修改敌人预算。

`BattleSceneResult.leftOpeningBonds/rightOpeningBonds`返回不同身份数、水手数、行商数、水手单项增量、行商增加轴与增量。结果独立复制，可用于以后接入战报解释。

阶段参考生成器尚未提供固定的身份阵容模板；其外观抽样会带入外观对应的标签。因此**已校准固定遭遇保持默认关闭羁绊**；需要有羁绊的固定NPC时，传入身份明确的实际阵容与显式开关，不能把随机外观生成当成已校准身份阵容。

## 验证范围

本轮是运行时一致性验证，没有重新宣称两项机制的泛用胜率或完成全部羁绊平衡。

- `label_validation.json`逐一核对1229条素材、1213个人物、GUID、资料复制与异常输入。人物数据库原有属性、阶位和Sprite引用保持一致，审计会删除派生traits区块后逐行对照修改前的数据库。
- `opening_parity.json`：1920场开局羁绊对照，六阶段、已有真实技能/装备固定输入、四组双方开关和旅行组合；身份组合用于机制检验，不冒充真实收集分布。
- `limited_parity.json`、`runtime_parity.json`、`runtime_invariants.json`：2400场旅行对照、480场旧对照、11项机制检查。
- `unity_validation.json`：首批羁绊与资料快照的六阶段真实场景验证。
- `expedition_validation.json`、`lifecycle_validation.json`：135项旅行接入与73项原有场景/特效时序回归。
- `baseline_regression.log`：37,500场原基准，六流派胜率极差见`delivery_checks.json`。

新对照以原`joint_core.Team`构造器为开局属性真值，再通过原生动作管线和共享随机数带核对战斗。适配层将开局结果设为本场初始预算，以保留敌方遭遇宏参数后的水手先机加成；旧Python宏函数直接恢复`base_initiative`会丢掉敌方这部分开局增量。该边界在本轮接入中明确处理，没有改写旧研究代码或把旧敌方结果改记成新数据。

执行`run_numeric_checks.ps1`复测数值，`run_unity_checks.ps1`复测Unity，最后`verify_delivery.py`审计。上轮2026-10-27源码签名仍对应当时快照；本轮源码与人物数据库的版本以此目录`delivery_manifest.json`为准。

下一批优先可接军人/忍者、学者/剑士等战斗事件机制。它们涉及强制命中、绝对闪避、次数恢复或额外攻击，需要独立验证事件顺序及表现战报，不能仅贴身份名就称为已完成。
