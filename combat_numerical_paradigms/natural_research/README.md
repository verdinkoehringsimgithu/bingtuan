# 六阶段自然属性战斗研究

本目录完成5/10/15/20/25/30人、六种流派的敌人投放、时序聚类、角色补强与装备研究。最终结论见 `DESIGN_SPECIFICATION.md` 和 `stage_guides/`；CSV、原始回合及成员日志在 `results/`。实际指标偏离目标的配置逐项列出，不把研究完成等同于全部胜率目标达成。

## 阵容与数值来源

双方均有阶段对应数量的真实成员记录。成员技能与四维由当前研究快照的 C# 技能生成器导出；四维逐人相加，未归一化到1000/500。每人一件装备、每队最多四件顶级装备。顺位检索、条件、发动概率、次数、未触发普攻和持有者限定效果均进入战斗。BP 使用权威阶段标尺均分，未声称覆盖完整等级/角色生产数据库。

源模型、研究适配和研究机制的边界在最终规范中列明。根模拟器未修改；相同管线模式通过600例一致性与37500局回归。研究适配按数学规范使用防守方先机计算闪避，使用有效坚韧结算流失，与原脚本对应两处实现差异明确列出。

## 运行

从 D:/123 或交付压缩包解压后的项目根目录执行：

```powershell
& ./combat_numerical_paradigms/natural_research/run_all.ps1 -Workers 8
```

优先使用原 `v11_research/.venv`。不存在则自动建立本目录 `.venv` 并安装 `requirements.txt`。已有完整结果会被复用。数值扫描将每个完成参数单元存入 SQLite；每个遥测场景单独保存后再汇总。参数与计算源签名不同不会复用旧缓存。

所有脚本必须保留项目目录层级：自然研究脚本依赖 `roster_research/` 中的规范研究适配及少量统计函数，和项目根的两个 Python 源文件。交付包包含这些必要依赖。

若需完整重算，请指定新的研究副本目录并复制冻结源、三套当前技能库和 `selected_stat_profile.json`，保留原成果用于对照。不要直接删除结果来验证复现。

## 技能导出与冻结

`export_catalog.ps1` 默认编译 `source_snapshots/SkillGenerator_checkpoint.cs`，避免当前根目录的并行特效代码改变研究输入。三个当前技能库的样本偏移为0、128、384；384用于独立最终测试。`catalog_before.json` 是调整前预算对照。

```powershell
& ./combat_numerical_paradigms/natural_research/export_catalog.ps1 -Output ./combat_numerical_paradigms/natural_research/results/catalog_reproduction.json -Samples 128 -Offset 384
```

上例写新文件，可与 `catalog_final_test.json` 比较。GUI生成器研究快照为 `source_snapshots/SkillGenerator_research.exe`；运行时将当前目录设为项目根以读取同一词库。根目录正在修改的源码及旧GUI文件保持原状。

## 实验阶段

1. `run_natural.py --phase all --workers 8`：敌人、角色顺位、普通装备、机制及四件分配、36000场遥测、基础聚类。
2. `enrich_discovery.py`：补全未出技能步长、覆盖面积及先机漂移，重新训练六阶段无监督模型。
3. `advanced_study.py --phase all --workers 8`：主C边际、保底方差、质变响应、预算干预、特化与跨流派、三种对抗路径和异质嵌入。
4. `refine_delivery.py --workers 8`：D2验证细化、全新技能库测试、共享宏观投放验证、连续参数投放策略。
5. `calibrate_equipment.py`、`calibrate_unique.py`、`unique_mechanism_holdout.py`、`calibrate_counter.py`、`embedding_audit.py`：目标档位及机制独立测试。
6. `plot_research.py --workers 8`、`derive_design_tables.py`、`build_report.py`：实测等高线、统计图、数值表和规范。
7. `validate_natural.py`、`validate_delivery.py`、`package_delivery.py`：模型、交付数据与成果包校验。

原优化候选表产生于分配镜像修正之前，最终设计不使用它们证明最优；最终达标证据来自真实C#导出和独立技能库。当前全局预算是已验证可行候选，未宣称全局最优。
