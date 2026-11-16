# 研究断点：2026-10-12 20:54（北京时间）

## Quick Reference (for AI scanning)
**Confidence keywords:** natural_research、SkillGenerator、GetStatBudget、AllocateStats、1000/500、T1-T6、四件顶级装备、六阶段、D1-D4、PCA、K-Means、mechanism_response_scan、source_stat_allocation_exact、CPR。
**Projects:** D:/123 战团数值研究；当前自然成长研究目录 combat_numerical_paradigms/natural_research。
**Outcome:** 已保存自然属性达标、六阶段难度验证、角色顺位扫描与普通装备属性扫描；因额度剩约4%而停止进一步计算，三项研究尚未全部完成。

这是可审阅的研究决策与证据摘要，不包含内部思维链。用户最新指令是即时存档，并在 token 不足时终止计算；已中止运行会话 26229，退出码1，检查未发现该运行的 Python 主进程或 spawn_main 子进程。

## Decisions Made
- 原始任务仍覆盖 5/10/15/20/25/30 人六阶段，每阶段均需敌人投放、无监督短板挖掘、全员装备三个任务。流派只用 C_I、C_R、M_I、M_R、M_C、R_I。
- 用户已授权补充要求后直接执行，不再询问未知装备数值。每人一件装备，每队最多4件顶级装备；主C、保底、填充角色均纳入。
- 本轮由真实 C# 技能生成器生成成员四维，然后累加装备；禁止将总四维重新归一到阶段目标。1000/500 是30人队伍装备后主副属性的达标要求，裸装另报。
- 原生成器 T1-T6 四维总预算为0、1–2、3–4、5–7、8–11、12–16，不能把技能综合强度W当四维预算。原预算无法自然达到新要求，故优先调整生成器的全局四维投放，未改变技能发动率、条件、次数与主动效果参数。
- 真实预算导出的候选已验证可达，但只是一个可行候选，不能称为全局最优或最终投放规范。高阶各流派属性存在不同程度超额，后续需要经济与战斗效果共同定标。
- BP 暂用规范阶段总量并均分到成员；这不是完整的生产卡池等级成长验证。角色满阶四维加成另列，不混入主要达标结果。
- 战斗保留逐成员顺位判断、首个成功技能、发动条件、次数、技能衰减和装备实际持有者；普通属性装备不依赖技能触发，技能增强装备仅在持有者实际发动时生效。
- 不按人工阈值预设败因。后续聚类不使用胜负和场景标签作为输入；完整战斗轨迹聚类是事后分析，不能直接声称能预测未来败局。
- 旧研究保留：roster_research 是归一化阶段预算研究，可用作机制与历史参考，不能作为自然1000/500达标证据。

## Key Learnings
- AllocateStats 使用 C# Math.Round 的偶数舍入以及固定残差归属顺序。Python 初始镜像曾把部分第三/第四属性顺序交换，已修复并通过3072条真实导出逐字段校验。
- 优化训练表及 candidate_reachability 数据产生于该镜像修复之前，属于暂存候选证据，不可用来宣称最优。实际 C# tuned 数据、独立导出 holdout 数据和战斗评估不受镜像错误影响。
- 生成器源代码已经修改，但 GUI 可执行程序尚未重编译。Unity 的独立角色属性生成策略尚未同步；不能宣称游戏运行时已全面应用新预算。
- 当前运行只在阶段完成后写结果。中止时机制扫描最新进度6600/8100，这些机制扫描中间结果仅在内存，未写出CSV，不能计入可交付完成成果。
- 完成阶段可以复用；恢复时机制扫描需要重跑。下一次先增加按批次落盘和断点恢复，再执行耗时扫描。

## Solutions & Fixes
- GeneratorBridge.cs 直接调用真实生成器，读取实际导出的技能和成员属性，不手造最终总属性。
- natural_core.py 实现当前战力治疗、固定流失绝对量、当前战力物理流失的研究适配，并校验对应单位与减伤行为。
- 模型验证已通过：600个原引擎管线一致性案例；3072条四维导出精确一致；主动参数未改变；串行/并发一致；原引擎37500局回归流派胜率极差13.4个百分点。
- 原引擎文件保持不变，SHA256 为 d82477b368cea5994053bcee99a618d560135e6a5195926afe26f78aa91ba75e。

## Files Modified
- D:/123/SkillGenerator.cs：StatBudgetRanges、StatPrimaryWeight、StatSecondaryWeight、GetStatBudget、GetStatBudgetDesc、AllocateStats。
- D:/123/combat_numerical_paradigms/natural_research/GeneratorBridge.cs、export_catalog.ps1：真实C#导出与独立样本偏移。
- 同目录 natural_core.py、reachability.py、run_natural.py、validate_natural.py：自然阵容、达标测试、阶段扫描和模型验证。
- 同目录 source_snapshots/SkillGenerator_before.cs：修改前源代码。
- D:/123/combat_numerical_paradigms/roster_research/NEXT_RESEARCH_GUIDE.md、RESEARCH_CONTRACT.md、README.md 与 D:/123/AGENT.md：前轮已追加新的研究要求。

## Setup & Config
- 工作目录 D:/123；PowerShell；Python：D:/123/combat_numerical_paradigms/v11_research/.venv/Scripts/python.exe。
- C# 编译器 C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe。桥接编译不启动GUI。
- 包版本 numpy2.2.6、pandas2.2.3、scipy1.15.3、scikit-learn1.6.1、matplotlib3.10.3、joblib1.6.0。
- 本轮8个工作进程，BLAS线程限制为1；当前运行已终止。
- 调整后T1-T6总四维范围：36–44、54–66、54–66、54–67、55–68、62–75。
- 主属性权重0.6931515783314715，副属性权重0.10771411490803917，另两维均为剩余的一半。固定副属性映射 C→M、R→C、I→C、M→R。
- 主样本为每tier/genre生成128个技能；独立库样本偏移128，再取阵容池512–767。各技能种类主动参数真实保留。未来若用该独立库重新调参，它应改称验证集并另外生成最终测试集。
- 当前参考编成主C2、保底4（小阶段按人数裁剪）、其余填充，主/副属性成员比例约0.7/0.3。角色数量扫描已开放其他构成，但尚未替换参考基线。
- 普通装备总属性点沿用旧研究操作点，按流派主/副属性67%/33%分配；顶级装备占用同一件装备位置，继承普通属性底座。

## 已落盘计算成果
结果目录：D:/123/combat_numerical_paradigms/natural_research/results。

| 已完成阶段 | 主要结果文件 | 范围 |
|---|---|---|
| 原投放与调整后达标 | source_reachability*、tuned_reachability* | 真实生成器导出，含裸装与装备档位 |
| 独立达标验证 | reachability_independent_holdout.csv、reachability_independent_summary.csv | 6阶段×6流派×256阵容=9216条 |
| 敌人全局扫描 | enemy_global_scan.csv | 33696参数/对局组合单元 |
| 敌人联合局部优化 | enemy_joint_refinement.csv | 9072单元 |
| D1-D4独立对战验证 | difficulty_candidates.csv、difficulty_holdout.csv | 144场景，378000次执行 |
| 主C/保底人数和顺位 | role_count_order_scan.csv、role_count_holdout.csv | 1344扫描单元及36个验证场景 |
| 普通装备属性响应 | common_stat_scan.csv、common_stat_ranges.csv、stat_partial_derivatives.csv | 3024扫描单元 |
| 模型验证 | model_validation.json、native_37500_regression.txt | 全部已列验证通过 |

foundation_manifest.json 记录基础阶段1943568次执行；它不是本轮所有后续阶段的总计。未生成 continuation_manifest.json，不补写虚构完整总量。机制扫描的6600个内存单元不属于保存结果。

独立达标验证各阶段六流派均值（主/副；目标来自阶段规范，仅做达标参照）：

| 人数 | 主属性均值 | 副属性均值 | 达标说明 |
|---|---:|---:|---|
| 5 | 167.289 | 66.967 | 全部独立样本达标 |
| 10 | 360.408 | 190.548 | 全部独立样本达标 |
| 15 | 533.886 | 310.691 | 全部独立样本达标 |
| 20 | 781.713 | 413.227 | 全部独立样本达标 |
| 25 | 1009.025 | 507.474 | 达标比例约99.9%，有少量未达标 |
| 30 | 1180.116 | 626.121 | 全部独立样本满足1000/500 |

达标是在当前参考普通装备属性投放下，不依赖额外顶级机制装备。不同流派超额不同，需要继续压缩差异，不能据此认定该预算最终合适。

六阶段 D1 测试的流派平均胜率约99.9%–100%，平均1.05–1.29回合，平均终局血量约96.2%–99.9%，明显改善旧归一化研究结果。D2 流派平均胜率约94.1%–98.3%，平均3.68–6.31回合，终局血量约59.7%–63.6%；部分阶段胜率过高、回合范围偏离，尚未联合达标。平均值不能替代逐流派门槛验收。D3/D4已保存候选和验证结果，但完整装备/补强研究尚未做完。

## Pending Tasks
- [ ] 先为 run_natural.py 增加机制扫描批次保存、精确参数键和断点恢复，保留已经完成的阶段文件。
- [ ] 重新计算镜像修复后的优化证据，或明确将原训练/候选表从最终设计证据中排除；不要声称所选预算全局最优。
- [ ] 重跑8100单元机制响应扫描，完成四件顶级装备组合、持有者分配、强度曲线、持有数量曲线、D3/D4独立验证。
- [ ] 采集36000场完整D3/D4时序；完成六阶段相关性、PCA贡献率、K-Means质心及独立测试统计。
- [ ] 实现独特角色预算占比与机制干预，分开原阵容/只重分配/只机制/两者合用四个对照，验证针对自然聚类的胜率提升。
- [ ] 六阶段测试五维装备需求、四大战略路径，包括敌人装备应对、异质角色嵌入、全流派矩阵，不以未经实测的胜率阈值强行宣称成功。
- [ ] 如继续调D2，先将现有holdout明确作为验证反馈，新增未参与调参的技能库与阵容池作最终测试。
- [ ] 生成各阶段/流派胜率与对局时长等高线，形成可使用的敌人参数投放表与拟合函数，报告适用范围和未达标项。
- [ ] 形成完整六阶段三任务设计规范、普通装备属性上下限、顶级装备分配与角色占比；做交付复核与独立运行说明。
- [ ] 重编译GUI并审视Unity独立生成路径同步；在完成之前清楚区分源码候选、研究工具与实际游戏运行时。

## Errors & Workarounds
- 本轮机制扫描在6600/8100后因额度不足中断，未落盘该阶段局部结果。保留完成阶段，恢复需重跑该机制阶段。
- 现有 --phase all 会按已完成文件跳过难度、角色扫描和普通属性扫描，机制阶段从头开始。增加批次保存之后再运行：

```powershell
& 'D:/123/combat_numerical_paradigms/v11_research/.venv/Scripts/python.exe' 'D:/123/combat_numerical_paradigms/natural_research/run_natural.py' --phase all --workers 8
```

该命令只覆盖已实现的流程，不会自动完成尚未编写的角色干预、四大战略、最终设计文档。

## Custom Notes
- 用户没有暂停长期goal的指令；本项目未创建goal。此次停止来自用户明确的额度条件，不对任何goal状态作更改。
- 本断点使用CPR结构化摘要；不归档私有推理。未自动读取其他Claude会话，以免将无关会话拼接到本研究日志。
- 完整归档包将包含本轮脚本、结果、源代码快照、必要研究依赖和SHA256成果清单。旧研究结果保留原处，不重复复制其大型归档。

## Quick Resume Context
当前研究已经将四维从强行设定的阶段总量改为真实技能生成器预算加全员装备，并修改根SkillGenerator.cs；独立30人样本达到1000/500，但预算候选尚非最终规范。六阶段D1-D4、角色顺位和普通属性扫描已完成；机制扫描未保存中间结果，遥测聚类、角色补强和四大战略仍待完成。先读本断点与成果清单，补批次保存，再恢复 --phase all；不要把三个任务标为全部完成。
