# 军人、忍者正式战斗接入

2026-10-28。继人物标签、水手、行商后，本轮完成军人强制命中与忍者绝对闪避，包括技能发动后延迟增长、战报标记和六阶段人数门槛。其余19项机制继续保留既有设计与研究实现，尚未整体移植至Unity。

## 结算规则

1. 军人占比的分母是**阶段人数上限**，不是实际出战人数。正式场景自动传入5/10/15/20/25/30。低于50%不触发军人判定；达到门槛后，仅军人本人成功发动的技能可以掷强制命中。
2. 普通攻击保底不获得军人强制命中，其他身份的技能也不获得。技能的发动率、条件、次数与装备仍先按原管线判定，不因军人而必定发动。
3. 强制命中成功后，本次行动跳过绝对闪避与普通闪避判定，仍正常判定暴击、伤害、减伤和附加效果。
4. 忍者为全队提供绝对闪避；它先于暴击判定，能够避开本来必定暴击的攻击。被绝对闪避的技能仍消耗次数，不执行后续直伤、恢复与附加效果。原有命中前先机增长仍保留。
5. 忍者本人成功发动技能，就把本次羁绊增长加入待生效量，命中与否都计入；普攻不增长。**双方本回合行动结束后统一提交，从下一回合起供后续判定使用**，当前回合的敌方反击不会提前吃到增长。
6. 已经施加的流失等回合伤害继续独立结算，不掷绝对闪避。每场战斗重新建立羁绊状态，不把忍者增长带到下一场。

普通闪避仍沿用原规则：暴击能够绕过普通闪避。本轮没有改动四维职责、伤害倍率、技能投放或特效配置。

## 可配置候选

规则类`CombatEvasionRules`，军人和忍者默认均关闭；参数沿用已有研究候选，调用方可分别配置双方。

| 字段 | 当前候选 | 作用 |
|---|---:|---|
| `military` / `ninja` | false / false | 两项独立开关 |
| `gain` | 1 | 强度倍率 |
| `countK` | 4 | 忍者人数曲线`q(n)=n/(n+k)` |
| `militaryHit` | 0.75 | 满编军人的强制命中基系数 |
| `ninjaBase` | 0.12 | 开局绝对闪避基系数 |
| `ninjaCast` | 0.025 | 忍者每次发动技能的增长基系数 |
| `ninjaCap` | 0.65 | 绝对闪避概率上限 |

令军人占比为`r=军人数/阶段人数上限`。`r<0.5`时不掷判定；否则强制命中概率为：

`min(1, militaryHit × (0.25 + 0.75 × (2r−1)) × gain)`。

忍者开局概率为`min(ninjaCap, ninjaBase × q(忍者数) × gain)`；每次忍者技能提交`ninjaCast × q(忍者数) × gain`的待增长，最终概率受`ninjaCap`限制。这些是已测候选的运行时实现，不代表本轮重新优化了所有阶段的强度或给出新的胜率承诺。

## 正式调用

```csharp
var session = BattleSceneFlow.Enter(new BattleSceneRequest
{
    stage = 3, // 上限15，即使实际只上7人，军人门槛仍按15人算。
    left = playerMembers,
    right = fixedEnemyMembers,
    playerLimits = travel.BattleLimits(),
    leftOpeningBonds = new OpeningBondRules { sailor = true, merchant = true },
    leftEvasionBonds = new CombatEvasionRules { military = true, ninja = true },
    rightEvasionBonds = new CombatEvasionRules { ninja = true },
    autoPlay = true
});
```

真实身份来自`BattleMember.traits.identity`，人物资料按上一轮GUID链路复制。阵容顺位不由模块重排。输入规则进入时立即复制，之后修改原对象不会改变正在进行的战斗。

如果直接调用纯数值`CombatTeam`，应在构造器第五个参数显式给出人数上限。直接使用`BattleTroop/BattleEngine`时填写`BattleTroop.memberCapacity`；零值仅表示通用非阶段测试按实际人数建立容量。正式`BattleSceneFlow`入口始终从stage注入上限，不依赖该回退。

## 战报与结果

- `BattleTurnReport.isForcedHit`：本次军人强制命中已掷成功。
- `isAbsoluteDodge`：本次被忍者绝对闪避。
- 原有`isDodge`在两种闪避下均为true，继续驱动现有闪避表现；`isCrit`保持实际判定结果。绝对闪避先返回，不会显示一个已经被拦截的暴击结果。
- `BattleSceneResult.leftEvasionBonds/rightEvasionBonds`：包含阶段容量、军人/忍者数、军人占比、达到门槛的军人技能判定次数、强制命中次数、绝对闪避次数、忍者技能次数、已提交增长、待提交增长及下一次可用概率。
- 结果摘要为独立副本；中途离开保留真实累计记录，仍按原有`Interrupted`结果处理，不因此结算旅行损耗。

数值在原核心中决定；表现仍在原来配置的伤害时点发布战报。特效排序、位置、回血时点、前移停留后退配置均未修改。

## 证据与范围

`generate_parity.py`直接调用冻结的`joint_core/bond_core`机制实现，以同一随机数带对照Unity纯C#核心。只在新适配层修正军人分母为阶段容量、保留遭遇宏参数前的开局先机，并使用共享顺序随机数协议；没有改写旧研究源码或签名。

- `evasion_parity.json`：2400场、38,491次行动逐一核对，覆盖六阶段、五种军人/忍者/少人出战/开局羁绊/旅行组合。比较胜负、回合、双方余量、实际承伤、最低血线、四维、技能次数、每次出手的主人、暴击、普通/绝对闪避、强制命中及随机数消耗。固定身份组合用于机制一致性，不作为最优排阵收益估计。
- `evasion_invariants.json`：54项边界检查，含少人全军人仍未达门槛、普通攻击与非军人技能、暴击与绝对闪避、延后增长、流失独立结算、次数消耗、状态复制及非法参数。
- `unity_validation.json`：142项真实Unity检查，包含六阶段正常/少人出战、原表现播放器的实际战报发布、增长时序和重复开战清零。
- `opening_parity.json`、`limited_parity.json`、`runtime_parity.json`：1920场水手行商、2400场旅行、480场旧核心对照；`runtime_invariants.json`为已有11项机制检查。
- `identity_validation.json` / `label_validation.json`：旧人物资料与开局羁绊检查；`expedition_validation.json`与`lifecycle_validation.json`为旅行和原有场景/特效回归。
- `baseline_regression.log`：37,500场原基准；最终综合胜率极差见`delivery_checks.json`。

原人物标注、派生人物数据库、正式场景、特效与阵容配置均按修改前SHA核对。源码快照见`delivered_sources/`，本次版本签名见`delivery_manifest.json`。旧版本签名仍对应旧快照，不重签覆盖。

复测：`run_numeric_checks.ps1`、`run_unity_checks.ps1`，最后`verify_delivery.py`。首个数字对照失败是测试摘要把整数计数输出为浮点，已修正生成器后完整重跑；没有因此调整生产战斗倍率。

后续优先接学者的智能次数恢复与剑士完整技能追加，再验证递归次数、使用次数消耗以及多次攻击的表现顺序。
