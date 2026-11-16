# LegionBattle 战斗系统与数值引擎 (Unity C# 复刻规范)

本模块是一套完全解耦、高还原度、支持脱敏商用的**战团回合制概率战斗模拟引擎**。
代码采用纯 C#（netstandard2.0 / .NET 8 / Unity 通用）编写，零 `UnityEngine` 强依赖，既可在 Unity 客户端驱动高速演播与回放，也可直接移植至服务端做战斗校验。

---

## 一、 快速导入 Unity 说明

1. **源码导入**：
   将 `LegionBattle/Core/`、`LegionBattle/Bridge/`、`LegionBattle/Data/` 目录直接拖入 Unity 工程的 `Assets/Plugins/LegionBattle/` 或 `Assets/Scripts/Combat/` 目录下即可完成编译。
2. **命名空间引用**：
   ```csharp
   using LegionBattle.Core.Enums;
   using LegionBattle.Core.Data;
   using LegionBattle.Core.Config;
   using LegionBattle.Core.Simulation;
   using LegionBattle.Core.Bridge;
   ```
3. **平台兼容性**：
   支持 Unity 2020.3+ / 2021.3+ / 2022.3+ / Unity 6 等所有 LTS 版本，兼容 IL2CPP、WebGL、iOS、Android、PC/Mac。

---

## 二、 概念脱敏映射表

为规避版权争议，本引擎采用全套自主术语体系：

| 原始概念 | 本引擎代码术语 (C#) | 策划文档术语 (中文) | 核心机制作用 |
| :--- | :--- | :--- | :--- |
| **战力 (BP)** | `Vigor` | **精力值** | 战团共享的生命血池 |
| **先攻 (Speed)** | `Initiative` (INI) | **先机** | 决定先后手；隐式提升暴击暴伤（+0.5%/点） |
| **防御 (Defense)** | `Fortitude` (FRT) | **坚韧** | 双曲免伤；隐式提升精准伤害（+0.5%/点） |
| **闪避 (Dodge)** | `Agility` (AGI) | **灵敏** | 双曲回避率；隐式提升治疗量（+0.5%/点） |
| **王者 (Authority)**| `Dominance` (DOM) | **统御** | 相对差值增伤乘区（+1.0%/点差值） |
| **暴击技能** | `Havoc` | **暴击流** | 暴击爆发；天生无视 50% 坚韧；可被闪避 |
| **纯粹技能** | `Precision` | **精准流** | 绝对必中不可闪避；王者差值全额转真实伤害 |
| **闪避回复** | `Tenacity` | **恢复流** | 高回避 + 巨额过量治疗（无血量上限） |
| **战团/佣兵** | `Legion` / `Operative` | **战团 / 干员** | 30人编制群殴阵列 |
| **合体技** | `Synergy Skill` | **连携技** | 战团满足指定干员模板数量时激活 |
| **修炼系统** | `Discipline` | **心法修炼** | 攻守对抗系数乘区（进攻加成/防守抗性） |

---

## 三、 核心底层公式系统

### 1. 基础输出基数 (Base Output, $B$)
$$B = 0.2 \cdot \text{Vigor}_{\max} + 0.1 \cdot \text{Vigor}_{\text{cur}}$$
保证即使残血依然有 20% 最大生命保底输出，同时满血时具备更高攻击力。

### 2. 四维下限与一级属性换算
所有属性在运算前自动受硬下限约束：
$$\text{Stat}_{\text{eff}} = \max(-50, \; \text{Stat}_{\text{raw}})$$

* **坚韧免伤因子 (DRF)**：
  $$\text{DRF} = \frac{100}{100 + \text{Fortitude}}$$
  （坚韧为 100 时减伤 50%；坚韧为 -50 时承受 200% 易伤）
* **千分比灵敏回避率 ($P_{\text{agi}}$)**：
  $$P_{\text{agi}} = \frac{\text{Agility}}{100 + \text{Agility}} \times 1000 \quad (\text{Agility} \ge 0)$$
* **统御差值增伤乘区 ($M_{\text{dom}}$)**：
  $$M_{\text{dom}} = 1 + \max(0, \; \text{Dominance}_{\text{caster}} - \text{Dominance}_{\text{target}}) \times 0.01$$
  （注：低于目标时不降低伤害，乘区保底 1.0）

### 3. 四维对称“隐式次级加成”矩阵
| 属性 | 一级职能 | 二级隐式加成公式 | 联动受益流派 |
| :--- | :--- | :--- | :--- |
| **先机 (INI)** | 决定先后手（平局攻方先手） | $K_{\text{havoc}} = K_{\text{base}} + 0.005 \times \text{INI}$ | 暴击流（爆伤上限质变） |
| **坚韧 (FRT)** | 双曲免伤率 | $K_{\text{prec}} = K_{\text{base}} + 0.005 \times \text{FRT}$ | 精准流（高防转高真伤） |
| **灵敏 (AGI)** | 双曲回避率 | $M_{\text{heal}} = 1.0 + 0.005 \times \text{AGI}$ | 恢复流（巨额过量治疗） |
| **统御 (DOM)** | 全局王者差值 | $M_{\text{dom}} = 1.0 + 0.01 \times \Delta\text{DOM}$ | 全局输出与真伤放大 |

### 4. 三大流派结算公式
* **暴击流 (HavocStrike)**：
  - 受闪避制约（可 MISS）；
  - 穿透 50% 坚韧：$\text{DRF}_{\text{havoc}} = \frac{100}{100 + \max(-50, \text{Fortitude} \times 0.5)}$；
  - 最终伤害：$D = \lceil B \times (K + 0.005 \cdot \text{INI}) \times \text{DRF}_{\text{havoc}} \times M_{\text{dom}} \rceil$。
* **精准流 (PrecisionStrike)**：
  - **绝对必中**（强制跳过回避判定，不可闪避）；
  - 无视坚韧免伤，全额真实伤害（优先破盾后削精力）；
  - 最终真伤：$D = \lceil B \times (K + 0.005 \cdot \text{FRT}) \times M_{\text{dom}} \rceil$。
* **恢复流 (SelfMaxRestore)**：
  - 单次回血：$H = \lceil \text{Vigor}_{\max} \times K \times (1.0 + 0.005 \cdot \text{AGI}) \rceil$；
  - **过量治疗允许 $\text{Vigor}_{\text{cur}} > \text{Vigor}_{\max}$**，无上限滚雪球。

---

## 四、 核心接口与外部调用空间

### 1. 战前组装与执行战斗（极简用法）
```csharp
using LegionBattle.Core.Config;
using LegionBattle.Core.Data;
using LegionBattle.Core.Enums;
using LegionBattle.Core.Simulation;

// 1. 创建攻守双方战团
var leftLegion = new Legion("Player Legion", maxVigor: 1500000, init: 110, fort: 40, agi: 20, dom: 65, isLeft: true);
var rightLegion = new Legion("Boss Legion", maxVigor: 2000000, init: 80, fort: 150, agi: 10, dom: 30, isLeft: false);

// 2. 装配技能
leftLegion.EquippedSkills.Add(new ActiveSkillData
{
    Id = 1001,
    Name = "Blade Tempest",
    EffectType = SkillEffectType.HavocStrike,
    Param = 240f,
    TriggerWeight = 600
});

// 3. 运行确定性模拟并获取回放数据
var simulator = new BattleSimulator(seed: 123456);
BattleRecord record = simulator.Simulate(leftLegion, rightLegion, maxTurns: 30);

// 4. 查看结果
Debug.Log($"Battle Ended in {record.TotalTurns} turns. Result: {record.Result}");
```

### 2. Unity 视图绑定（`IBattlePresenter`）
实现 `IBattlePresenter` 接口即可将战斗逻辑与 Unity UI、动画和音效无缝结合：

```csharp
using UnityEngine;
using LegionBattle.Core.Bridge;
using LegionBattle.Core.Data;
using LegionBattle.Core.Enums;
using LegionBattle.Core.Simulation;

public class UnityBattleView : MonoBehaviour, IBattlePresenter
{
    [SerializeField] private HealthBarUI leftHpBar;
    [SerializeField] private HealthBarUI rightHpBar;
    [SerializeField] private CombatTextSpawner textSpawner;

    public void OnBattleStart(Legion left, Legion right)
    {
        leftHpBar.Init(left.MaxVigor, left.CurrentVigor);
        rightHpBar.Init(right.MaxVigor, right.CurrentVigor);
    }

    public void OnTurnStart(int turnNumber, Legion attacker, Legion defender)
    {
        Debug.Log($"Turn {turnNumber}: {attacker.Name} is attacking!");
    }

    public void OnSkillCast(Legion caster, ActiveSkillData skill)
    {
        // 弹出技能名称横幅（Skill Pop-up Banner）
        textSpawner.ShowSkillBanner(caster.IsLeft, skill.Name);
    }

    public void OnDamageDealt(Legion target, long damage, DamageType type)
    {
        // 播放震屏、受击闪白与飘字
        textSpawner.SpawnDamageText(target.IsLeft, damage, type);
        if (target.IsLeft) leftHpBar.UpdateHp(target.CurrentVigor, target.ShieldVigor);
        else rightHpBar.UpdateHp(target.CurrentVigor, target.ShieldVigor);
    }

    public void OnHealApplied(Legion target, long heal, bool isOverheal)
    {
        textSpawner.SpawnHealText(target.IsLeft, heal, isOverheal);
        if (target.IsLeft) leftHpBar.UpdateHp(target.CurrentVigor, target.ShieldVigor);
        else rightHpBar.UpdateHp(target.CurrentVigor, target.ShieldVigor);
    }

    public void OnEvasion(Legion target)
    {
        textSpawner.SpawnMissText(target.IsLeft);
    }

    public void OnBuffApplied(Legion target, BuffData buff) { }

    public void OnBuffTick(Legion target, string buffName, long tickDamage)
    {
        textSpawner.SpawnDotText(target.IsLeft, buffName, tickDamage);
    }

    public void OnDeathDefy(Legion target, int remainingCount)
    {
        // 名刀锁血特效
        textSpawner.SpawnDeathDefyEffect(target.IsLeft);
    }

    public void OnShieldBreak(Legion target) { }

    public void OnBerserkActivated(int turnNumber)
    {
        // 超时狂暴全屏光效
        textSpawner.ShowBerserkAlert(turnNumber);
    }

    public void OnBattleEnd(BattleResult result)
    {
        // 弹出结算界面
        Debug.Log($"Game Over: {result}");
    }
}
```

---

## 五、 完备机制特性对照

| 特性分类 | 机制名称 | 源码/引擎对应实现 |
| :--- | :--- | :--- |
| **主动机制 (17种)** | 普攻、暴击、精准必中、逆境斩杀、精力吸取/回复、真实伤害、镜像技能复制、同损自爆A/B、血量互换 | `SkillResolver.cs` 完整枚举实现 |
| **被动机制 (10种)** | 先机/坚韧/灵敏/统御增幅、属性比例转换、阈值突破、免死锁血、开场护盾、回避压制 | `PassiveResolver.cs` 战前编译注入 |
| **状态机制 (4种)** | 创伤流血(回合前)、腐蚀剧毒(回合后)、虚弱(伤害削弱)、重创(治疗削弱) | `BuffProcessor.cs` 时点严格分离 |
| **队列机制** | 12项条件判定（回合窗、血量窗、连击失手补偿、相对战力、次数上限） + 100% 截断 | `SkillSelector.cs` 精确概率池抽取 |
| **隐藏机制保障** | 四维硬下限 -50、负防易伤、平局攻方先手、过量治疗无上限、非零保底 1 点、超时狂暴 | `Legion.cs`, `BattleSimulator.cs` |

全部机制经过 .NET 9 / C# 8 严格自动化测试验证，公式数学自洽，可放心用于正式游戏工程。
