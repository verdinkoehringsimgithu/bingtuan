# 旅行损耗接入正式战斗：2026-10-27

已把研究中使用的五通道上限损耗接入Unity正式战斗入口。损耗状态归调用方所有；战斗场景接收其快照，返回真实战斗结果。六阶段仍为5/10/15/20/25/30人。

## 实际行为

- `BattleSceneRequest.playerLimits`填写BP、勇气、坚韧、先机、魔力的**剩余比例**，范围为`(0,1]`；省略时全部为1。
- 角色与装备正常求和后应用这些比例。战斗内先机增长和临时四维削弱仍受长期上限比例约束；净化只移除战斗内状态。
- 每次进入战斗时，当前BP回满至本次有效上限。技能次数、累计承伤、护盾和战斗状态重新初始化。上一战残余BP不带入下一战。
- 该输入只限制左侧玩家，右侧固定遭遇不随玩家损耗追平。场景保留调用方传入的阵容顺位。
- `Completed`的BP保持真实终局值，便于评估险胜程度；下次开战回满不会覆盖这份结果。
- 调用方继续决定退出去向。场景、特效配置与表现时序沿用现有设置。

源码目录：`D:/123/LegionBattle/LegionBattle/Assets/Scripts/Battle/`。新增`CombatPersistentLimits.cs`、`ExpeditionState.cs`，并接通`BattleSceneFlow → BattleSceneController → BattleInspectionManager → BattleTroop → CombatTeam`。

## 调用例子

以下片段假设项目已有自己的存档与地区损耗抽取逻辑。数组通道顺序始终为`BP / 勇气 / 坚韧 / 先机 / 魔力`。

```csharp
var travel = new ExpeditionState { troopId = persistentTroopId };
// 已有存档时改用 JsonUtility.FromJson<ExpeditionState>(savedJson)，然后 Validate()。
var battleId = uniqueEncounterId; // 同一场战斗跨回调、跨读档必须沿用同一个ID。
var session = BattleSceneFlow.Enter(new BattleSceneRequest
{
    stage = stage,
    left = playerMembers,
    right = fixedEnemyMembers,
    playerLimits = travel.BattleLimits(),
    autoPlay = true
});

session.Completed += result =>
{
    bool resolved = result.initialized &&
        (result.outcome == BattleSceneOutcome.LeftWon ||
         result.outcome == BattleSceneOutcome.RightWon ||
         result.outcome == BattleSceneOutcome.Draw);
    if (!resolved || travel.settledOperations.Contains(battleId)) return;

    // 地区配置决定触发概率和各通道损耗；未触发时给五个0。
    // 抽取结果应与battleId一同保存，避免读档或重复回调重新ROLL。
    double[] losses = RollConfiguredRegionLoss(result, travel.victoriesSinceRest);
    if (travel.SettleBattle(battleId, result, losses))
        SaveTravel(JsonUtility.ToJson(travel));
};
session.Closed += result => NavigateFromCaller(result);
```

`RollConfiguredRegionLoss`、`SaveTravel`、`NavigateFromCaller`是调用方已有业务接口的示意名，不是本模块内置方法。`troopId`用于保存归属，调用方须保证状态与传入玩家阵容属于同一个战团。多个并发旅行状态的存档合并仍由项目存档层负责。

本次没有把候选地区参数设成全局默认。上一轮的25人前后段概率、温和期和危险地区即时损耗仍见研究文档：
`D:/123/combat_numerical_paradigms/expedition_research/gaps_2026_10_27/RECOMMENDATIONS.md`。

## 旅行事件、补给与休息

`ExpeditionState`可用Unity `JsonUtility`序列化。它记录五通道log损耗、休息后胜场数和已结算操作ID。状态不保存上一战残余BP。

| API | 含义 |
|---|---|
| `BattleLimits()` | 导出独立的战斗输入快照 |
| `SettleBattle(id, result, losses)` | 对已结束的胜/负/同时耗尽结果应用明确损耗；胜利时计程加1 |
| `ApplyEventLoss(id, losses)` | 旅行或副本事件施加损耗，胜场计程不变 |
| `RestoreMissingCaps(id, fractions)` | 各通道恢复其**已损上限**的一部分，胜场计程不变 |
| `Rest(id)` | 恢复全部上限并将本次行程胜场归零 |
| `Validate()` | 读档后校验版本、通道、数值与结算ID |

损耗比例`losses`范围为`[0,1)`，连续损耗乘算。例如上限先损40%、再损50%，剩余为`0.6×0.5=0.3`。补给比例范围为`[0,1]`；剩余上限60%时恢复50%的已损部分，结果为80%，不是恢复到100%。

同一个操作ID重复调用返回`false`，不再次修改状态；普通补给、休息及战斗也共用此去重规则。中断、未初始化、失败初始化、120回合未决均不自动结算损耗或增加计程。败局接受调用方显式传入的损耗，本模块没有默认败退惩罚，也不结算战利品。

## 遥测口径

`BattleSceneResult`新增双边字段：

- `left/rightUnrestrictedMaxBP`：包含装备与遭遇倍率、应用长期损耗前的BP预算。
- `left/rightDamageReceived`：减伤吸收和护盾之后，实际扣除过的BP总量；不计超杀。每次扣除在免死恢复之前计入，治疗不会冲销，可能超过本次BP上限。
- `left/rightMinimumBPRatio`：全场最低BP/本次有效上限，记录免死恢复之前的最低值。
- `left/rightDamageExposure`：`min(1, DamageReceived / 有效BP上限)`；用于已经采用该口径的研究候选策略。

累计承伤只增加遥测，不改变原伤害返回值或吸血等结算。

## 数值一致性与验证

初始BP预算保留6位小数、四维预算保留10位小数，与Python既有成员汇总规则一致。此处解决了小数装备求和造成的同速判定分歧：一边出现`75.99999999999997`而另一边是`76`时，不应凭浮点尾差获得固定行动顺序。只在初始预算求和后统一精度，战斗中的真实属性差异仍正常决定顺序。

本轮验证记录：

- `runtime_parity.json`：480场既有C#/Python固定输入对照。
- `limited_parity.json`：2400场带损耗对照，覆盖六阶段、五种损耗组合，比较胜负、回合、双边余量、累计承伤、最低血线、终局四维、逐角色技能次数及随机数消费。
- `runtime_invariants.json`：11项已有核心机制检查。
- `unity_validation.json`：真实Play Mode的六阶段损耗接入、结算、补给、休息、序列化及去重检查，项目使用最终源码编译。
- `lifecycle_validation.json`：73项原有正式场景/特效时序回归。
- `baseline_regression.log`：37,500场六流派基准；最终胜率极差由`delivery_checks.json`记录。
- `presentation_before.json`与`delivery_checks.json`：正式场景、特效和阵容配置的哈希保护检查。

2400场对照生成器先后发现两类分歧：最初基准漏装`natural_core`的生成器附加效果，修正测试装配后再发现Unity初始四维浮点尾差。前者只修正测试引用，后者修正正式汇总精度。调试轨迹保留在`python_diagnostic*.json`与`csharp_diagnostic*.json`，不作为最终成功证据；以最终验证JSON为准。

本轮只验证正式原生战斗/装备和旅行损耗链路。23项身份羁绊仍是Python研究实现，尚未整体移植至Unity；因此不能把此前启用羁绊的研究胜率直接宣称为本次Unity实测胜率。地图事件、地区策略绑定、补给入口、项目存档调用与战利品业务须由其调用方接入。

复测命令见`run_checks.ps1`；正式源码快照及证据签名见`delivery_manifest.json`。
