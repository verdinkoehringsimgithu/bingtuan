# 2026-10-27：旅行补给、返程与混合身份

本轮承接用户“行继续”，推进[上一轮](../DESIGN_GUIDE.md)留下的补给/返程/混合身份缺口。

- [具体研究协议与未定项](PROTOCOL.md)
- [本轮应采用的边界与数值修订方向](RECOMMENDATIONS.md)
- [实测结论](DESIGN_GUIDE.md)
- [换人、持久状态、补给与Unity接入建议](INTEGRATION_SPEC.md)
- [计算和账本审计](results/audit.json)、[交付检查](results/delivery_checks.json)

研究入口：`run_research.ps1 -Workers 6`。Python使用已配置捆绑运行时，依赖复用既有研究环境；支持SQLite逐格续跑，源哈希变化不会复用旧签名结果。5人顺位穷举训练排列，较大队伍有限搜索；所有选择与最终测试种子分离。

`state_contract.py`是供调用方接入的候选持久状态，`supply_adapter.py`提供“恢复缺失上限比例”的明确换算。原生旅行矩阵以“清除log损耗比例”测试，见协议；两种补给语义不能混用。不会修改Unity、人物标签、旧引擎或冻结研究输入。

`study_closure.py`原始诊断投影中worker_saves不可用，原生计数为worker_procs；正式分析不发布该字段，也不把它当成社畜未触发。社畜完整战斗机制和开关比较均参与测试。
