# 等级成长与阶段难度模型

主结论在 `DESIGN_GUIDE.md`，直接可读的投放表在 `results/designer_delivery_table.csv`，工具输入在 `results/encounter_model.json`。

本模型以旧四维为1级、已测新四维为30级；按阶段给出5/10/15/20/25/30人上限和参考等级分布，再实测三档难度及五种培养/编成状态。参考等级分布是设计输入，可调整，不宣称来自真实玩家统计。每人一件装备、最多四件顶级装备，战斗技能条件、概率、限次与顺位均保留。

## 直接调用

`model.py`只依赖Python标准库。以下示例仅演示接口，实际起点与终点使用角色自己的四维：

```python
from model import character_stats, encounter

stats = character_stats(15, [8, 1, 1, 2], [47, 7, 7, 7])
enemy = encounter(3, '很难')
typed_enemy = encounter(3, '很难', archetype='C_I', position='upper')
```

敌人是固定的阶段模板，不读取当前玩家属性来追平。`enemy_max_bp`、`enemy_full_bp_base_hit`是联动强度节点，`enemy_attack_factor`为打击修正因子；四维均值用于描述模板，技能组成仍需保留。采用自定义NPC类型可查完整108组区间。

## 复现

在项目根目录执行：

```powershell
& ./combat_numerical_paradigms/progression_difficulty/run_all.ps1 -Workers 8
```

依赖沿用 `natural_research/requirements.txt`。所需原/新C#导出与研究源码都包含在交付包中。没有虚拟环境时创建本研究的 `.venv`。逐参数结果保存到SQLite，已完成结果表复用，未完成单元恢复；不会覆盖上一轮数值研究结果。

## 档位与解读

- 难：常规参考胜率70%–80%。
- 很难：55%–70%。
- 非常难：45%–55%。

这是设计目标。实际六流派均值、极差、培养不足/高收集/顺位不同/四件装备的变化范围与截尾率均有实测，不把目标当成所有阵容的保证。某些配置没有落在目标区间时明确保留偏差。

原BP阶段标尺保持不变，等级仅改变四维；不宣称已覆盖等级BP成长、缺员队伍或单敌人单技能。研究未改Unity运行时或根目录的并行生成器工作。
