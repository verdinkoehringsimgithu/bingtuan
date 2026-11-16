# 下一轮特效工具实施与交接计划

后续新增且已认可的外部人物分类工具需求：大窗口人物网格总览，点击人物编辑种族/身份/职业，词条复用与批量标注；完整计划见 `D:/123/combat_numerical_paradigms/progression_difficulty/CHARACTER_TAGGING_TOOL_PLAN.md`。此项尚未实现，与下列特效工具待办共同保留。

更新：2026-10-14。用户最新要求：停止本轮实现，写计划交给下一位；炸飞距离、两军靠近程度、回血时点都通过游戏内工具配置。

## 任务与完成边界

1. 缩小中心炸散的炸飞距离，提供工具调节。
2. 两军靠近一些，提供工具调节；阵容内部间距、纵向位置、整体居中保持。
3. 将所有对自身的特效单独筛选出来，己方血条从空血开始，用现有逐帧工具调整回血时间点；保存后正式播放读取相同配置。

这三项尚未修改、尚未测试。上一轮技能词条配对优化已完成，不能把旧测试结果当成这三项已通过的证据。

## 当前项目与成果

- 根目录 `D:/123`；先读 `AGENT.md`、Unity实现与因果排查技能。
- 主项目：`D:/123/LegionBattle/LegionBattle`。
- 用户正在检查的项目：`D:/123/.gemini/battle_scene_validation`。不要关闭用户Unity，不要覆盖其最新调校。实现后本次需求需要同步到这里。
- 独立验证项目：`D:/123/.gemini/effect_sorting_validation`。验证用Unity `C:/Program Files/Unity/Hub/Editor/2022.3.62f3c1/Editor/Unity.exe`；新启动的验证进程用隐藏窗口。
- 当前63类/467变体，原始动画ID保留；3类19变体有原生前后层。固定初始阵容中心、逐帧可见像素锚点和同排排序已处理，不能回退。
- 共用前移/停留/后退当前用户值0.15/0.35/0.30秒，源为1001的配置。其他特效独立保存大小、XY偏移、排序标记、目标方、负帧及旋转设置。
- 主项目及根目录生成器已有最新词条配对；正在检查的用户项目尚未同步这项匹配优化。详见 `EFFECT_MATCHING_GUIDE.md` 及 `CC-Session-Logs/2026-10-14-semantic-effect-matching.md`。

## 已查清的原因

### 炸散距离

`Assets/Scripts/Battle/BattleCharacterPreview.cs` 的 `CoHitReaction`，模式6：

```csharp
float dist = (2.2f + UnityEngine.Random.Range(0f, 0.6f)) * intensity;
Vector3 apexPos = customScatterDir.normalized * dist;
apexPos.y += UnityEngine.Random.Range(0.2f, 0.5f);
```

向外2.2～2.8单位，另加垂直抬升，造成截图中的大面积散开。`SampleHitReaction`复用同一协程并保存/恢复随机状态，所以修改应在共享逻辑完成，不能只改预览。

### 两军间距

`FormationConfig.Load()` 编辑器优先读 `Assets/Characters/FormationConfig.json`，其次读Resources。两个位置都要核对，不能只改Resources后声称生效。

当前左右原点约-5.581794与0.816266，原点差约6.398060；`BattleInspectionManager.ApplyFormationLayout` 已按相机静止位置共同平移居中。标准30人向左右外侧排布，动态阶段也有共用布局入口。

### 回血时点

- `EffectTimingProfile` 版本4有damageFrame/physicsFrame，没有healFrame。
- `BattlePresentationTimeline` 对自身特效从ReturnEnd起播放，伤害和物理仍固定Contact，回血尚未独立。
- `BattleEffectTestModule.CaptureReport()` 只取一次真实战报；`Seek()`按DamageTime一次性切换双边战力，不能显示独立回血事件。
- `BattleInspectionManager.CoDamageCue()` 中 `report.healDone` 与伤害同一事件处理，且末尾直接同步双方最终血量；新增延迟回血时必须防止此处提前显示治疗后的血条。

## 实施顺序与建议

### A. 炸散距离工具化

- 在现有每类特效配置中新增炸散距离倍率（建议字段`scatterDistanceScale`，实际命名由实施者统一），模式6显示对应输入。
- 让倍率同时缩放径向距离和额外抬升，避免缩小水平后仍跳得很高。保留原来的方向、时间段和复位规则。
- 初始建议值0.45，预期从2.2～2.8降至约0.99～1.26单位；这是待视觉验证的建议，不是用户确定的精确数值。
- 配置默认与迁移明确：旧JSON缺字段不能读成0导致完全不动；其他模式忽略此字段。
- 正式`PlayHitReaction`和预览`SampleHitReaction`都传入同一配置倍率；不得用降低伤害或更换特效来实现。

### B. 两军间距工具化

- 测试模块中提供两军间距控制。使用现有FormationConfig表达，避免再加一个布局后重复缩放的隐含常量。
- 可将新间距转换为左右原点：先求现有中点，再按新间距对称更新左右原点，调用ApplyFormationLayout。
- 初始建议当前原点差缩至80%，约5.118448；保留spacingX、spacingY、originY、rowStaggerX。
- 此项是全局站位配置，不是逐特效位置偏移。改动后重新Seek以重新计算固定阵容中心、特效和角色位置；注意旧缓存和相机震屏不能进入中心计算。
- 增加自动保存/备份，编辑器与构建加载口径一致。当前FormationConfig.Save只写主文件，不具备特效配置已有的完整保存保底，应补齐这项明确要求。

### C. 自身特效回血预览

- 复用现有模块、播放/暂停、重播、时间滑条、逐时间轴帧、逐特效帧、方向交换；不新建外部exe。
- 添加自身特效筛选或独立列表入口，按最新有效`Profile.playOnCaster`筛选，不能仅依赖注册表原始布尔值。切换目标方后筛选需正确更新。
- 所有对自身的特效都可做回血时点校准，包括正式机制属于增益/护盾的素材；预览校准不赋予其正式治疗能力。
- 新增独立`healFrame`，以特效起点为0、单位为特效帧，允许负数。`healTime=effectStart+healFrame/fps`，不与damageFrame/physicsFrame绑定。
- 统一Timeline纳入healTime的起止边界；工具需显示回血时间与特效帧。
- 进入自身回血预览时，行动方展示0血、保留全体角色和正常特效。不要将真实战团currentBP设为0再执行引擎，以免触发战败，用户要求的空血是可播放的校准场景。
- 预览回血量采用明确的校准量，使变化容易辨认；建议空血→满血作为预览标尺，标明是预览，不写入战斗数值。正式战斗只显示真实`report.healDone`。
- Seek每次从固定初态计算：回血时点之前0，达到时点之后显示校准回血值，往回拖动恢复0，重播重新从0开始。交换方向时空血/回血跟随行动方。
- 为正式播放拆分治疗提示与血条更新事件，真实数值核心仍只执行一次。延迟显示期间其他事件不能提前把行动方血条更新为最终值；动作与特效总时长应包含治疗事件，回调顺序需保持既有契约。
- 注意吸血与对敌特效的治疗：先核对战报结构，新增时点不能丢失现有治疗表现，也不能把所有对敌技能自动变成治疗。兼容默认行为与新自身校准区分清楚。

### D. 保存、迁移与同步

- 在现有EffectTimingConfig链路增加字段并迁移版本，保留全部旧profile。记录字段、默认值、归一化和新旧读取行为。
- 改动即自动保存；退出、脚本重载、失焦/暂停保底与最近有效.bak延续；打包仍导出Resources。
- 用户项目最新来源可能是Resources或UserSettings自动保存，先读取最新有效副本并备份。逐字段合并新字段，不能用主项目JSON整体覆盖用户配置。
- `.gemini/sync_effect_sorting_to_open_project.py` 是旧版全量发布脚本，会连带匹配源码等并处理配置。必须审阅后适配，不可直接运行；本次优先只同步确实改动的文件。

## 必须验证的结果

- 模式6在各方向、随机种子和强度下，距离随倍率改变；完整复位；预览与正式协程一致；其他九种模式不变。
- 六阶段标准/动态阵容在缩小间距后仍居中，无角色重叠；反复Seek与震屏不累积偏移；固定特效锚点、前后层和同排排序保持。
- 自身筛选准确；空血可播放，治疗前后与逐帧回退正确；负帧、延迟到特效结束后、交换方向均正确。
- 修改任何新控件后重启/脚本重载可以恢复，旧调校不丢失；构建读取同一配置。
- 正式治疗以真实量显示一次，不提前、不重复；战报和结果不因Seek重复计算；调用方拥有退出去向。
- 独立Unity验证项目运行更新的工具Probe与正式场景生命周期，再同步用户项目。现有27525/73检查是上一轮基线，新增断言后重新执行并记录新结果。

## 停止点与继续入口

本轮只查验与写计划，没有修改上述三项相关源码或配置，也没有同步用户项目。上一轮配对优化文件与二进制仍已发布在主项目。下一位先确认用户当前最新调校，再按A→B→C→D实施，初始视觉建议值允许用户通过工具调整。

## 文件导航与经验补充

以下Unity文件均位于主项目 `D:/123/LegionBattle/LegionBattle`，用户项目和独立验证项目具有相同的Assets相对路径。应先确认所改文件属于哪个项目，避免改了主项目却要求用户在旧副本检查。

| 主项目下的相对路径 | 负责内容与注意事项 |
| --- | --- |
| `Assets/Scripts/Battle/BattleEffectTestModule.cs` | 工具列表、输入、逐帧Seek、血条预览；此次三项控件主要入口。Seek从固定初态重新采样，不推动数值引擎。 |
| `Assets/Scripts/Battle/EffectTimingConfig.cs` | 每类配置、版本迁移、归一化、共用动作、自动保存、最新有效副本读取；新增字段贯穿全链路。 |
| `Assets/Scripts/Battle/BattlePresentationTimeline.cs` | 唯一共用表现时间轴；Contact、ReturnEnd、effectStart、damageTime、physicsTime、总起止时间与旋转数。新增healTime放这里。 |
| `Assets/Scripts/Battle/BattleCharacterPreview.cs` | 正式受击协程与确定性SampleHitReaction；模式6散开位移、其他物理模式和角色还原。 |
| `Assets/Scripts/Battle/BattleInspectionManager.cs` | ApplyFormationLayout、正式回合表现、伤害与治疗提示、血条更新；分离回血事件时核对最终状态同步。 |
| `Assets/Scripts/Battle/FormationConfig.cs` | 站位读取/保存；编辑器Characters优先，构建persistentDataPath优先、Resources后备。 |
| `Assets/Characters/FormationConfig.json`、`Assets/Resources/FormationConfig.json` | 可编辑站位与打包站位；不要只更新其中之一。 |
| `Assets/Scripts/Battle/BattleFormationCenter.cs` | 根据BasePosition计算固定阵容中心，包含角色高度校正；不使用受击后的实时中心。 |
| `Assets/Scripts/Battle/BattleEffectSorting.cs` | 角色行间深度、最高层标记、原生前后层适配。 |
| `Assets/Scripts/Battle/BattleEffectPlayer.cs` | 帧加载、ShowFrame、正式播放、原生层、有效特效ID保留；不是此次数值调整入口。 |
| `Assets/Scripts/Battle/EffectFrameAlignment.cs`、`Assets/Editor/EffectSpriteSheetSlicer.cs` | 可见像素锚点与烘焙；此轮通常不用动，不必重新切图。 |
| `Assets/Scripts/Battle/CameraShakeController.cs` | 随伤害震屏及静止相机位置RestWorldPosition；站位居中用静止位置。 |
| `Assets/Scripts/Battle/BattleHealthBarUI.cs` | ApplyHeal、ApplyDamage、飘字、实际与显示血量；预览SnapBar直接按时间轴显示。 |
| `Assets/Scripts/Battle/BattleEffectTestProbe.cs` | 工具Play Mode回归；新增断言写这里，现有验证隔离配置写入临时目录。 |
| `Assets/Scripts/Battle/BattleSceneLifecycleProbe.cs` | 正式场景真实生命周期回归。 |
| `Assets/Editor/BattleEffectTestTools.cs`、`Assets/Editor/BattleSceneTools.cs` | 工具场景与正式场景验证启动入口。 |
| `Assets/Editor/BattleEffectBuildPreparation.cs` | 构建前导出最新配置，避免只打包旧Resources。 |
| `Assets/Scenes/BattleEffectTestScene.unity`、`Assets/Scenes/BattleScene.unity` | 当前工具场景与正式战斗场景；正式入口BattleSceneFlow.Enter，退出由调用方决定。 |

### 配置与素材位置

- 用户最新特效配置：`D:/123/.gemini/battle_scene_validation/Assets/Resources/EffectTimingConfig.json`、`D:/123/.gemini/battle_scene_validation/UserSettings/EffectTimingConfig.autosave.json`，两者及各自`.bak`比较修改时间和有效性。复制前先备份，不以主项目配置为权威覆盖。
- `D:/123/effect_animation_ids.json`：历史495个稳定ID登记，已移除28个ID仍占位，不能重新编号。
- `D:/123/effect_skill_mapping.json`、`D:/123/effect_names.json`：现行63类投放与名称元数据；Unity有Resources映射副本。
- `Assets/Resources/EffectDatabase.asset`仍可能包含历史495个条目；运行时目录门禁拒绝已移除ID，这不是必须重烘焙的错误。
- 移出的四类：fx2_bubble_pop、fx2_magic_swirl、fx3_lightning_aura、scifx2_tech_aura。完整拼接泡泡护盾fx2_bubble_appear保留。
- 原生前后层为fanfx1_spellcast_B、fanfx1_spellcast_C、fanfx2_cure；后层低于全部角色，Sprite GUID与主图锚点不能破坏。

### 已验证的设计依据

- **时间轴统一而事件分开**：移动、特效、伤害、物理与治疗各自有时点，但共用一条时间轴。攻击者按普通攻击前移/停留/后退完成，不等待特效播完；自身特效默认归位后播放，敌方特效默认接触时播放。
- **预览是状态采样**：每次Seek计算该时刻应有的角色、颜色、相机、帧与血条状态，而不是向前触发一次事件后记住结果。这保证向后拖动、重播及方向交换可复现。
- **数值与展示分离**：真实战报只生成一次，伤害/治疗已经由数值引擎结算；时点仅决定呈现。空血校准不能触发真实战败，也不能给非治疗技能添加治疗机制。
- **全局与单类配置分工**：两军站位与共用动作属于全局；缩放、偏移、排序、特效帧以及回血帧按特效家族保存。炸散幅度建议按家族保存，以适配不同爆炸；不是每个颜色变体重复调。
- **改变间距不改变对齐规则**：整体对称靠近，固定中心重新取BasePosition；不得通过改Sprite pivot、特效Y偏移或相机偏移来假装两军靠近。
- **排序先于特殊标记**：下排角色在前，同排整体排序一致；特效放在行排序带之间。最高层标记是用户逐类选择，不靠单个特效名称硬编码处理。
- **持久化先于扩展控件**：用户曾整轮调校未保存。任何新字段必须有自动写入、重载恢复、备份、迁移与打包导出证据，不能只增加面板输入。
- **现有词条匹配不静默覆盖**：合法已有特效ID保留；新生成或生成器显式全表刷新使用优化规则。此次同步不要顺手重新分配用户已有技能ID。

### 验证与运行经验

现有结果在 `D:/123/combat_numerical_paradigms/progression_difficulty/effect_tuning/`：`visual_validation.json`（27525）、`sorting_lifecycle_validation.json`（73）、`generator_validation.json`（12000）、`matching_improvement_summary.json`、`matching_family_coverage.csv`及逐条TSV。11条语义样例、24000条冻结语料与384条跨端旧样例在独立项目Resources中供Probe读取。

工具验证PowerShell示例（换用新的输出名，保留旧基线）：

```powershell
$env:LEGION_EFFECT_VALIDATION='D:/123/combat_numerical_paradigms/progression_difficulty/effect_tuning/heal_tool_validation.json'
Start-Process -FilePath 'C:/Program Files/Unity/Hub/Editor/2022.3.62f3c1/Editor/Unity.exe' -WindowStyle Hidden -PassThru -ArgumentList @('-batchmode','-force-d3d11','-projectPath','D:/123/.gemini/effect_sorting_validation','-executeMethod','LegionBattle.EditorTools.BattleEffectTestTools.Validate','-logFile','D:/123/combat_numerical_paradigms/progression_difficulty/effect_tuning/unity_heal_tool.log')
```

正式生命周期同样使用独立项目，环境变量`LEGION_SCENE_VALIDATION`，入口`LegionBattle.EditorTools.BattleSceneTools.ValidateLifecycle`，可用`-nographics`。不要加启动即退出的`-quit`：Probe进入Play Mode完成验证后会自己退出。启动前确认同一独立项目没有另一个Unity进程占用。不要关闭用户项目进程。

只检查相关编译错误、异常、成功标记与结果JSON，不广泛打印Unity启动日志或进程完整命令行，其中可能有登录令牌。工具视觉验证需图形设备；纯数值/生命周期检查可以无图形。

验证先把本轮必要源码同步到独立项目，确认结果通过再同步用户项目。Probe的`EffectTimingConfig.UseValidationDirectory`避免自动保存污染真实调校，新站位配置测试也应增加对应隔离。

`D:/123/.gemini/validate_effect_tuning.ps1`、`prepare_effect_database.py`、`publish_effect_tuning.py`与`validate_reviewed_effect_builder.py`可参考，但有历史参数/断言，不直接无检查重跑。尤其不要对真实项目运行全量素材重建。

本轮是表现与调校修改，不改战斗规则，通常无需37500局数值重跑；若实施者确实改动CombatRuntime或Python战斗公式，则依AGENT.md另行执行必要数值检查。

### 匹配优化与生成器相关经验

- 双端源码：`D:/123/SkillGenerator.cs`内嵌SkillEffectMatcher、主Unity`Assets/Scripts/Battle/SkillEffectMatcher.cs`。若此轮不改配对，不必重新编译生成器。
- `.gemini/sync_matching_methods.py`只用于核对后的方法同步；`.gemini/optimize_effect_matching.py`是一次性转换，已执行过，不再执行，避免重复插入辅助方法。
- `.gemini/EffectMatchingAudit.exe`是优化前基线，`EffectMatchingAudit_after.exe`是优化后版本。冻结语料`matching_corpus.tsv`使用seed314159，对比不能重新随机生成另一批。
- 编译生成器用`C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe`，路径在编译参数中用带引号的Windows反斜杠绝对路径；过去正斜杠形式在旧编译器下异常解析了`.gemini`目录。
- 根目录SkillGenerator.exe/SkillGenerator_cli.exe已发布；旧程序备份在`D:/123/.gemini/matching_optimization_backup`。不要自动启动生成器GUI读取历史默认CSV。
- Python中文输出先设置`PYTHONIOENCODING=utf-8`，避免Windows默认编码使证据难读。

### 必须保留的工作边界

不读取`D:/123/unpacked/`、`all_tables_parsed.json`，不无差别扫描`.archive_scratch/`。项目没有可依赖的Git回滚，应先备份确实要改的文件，再做最小范围同步。总结设计依据和结果即可，不存储私有思维链。

继续前优先读本计划及两篇日志：`D:/123/CC-Session-Logs/2026-10-14-semantic-effect-matching.md`、`D:/123/CC-Session-Logs/2026-10-14-effect-tool-next-handoff.md`。用户已授权三项游戏内配置，不需要再询问是否要做；精确视觉值由工具让用户调整。
