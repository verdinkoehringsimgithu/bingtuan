# 旅行与副本长期减益研究

用户2026-10-21确认：每战后回满当前有效战力上限，长期减益保留；主动撤退带走所有已得战利品。目标是优势地区30战内能力降至约50%胜率、极低余量胜利地区两三战内产生补给压力，并直接限制副本抵达Boss入口的概率。

主交付：[设计指南](DESIGN_GUIDE.md)。记录用户要求与研究假设：[requirements.json](requirements.json)。

六阶段5/10/15/20/25/30人，六流派，真实人物与生成技能，普通装备/四件顶级，各状态独立搜索顺位。长期层独立于普通战内减益；自动回血不清除长期层，治疗只能回到受限上限。没有修改Unity、旧引擎或既有研究输入。

复现入口：`D:/123/combat_numerical_paradigms/expedition_research/run_expedition_research.ps1 -Workers 6`。支持用`-Phases`指定阶段。捆绑Python3.12，自动引入已有研究依赖；候选与矩阵逐格SQLite提交，重新运行复用相同签名记录。

- `measure_response.py`：固定地区校准与战力/四维/混合长期上限的真实战斗响应。
- `low_margin_reference.py`：额外快速威胁参照，实际胜后余量不足目标时保留差异，不把参照名当成实测标签。
- `fit_paths.py`：仅用校准响应和加权条件路径拟合，显式保留生存者选择。
- `confirm_paths.py`：温和候选的独立原生连战对照；`refine_policy_targets.py`按30/3战目标重新排序既存校准候选；`confirm_refined.py`使用独立目录验证新候选。
- `audit_research.py`：源哈希、真实编制、事件账本、战斗计数、逐场精确复现。
- `analyze_expedition.py`：原生幸存者曲线、独立响应预测、副本不利事件/战败战利品/往返遭遇敏感性。
- `bond_trip_core.py`、`verify_bond_trip.py`：隔离复合羁绊引擎的长期损耗层；无损耗同轨迹及治疗上限核对。
- `recovery_stress.py`、`analyze_recovery.py`：女仆长两档复合预算与农民果实，六阶段真实连战；胜后血量/累计承伤两种压力信号配对比较，结果见[强恢复补测](RECOVERY_STRESS.md)。
- `strong_pressure.py`、`audit_strong_pressure.py`：沿预先扫描空间核验较强地区损耗档，复用强恢复人物与顺位作配对探索，见[较强档结果](STRONG_PRESSURE.md)。
- `verify_delivery.py`：交付表格行数、源哈希、文档链接、审计记录与基准胜率极差核对。

地区选择接口为`results/regions.json`与`results/low_margin/regions.json`；完整区域校准矩阵由审计从签名SQLite提交恢复到`region_calibration_evidence.json`。正式修订候选及原始记录位于`results/refined/`。旧候选记录完整保留，不能将原版与修订版作为独立玩家总体数量相加。

报告中的上限、目标包、事件强度都是研究候选；战败战利品保留、补给价格/携带量、地图遭遇密度尚未指定。副本入口数据与Boss胜率分开，经济用通过普通战斗数作为无价格代理，不捏造金币收益。

正式确认主矩阵未开启身份羁绊；强恢复补测单独开启女仆或农民，并保持敌方羁绊关闭。尚未覆盖23种羁绊任意混搭。各表的难度参照名不代替实测胜率；20/25/30人真实低余量且胜率高于50%的参考目前未覆盖。
