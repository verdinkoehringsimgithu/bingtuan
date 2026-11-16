# 25人后段与高阶段压力补测

- [可采用的阶段×地区设计建议](RECOMMENDATIONS.md)
- [详细结果与不确定性](DESIGN_GUIDE.md)
- [主研究协议](PROTOCOL.md)
- [第一局部25人协议](LOCAL25_PROTOCOL.md)、[第二局部区间](TERMINAL25_PROTOCOL.md)、[固定NPC扩大阵容](ROSTER25_PROTOCOL.md)
- [完整审计](results/audit.json)、[交付检查](results/delivery_checks.json)
- [20/25/30人的具体NPC与玩家快照](results/usable_references.json)

复现：`run_research.ps1 -Workers 6`。阶段25校准与高难固定NPC校准分别保存，正式新阵容确认与同人物精度追加分开记账。每次运行按源哈希和SQLite逐格续跑。

`stage25.py`选择后段并做48格新配置确认；`hard_regions.py`216固定NPC校准、144格新配置确认；`baseline_extension.py`复核96场边缘点；`local25.py`/`terminal25.py`保留两轮局部失败；`roster25.py`固定NPC扩大真实阵容检查；`analyze_gaps.py`精确复演与汇总。

未修改战斗物理、生产人物标签、技能生成器、Unity或经济；分段行程仍是研究机制候选。研究失败候选与实际可用场景均保留，未把筛选门槛改名为成功标签。
