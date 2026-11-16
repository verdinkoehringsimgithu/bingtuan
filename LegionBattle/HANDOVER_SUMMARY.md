# 战团战斗系统技术复盘与研发规划白皮书 (Technical Handover & Roadmap)

> **项目定位**：基于原版数值体系脱敏重构的战团回合制概率战斗模拟引擎（纯 C# / Unity 表现层解耦）。  
> **文档目标**：梳理底层战斗引擎架构、盘点已有代码资产、规范配表工程字段契约，并制定后续研发施工路线图。

---

## 一、 战斗引擎架构复盘 (Architecture Retrospective)

本项目完成对原版战斗数值体系的底层数学重构与代码脱敏，建立了一套逻辑层零 `UnityEngine` 依赖、可同时运行于 Unity 客户端与服务端的独立对决模拟引擎。

### 1. 概念脱敏与术语映射
全套命名空间独立为 `LegionBattle`，核心术语规范如下：

| 原始概念 | 代码术语 (C#) | 中文术语 | 机制职能 |
| :--- | :--- | :--- | :--- |
| **战力 (BP)** | `Vigor` | **精力** | 战团共享的生命血池 |
| **先攻 (Speed)** | `Initiative` (INI) | **先机** | 决定先后手；次级加成暴击暴伤（+0.5%/点） |
| **防御 (Defense)** | `Fortitude` (FRT) | **坚韧** | 双曲免伤；次级加成精准伤害（+0.5%/点） |
| **闪避 (Dodge)** | `Agility` (AGI) | **灵敏** | 双曲回避率；次级加成精力回复量（+0.5%/点） |
| **王者 (Authority)**| `Dominance` (DOM) | **统御** | 相对差值全局放大（+1.0%/点差值） |
| **暴击技能** | `Havoc` | **暴击流** | 暴击爆发；天生无视 50% 坚韧；可被灵敏闪避 |
| **纯粹技能** | `Precision` | **精准流** | 绝对必中不可闪避；王者差值全额转真实伤害 |
| **回复技能** | `Tenacity` | **恢复流** | 高回避与过量精力回复（突破 100% 血量上限） |
| **特异技能** | `Utility` | **特异流** | 吸血、斩杀、持续伤害(DOT)、虚弱、名刀、技能复制等 |
| **合体技** | `Synergy Skill` | **连携技** | 战团满足特定干员组合时激活的独立合体技能 |
| **修炼系统** | `Discipline` | **心法修炼** | 攻守对抗系数（进攻加成与防守抗性代数抵消） |

---

### 2. 底层战斗数学闭环
1. **基础输出基数 ($B$)**：
   $$B = 0.2 \cdot \text{Vigor}_{\max} + 0.1 \cdot \text{Vigor}_{\text{cur}}$$
   保证战团残血时具备 20% 最大生命保底攻击力，满血时获得额外输出权重。
2. **四维硬下限与一级属性换算**：
   $$\text{Stat}_{\text{eff}} = \max(-50, \; \text{Stat}_{\text{raw}})$$
   * 坚韧免伤因子：$\text{DRF} = \frac{100}{100 + \text{Fortitude}}$
   * 灵敏千分比回避率：$P_{\text{agi}} = \frac{\text{Agility}}{100 + \text{Agility}} \times 1000 \quad (\text{Agility} \ge 0)$
   * 统御差值增伤乘区：$M_{\text{dom}} = 1.0 + \max(0, \; \Delta\text{DOM}) \times 0.01$
3. **四维对称次级加成**：
   * 先机 $\to$ 暴伤：$K_{\text{havoc}} = K_{\text{base}} + 0.005 \times \text{INI}$
   * 坚韧 $\to$ 精准增伤：$K_{\text{prec}} = K_{\text{base}} + 0.005 \times \text{FRT}$
   * 灵敏 $\to$ 治疗放大：$M_{\text{heal}} = 1.0 + 0.005 \times \text{AGI}$
   * 统御 $\to$ 全局与真伤放大：$M_{\text{dom}} = 1.0 + 0.01 \times \Delta\text{DOM}$
4. **流派克制闭环**：
   * **暴击流**（50%破防+高爆发）克制 **高坚韧精准流**；
   * **精准流**（绝对必中+真伤穿透）克制 **高闪避恢复流**；
   * **恢复流**（双曲高回避+过量大额回复）克制 **暴击流**（闪避使暴击空刀）。

---

### 3. 状态机与技能抽取逻辑
* **触发判定**：12 项条件过滤（回合上下限、自身精力百分比窗口、敌方精力百分比窗口、上回合击中状态、敌我战力对比）。
* **截断队列**：概率千分比累加，达到 1000（100%）时强制截断后续技能判定。
* **首轮必发机制**：`IsFirstTurnGuaranteed` 标记在第 1 回合拥有最高抽取优先级。
* **Buff 时点严格分离**：
  * 回合开始前：结算流血（扣除当前精力百分比）；
  * 回合结束后：结算剧毒（扣除最大精力百分比）；
  * 命中后判定：若 `NeedHit = true`，未命中时跳过附带减益与 Buff 施加。

---

## 二、 已有代码资产盘点 (Asset Inventory)

源码统一位于 `d:/123/LegionBattle/` 目录下，并通过了 .NET 8 自动化测试验证。

### 1. 核心代码库

| 模块目录 | 源码文件 | 技术职责说明 |
| :--- | :--- | :--- |
| **`Core/Enums/`** | `BattleEnums.cs` | 17 种主动机制、10 种被动机制、4 种 Buff、流派、四维、伤害类型枚举 |
| **`Core/Config/`** | `FormulaConfig.cs` | 公式系数单例、全局战斗常量（四维下限 -50、超时狂暴阈值等） |
| **`Core/Data/`** | `BattleDataModels.cs` | `ActiveSkillData` (35个技术字段)、`PassiveSkillData`、`BuffData`、`DisciplineData` |
| **`Core/Simulation/`**| `Legion.cs` | 30人战团实体（精力池、护盾池、名刀计数、过量治疗、四维派生计算） |
| **`Core/Simulation/`**| `DamageCalculator.cs` | 基础输出基数 $B$、50% 破防、心法乘区、超时狂暴、虚弱削弱结算 |
| **`Core/Simulation/`**| `BuffProcessor.cs` | 时点分离结算：回合前流血、回合后剧毒 |
| **`Core/Simulation/`**| `SkillResolver.cs` | 17 种主动技能效果结算器（精准真伤、自爆、镜像复制、宿命换血等） |
| **`Core/Simulation/`**| `SkillSelector.cs` | 12 项条件过滤 + 100% 截断 + 首轮必发判定 |
| **`Core/Simulation/`**| `PassiveResolver.cs` | 被动编译、四维属性转化、阈值突破、连携技同名卡核验 |
| **`Core/Simulation/`**| `BattleRecord.cs` | 单回合战斗回放切片记录器（与客户端五元组数据对齐） |
| **`Core/Simulation/`**| `BattleSimulator.cs` | 战斗主循环（平局攻方先手、时钟推进、超时狂暴、胜负终局判定） |
| **`Core/Bridge/`** | `IBattlePresenter.cs` | Unity 表现层解耦接口（UI、动画、飘字、震屏回调） |
| **`Core/Bridge/`** | `SamplePresenter.cs` | 控制台战斗事件格式化输出（调试测试用） |
| **`Bridge/`** | `TroopVisualPresenter.cs` | 表现层动画控制：步行图切帧、前突突进、8 种受击物理动力学 |
| **`Data/Importers/`** | `CsvTableReader.cs` | 高性能 CSV 解析器，支持引号转义与字段安全转换 |
| **`TestRunner/`** | `Program.cs` | 自动化对局模拟验证入口 |

### 2. 文档资产

| 文档名称 | 定位与说明 |
| :--- | :--- |
| **`README.md`** | 引擎快速导入 Unity 说明、四维公式全景、外部调用接口与接入示例 |
| **`ORIGINAL_NUMERICAL_ANALYSIS.md`** | 原始解包 1,118 名干员统计学分析报告（阶位分布、成长曲线、心法体系） |
| **`DESIGN_GUIDELINES.md`** | 角色数值设计规范、四大流派参数红线、受击动力学枚举规范 |
| **`PROGRESSION_SYSTEM_DESIGN.md`** | 角色成长数值规范：等级经验、飞升觉醒、专属宝具与心法修炼体系 |

---

## 三、 研发实施路线图 (Master Roadmap)

按照**“配置表工程化 $\to$ 表现层与组件装配 $\to$ 关卡与数值闭环验证”**三阶段推进：

```
┌────────────────────────────────────────────────────────────────────────┐
│ 第一阶段：配表工程 (Data Table Engineering)                           │
│ • 基于原版解包数据清洗并规范标准 CSV 配置表                           │
│ • 固化数值区间红线，完成 C# 表格数据加载器与自动化校验脚本             │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 第二阶段：表现层与组件装配 (Presentation & Component Assembly)         │
│ • Unity 工程框架搭建与 LegionBattle 引擎对接                           │
│ • 像素角色预制体拼装与 8 种受击物理动画联调                            │
│ • UI 制作：30 人战阵编队布阵盘、战斗血条与事件跳字展示                │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 第三阶段：关卡接入与数值验证 (Stages & Numerical Validation)           │
│ • 战役关卡与怪物战团配置表接入                                         │
│ • 自动化回归对决压测，校验各流派对抗胜率与确定性回放                   │
│ • 打包可运行 Demo 与技术交付                                           │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 四、 第一阶段：配表工程规范 (Phase 1 Specification)

配置表采用标准 UTF-8 编码 CSV 格式，统一存放于 `d:/123/LegionBattle/Data/Configs/`。

### 1. 核心数据表清单

```text
Data/Configs/
├── skills_active.csv       ← 主动技能配置表 (基于 active_skill.csv 清洗映射)
├── skills_passive.csv      ← 被动技能配置表 (基于 passive_skill.csv 清洗映射)
├── skills_synergy.csv      ← 连携合体技配置表 (基于 cooperative_skill.csv 清洗映射)
├── operatives.csv          ← 干员基础数据表 (基于 mercenary.csv 清洗映射)
├── artifacts.csv           ← 专属宝具配置表 (基于 mercenary_artifact.csv 清洗映射)
└── disciplines.csv         ← 心法修炼配置表 (基于 cultivation.csv 清洗映射)
```

### 2. 表格通用结构格式
每张 CSV 表格采用前三行定义元数据、第四行起为数据主体的标准工程规范：
* **第 1 行**：中文字段注释说明；
* **第 2 行**：C# 强类型标记（`int`, `float`, `string`, `bool`）；
* **第 3 行**：程序字段英文名称（严格对应 `BattleDataModels.cs` 属性名）；
* **第 4 行及以后**：具体配置数据行。

### 3. 关键表格字段规范

#### 表 1：`skills_active.csv` (主动技能配置表)
严格对齐 [`ActiveSkillData`](file:///d:/123/LegionBattle/Core/Data/BattleDataModels.cs#L9-L65)：
* `id` (int): 技能唯一标识
* `name` (string): 技能名称
* `description` (string): 技能描述
* `min_turn` (int): 最早可用回合数（turn_cond1）
* `max_turn` (int): 最晚可用回合数（turn_cond2，0为无限制）
* `min_self_vigor_pct` (int): 自身精力下限百分比（self_bp_cond1）
* `max_self_vigor_pct` (int): 自身精力上限百分比（self_bp_cond2，0为无限制）
* `min_target_vigor_pct` (int): 目标精力下限百分比（enemy_bp_cond1）
* `max_target_vigor_pct` (int): 目标精力上限百分比（enemy_bp_cond2，0为无限制）
* `compensation` (int): 连击/失手补偿类型（0=无, 1=命中后连击, 2=失手补偿）
* `relative_power_cond` (int): 相对战力条件（0=无, 1=我方高于敌方, 2=我方低于敌方, 3=相等）
* `trigger_weight` (int): 触发概率千分比权重（1~1000）
* `use_count_limit` (int): 单场战斗最大释放次数（0为无限制）
* `effect_type` (int): 效果类型枚举（1~17，对应 `SkillEffectType`）
* `param` (float): 主效果倍率
* `param2` (float): 次级效果倍率
* `need_hit` (bool): 附带效果是否需要命中才触发
* `self_stat_ini / frt / agi / dom` (int): 临时增减自身四维量
* `target_stat_ini / frt / agi / dom` (int): 临时增减目标四维量
* `turn_fixed` (int): 时钟推进修正值
* `exhaust_duration` (int): 虚弱持续回合数
* `ignore_evasion` (bool): 是否不可闪避（必中）
* `ignore_fortitude` (bool): 是否无视坚韧（完全破防）
* `seal_genre` (int): 封印技能流派类型
* `seal_duration` (int): 封印持续回合数
* `hit_reaction_type` (int): 受击物理动画类型（0~8）

#### 表 2：`skills_passive.csv` (被动技能配置表)
严格对齐 [`PassiveSkillData`](file:///d:/123/LegionBattle/Core/Data/BattleDataModels.cs#L125-L165)：
* `id` (int): 被动技能唯一标识
* `name` (string): 被动技能名称
* `passive_type` (int): 被动效果类型枚举（1~10，对应 `PassiveType`）
* `target_genre` (int): 目标流派限定
* `stat_ini / frt / agi / dom` (int): 四维属性常驻修正量
* `multiplier` (float): 效果倍率参数
* `threshold` (float): 触发条件阈值
* `max_stacks` (int): 最大叠加上限

#### 表 3：`operatives.csv` (干员基础数据表)
* `id` (int): 干员唯一 ID
* `name` (string): 干员名称
* `tier` (int): 阶位品质（1~6，对应灰/绿/蓝/紫/金/彩）
* `genre` (int): 所属流派（1=暴击, 2=精准, 3=恢复, 4=特异）
* `init_vigor` (long): 初始精力值
* `vigor_growth` (float): 战力/精力成长因子（bp_factor）
* `active_skill_id` (int): 绑定的主动技能 ID
* `passive_skill_id` (int): 绑定的被动技能 ID
* `artifact_id` (int): 关联的专属宝具 ID
* `sprite_asset_path` (string): 步行图切片资源相对路径
