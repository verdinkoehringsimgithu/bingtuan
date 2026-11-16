# Unity正式战斗场景接入

场景：`LegionBattle/LegionBattle/Assets/Scenes/BattleScene.unity`。
运行时入口：`LegionBattle.Battle.BattleSceneFlow.Enter`。
退出后的去向由调用方决定，战斗模块不加载地图、结算页或其他目标场景。

## 外部进入

在Unity主线程调用：

```csharp
using LegionBattle.Battle;

var session = BattleSceneFlow.Enter(new BattleSceneRequest
{
    stage = 3,                 // 1..6，对应5/10/15/20/25/30人
    left = playerMembers,     // 保留调用方的实际阵容顺位、属性、技能及装备
    right = enemyMembers,
    autoPlay = true
});

session.Completed += result =>
{
    // 接收实际胜负、剩余BP、回合数和每位成员技能发动次数。
};
session.Closed += result =>
{
    // 调用项目自己的导航逻辑，在这里决定下一场景或页面。
};
```

传入的阵容在进入时立即复制，战斗过程不反写原成员、技能或装备。
人数不能超过所选阶段上限；角色等级1—30，每人一个主动技能、一件装备，每队最多4件顶级装备。
成员四维字段的对应关系：`dodge=勇气`、`defense=坚韧`、`speed=先机`、`authority=魔力`。成员属性填写角色自身值，装备四维单独放在`equipment.stats`，不重复叠加。
自定义技能的数值配置放在`BattleSkill.combat`，特效名称和编号保留在同一技能对象的表现字段中。

## 使用阶段参考阵容与固定遭遇

```csharp
var session = BattleSceneFlow.Enter(new BattleSceneRequest
{
    stage = 3,
    leftFlow = "C_I",
    fixedEncounter = true,
    difficulty = "very_hard", // hard / very_hard / extremely_hard
    maxLevel = false,          // false：阶段参考培养区间；true：30级
    topEquipment = true,      // 读取实测配置，每队最多4件
    useSeed = true,
    seed = 42
});
```

未传入的阵容使用参考生成；明确传入的阵容优先。固定遭遇的敌人使用校准模板与参数，不随玩家强度自动提升。
自定义右侧阵容可同时传入`enemyMacro`配置攻防通量。参考固定遭遇使用其校准参数。
给定种子同时控制参考阵容生成与数值结算；视觉播放不参与数值随机判定。

## 生命周期与退出

- `Entered`：场景和阵容已准备完成。
- `TurnResolved`：在该行动配置的伤害表现时点提供实际战报；伤害与受击动作、特效的先后顺序由特效配置决定。
- `Completed`：战斗结束且当前表现播放完成，或退出时提供中断/失败结果；只触发一次。
- `Closed`：停止播放、清理战斗场景并恢复调用方显示后触发；只触发一次，调用方在此决定去向。
- `session.Leave()`：可在加载中、战斗中或战斗结束后离开；重复调用不会重复结算。
- `autoPlay=false`时，使用`session.Advance()`或空格推进一次行动。
- `autoLeave=true`时，战斗完成后自动关闭本战斗场景，仍由`Closed`的调用方决定去向。

结果类型为`LeftWon / RightWon / Draw / Unresolved / Interrupted / Failed`。达到120回合仍双方存活时为未决；提前离开保留真实BP和已发动次数，不指定胜者。`rounds`在中断时表示当时的当前回合。
`initialized=false`表示尚未建立战斗实例，不包含可用于扣血结算的战斗快照。

场景通过Additive载入，调用方原场景保留。战斗期间隔离原场景的相机、画布和渲染显示，退出恢复原有启用状态。项目自己的探索、业务计时与输入逻辑由调用方在进入前暂停、按退出回调恢复。

## 在Unity内直接检查

打开`BattleScene.unity`并进入Play，使用`BattleSceneController.directPlayRequest`的阶段参考配置运行。场景有完整战斗播放、结果显示及“离开”按钮，预览工具的翻页和调试入口不参与正式场景运行。

直接Play且仅有一个场景时，Unity不能卸载最后一个场景；“离开”会停止并关闭该场景内容，发出`Closed`。外部进入时则正常卸载战斗场景。两种情况下都不自行选择下一场景。

场景维护菜单：`Tools → 战斗 → 创建或更新正式战斗场景`。现有预览场景继续作为表现调试工具。

## 验证

Unity真实Play Mode的55项检查通过，覆盖六阶段、自动播放、手动推进、输入复制、正常结束、重复进入/退出、加载前退出、中途退出、异常装备输入清理、调用方导航、直接Play、离开按钮、初始化状态和种子复现。
机器记录：`scene_integration/lifecycle_validation.json`及`unity_scene_validation.log`。

数值核心沿用已经验证的480场C#/Python对照、11项机制不变量、8,640组成长对照与37,500场基准回归；这些验证不替代场景生命周期验证。
