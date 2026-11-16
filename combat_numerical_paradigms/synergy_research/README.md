# 六阶段身份羁绊研究

三项最新投放建议：[女仆、农民与冒险者设计指南](THREE_BOND_DESIGN_GUIDANCE.md)，补齐D4预算曲线、果实消融与同最大奖励的冒险目标组合，逐阶段数据见[COMPOUND_D4_GUIDE.md](COMPOUND_D4_GUIDE.md)。完整展开参数在`results/compound_d4/resolved_candidate_parameters.json`，独立入口`run_compound_d4.ps1`；与既有23项规范配套。

2026-10-21效果补充：[女仆长、果实与冒险者复合效果研究](COMPOUND_EFFECT_DESIGN.md)，以用户新确认方向为基础，将女仆长改为逐步扩展复合效果、果实改为同时回复与多种四维、冒险目标改为真实血线/暴击/防守闪避节点。确认要求见[补充定义](../progression_difficulty/IDENTITY_SYNERGY_COMPOUND_ADDENDUM.md)，候选解锁点与数值见`compound_effects.json`。独立入口`run_compound_research.ps1`，旧研究矩阵保持。

最新规范（2026-10-21）：[身份技能、装备与专门克制设计指南](JOINT_DESIGN_GUIDE.md)。包含23项身份的六阶段/六流派技能供给独立确认、四件顶级与全员普通属性装备联测、仅非顶级装备的属性带，以及按实际技能动作检查的装备归属。逐阶段见`joint_stage_guides/`，专门反制详见[六阶段克制测试](COUNTER_DESIGN_GUIDE.md)。数据与源清单在`results/joint/`；复现入口`run_joint_research.ps1 -Workers 6`，逐完成格自动存档并验证，保持Unity与生成器现状。

顺位基线复核（2026-10-20）：[最优顺位设计指南](OPTIMAL_ORDER_DESIGN_GUIDE.md)。23项按现有人物供给覆盖六阶段、六流派，822单元、5,538,432次研究执行；这是旧候选系数的复核。复现入口`run_optimal_order.ps1 -Workers 6 -Rosters 1`，串联断点续算、全量验证、敌方事件补录和报告。旧`run_all.ps1`保留用于历史研究复现。

**2026-10-16顺位口径修订**：正式结论只按固定阵容的搜索最优顺位评估，开启/关闭羁绊与参考阵容分别优化。下述旧数据保留为历史实测，候选系数待新口径复核；见[顺位评估规范](ORDER_EVALUATION_PROTOCOL.md)。新入口`order_search.py`，不再用前后/随机顺位的平均值定强度。

机制原文：[用户确认的23项设计](../progression_difficulty/IDENTITY_SYNERGY_DESIGN.md)。
交付结果：`DESIGN_SPECIFICATION.md`、`stage_guides/`、`results/recommended_design.json`。

从任意目录运行 `D:/123/combat_numerical_paradigms/synergy_research/run_all.ps1 -Workers 8`。
运行环境沿用 `v11_research/.venv`，依赖版本沿用 `natural_research/requirements.txt`。

研究层使用真实身份阶级和唯一人物数、真实生成技能、1～30级成长、全员装备以及既有固定阶段敌人。研究代码独立于Unity生产工程，不写入人物标签、技能生成器、钱包或正式战斗规则。

人物标签不含生产技能绑定，研究按身份阶级抽取实际生成技能；技能供给偏好是待采用的设计候选。女仆长、果实与冒险目标的效果方向采用2026-10-21补充定义，具体解锁点、数值和目标组合继续作为研究候选。

`run_bonds.py`执行人数/强度扫描、独立抽样、两两消融、装备/等级稳健性、未定效果候选与双方全羁绊混编。
`refine.py`只使用验证技能库选择阶段系数，再用独立技能库与新种子确认。软校准参照5/10/20个百分点均保存，不将胜率参照当作硬约束。
`skill_supply.py`比较随机、可重复、吞吐、前期释放、顺位编排等投放候选，保持角色四维与装备不变。验证选择后独立确认，保留原随机方案作为候选。
`analyze.py`汇总时序相关性、PCA与聚类质心，并输出图表和设计规范。

`results/checkpoints.sqlite`逐完成单元提交，源/输入变化时生成不同签名，历史结果不冒充新版本结果。
`results/skill_supply_checkpoints.sqlite`单独保存技能供给实验。当前执行量只统计对应输入签名已完成单元，旧版本、中断及派生表不重复计入。

`replicates/`保留逐场配对结果；`telemetry/`保留抽样对局每回合双边状态和成员技能装备；这些是运行生成的数据。
种子在作业中明确记录，攻击随机值按回合/成员/通道寻址。重新运行复用完成单元，不需删除旧成果。
