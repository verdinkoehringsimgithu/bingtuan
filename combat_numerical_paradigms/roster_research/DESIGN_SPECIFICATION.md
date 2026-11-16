# 六阶段战团数值设计规范：逐角色阵容与装备实测

本次三项任务均按 S1～S6、六大流派重新测试。每边按对应阶段人数构造完整成员列表；成员具有自身四维、战力、技能条件、发动率、独立次数与一件装备。每回合从队首逐个独立判定，首个成功技能结束技能搜索；全未成功才由随机成员普攻。战斗使用共享全队战力和合计四维，成员贡献通过拥有者记账。

这份规范可以直接用于数值配表的首轮参考；所有推荐旁边提供实测区间、独立复测和适用阵容。顶级装备数量上限为4，与主C模板数量分别扫描。

## 测试边界与数值单位

阵容是由原始模拟器四技能组合、当前技能生成器及六阶段预算构造的可复现基准成员库；不是生产角色全集的随机抽卡样本。所有成员、技能、门槛、顺位和装备已导出到 [operating_roster_equipment_configs.json](D:/123/combat_numerical_paradigms/roster_research/results/operating_roster_equipment_configs.json)。主C模板使用原生高阶/条件技能，保底模板使用原生常态技能并保持可重复发动，填充模板携带T1技能及较高个体属性权重。低阶段技能参数按全局阶位配方投影；不把该投影当作所有实际角色的最终配表。

研究结算采用01数学文档规定的受击者先机闪避与有效坚韧流失减伤；原始Python对应两处存在不同取值，因此另设保持原始行为的对照模式。原文件未修改。600场对照与原生37,500场回归保存于 [final_model_checks.json](D:/123/combat_numerical_paradigms/roster_research/results/final_model_checks.json)、[native_37500_regression.txt](D:/123/combat_numerical_paradigms/roster_research/results/native_37500_regression.txt)。研究统计到120回合仍存活记为删失，单列报告；不把战力比较强行记为真实胜利。

胜率均为胜场/全部场次；终局战力默认全样本，败局计0；胜局战力单独换算展示。增加发动率0.1是+10个百分点；倍率增量0.3是×1.3；四维均分装备“8点”指每维2点。CSV中stage为0～5，报告与完整阵容JSON为S1～S6。

模型预算合计四维保留10位、战力6位，防止守恒重分配的浮点余差改变同速抛硬币。持续伤害保留原始施放者归属。技能激活即耗次数，未命中也耗次数；条件门槛不被概率/次数装备绕过。

## 概率与装备投放公式

令 $a_j(t)$ 表示条件和次数均可用，$p_j(t)$ 为当回合发动率，则 $q_j(t)=a_jp_j\prod_{k<j}(1-a_kp_k)$，普攻概率为 $\prod_j(1-a_jp_j)$。

技能强化的收益取决于拥有者实际成功释放概率、命中及剩余次数，并通过完整战斗复测得到；不能按人数平均折损。后排成员即使从未发动技能，其装备四维和战力仍完整计入全队。例：4个可用且各30%发动率的技能，总覆盖率为75.99%，各顺位实际释放概率为30%、21%、14.7%、10.29%。

每个成员只占一件装备槽。这里的一件顶级装备可同时保留普通装备基础属性并附带一个测试机制；不会叠加第二件普通装备。4件顶级属性基础与其余N−4件普通属性均计入总预算。开局盾和免死属于不等待自身技能的通道；护盾按全队战力比例计价，其数值规模与个人四维增幅不可直接用同一百分比比较。

## 六阶段的直接投放参考

常规预算取起效参考与饱和参考的几何中点；没有检出起效参考时取饱和值1/4。这是本轮选择的可复测工作点，不是优化证明或价格体系。敌人随后针对该工作点重新校准。优先使用下表和分阶段详表，饱和值用于控制膨胀边界。

| 阶段 | 单件常规四维总点数范围 | D3胜率 | D4胜率 | D4回合 | 四顶级后D4 | 四顶级提升 | PCA90%/簇数 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S1/5人 | 5.75～11.50 | 71.4% | 50.2% | 13.6 | 97.2% | +45.7个百分点 | 26/2 |
| S2/10人 | 6.71～18.98 | 70.6% | 50.0% | 13.7 | 95.0% | +45.7个百分点 | 30/7 |
| S3/15人 | 5.47～13.67 | 73.3% | 52.5% | 11.4 | 91.5% | +38.7个百分点 | 34/2 |
| S4/20人 | 8.22～15.00 | 69.0% | 49.2% | 9.9 | 90.9% | +41.9个百分点 | 34/8 |
| S5/25人 | 5.96～21.07 | 69.8% | 51.4% | 11.1 | 90.4% | +39.9个百分点 | 37/7 |
| S6/30人 | 7.76～20.03 | 67.8% | 50.2% | 12.3 | 88.5% | +37.9个百分点 | 36/7 |

四件最强组合在本轮D4上总体超过原80%～85%参考，说明这些数值是强机制边界测试。进一步实测同一四件组合的机制强度0/25/50/75/100%五档，在每流派800组配对训练后选择最接近82.5%的档位，再独立1200组配对验证。次数/净化数量按整数结算，降低强度不等于线性降低收益。单件普通属性上限同样是饱和参考，不建议直接将全队每件装备配置到上限。

| 阶段 | 较低顶级强度后D4 WR | 较普通基准增益 | 独立复测范围 |
| --- | --- | --- | --- |
| S1 | 84.9% | +34.6个百分点 | 81.4%～88.5% |
| S2 | 80.9% | +31.4个百分点 | 76.2%～89.5% |
| S3 | 84.1% | +31.3个百分点 | 80.8%～89.8% |
| S4 | 82.0% | +33.7个百分点 | 79.8%～84.3% |
| S5 | 83.6% | +33.7个百分点 | 80.2%～85.0% |
| S6 | 82.2% | +30.8个百分点 | 77.5%～86.2% |

该较低强度档位是原80%～85%目标的接近参考；表中所有偏离均保留，阶段平均不代表每流派同时达标。两套具体装备配置均可直接复现。

D1/D2保留作为较轻投放参考；当前搜索主要围绕胜率和回合校准，并未同时拟合全部终局血量目标。每流派的实际回合与胜局血量在阶段表展开，不能以平均胜率代替这些指标。

## 敌人宏观投放公式

$BP_e=\alpha BP_s$；敌人攻击基底为 $(\beta/\alpha)(0.09BP_e+0.045BP_e(t))$；额外吸收后伤害乘 $(1-\gamma)$；回合末存活恢复 $\delta BP_e$；有效先机基底 $\max(0,I_s+\theta)$；技能发动率截断为 $\min(1,\mu p)$，非恢复技能倍率乘 $\mu$。

β/α分离了加血与提高打击力；不分离会把血量提升同时误算成攻击提升。γ为额外宏观吸收层，区别于坚韧原生减伤。原始高维扫描覆盖用户给出的六维范围；装备工作点校准将β扩展到[0.05,4]，其余轴保留原范围。双方均有完整阶段人数，敌方技能谱由opponent代号指定。

全流派共用连续解析形式：$f_g(x,y)=\sum_{s,d}h_s(x)h_d(y)p_{g,s,d}$，$h_k(z)=\max(0,1-|z-k|)$，$x=N/5-1$，$y=D-1$。在实测节点上精确等于投放表，各流派不同的参数节点保存在 [continuous_equipped_delivery.json](D:/123/combat_numerical_paradigms/roster_research/results/continuous_equipped_delivery.json)。

这种连续标尺保留技能谱的离散选择；节点之间的插值是调参工具，只有六个实际编制阶段被独立测试。早期二次拟合在continuous_delivery_by_flow.json，供比较，不代替最终装备工作点标尺。攻防等高线是固定其余四轴与技能谱的条件截面，全六维原始扫描仍保留。

## 短板挖掘与独特角色阶梯

每阶段4,800场，共28,800场D3/D4完整遥测、294,212回合、504,000条玩家成员归属记录。聚类从物理时序特征生成，胜负、阶段、流派、敌人参数和终局标签不作为输入；胜率仅在簇生成后关联展示。逐阶段标准化/PCA/K-Means按训练70%、留出30%运行，K由留出轮廓系数在2～8中选择。PCA以90%累积解释率作为降维规模参考。

这些是整场战斗的事后统计维度。包含血线全过程，因此与胜负相关性不能作为开战预测准确率或因果证明。轮廓系数约0.11～0.23，表示簇间存在连续重叠，不宜把簇名称变成硬性玩法标签。每阶段质心、主要偏离特征、样本量、独立补强效果均在阶段详表。

独特角色测试先在全队四维总预算不变下调整1号位占比，再加一个拥有者机制。预算占比扫描0.5/N、1/N、2/N、4/N，上限80%；其他成员按比例扣回。owner_stats机制额外增加拥有者四维，增量成本另计；盾/免死不依赖该角色释放，技能强化依赖释放。测试用一件顶级装备表达该机制，若转为角色固有机制需要重新核对成本。

同一共享四维预算下，单纯重新分配到个体不应改变无装备战斗能力。它主要改变个人比例属性装备的收益；不存在凭“单体占比大”自动放大全队技能的通道。当前选出的许多0.5/N为扫描下边界，只能称最小已测成本，不构成证明真实最优占比。

## 五维装备需求与四条交互路径

| 需求 | 实测证据与应用 |
| --- | --- |
| 变强 | stat_partial_derivatives.csv：每件/全队点数胜率偏导；operating_mechanic_responses.csv：工作点技能倍率、破防、概率响应。 |
| 兜底 | death_lock、normal_damage、skill_crit：免死、普攻补偿、暴击必中通道；同时记录负战力差平方downside，避免仅看均值。 |
| 质变 | 溢出暴击转纯真伤、过量恢复转盾：five_dimension_mechanism_evidence.csv给出最大响应相邻区间；不是数学上已证明的相变临界点。 |
| 特化 | 各流派/敌技能谱的最大收益、最差收益及独立反制路径；优势/劣势保留实测区间。 |
| 泛用性 | 四维跨属性扫描和异质单体植入；同时复测输出及治疗/控制/流失等通道，收益不能由名称推断。 |

全机制宽范围初扫在饱和普通属性背景下进行，适合识别数值边界；最终装备选择依据较低常规预算的1620格机制复测及逐顺位分配搜索。拥有者装备15种，每种5个强度、3种分配优先级；4件组合用顺序贪心搜索，其独立胜率为可复测结果，不宣称穷举全局最优。

三个战局参考分别校准到约65%、28%、50%后复测，可能出现离散跳变和留出偏差。优势目标≥92%且敌翻盘率<5%、反制目标45%～55%、胶着≥8回合且提升≥30个百分点仅用于最后对照；并未成为聚类类别。反制超过55%表示当前配置更强，不能冒充均势。敌人亦给4件顶级装备复测，敌翻盘率直接以1−玩家胜率记录。异质路径只替换一个成员，总个人四维点数和个人战力守恒，提供新通道变化及输出比例，输出保留与新抗性须分别检查。

| 阶段 | 路径 | 基准胜率 | 装备后 | 增益 | 基准回合 | 原参考同时满足 |
| --- | --- | --- | --- | --- | --- | --- |
| S1 | 扩大克制 | 65.5% | 96.7% | +31.2个百分点 | 6.5 | 3/6 |
| S1 | 绝地反制 | 29.7% | 84.5% | +54.8个百分点 | 6.0 | 0/6 |
| S1 | 僵局破局 | 49.2% | 99.3% | +50.1个百分点 | 24.1 | 6/6 |
| S2 | 扩大克制 | 64.4% | 94.8% | +30.4个百分点 | 7.2 | 4/6 |
| S2 | 绝地反制 | 27.8% | 76.3% | +48.5个百分点 | 6.4 | 0/6 |
| S2 | 僵局破局 | 51.2% | 95.6% | +44.4个百分点 | 15.7 | 6/6 |
| S3 | 扩大克制 | 65.9% | 93.9% | +28.0个百分点 | 7.7 | 1/6 |
| S3 | 绝地反制 | 26.8% | 70.2% | +43.4个百分点 | 6.5 | 1/6 |
| S3 | 僵局破局 | 49.1% | 91.7% | +42.6个百分点 | 12.0 | 6/6 |
| S4 | 扩大克制 | 62.2% | 94.1% | +31.8个百分点 | 7.4 | 3/6 |
| S4 | 绝地反制 | 27.1% | 72.9% | +45.8个百分点 | 6.1 | 0/6 |
| S4 | 僵局破局 | 41.7% | 79.8% | +38.1个百分点 | 23.5 | 4/6 |
| S5 | 扩大克制 | 65.5% | 89.3% | +23.8个百分点 | 6.9 | 2/6 |
| S5 | 绝地反制 | 30.2% | 63.7% | +33.5个百分点 | 5.6 | 1/6 |
| S5 | 僵局破局 | 49.7% | 81.6% | +31.9个百分点 | 16.6 | 1/6 |
| S6 | 扩大克制 | 63.6% | 88.3% | +24.7个百分点 | 7.5 | 0/6 |
| S6 | 绝地反制 | 29.9% | 61.2% | +31.3个百分点 | 6.2 | 2/6 |
| S6 | 僵局破局 | 49.4% | 82.0% | +32.6个百分点 | 8.6 | 3/6 |

## 分阶段配表与证据入口

- S1（5人）：[S1_5_MEMBERS.md](D:/123/combat_numerical_paradigms/roster_research/stage_guides/S1_5_MEMBERS.md)

- S2（10人）：[S2_10_MEMBERS.md](D:/123/combat_numerical_paradigms/roster_research/stage_guides/S2_10_MEMBERS.md)

- S3（15人）：[S3_15_MEMBERS.md](D:/123/combat_numerical_paradigms/roster_research/stage_guides/S3_15_MEMBERS.md)

- S4（20人）：[S4_20_MEMBERS.md](D:/123/combat_numerical_paradigms/roster_research/stage_guides/S4_20_MEMBERS.md)

- S5（25人）：[S5_25_MEMBERS.md](D:/123/combat_numerical_paradigms/roster_research/stage_guides/S5_25_MEMBERS.md)

- S6（30人）：[S6_30_MEMBERS.md](D:/123/combat_numerical_paradigms/roster_research/stage_guides/S6_30_MEMBERS.md)

## 重现与数据索引

运行方式见 [README.md](D:/123/combat_numerical_paradigms/roster_research/README.md)；完整流程支持多进程、本地导出和已完成阶段复用。结果核验见 [final_model_checks.json](D:/123/combat_numerical_paradigms/roster_research/results/final_model_checks.json)。

| 证据 | 文件 |
| --- | --- |
| 六维全域扫描 | [enemy_global_scan.csv](D:/123/combat_numerical_paradigms/roster_research/results/enemy_global_scan.csv) |
| 最终敌方配表 | [equipped_difficulty_candidates.csv](D:/123/combat_numerical_paradigms/roster_research/results/equipped_difficulty_candidates.csv) |
| 完整概率/次数遥测 | [owner_probability_decay.csv](D:/123/combat_numerical_paradigms/roster_research/results/owner_probability_decay.csv) |
| 每回合技能衰减 | [skill_decay_by_round.csv](D:/123/combat_numerical_paradigms/roster_research/results/skill_decay_by_round.csv) |
| 相关性矩阵 | [feature_correlations.csv](D:/123/combat_numerical_paradigms/roster_research/results/feature_correlations.csv) |
| 全局PCA | [pca_variance.csv](D:/123/combat_numerical_paradigms/roster_research/results/pca_variance.csv) |
| 属性偏导 | [stat_partial_derivatives.csv](D:/123/combat_numerical_paradigms/roster_research/results/stat_partial_derivatives.csv) |
| 常规属性范围 | [common_stat_recommendations.csv](D:/123/combat_numerical_paradigms/roster_research/results/common_stat_recommendations.csv) |
| 机制上下沿 | [mechanic_recommendations.csv](D:/123/combat_numerical_paradigms/roster_research/results/mechanic_recommendations.csv) |
| 常规预算机制复测 | [operating_mechanic_responses.csv](D:/123/combat_numerical_paradigms/roster_research/results/operating_mechanic_responses.csv) |
| 顶级强度五档曲线 | [four_item_strength_curves.csv](D:/123/combat_numerical_paradigms/roster_research/results/four_item_strength_curves.csv) |
| 较低顶级预算复测 | [regular_four_item_holdout.csv](D:/123/combat_numerical_paradigms/roster_research/results/regular_four_item_holdout.csv) |
| 跨流派泛用性矩阵 | [versatility_all_flow_matrix.csv](D:/123/combat_numerical_paradigms/roster_research/results/versatility_all_flow_matrix.csv) |
| 战略目标对照 | [strategic_path_reference_checks.csv](D:/123/combat_numerical_paradigms/roster_research/results/strategic_path_reference_checks.csv) |
| 敌四件装备反制 | [enemy_counter_equipment_by_stage.csv](D:/123/combat_numerical_paradigms/roster_research/results/enemy_counter_equipment_by_stage.csv) |
| 异质通道独立复测 | [heterogeneous_channel_holdout.csv](D:/123/combat_numerical_paradigms/roster_research/results/heterogeneous_channel_holdout.csv) |

报告中的上下限是有限网格的经验参考，不是价格、稀有度、掉率或跨所有敌人配置的全局上限。技能保底、概率衰减与普通属性完整计入后，输出一组具体装备/角色建议应始终带上阶段、阵容顺位、敌技能谱和宏观参数。