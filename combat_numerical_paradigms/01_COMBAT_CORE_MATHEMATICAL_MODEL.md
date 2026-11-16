# 战团战斗系统全量机制、物理边界与数学公式全典 (V11.0 Canonical)

- **更新时间**：2026-10-12
- **权威代码源**：`d:/123/test_30man_combat_simulator.py` (V11.0 Full Audit Canonical)
- **立项契约**：`d:/123/AGENT.md`

---

## 一、 四维属性职责物理边界与作用管线

系统由纯净四大属性驱动，各司其职，物理边界严格正交，绝对禁止跨界污染与私自混合：

| 属性 | 英文键名 | 核心定位 | 物理作用管线 | 绝对禁令 |
| :--- | :--- | :--- | :--- | :--- |
| **勇气 (Courage)** | `dodge` (CSV历史键) | 物理直伤基底 / 暴击必中 / 斩杀反噬 | 提供暴击率与暴伤增幅；暴击必定命中目标并强行绕过闪避；提供已损反噬与斩杀基础 | 勇气伤害严格接受目标坚韧减伤结算，严禁将其作为无视防御的伪真伤 |
| **坚韧 (Resilience)** | `defense` | 防御屏障 / 减伤铁壁 / 战力自愈 | 提供固定数值减伤 (`flat_dr`)、全域百分比减伤 (`pct_dr`)、战力恢复 (`heal`) | 战力自愈为原生战力比例，本职守恒，绝对禁止与魔力乘算挂钩 |
| **先机 (Initiative)** | `speed` | 行动时序 / 身法闪避 / 先击差值增伤 | 动态决定回合出手顺位、提供基础闪避率、先手直接命中差值增伤 (`preempt_factor`) | 先手增伤仅限当回合直接命中直伤，绝对禁止放大持续流失 (DoT) 或减益 (Debuff) |
| **魔力 (Magic)** | `authority` | 百分比放大器 / 破防穿透 / 状态强化 | 放大技能破防比例、放大持续流失比例、放大吸血比例、放大技能基础暴击率、放大削弱Debuff | 绝对禁止将魔力放大器直接乘以技能总伤害倍率 (`mult *= m_amp` 绝对禁止) |

---

## 二、 基础攻击力与行动时序判定

### 1. 基础攻击力模型 (Base Power)
为消除第 1 回合开局秒杀，同时保留残血与满血状态下的技能高光，普攻与技能的基础打击力统一采用生命加权公式：
$$\text{BasePower} = 0.09 \times \text{MaxBP} + 0.045 \times \text{CurrentBP}$$
* 满血时基准打击力：$0.135 \times \text{MaxBP}$（即满血打出 13.5% 最大战力基底）；
* 濒死残血时基准打击力：逼近 $0.09 \times \text{MaxBP}$（即 9.0% 最大战力基底）。

### 2. 动态顺位与先手判定
* 行动顺位在每回合开始时，动态读取受 Debuff（四维削弱等）影响后的**有效先机值 (`eff_i`)** 降序排列。
* **同速随机抛硬币**：若双方有效先机完全相等，采用 50/50 独立随机抛硬币决定首发，消除攻方默认先手特权。

---

## 三、 四维底层换算数学公式

### 1. 魔力响应式放大器 (Responsive Magic Amplifier)
$$\text{m\_amp} = \begin{cases} 1.0, & \text{magic} \le 0 \\ 1.0 + \left(\frac{\text{magic}}{\text{magic} + 280.0}\right) \times 1.5 + \left(\frac{\text{magic}}{1400.0}\right) \times 0.7, & \text{magic} > 0 \end{cases}$$
* **属性敏感度实测**：
  * $\text{magic} = 50 \implies 1.25\times$
  * $\text{magic} = 100 \implies 1.44\times$
  * $\text{magic} = 280 \implies 2.04\times$
  * $\text{magic} = 500 \implies 2.21\times$
  * $\text{magic} = 1000 \implies 2.67\times$

### 2. 坚韧减伤与防御公式 (Resilience DR)
* **百分比减伤 (`pct_dr`)**：上限封顶 68%
  $$\text{pct\_dr} = \min\left(0.68, 0.25 + \frac{\text{resilience}}{\text{resilience} + 450.0} \times 0.45\right)$$
* **固定数值减伤 (`flat_dr`)**：
  $$\text{flat\_dr} = \text{resilience} \times 12.0 \times 0.38 = \text{resilience} \times 4.56$$

### 3. 勇气暴击与命中公式 (Courage Crit)
* **原生暴击率 (`crit_rate`)**：
  $$\text{crit\_rate} = \frac{\text{courage}}{\text{courage} + 750.0} \times 0.45$$
* **暴击伤害增幅加成 (`crit_bonus`)**：
  $$\text{crit\_bonus} = 0.45 + \frac{\text{courage}}{\text{courage} + 650.0} \times 0.75$$
* **魔力对技能自带暴击率加成**：
  $$\text{esc} = \text{base\_crit\_rate} \times \left(1.0 + (\text{m\_amp} - 1.0) \times 0.45\right)$$
* **全量暴击率**：
  $$\text{total\_crit\_rate} = \text{crit\_rate} + \text{esc}$$
* **超额暴击溢出转换法则**：当全量暴击率超过 100% 时，超出部分按 1:1.5 比例无损转化为额外暴伤：
  $$\text{extra\_overflow} = (\text{total\_crit\_rate} - 1.0) \times 1.5 \quad (\text{if } \text{total\_crit\_rate} > 1.0)$$
* **暴击必定命中法则**：暴击判定为真时，必定直接命中，彻底绕过目标的所有闪避判定。

### 4. 先机闪避与先手增伤公式 (Initiative Stats)
* **身法闪避率 (`dodge_rate`)**：上限封顶 35%
  $$\text{dodge\_rate} = \min\left(0.35, \frac{\text{initiative}}{\text{initiative} + 450.0} \times 0.48\right)$$
* **先手差值增伤 (`preempt_bonus`)**：上限封顶 35%
  $$\text{diff} = \max(0.0, \text{acting\_initiative} - \text{defender\_initiative})$$
  $$\text{preempt\_bonus} = \begin{cases} \left(\frac{\text{diff}}{\text{diff} + 500.0}\right) \times 0.35, & \text{diff} > 0 \\ 0.0, & \text{diff} \le 0 \end{cases}$$
  $$\text{preempt\_factor} = \begin{cases} 1.0 + \text{preempt\_bonus}, & \text{is\_first is True and diff} > 0 \\ 1.0, & \text{其他情况} \end{cases}$$

---

## 四、 战斗结算完整物理管线

### 1. 伤害与治疗主阶段
1. **先机动态成长**：若技能附带 `ini_bonus > 0`，自身当前先机即刻累加（持续本场战斗）。
2. **命中与暴击判定**：
   * 判定暴击：$\text{random}() < \min(1.0, \text{total\_crit\_rate})$；
   * 若未暴击：判定敌方闪避 $\text{random}() < \text{dodge\_rate}$，若闪避成功则直接判定 Miss 结束本次行动。
3. **主倍率合成**：
   $$\text{mult} = \frac{\text{main\_param}}{100.0} + (\text{crit\_bonus} + \text{extra\_overflow} \text{ if is\_crit else } 0)$$
   $$\text{raw\_dmg} = \text{BasePower} \times \text{mult} \times \text{preempt\_factor} \times \text{dmg\_output\_factor}$$
4. **坚韧治疗结算**：
   若技能主类型为 `Heal`：
   $$\text{HealAmount} = \text{acting.MaxBP} \times \text{sub\_param}$$
   自身战力恢复该数值（上限为 MaxBP），直伤倍率按 100% 结算。
5. **防御减免与纯真伤穿透**：
   * 计算魔力放大后的破防比例：$\text{eff\_ignore\_def} = \text{ignore\_def\_ratio} \times \text{m\_amp}$；
   * **纯真伤穿透门槛**：当 $\text{eff\_ignore\_def} \ge 0.85$ 时，判定为纯真伤穿透，完全绕过坚韧的固定减伤与百分比减伤，并触发魔力穿透阶梯增幅：
     $$\text{true\_bonus} = 1.0 + (\text{m\_amp} - 1.0) \times 0.20$$
     $$\text{actual\_dmg} = \text{raw\_dmg} \times \text{true\_bonus}$$
   * **常规物理/魔法减伤**：
     $$\text{eff\_pct\_dr} = \max\left(0.0, \text{pct\_dr} \times (1.0 - \text{eff\_ignore\_def})\right)$$
     $$\text{actual\_dmg} = \max\left(1.0, \text{raw\_dmg} \times (1.0 - \text{eff\_pct\_dr}) - \text{flat\_dr}\right)$$

### 2. 附加效果物理管线 (SubEffects)
| 效果名称 | 触发时机 | 数学计算公式 | 物理约束 |
| :--- | :--- | :--- | :--- |
| **自身已损反噬** | 攻击命中后 | $\text{extra} = (\text{MaxBP} - \text{CurBP}) \times \text{sub\_param} \times (1.0 - \text{pct\_dr})$ | 严格受目标坚韧减伤约束，绝无穿透 |
| **敌方已损斩杀** | 攻击命中后 | $\text{extra} = (\text{Def.MaxBP} - \text{Def.CurBP}) \times \text{sub\_param} \times (1.0 - \text{pct\_dr})$ | 严格受目标坚韧减伤约束，绝无穿透 |
| **战力吸收 (吸血)**| 攻击命中后 | $\text{Heal} = \text{actual\_dmg} \times (\text{sub\_param} \times \text{m\_amp})$ | 恢复量受实际造成的伤害和魔力放大 |
| **最大流失 (DoT)** | 回合开始前结算 | $\text{Loss} = \text{Def.MaxBP} \times (\text{sub\_param} \times \text{m\_amp}) \times (1.0 - \text{pct\_dr}) \times \text{src\_factor}$ | 受坚韧减免与施法者输出削弱约束 |
| **已损流失 (DoT)** | 回合结束后结算 | $\text{Loss} = (\text{Def.MaxBP} - \text{Def.CurBP}) \times (\text{sub\_param} \times \text{m\_amp}) \times (1.0 - \text{pct\_dr}) \times \text{src\_factor}$ | 回合末结算，受坚韧减免约束 |
| **虚弱压制** | 攻击命中后施加 | $\text{scaled\_pct} = \min(0.60, \text{base\_pct} \times (1.0 + (\text{m\_amp} - 1.0) \times 0.25))$ | 降低目标造成的所有伤害，持续 N 回合 |
| **四维削弱** | 攻击命中后施加 | $\text{scaled\_pct} = \min(0.40, \text{base\_pct} \times (1.0 + (\text{m\_amp} - 1.0) \times 0.25))$ | 按百分比降低目标当前四维，持续 N 回合 |
| **先机加n** | 技能触发时施加 | $\text{cur\_initiative} += \text{ini\_bonus}$ | 梯队绑定：1/2/3/5/7/10，持续整场战斗 |
