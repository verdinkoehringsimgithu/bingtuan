# 六阶段逐角色战团数值研究

下一轮研究按 [研究与优化要求](D:/123/combat_numerical_paradigms/roster_research/NEXT_RESEARCH_GUIDE.md) 执行：先依据技能生成器T1～T6四维投放和装备验证阶段属性可达性；不足时优先调优技能四维投放，确认玩家基准后再优化敌人难度。下面的运行流程对应已交付研究，下一轮新增可达性流程需按该指南实现。

先读 [数值设计规范](D:/123/combat_numerical_paradigms/roster_research/DESIGN_SPECIFICATION.md)，其中连接六个阶段的三个任务配表。完整角色与常规装备配置、顶级强度边界、每件普通属性范围、技能条件/发动率/次数/顺位均导出在 results。

## 运行全部任务

在本目录运行：

```powershell
.\run_all.ps1 -Workers 8
```

需要Python 3.11或3.12；脚本创建独立环境并安装 requirements.txt。也可以指定已经安装依赖的解释器：

```powershell
.\run_all.ps1 -Workers 8 -Python 'D:/123/combat_numerical_paradigms/v11_research/.venv/Scripts/python.exe'
```

使用新的输出目录重新执行全部实验：

```powershell
.\run_all.ps1 -Workers 8 -Output '.\results_fresh'
```

各阶段脚本可单独运行，均支持 `--workers` 和 `--output`：

1. `run_study.py --phase foundation`：预算与原生对照、阵容数量/顺位、六维敌人扫描、D1～D4参考、28,800场D3/D4时序遥测、无监督统计。
2. `equipment_study.py`：普通四维/战力、15种机制、持有者分配、库存0～4曲线。
3. `stage_extensions.py`：各阶段PCA/簇、主C模板数量开放至N、独特角色预算与机制、技能衰减。
4. `delivery_validation.py`：较低普通装备工作点、重新校准敌人、四件分配独立验证、四条策略路径和敌方四件装备反制。
5. `final_checks.py`：预算/概率/次数/装备约束/源引擎对照/遥测重放、多进程一致性、攻防等高线、异质通道、顶级强度梯度及独立验证。
6. `build_report.py`：从数据生成设计规范及六阶段详表。

每个数据阶段存在目标文件则复用，不必重跑已完成矩阵。修改规则、角色生成或扫描参数后，应选择新的输出目录，避免复用不同实验条件的数据。构建规范使用当前输出目录；所有数字来自表格。

## 数据约定

- CSV的stage为0～5；完整阵容JSON和报告的阶段为1～6。
- 六流派仅使用C_I、C_R、M_I、M_R、M_C、R_I。
- `win`为真实击败敌方；120回合未分胜负为`censored`，不强制判胜。
- `wr`区间为Wilson 95%；配对`delta`为胜率增益（0.2=20个百分点）。敌人恢复参数与配对增益同时出现时，恢复列名为`macro_delta`。
- 属性点数为单件增量；balanced为四维总点数，均分到四维；bp轴为单件战力。
- 顶级装备与普通基础属性在同一件装备内，逐成员至多一件、每队最多4件顶级。
- `rounds_*.jsonl.gz`保存每场完整双边时序和每回合玩家/敌人技能顺位概率；`owners_*.jsonl.gz`保存玩家成员贡献，每人每场一条。
- `stage_S*_models.joblib`保存本次可信本地生成的特征标准化/PCA/K-Means模型。
- 相同种子支持复现，串行与并行检查记录在`final_model_checks.json`。

## 依赖的项目源

保持目录关系：本目录位于`combat_numerical_paradigms/roster_research`；根目录有`test_30man_combat_simulator.py`和`generate_skills_preview.py`。源码归档包提供原始源文件快照、数学规则和研究数据。Python生成器的词库读取不影响本研究使用的倍率/发动率函数。

主C、保底、填充是研究成员模板分类，实际贡献需看拥有者触发分布。报告给出实测参考区间，角色全集、装备价格/掉率或新生产技能需要用相同框架接入实际清单后复测。
