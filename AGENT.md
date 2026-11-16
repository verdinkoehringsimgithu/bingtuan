# 战团对决与技能数值系统开发守则 (AGENT.md)

- **更新时间**：2026-10-14
- **身份羁绊设计（2026-10-15）**：用户确认的23项机制与补充见[IDENTITY_SYNERGY_DESIGN.md](combat_numerical_paradigms/progression_difficulty/IDENTITY_SYNERGY_DESIGN.md)，当前为设计存档、尚未实现。后续羁绊工作优先读取；剑士递归完整技能是用户明确要求的额外攻击例外，工程师/忍者增长不影响当前回合，农民共用果实。按本项目战团逻辑承接，不将参考游戏的机制或未采纳的助手建议当成要求。
- **当前核心引擎**：Combat Simulator V11.0 / Skill Generator v2.0
- **当前成长口径**：角色与战团等级上限30；角色1级旧四维→30级实测新四维；成长与难度以 `combat_numerical_paradigms/progression_difficulty/DESIGN_GUIDE.md` 为准。六阶段实测入口 `test_stage_combat_simulator.py`，每人一件装备、顶级装备最多4件。Unity正式数值核心为 `CombatRuntime.cs`，正式场景为 `BattleScene.unity`；接入规范见 `combat_numerical_paradigms/progression_difficulty/BATTLE_SCENE_INTEGRATION.md`，外部入口 `BattleSceneFlow.Enter`，退出去向由调用方决定。
- **基准验证文件**：[`d:/123/test_30man_combat_simulator.py`](file:///d:/123/test_30man_combat_simulator.py)
- **特效逐帧测试**：Unity菜单 `Tools/战斗/打开特效测试模块`，场景 `BattleEffectTestScene.unity`；当前63家族/467变体共用 `Assets/Resources/EffectTimingConfig.json`。泡泡护盾破裂片段、圣堂光柱循环、双半圆雷电循环、灵气气泡循环移出投放；现有ID保留，登记 `effect_animation_ids.json`。自身归位后播放，对敌从接触播放，伤害与物理分别配置；操作见 `combat_numerical_paradigms/progression_difficulty/EFFECT_TEST_MODULE.md`。
- **特效定位与排序**：固定初始阵容中心，不跟随受击移动；左右阵容整体居中于相机静止位置，保留间距，震屏期间重复布局不累积偏移。`useFormationSorting`按家族保存，勾选参与阵容深度，取消为最高层。当前3家族19变体使用原始前后层，后层低于角色。统一规则，不按家族名称硬编码抬升。
- **特效图片锚点**：按每帧非透明像素包围盒中心计算Sprite pivot，前后层共享主图锚点；整张画布的(.5,.5)会让首帧光斑因透明留白落到阵容下方。烘焙与备用加载均用`EffectFrameAlignment`。
- **同排遮挡一致**：角色下排在前；特效深度必须位于两排排序区间之间，不能对含列序号的角色排序值取平均后插进同一排。中间排整体位于特效前方，最高层标记不受此规则限制。
- **动作与特效时序**：前移、停留、后退全类型参照第一个特效`expfx1_epic_explosion_A`，当前用户调校0.15/0.35/0.30秒；任一类型面板修改这三项都会更新共用值，支持0。版本5支持炸散距离倍率`scatterDistanceScale`、两军站位间距`ArmyDistance`与回血时点`healFrame`。自身特效提供独立筛选，测试模块以空血→满血作为时点校准标尺；正式战斗拆分`CoHealCue`独立呈现治疗并更新血条。
- **调校保存保底**：测试模块修改即写入项目`UserSettings/EffectTimingConfig.autosave.json`与`FormationConfig.autosave.json`，退出/脚本重载补存，保留最近有效`.bak`；读取最新有效主文件或副本，构建前导出到Resources。同步代码必须保留用户当前项目的配置，禁止用源项目默认JSON覆盖。
- **技能与特效配对**：高阶名称整体意象优先于动作词；近义特效通过流派及自身/敌方限制后稳定选择，颜色依据前部元素与材质。有效已赋ID保持，旧表显式刷新后保存。24000条固定语料变体覆盖427/467，详见`combat_numerical_paradigms/progression_difficulty/EFFECT_MATCHING_GUIDE.md`。
- **人物外部标注**：`CharaClassifier.exe`默认人物总览，源码`CharacterTagging.cs`；排除场景GroundShadow后1229张人物素材归为1213人物，8组同名前缀walk/pose按稳定ID归组，标签同步全部成员、冲突保留提示。点选/多选设置种族、性别、单个身份及底部1～6阶；旧多身份用顶部检查入口处理，点击词条替换，不自动丢弃。性别男/女/无/双，未标记与无分开，种族/性别为效果目标用固有资料。宽侧栏身份区随窗口扩展；自动保存与50次运行内撤销。图库内`character_bond_labels.json`版本4兼容1～3、GUID关联及`.bak`恢复。使用见`combat_numerical_paradigms/progression_difficulty/CHARACTER_TAGGING_GUIDE.md`。

---

## 零、 核心战斗心智模型 (CORE COMBAT LOOP - 绝对基石)

> **战斗基本法**：
> 1. **30人按 1~30 号位顺位排开**。每回合轮到己方行动时，引擎**从头到尾（1号位 -> 30号位）逐个检索**。
> 2. 每个成员先判定技能门槛（回合数、战力百分比、限次），满足则按概率 ROLL 点。
> 3. **一旦命中任意技能，当回合立刻释放该技能并结束判定（一回合全队只打 1 个技能）**！
> 4. **若 30 人遍历完毕全部未触发，则执行 100% 普通攻击保底**！
> 5. **策略启示**：关键技能排在队头，保底技能维持回转。多个符合门槛且有剩余次数的技能，总发动概率为 `1-∏(1-p_i)`，不能相加后声称必定触发；每回合按实际门槛和剩余次数重新计算。

---

## 一、 项目文件导航地图 (FILE NAVIGATION - 白名单与禁飞区)

| 区域类别 | 目标文件 / 路径 | 核心定位与使用规范 |
| :--- | :--- | :--- |
| **最高宪章 (SSOT)** | [`d:/123/AGENT.md`](file:///d:/123/AGENT.md) | 本文件。任何会话进入必须优先读取，不可违背。 |
| **历史主档案** | [`d:/123/HANDOVER_ARCHIVE.md`](file:///d:/123/HANDOVER_ARCHIVE.md) | 演进全史、各模块数学模型、三大违规治理复盘。 |
| **执行级日志** | [`d:/123/HANDOVER_LOG.md`](file:///d:/123/HANDOVER_LOG.md) | 日常开发交接日志（控制在 200 行以内）。 |
| **主战斗引擎** | [`d:/123/test_30man_combat_simulator.py`](file:///d:/123/test_30man_combat_simulator.py) | 30人战团六流派 V11.0 基准模拟器 (37,500 场全排列)。 |
| **技能生成工具** | [`d:/123/SkillGenerator.cs`](file:///d:/123/SkillGenerator.cs), [`.exe`](file:///d:/123/SkillGenerator.exe), [`_cli.exe`](file:///d:/123/SkillGenerator_cli.exe) | 纯净四维自然语言技能配表生成器主程序。 |
| **词库配置** | [`d:/123/skill_affixes.txt`](file:///d:/123/skill_affixes.txt) | 技能前后缀唯一合法词库（带 8 种受击表现标记）。 |
| **Unity实机源码** | [`d:/123/LegionBattle/.../Assets/Scripts/Battle/`](file:///d:/123/LegionBattle/LegionBattle/Assets/Scripts/Battle/) | `BattleEngine.cs`, `BattleTroop.cs`, `BattleRosterStrategy.cs` 等。 |
| **绝对禁飞区 (NO-FLY)** | `d:/123/unpacked/`, `all_tables_parsed.json` | **历史拆包冷库，日常严禁阅读！严禁提取统御/灵敏/精准等死尸词！** |
| **临时归档冷库** | `d:/123/.archive_scratch/` | 历史临时抓取文本存档，禁止无差别检索。 |

---

## 二、 四维属性职责物理边界 (PROTECTED)

系统由纯净四大属性驱动，各司其职，严禁跨界污染：

| 属性 | 核心定位 | 作用物理管线 | 绝对禁令 |
| :--- | :--- | :--- | :--- |
| **勇气 (Courage)** | 物理基底 / 暴击必中 | 提供暴击率与暴伤；暴击必定命中目标 | 反噬伤害必须遵循减伤结算，严禁作为无视减伤的伪真伤 |
| **坚韧 (Resilience)** | 防御屏障 / 战力愈合 | 提供固定减伤、全域百分比减伤 (`pct_dr`)、生命恢复 | 战力恢复为原生比例，严禁与魔力乘算挂钩 |
| **先机 (Initiative)** | 行动速度 / 闪避 / 先击 | 决定行动先后顺位、提供基础闪避率、先手直接命中差值增伤 | 先手差值增伤 (`preempt_factor`) 仅限当次直接命中，严禁放大 DoT 或 Debuff |
| **魔力 (Magic)** | 百分比放大器 / 穿透 | 放大破防比例、DoT流失比例、吸血比例、技能基础暴击率、Debuff百分比 | 严禁直接乘以技能总伤害倍率 (`mult *= m_amp` 绝对禁止) |

---

## 二、 战斗计算管线与数学契约 (PROTECTED)

### 1. 行动顺位判定
- 行动顺位按当回合动态受减益影响后的**有效先机值 (`eff_i`)** 降序排列。
- 先机相同（同速对决）采用 50/50 随机抛硬币，消除攻方默认先手特权。

### 2. 伤害结算分层
- **直接攻击伤害**：
  $$\text{Damage} = \text{BaseDamage} \times (1.0 - \text{TargetDR}) \times \text{CritFactor} \times \text{PreemptFactor}$$
  - `PreemptFactor`：仅当先手机制成立时作用于首击直伤。
  - `CritFactor`：暴击成立时生效，暴击攻击必定命中（绕过闪避）。
- **持续伤害 (DoT)**：
  - 流失伤害比例受自身魔力放大 (`dot_pct * m_amp`)，独立结算，不受 `PreemptFactor` 影响。
- **减益削弱 (Debuff)**：
  - 虚弱压制与四维削弱比例受魔力放大，作用于目标有效属性，不受 `PreemptFactor` 影响。
- **真实伤害与穿透**：
  - 破防比例达 100% 后，溢出魔力按阶梯转化为穿透增伤因子：
    $$\text{PierceFactor} = 1.0 + (\text{m\_amp} - 1.0) \times 0.18$$

---

## 三、 防破窗与架构红线 (PROTECTED)

1. **反微观调参禁令 (Anti-Patchwork Engineering)**：
   - 严禁为了局域胜率单独拔高或调低单个技能的倍率或数值。
   - 所有平衡调整必须立足于全域物理规则与属性分层管线。
2. **术语与描述纯净规范**：
   - 严禁使用废弃名词（精准、统御、灵敏、先攻、无法闪避、暴击伤害等）。
   - 描述格式统一为：`[条件]n%概率发动，命中后造成n%的伤害[，效果][，先机加n][，有概率暴击]。`
3. **交付前自动化验证**：
   - 任何涉及战斗规则的修改，必须运行 `python test_30man_combat_simulator.py` 执行 37,500 场全排列模拟，六大流派胜率极差须收敛在健康区间（<=15%）。

---

## 四、 上下文防污染与真理源契约 (PROTECTED)

1. **废弃资产与临时文档物理隔离**：
   - 严禁在项目根目录存放未受控的临时抓取文档（如 `user_step_*.txt`）。所有临时调试文件统一存放至 `.archive_scratch/` 或 `.gemini/`。
2. **禁止对废弃物考古 (No Toxic Code Archaeology)**：
   - 任何代码与数值实现必须以本规范与最新主程序为准，严禁去未清理的旧代码或废弃配表中“挖坟”继承旧逻辑。
3. **禁止并列兼容 (No Legacy Aliasing)**：
   - 严禁书写 `legacy || new` 的妥协代码（如曾导致先机错误继承“无法闪避”的致命缺陷）。旧分支必须物理彻底铲除。
4. **动工前校对立项宪章 (Recall Charter Before Action)**：
   - 严防上下文截断导致的“局部打补丁”退化。面对机制疑问时，优先回溯第一法则（四维纯净分工），严禁凭臆想发明规则。

---

## 五、 行为准则与反脑补铁律 (BEHAVIOR CONTRACT - PROTECTED)

1. **三步刹车法则（严禁一步登天与擅自暗改）**：
   - 面对用户指出的问题或机制异常，**严禁跳过沟通直接改代码**。必须严格执行：
     - **第 1 步：查验核实**：调阅代码/测试数据，明确指出该问题是否存在、发生的具体代码段与事实依据。
     - **第 2 步：因果归因与方案提案**：阐明产生该现象的底层系统原因，给出 1~2 个架构规范的解决方案，列出各自逻辑与影响。
     - **第 3 步：确认后执行**：明确征求用户意见，待方案确认后再动手实施修改并测试验证。
2. **零脑补与命名锁死（严禁自创命名）**：
   - **流派名称绝对锁死**：仅允许四维基础名（勇气、坚韧、先机、魔力）与两两组合（如魔力+坚韧、勇气+先机），**严禁自造任何门派、江湖别名、花哨前缀**！
   - **技能命名规范**：严格使用 `skill_affixes.txt` 词库拼装或遵循既定标准，严禁自造违规词。
   - **物品/装备/系统零发明**：用户未明确下达指令的，**严禁私自脑补捏造任何装备、道具、消耗品或系统**。
3. **文件读取禁飞区 (No-Fly Zone)**：
   - 严禁在日常开发中读取 `unpacked/` 或历史解包数据猜测当前机制，该目录为历史冷库。
   - 严禁任何输出出现“统御、灵敏、先攻、精准、王者、无法闪避”等死尸名词。
   - 理解当前战斗机制的唯一法定真理源为 [`d:/123/AGENT.md`](file:///d:/123/AGENT.md) 与最新模拟器 [`d:/123/test_30man_combat_simulator.py`](file:///d:/123/test_30man_combat_simulator.py)。

## 六、 下一轮数值研究要求（用户确认）

- 按5/10/15/20/25/30人六阶段验证技能生成器T1～T6实际四维投放加装备后的属性合计；30人主1000/副500为可达性检验目标，同时记录裸装数值。
- 四维投放核对 `SkillGenerator.cs` 的 `GetStatBudget`、`AllocateStats` 及导出/生效链路；成长与装备贡献分别记账，逐成员自然求和。
- 若技能四维投放加装备未达到阶段目标，优先调优技能四维投放梯度与分配规则；每人一件装备、顶级装备每队最多四件。
- 确认可达玩家基准后联合优化D1/D2胜率、回合与终局血量，并复测受预算调整影响的其他研究结论。
- 下一轮执行指南：[NEXT_RESEARCH_GUIDE.md](D:/123/combat_numerical_paradigms/roster_research/NEXT_RESEARCH_GUIDE.md)。
- 2026-10-12本轮已修改生成器四维预算并完成部分验证；额度条件触发停止。恢复前必读 [CHECKPOINT_2026-10-12.md](D:/123/combat_numerical_paradigms/natural_research/CHECKPOINT_2026-10-12.md)，三个任务尚未全部完成。
- 2026-10-13已承接上述断点完成六阶段三任务实验和数值指南；最新状态见 [CHECKPOINT_2026-10-13.md](D:/123/combat_numerical_paradigms/natural_research/CHECKPOINT_2026-10-13.md)，主规范见 [DESIGN_SPECIFICATION.md](D:/123/combat_numerical_paradigms/natural_research/DESIGN_SPECIFICATION.md)。严格体验目标仍有未达标配置，研究生成器使用冻结快照，当前根目录并行特效改动保持原状。
- 2026-10-13进一步形成角色1–30级成长与阶段难度标尺，见 [DESIGN_GUIDE.md](D:/123/combat_numerical_paradigms/progression_difficulty/DESIGN_GUIDE.md)。旧四维为1级、已测预算为30级；阶段与难度定标固定敌人，保留培养/收集/编成优势。参考等级分布是设计输入，JSON与model.py可复用；不强求统一胜率或改动运行时。
- 2026-10-13用户随后授权Unity内正式战斗场景整合。当前场景为 `Assets/Scenes/BattleScene.unity`，入口 `BattleSceneFlow.Enter`，外部真实阵容与参考遭遇均可接入；退出去向只由调用方在Closed回调决定。55项真实Play Mode检查通过，详见 [BATTLE_SCENE_INTEGRATION.md](D:/123/combat_numerical_paradigms/progression_difficulty/BATTLE_SCENE_INTEGRATION.md)。


