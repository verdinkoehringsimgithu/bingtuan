# 六阶段旅行节奏重标定

- [阶段投放建议](RECOMMENDATIONS.md)
- [完整对照与参数表](DESIGN_GUIDE.md)
- [预先声明的静态校准协议](PROTOCOL.md)
- [独立声明的分段探索协议](PROGRESSIVE_PROTOCOL.md)
- [审计](results/audit.json)、[交付检查](results/delivery_checks.json)

复现：`run_research.ps1`。校准72个静态候选，只用旧混合身份响应；确认使用新人物技能池1780000，144配置，12个减益状态。静态7组、分段3组各32条最多30战原生路线。各状态重新选两种装备归属和搜索顺位，训练/选择/最终种子分离。

分段候选改变旅行损耗投放节奏，单独保留签名与原始记录，不与静态档混算。它不是正式已确认游戏机制。原生战斗数值、敌方、旧研究、Unity和钱包均保持原样。

脚本：`fit_policies.py`校准，`confirm_policies.py`新阵容确认，`progressive_paths.py`同批分段探索，`analyze_retune.py`精确审计/汇总，`verify_delivery.py`交付检查。校准和分段探索默认6进程。
