# 战团 V11 数值研究运行说明

本目录保存基于两份权威规范和原生战团引擎的可复现实验。最终结果见 `V11_RESEARCH_REPORT.md`，逐回合原始数据、统计矩阵、参数和图表见 `results/`。研究不修改原引擎。

## 一键运行

在 `D:/123` 运行以下命令，脚本会创建独立 Python 环境并安装固定版本依赖：

```powershell
& ./combat_numerical_paradigms/v11_research/run_all.ps1 -Workers 8
```

默认使用已完成的阶段文件继续；改变样本量、种子或原引擎时使用新的输出目录：

```powershell
& ./combat_numerical_paradigms/v11_research/run_all.ps1 -Workers 4 -Output D:/123/combat_numerical_paradigms/v11_research/results_new
```

Windows 并发采用独立进程。每个实验由输入条件及固定 64 位种子决定；改变并发数不改变任务顺序或随机种子。恢复运行核对抽样设置和原引擎哈希。中断阶段会重新生成缺失的阶段输出。

## 分阶段运行

```powershell
$rp = './combat_numerical_paradigms/v11_research/.venv/Scripts/python.exe'
& $rp ./combat_numerical_paradigms/v11_research/scan_difficulties.py --workers 8
& $rp ./combat_numerical_paradigms/v11_research/run_research.py --workers 8
& $rp ./combat_numerical_paradigms/v11_research/extended_validation.py --workers 8
& $rp ./combat_numerical_paradigms/v11_research/target_unique.py --workers 8
& $rp ./combat_numerical_paradigms/v11_research/verify_research.py
& $rp ./combat_numerical_paradigms/v11_research/build_report.py
```

`run_native_regression.py` 保存固定种子 37,500 场原引擎回归，默认由一键运行调用。

## 文件用途

| 文件 | 用途 |
| --- | --- |
| `research_core.py` | 动态读取原生行动函数，插入遥测，执行保序研究驱动与显式实验杠杆 |
| `scan_difficulties.py` | 独立六维扫描入口 |
| `run_research.py` | 全域扫描、独立验证、截面、24,000 场遥测、PCA、K-Means/GMM、装备与策略实验 |
| `extended_validation.py` | 起始胜率校准、敌方装备应对、负向风险、实测异质通道 |
| `target_unique.py` | 由训练数据选出最小已测贡献比例，并在独立簇上验证 20–30 点提升 |
| `verify_research.py` | 原生一致性、互斥伤害和血量守恒、原始日志数量、种子重放及特征隔离 |
| `build_report.py` | 从保存的证据表生成报告、计数及哈希清单 |
| `requirements.txt` | 分析依赖的固定版本 |

## 数据定义

`wr` 是原引擎裁定的胜率，包含 40 回合时的血量比例裁定；`decisive_wr` 只计玩家存活且敌方死亡；`censor_rate` 表示两边仍存活。`hp` 是所有对局的终局平均血量；`winner_hp` 仅对胜局取均值。`rounds_*.jsonl.gz` 每行一场战斗，包含输入、种子、汇总和完整回合序列。`telemetry_features.csv.gz` 每行一场特征，`telemetry_cluster_assignments.csv.gz` 另加训练/独立验证标记和簇编号。

互斥伤害通道包括物理直伤、物理暴击增量、纯真伤、纯真伤暴击增量、最大流失、已损流失、反噬和斩杀。穿透贡献为诊断量，不与这些伤害重复求和；恢复记录实际恢复，原伤害与实际掉血分开。

S6 精确复用原生技能组合；S1–S5 的完整组合按公开统一阶位规则投影。敌方宏观参数为显式实验层。单角色装备采用 q=1/N 的整体贡献近似，源引擎没有角色级实体，因此不能识别真实个人预算最优值。所有未达到拟合目标的配置保留测量与残差，不自动升级为正式投放规范。
