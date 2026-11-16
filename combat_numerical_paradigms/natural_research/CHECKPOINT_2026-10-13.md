# 研究交接：2026-10-13

## Quick Reference
**Confidence keywords:** natural_research、1000/500、六阶段、四件顶级装备、GetStatBudget、AllocateStats、D1D2、PCA、K-Means、counter、embedding、calculation_checkpoints.sqlite、DESIGN_SPECIFICATION。
**Outcome:** 三项研究的六阶段实验及设计指导已完成；原始体验目标并非全部达标，已逐项记录。未宣称生产Unity集成完成。

## Decisions Made
- 沿用真实技能生成器四维加全员装备的自然求和基准，双方按阶段人数组成阵容，BP使用规范阶段标尺；不回退到预设1000/500。
- 顶级装备每隊最多4件，所有持有者效果按实际概率、门槛、次数及顺位结算。普通静态属性无需发动。
- 保留原预算候选，重新生成独立技能库偏移384作最终验证；原优化镜像修正前候选表不用于最优性证明。
- 模型未找到额外逐次技能倍率衰减公式，保留真实BP加权、次数耗尽、覆盖及减益倒计时，不自行添加物理规则。
- 开局护盾等被动能力放到未占用后排，技能装备保持实际持有者；强度校准后独立验证。
- 属性重分配前后团队四维守恒；单独重分配没有收益，持有者属性放大才产生集中预算效果。常规预算加单机制另有独立验证。
- 聚类由完整轨迹数据产生，不带预设敗因标签；输入排除胜负和场景字段，训练/验证/测试拆分固定，低轮廓系数明确披露。

## Completed Results
- 交付协议12029472次对战执行，包含配对基线；不计未落盘中断扫描，也不重复计派生表。
- 36000场D3/D4遥测，630000条玩家成员记录，双边回合初末BP、速率、加速度、伤害谱、覆盖、机会和耗尽均保存。
- 30人新技能库1536个独立阵容样本全部达到主1000/副500；其他阶段少量尾部样本未达标，普通装备覆盖下界表明确记录。
- D1全部36个阶段/流派配置达到原联合目标；D2只有3/36，D3为8/36，D4为16/36。用户已允许突破死板胜率约束，报告仍保留各指标，不强称全部达标。
- 四件装备校准的D4阶段均值约79.7%–84.9%，22/36个配置落在80%–85%；给出逐位置配置、普通属性下界/拐点和五维装备响应。
- 角色预算、单机制、跨流派特化/泛用、扩大克制、反制强档与均势档、僵局、敌方四装备应对、异质嵌入均有独立测试。
- 六阶段PCA解释90%方差需要51–59个分量，测试轮廓系数部分约0.08；不把低分离簇包装成确定败因。

## Solutions & Fixes
- run_natural.py参数单元逐项写SQLite，可恢复；遥测每个场景写独立完成文件；CSV原子替换；重跑的运行清单另写历史，避免覆盖原执行量。
- 新增17种主C机制响应，其中命中保底与命中附加流失有独立零效果、一致性和持有者校验。
- 最终模型校验通过：600例原管线一致性、3072条属性分配一致、串行/并发一致、原引擎37500局极差13.4个百分点。最终交付数据校验通过。
- 冻结生成器导出独立库3072条记录重现完全一致。

## Files and Entry Points
- 主规范：D:/123/combat_numerical_paradigms/natural_research/DESIGN_SPECIFICATION.md。
- 六阶段指南：同目录stage_guides/S1_5_MEMBERS.md至S6_30_MEMBERS.md。
- 一键复现：同目录run_all.ps1；固定依赖requirements.txt。
- 结果：同目录results，逐文件协议execution_protocol.csv，验证delivery_validation.json。
- 交付包：D:/123/combat_numerical_paradigms/NATURAL_RESEARCH_DELIVERY_2026-10-13.zip；文件哈希清单在研究目录DELIVERY_MANIFEST.json。
- 研究生成器：source_snapshots/SkillGenerator_checkpoint.cs和SkillGenerator_research.exe。
- 2026-10-12断点保留为历史记录，原机制扫描中断进度已通过重新运行完成。

## Concurrent Source Changes
- 研究期间根SkillGenerator.cs出现特效映射改动，独立编译新增依赖。对比数值生成前缀未变，详见results/concurrent_source_audit.json。
- 本研究保留根目录并行改动，未将研究快照覆盖回当前文件；附带生成器和导出脚本使用冻结快照。Unity独立生成路径仍需单独集成验证。
- 原战斗引擎SHA256保持 d82477b368cea5994053bcee99a618d560135e6a5195926afe26f78aa91ba75e。

## Pending Tasks
- 本次授权研究已交付，不遗留需继续运行的仿真任务。
- 后续可另做D2联合体验进一步优化、稀有度与等级经济、整数化装备、完整生产卡池及Unity集成；这些适用范围没有在当前证据中宣称完成。
- 新人数节点的连续插值未实测，不应自动视为同等体验。

## Quick Resume Context
直接读新DESIGN_SPECIFICATION与六阶段指南，2026-10-12断点已被本次完成结果承接。三项实验已完成，但严格联合体验目标并非全部通过；数值指导和失败边界均保存。研究使用冻结生成器，根目录有并行特效改动，后续不可盲目覆盖当前源码。
