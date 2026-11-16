"""Generate the final design specification from persisted measured results."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import numpy as np
import pandas as pd
from research_core import GENRES,LABELS,STAGES,PARAMS,SOURCE

def table(df):
    # No optional Markdown dependency; escape pipes and preserve useful precision.
    def fmt(v):
        if isinstance(v,(float,np.floating)):return f"{v:.4f}"
        return str(v).replace("|","/").replace("\n"," ")
    return "| "+" | ".join(map(str,df.columns))+" |\n| "+" | ".join(["---"]*len(df.columns))+" |\n"+"\n".join("| "+" | ".join(fmt(v) for v in row)+" |" for row in df.itertuples(index=False,name=None))

def pc(v):return f"{100*v:.2f}%"

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",default=str(Path(__file__).parent/"results"));args=parser.parse_args()
    q=Path(args.output).resolve();base=Path(__file__).parent.resolve()
    read=lambda name:pd.read_csv(q/name)
    load=lambda name:json.loads((q/name).read_text(encoding="utf-8"))
    manifest=load("manifest.json");native=load("native_regression.json");verification=load("verification.json")
    extended=load("extended_manifest.json");targeted=load("unique_targeted_manifest.json")
    study_total=manifest["persisted_simulation_total"]+extended["total"]+targeted["total"]
    total=study_total+native["battles"]
    hold=read("difficulty_holdout.csv");selected=read("selected_parameters.csv")
    smooth=read("continuous_function_holdout.csv");pca=read("pca_variance.csv");cl=read("cluster_descriptions.csv")
    models=read("cluster_model_selection.csv");rank=read("physical_feature_variance_ranking.csv")
    equip=read("equipment_matrix_holdout.csv").set_index("genre").loc[list(GENRES)].reset_index()
    unique=read("unique_targeted_holdout.csv");unique_max=read("unique_cluster_holdout.csv")
    ladder=read("unique_targeted_stage_ladder.csv");strategy=read("strategic_calibrated_holdout.csv")
    response=read("calibrated_enemy_counter_response.csv");heter=read("heterogeneous_joint_validation.csv");floor=read("floor_downside_risk.csv")
    con=load("continuous_deployment_function.json")
    if verification["telemetry_battles"]!=manifest["args"]["telemetry_battles"] or verification["source_sha256"]!=hashlib.sha256(SOURCE.read_bytes()).hexdigest():raise ValueError("Evidence/source mismatch")
    full_pass=hold.groupby(["stage","difficulty"]).point_pass.all().sum()
    intervals=hold.groupby(["stage","difficulty"]).interval_pass.all().sum()
    summary=hold.groupby(["stage","difficulty"]).agg(WR最低=("wr","min"),WR最高=("wr","max"),回合最低=("turns","min"),回合最高=("turns","max"),血量最低=("hp","min"),血量最高=("hp","max"),达标流派数=("point_pass","sum"),最大未终结率=("censor_rate","max")).reset_index()
    summary.columns=["阶段","难度","WR最低","WR最高","回合最低","回合最高","血量最低","血量最高","达标流派数","最大未终结率"]
    params=selected[["stage","difficulty",*PARAMS]].copy();params.columns=["阶段","难度",*PARAMS]
    pca_k=int(np.searchsorted(pca.cumulative,.9)+1)
    cl_display=cl[["cluster","n_train","n_holdout","wr_train","wr_holdout","censor_holdout","top_deviations"]]
    equipment=equip[["genre","slots","base_wr","wr","delta","delta_lo","delta_hi","turns","hp","d4_specialization_target"]].copy()
    equipment.columns=["流派","3槽配置","原胜率","装备胜率","提升","提升CI下界","提升CI上界","回合","终局全样本血量","WR目标点达标"]
    strategy_display=strategy[["genre","path","lever","base_wr","base_turns","base_censor_rate","wr","delta","target_pass"]].sort_values(["path","genre"])
    response_display=response.groupby("genre").agg(最大敌方翻盘率=("enemy_flip_probability","max"),最低玩家胜率=("wr","min"),响应数量=("enemy_response","size")).reset_index()
    floor_summary=[]
    for g in GENRES:
        b=floor[(floor.genre==g)&(floor.mechanism=="baseline")].iloc[0]
        d=floor[(floor.genre==g)&(floor.mechanism=="death_lock")].iloc[0]
        floor_summary.append(dict(流派=g,原胜率=b.wr,锁血胜率=d.wr,负向半方差原值=b.downside_semivariance,负向半方差装备值=d.downside_semivariance,负向风险降幅=1-d.downside_semivariance/b.downside_semivariance))
    best_heter=heter[heter.combined_target_pass].sort_values("output_ratio",ascending=False).groupby("genre").head(1)
    family=[]
    for row in rank.itertuples():
        name=re.sub(r"_[0-9]{2}$","",row.feature)
        name=re.sub(r"^[pe]_","",name)
        family.append(dict(family=name,contribution=row.explained_variance_contribution))
    fam=pd.DataFrame(family).groupby("family").contribution.sum().sort_values(ascending=False).reset_index()
    fam.to_csv(q/"feature_family_variance.csv",index=False)
    def fail_dimensions(r):
        from run_research import TARGETS,interval_distance
        names=("win rate","duration","terminal HP")
        dims=[name for name,v,b in zip(names,(r.wr,r.turns,r.hp),TARGETS[r.difficulty]) if interval_distance(v,b)>0]
        if r.censor_rate: dims.append("unresolved at cap")
        return "; ".join(dims)
    residual=hold.copy();residual["failed_dimensions"]=[fail_dimensions(r) for r in residual.itertuples()]
    residual.to_csv(q/"difficulty_constraint_residuals.csv",index=False)
    deployment_coeff=pd.DataFrame(con["coefficients"],index=PARAMS,columns=con["basis"]).reset_index(names="参数")
    passed_strategy=strategy.groupby("path").target_pass.sum().to_dict()
    report=f"""# 战团战斗系统 V11 数据挖掘与实测设计规范

本研究覆盖六个编制阶段、六个标准流派、六维敌方宏观参数、逐回合遥测、单贡献者装备近似及四条战略路径。可核对的研究对战为 **{study_total:,} 场**，另有原引擎 **{native['battles']:,} 场**固定种子回归，共 **{total:,} 场**。该计数按最终保存的数据表核对，不重复计入中途重跑、遥测重放或一致性检查。

总计包含配对实验中各次实际执行的基线复算；同种子复算不能视为独立新样本。去重后的攻坚时序样本为 {verification['telemetry_battles']:,} 场，各独立验证的有效样本数另列于对应数据表。

**实测结论：共享敌方参数在本次扫描中没有同时满足六流派的全部难度指标；短板数据呈现两个粗粒度轨迹簇及大量连续差异；实验装备可以明显拉升胜率，但三槽装备、合理角色成本及完整 D4 体验尚不能由现有整体战团模型共同认证。**

所有流派统一为 C_I（勇气+先机）、C_R（勇气+坚韧）、M_I（魔力+先机）、M_R（魔力+坚韧）、M_C（魔力+勇气）、R_I（坚韧+先机）。原仿真文件及两份权威规范均保持原样。

## 证据口径与物理边界

原生公式以实际执行的 `test_30man_combat_simulator.py` 为准；两份规范提供阶段战力、四维预算和阶位标准。文件哈希、环境版本与全部运行参数分别保存于 [manifest.json]({q.as_posix()}/manifest.json) 和 [audit.json]({q.as_posix()}/audit.json)。三份来源之间存在差异，涉及差异的结论按引擎当前行为限定，未把文档意图写回引擎。

| 事项 | 实际执行行为 | 研究处理 |
| --- | --- | --- |
| 闪避 | 当前行动函数使用出手方先机计算未暴击攻击的闪避概率 | 完整保留；不能把本次先机灵敏度直接解释为受击方的正确闪避价值 |
| 流失减免 | 使用当前坚韧，未使用受四维削弱影响的有效坚韧 | 完整保留 |
| 魔力示例 | M=280 时放大器为 1.89；数学文档示例写为 2.04 | 按函数计算 |
| 真伤穿透 | 门槛为 0.85，额外魔力增幅系数为 0.20；AGENT.md 另述 1.0 和 0.18 | 按当前引擎执行 |
| 治疗附带直击 | 重置为 100% 普攻基底，覆盖此前的暴击和先手加成 | 完整保留 |
| 回合上限 | 40 回合未终结时比较血量比例，同值偏向输入第一方 | 单独记录未终结率和真正击败敌人的胜率 |
| 早期技能 | 引擎仅有终局完整组合，没有 S1–S5 的完整技能组合 | S1–S5 使用公开的统一阶位投影；结论均以该投影为条件 |
| 单角色 | 引擎没有角色实体、各自行动、个人血量及装备经济成本 | 装备与独特角色结论限定为整体战团上的贡献比例实验 |

零干预遥测与原引擎在 {verification['cases']:,} 个固定种子案例中逐项完全一致，覆盖胜负、回合、血量、动态属性、技能使用和原伤害累计。另有 {verification['intervention_cases']} 个实验机制案例通过互斥伤害归因与血量守恒检查；{verification['exact_seed_replay_cases']} 场导出遥测可按 64 位种子重放。12 组实验的串行与并发结果逐项一致。[验证日志]({q.as_posix()}/verification.json)

原生 37,500 场回归的六流派综合胜率极差为 **{native['spread_percentage_points']:.2f} 个百分点**，通过项目的 ≤15 个百分点要求。原程序的镜像格为固定 50%，不计作真实镜像模拟。[完整原生日志]({q.as_posix()}/native_37500_regression.log)

胜率 `wr` 保留原引擎裁定；`decisive_wr` 仅计玩家存活且敌方死亡。平均终局血量 `hp` 包含败局，`winner_hp` 为胜局条件均值。本次将用户“终局平均血量”解释为全样本均值，并同时导出条件均值。未终结对局只表示观察被回合上限截断，不自动归入任何败因类别。

## 敌方六维投放模型与独立验证

敌方基础流派按六个标准组合等权分层投放，**同一宏观参数向量适用于六个玩家流派**。胜率是对该敌方混合总体的平均值，不能解释为对每个单独敌方流派都达到该胜率。阶段预算取权威表；S6 技能精确复用原配置。

宏观实验定义为：

- 最大战力 `BP_e,max = alpha × BP_stage`。
- 基础打击 `BasePower_e = beta × BP_stage × (0.09 + 0.045 × BP_e,pct)`。在原引擎基底上乘 `beta/alpha`，使血量和攻击通量可独立探索。
- `gamma` 是原生结算后的额外吸收比例，作用于直伤、真伤和流失；它是实验吸收层，不改写坚韧公式。
- `delta` 是存活敌人在完整回合末的原生比例恢复，恢复 `delta × BP_e,max`，不乘魔力。
- 初始先机 `I_e = max(0, I_stage + theta)`；该截断是属性非负约束。
- 技能概率 `p_s = min(1, mu × p_s,base)`，非治疗技能主倍率统一乘 `mu`。技能仍按引擎原顺序竞争，实际触发率还取决于前序技能、条件和次数限制。

范围完整覆盖 alpha∈[0.3,3.5]、beta∈[0.3,2.5]、gamma∈[0,0.8]、delta∈[0,0.5]、theta∈[-200,500]、mu∈[0.8,2]。先以 256 个打乱 Sobol 点和 64 个边界角点及 2 个参考点覆盖六维空间，再为每个阶段和目标局部加密 27 个候选。全域筛选每流派每点 24 场、加密 96 场，最终锁定候选后以每流派 600 场独立样本验证。各阶段 9×9 的 alpha–beta 截面另外实测，其他四维固定于该阶段 D3 候选。

目标函数只使用用户给定的胜率、时长和血量区间作为终局拟合目标，既不创造“猝死”等胜负标签，也不用于聚类输入。它最小化六流派平均与最差的归一化区间残差，并单独惩罚未终结率。24 个“阶段×难度”候选中，六流派同时满足点估计目标的数量为 **{full_pass}/24**；六流派同时通过胜率区间证据的数量为 **{intervals}/24**。单独流派格共有 {int(hold.point_pass.sum())}/144 个点估计达标，其中 {int(hold.interval_pass.sum())}/144 个胜率 95% Wilson 区间完全落入目标区间。回合、血量在此判据中仍是均值点估计。

{table(summary)}

这些结果只能说明**本次覆盖与加密未找到共同可行点**，不能据有限扫描证明整个连续空间无解。S6 的 D3 候选平均回合在不同流派间仍相差数回合；D4 候选直接回到原生参考点，既有时长不足，也有未终结率。因此不得把平均体验合格当作六流派共同合格。

### 可复现实验参数表

以下均为最小化本次样本残差的候选，不是已经达成目标的正式敌人数值。

{table(params)}

[原始全域矩阵]({q.as_posix()}/scan_global.csv)、[加密矩阵]({q.as_posix()}/scan_local.csv)、[独立验证]({q.as_posix()}/difficulty_holdout.csv)、[逐格不满足的维度]({q.as_posix()}/difficulty_constraint_residuals.csv)。

### 连续解析拟合函数

令 s=(阶段−1)/5，d=(难度−1)/3，phi=[1,s,d,s²,sd,d²]。对于参数 j，

`p_j(s,d) = L_j + (U_j-L_j) / (1 + exp(- dot(w_j, phi)))`。

{table(deployment_coeff)}

这是一条受边界约束的经验连续函数，系数由 24 个实测候选反推。其独立验证有 {int(smooth.point_pass.sum())}/144 个流派格满足均值目标，不能作为保证 D1–D4 体验的通用投放定律。[函数及系数]({q.as_posix()}/continuous_deployment_function.json)、[函数独立验证]({q.as_posix()}/continuous_function_holdout.csv)。

![S6 胜率截面]({q.as_posix()}/figures/contour_S6_wr.png)

六个阶段的胜率和回合等高线均在 [figures]({q.as_posix()}/figures) 中；截面是有抽样噪声的条件图，不是六维空间的全域边界证明。

## 无监督时序挖掘与短板证据

遥测为 **{verification['telemetry_battles']:,} 场、{verification['telemetry_rounds']:,} 个完整回合记录**，按六阶段×六玩家流派×两个攻坚目标分层收集。D3/D4 表示拟合目标对应的候选参数，不能暗示这些对局已经满足全部 D3/D4 指标。每场都有回合初末双边战力、每回合一阶和二阶差分、有效先机、输出削弱、属性削弱、技能未触发步长，以及互斥伤害与恢复通道。

直伤细分为普通物理部分、暴击增量、纯真伤部分及真伤的暴击增量；最大流失、已损流失、反噬、斩杀另记。吸血、自愈与宏观恢复记录实际恢复量，溢出治疗独立记录。破防贡献是同一命中下“有破防/无破防”的诊断差，不与互斥伤害分项求和；过量伤害与实际掉血分开记录。原始回合数据为 72 个 `rounds_*.jsonl.gz` 文件，每行保存一场战斗的种子、输入和完整序列。

全轨迹按归一化进程插值为每信号 12 点，并结合每回合通道通量、命中率、技能间隔均值/最大值/方差、削弱覆盖面积及先机漂移。训练样本 70%、独立验证 30%；标准化和 PCA 仅拟合训练集。胜负、终局汇总、阶段、难度、参数和种子均未进入 PCA/K-Means。

前 3 个主成分合计解释 **{pc(pca.variance.iloc[:3].sum())}** 方差；需要 **{pca_k} 个**主成分解释至少 90%。这支持“差异分布在很多物理通道中”，没有支持把所有短板压缩成极少数普适维度。

{table(pca.head(10))}

按保留主成分的方差贡献排序，前 12 个物理测量特征为：

{table(rank.head(12))}

命中率与未命中率互为补数，时序采样点也高度相关；这些排名依赖特征标准化及表示方式，不能直接当作属性价值或因果重要性。另附 [特征家族贡献]({q.as_posix()}/feature_family_variance.csv)，但家族包含的测量点数同样影响贡献总量。

K-Means 在 K=2…10 的候选中由独立验证轮廓系数选取 K=2，轮廓系数为 **{models.silhouette_holdout.max():.4f}**。GMM 的 BIC 在该搜索范围内仍持续改善到 K=10，说明混合结构尚未收敛，不能宣称物理世界只有两个败因。聚类名只采用质心偏移特征，胜负在分簇之后用于解释。

{table(cl_display)}

F00 的敌方掉血速度相对整体均值更接近零，独立样本胜率约 {pc(cl.loc[cl.cluster==0,'wr_holdout'].iloc[0])}；F01 的敌方掉血更快，独立胜率约 {pc(cl.loc[cl.cluster==1,'wr_holdout'].iloc[0])}。这两个簇是描述性轨迹群体，不是预先命名的失败类别。全轨迹包含终局附近的形态，虽然结果列没有作为输入，轨迹仍带有结果信息；随机干预验证才用于判断机制杠杆是否能改变这些对局。

![PCA 贡献率]({q.as_posix()}/figures/pca_variance.png)

![聚类质心]({q.as_posix()}/figures/cluster_centroids.png)

[完整相关矩阵]({q.as_posix()}/feature_correlations.csv)、[PCA 方差]({q.as_posix()}/pca_variance.csv)、[全部载荷]({q.as_posix()}/pca_loadings.csv)、[物理单位质心]({q.as_posix()}/cluster_centroids.csv)、[标准化质心]({q.as_posix()}/cluster_centroids_standardized.csv)、[模型选择日志]({q.as_posix()}/cluster_model_selection.csv)。

## 独特角色补强的贡献比例实验

现有模型只识别全队四维及整体技能组合，不能从相同全队输入区分“均匀分配”和“一个角色集中持有”。因此，**单角色四维预算的唯一最优占比不可识别**；本研究提供贡献比例条件下的机制前沿，不给出伪精确的角色最优值。

先在训练簇上测试 10 种杠杆及 1/N、2/N、min(0.4,4/N) 三组贡献比例，再为训练中达到 20–30 个百分点的机制扫描贡献倍数 0…2、步长 0.25。该范围是已测候选范围，不是角色强度上限。选择在训练样本中达标的最小已测比例后，保持机制不变，在独立簇样本上验证。

所选 U_FLOOR 是每场一次锁血比例 `0.3q` 加未触发技能的普攻补偿 `3q`，q 为贡献比例，效果作用于整体战团近似。对应终局 q=1/30 时为 1% 战团战力锁血和未触发普攻增加 10%。这不是原引擎机制，也不是单角色实体级免死验证。

{table(unique)}

F00 的实测提升约 {100*unique.delta.iloc[0]:.2f} 个百分点，95% 配对均值区间为 [{100*unique.delta_lo.iloc[0]:.2f}, {100*unique.delta_hi.iloc[0]:.2f}] 个百分点。点估计达到 20–30 的目标；区间下界尚未严格达到 20。最大化胜率的另一个已测方案 U_ATTACK、4 倍贡献比例提升约 {100*unique_max.loc[unique_max.cluster==0,'delta'].iloc[0]:.2f} 个百分点，超过目标区间，也不能把它称为经济成本最优。

F01 的独立原胜率约 {pc(cl.loc[cl.cluster==1,'wr_holdout'].iloc[0])}，其绝对胜率提升空间最多约 {100*(1-cl.loc[cl.cluster==1,'wr_holdout'].iloc[0]):.2f} 个百分点。因此在该总体上要求再提高 20–30 个百分点，在概率边界上已不成立。

### 已测阶段贡献阶梯

{table(ladder)}

阶段小样本行只描述分层效果，不承诺每阶段都提高同样的胜率。数值集中、机制成本与整个角色的行动/受击分布仍不能由此识别。[训练贡献前沿]({q.as_posix()}/unique_share_frontier.csv)、[逐场独立干预]({q.as_posix()}/unique_targeted_holdout_battles.csv.gz)。

## 三槽装备的五维需求实证

所有单贡献者实验默认 q=1/30。攻击强化 x 令全队基础打击系数为 `1+qx`；四维单属性强化 x 为全队四维总预算的 `qx`；穿透强化 x 给技能破防基底增加 `qx`。装备统计均为该定义下的近似，不能视为真实单角色属性变化。候选没有装备经济成本，不能认证“合理特化”。

| 需求 | 测试与证据 | 判读范围 |
| --- | --- | --- |
| 变强 | 攻击、四维及穿透连续梯度扫描，配对种子，导出 ∂WR/∂X | 差分导数是局部样本估计；单贡献者单位与全队单位相差 1/q |
| 兜底 | 锁血、命中补偿、未触发技能普攻补偿；使用终局差值的负向半方差 | 不采用“败局血量方差”作为主指标，死亡血量常恒为零 |
| 质变 | 暴击溢出转纯真伤、过量治疗转护盾；计算触发门槛并扫描 | 门槛计算区分规则激活和胜率相变，未激活机制不能归功于装备 |
| 特化 | 固定全队四维总预算，把 0…100% 预算转向一维并对全部敌方流派测试 | 收益上限与劣势坍塌只对已测构筑有效 |
| 泛用性 | 最优三槽配置对六个原生敌方流派再测，比较跨对局胜率极差 | 在混合敌方上的最高胜率不保证跨对局极差最小 |

兜底指标为 `M = 玩家终局BP比例 − 敌方终局BP比例`，负向半方差 `E[min(M,0)^2]`。同种子对照 1,500 场/流派的锁血结果：

{table(pd.DataFrame(floor_summary))}

过量治疗护盾在无恢复来源的流派上没有生成通道；M_R 的原生治疗条件通常也无法制造过量恢复，在本次该机制测试中没有拉升胜率。M_I 的吸血能形成过量恢复，因此出现收益。[完整兜底数据]({q.as_posix()}/floor_downside_risk.csv)

暴击溢出触发边界按 `c_native + (crit_skill + q×crit_item) × [1+(amp_M−1)×0.45] > 1` 计算，穿透门槛按 `(pierce_skill + q×pierce_item) × amp_M ≥ 0.85` 计算。批量扫描中的大额暴击输入只用于定位边界，其装备成本和可获得性未获来源支持。[激活边界]({q.as_posix()}/spike_activation_thresholds.csv)

### 主贡献者三槽配置矩阵

核心槽 K2：每回合基础打击贡献递增，战团系数 `1+(2/30)(t−1)`；属性槽 A1：全队基础打击系数乘 1.1；策略槽 S1：每场一次锁到 1% 全队最大战力；S3：技能基础暴击率增加 0.1，并把实际溢出部分转为纯真伤。S3 的单独溢出转化是否激活必须读取门槛，增加暴击率的收益不能自动归因于溢出真伤。

64 个三槽组合经训练筛选后，每流派 600 场独立样本结果如下。WR 目标点达标仅指 80%–85% 的特化胜率区间，不包括完整 D4 的时长和血量目标。

{table(equipment)}

装备能明显提高胜率，同时缩短战斗、抬高剩余血量；因此即使特化 WR 达标，也不能认定完整 D4 体验达标。各配置配对提升区间已输出，装备胜率自身的 Wilson 区间见原表。K2 的递增杠杆在本次无经济成本候选中收益显著，正式装备数值不能直接照搬这些强度。

[装备全部候选]({q.as_posix()}/three_slot_search.csv)、[最终矩阵]({q.as_posix()}/equipment_matrix_holdout.csv)、[偏导数曲线]({q.as_posix()}/winrate_partial_derivatives.csv)、[特化边界]({q.as_posix()}/specialization_boundaries.csv)、[跨对局极差]({q.as_posix()}/versatility_ranges.csv)。

![装备响应曲线]({q.as_posix()}/figures/equipment_response_curves.png)

## 四条动态博弈路径

前三条路径先按全域筛选选定敌方血量，再对基础威胁做 11 轮校准，每轮 1,800 场、共享种子降低输入比较噪声。装备在单独训练样本中选定，最终每条件 1,500 场独立验证。扩大克制的起始 65% 和僵局的 50% 用原胜率的 95% 区间包含目标值判定；绝地反制严格检查原胜率点估计 ≤30%。任何基线或最终结果的未终结/双亡均单独阻止路径认定。

{table(strategy_display)}

在上述判据下，扩大克制的单边装备测试达标 {passed_strategy.get('advantage',0)}/6，绝地反制 {passed_strategy.get('counter',0)}/6，僵局破局 {passed_strategy.get('stalemate',0)}/6。表中的失败项保留原始测量，不能因装备后胜率较高而跳过基线条件。

### 敌方应对后的扩大克制

敌方也装配六组策略候选后，观测到的最高翻盘率为：

{table(response_display)}

没有流派在这一敌方可应对集合下把最大翻盘概率压到 <5%。因此，“对固定敌人达到高胜率”不能扩展为已经验证动态博弈中的 <5% 翻盘目标。[应对逐格数据]({q.as_posix()}/calibrated_enemy_counter_response.csv)

### 异质嵌入

按一个角色的比例 1/30 在全队四维预算内混合另一流派，并把技能触发机会按相同比例混合。每组合在等权敌方混合总体中作 720 场同种子对照，直接观测实际恢复通道及对敌虚弱/四维削弱覆盖面积。全队输出口径为实际对敌掉血通量/回合，终局长度对该指标存在影响。

30 个“本流派×异质流派”组合中，{int(heter.combined_target_pass.sum())} 个同时满足输出比 ≥0.95，并观测到原组合没有的恢复或压制通道。各流派符合双重条件的一个代表组合为：

{table(best_heter[['genre','foreign','base_wr','wr','output_ratio','new_healing_observed','new_suppression_observed']])}

M_I 与 R_I 的原生技能已包含本次测量的恢复/压制维度，新增相似通道不算“全新抗性维度”；它们在这组定义下没有双重达标组合。该结果没有证明所有可能异质角色都无法引入新抗性。[观测通道]({q.as_posix()}/heterogeneous_observed_channels.csv)、[双重判据]({q.as_posix()}/heterogeneous_joint_validation.csv)

## 基于实测的设计规范

1. **敌方投放**采用本报告定义的六个独立通量与固定敌方总体，保留每流派独立验收结果。现阶段输出候选及残差，不能标为已经认证的 D1–D4 通用配置。连续函数可生成实验输入，其验收状态由独立对战数据决定。
2. **角色补强**以低敌方掉血通量的 F00 轨迹为本次可验证对象。U_FLOOR 在 q=1/N 的近似下达到约 21.83 个百分点提升，贡献阶梯按阶段表给出；该份额是最小已测点估计达标方案。角色四维预算最优比例仍不可识别，不能把机制曝光份额误当成已证明的个人属性集中度。
3. **装备投放**沿用三槽互斥结构，按矩阵明确机制强度、胜率、时长、血量与跨对局极差。收益来自递增攻击、攻击强化、锁血或暴击强化等具体杠杆；未激活的溢出真伤/护盾不记作有效补强。
4. **规则跃迁**须同时满足机制激活、配对胜率变化与可用构筑成本三项证据。本次只具备前两项可测证据及无成本候选范围，不能认证商业化装备强度。
5. **真实单角色结论**需要角色级输入、个人属性预算、行动与受击模型和装备成本；当前战团总量引擎无法识别这些变量。S1–S5 完整技能组合也需要权威来源定义。现有报告给出可复现实验规范和验证边界，不将投影假设升级为权威规则。

## 复现与数据索引

在项目根目录执行：

```powershell
& ./combat_numerical_paradigms/v11_research/run_all.ps1 -Workers 8
```

仅扫描敌方参数：

```powershell
& ./combat_numerical_paradigms/v11_research/.venv/Scripts/python.exe ./combat_numerical_paradigms/v11_research/scan_difficulties.py --workers 8
```

完整执行脚本、独立扫描脚本、原生回归、补充校准、贡献前沿、遥测验证与报告生成均保存在同一目录。改变抽样参数或真理源后应使用新的 `--output` 目录；并发数不影响种子。原始数据、置信区间、参数、环境和代码哈希随交付保存。

[项目运行说明]({base.as_posix()}/README.md)、[全部证据清单]({q.as_posix()}/evidence_inventory.json)。
"""
    report_path=base/"V11_RESEARCH_REPORT.md"
    if q!=base/"results":report_path=q/"V11_RESEARCH_REPORT.md"
    report_path.write_text(report,encoding="utf-8")
    counts=dict(main=manifest["persisted_simulation_total"],extended=extended["total"],targeted=targeted["total"],native_regression=native["battles"],total=total,definition="Final persisted experiment rows; reruns and verification checks excluded")
    (q/"delivery_counts.json").write_text(json.dumps(counts,indent=2),encoding="utf-8")
    code_inventory={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(base.glob("*")) if p.is_file() and p.suffix in (".py",".ps1",".txt")}
    (q/"research_code_inventory.json").write_text(json.dumps(code_inventory,indent=2),encoding="utf-8")
    inventory={}
    for path in sorted(q.rglob("*")):
        if path.is_file() and path.name!="evidence_inventory.json":inventory[str(path.relative_to(q))]=dict(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (q/"evidence_inventory.json").write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(dict(report=str(report_path),total_persisted_battles=total,shared_difficulty_all_flow_passes=int(full_pass),pca_k=pca_k,cluster_k=len(cl),heterogeneous_joint_passes=int(heter.combined_target_pass.sum())),ensure_ascii=False,indent=2))

if __name__=="__main__":main()
