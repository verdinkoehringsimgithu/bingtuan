"""Produce six stage specifications from the preserved experimental evidence."""
from run_natural import *

NAMES={'skill_damage':'持有者技能直伤增强','skill_pierce':'持有者技能破防','skill_crit':'技能暴击与溢出纯真伤','skill_heal':'持有者技能恢复增强','skill_dot':'已有流失技能增强','skill_chance':'持有者技能概率补偿','extra_use':'有限技能次数增加','cast_ramp':'持有者重复发动递增','chance_ramp':'判定失败后概率递增','overheal_shield':'持有者过量治疗转盾','opening_shield':'开局全队护盾','death_lock':'单次免死恢复','owner_stats':'持有者个人四维放大','normal_damage':'持有者普攻补偿','cleanse':'持有者命中后清除减益','skill_hit':'持有者技能命中保底','added_dot':'持有者技能命中后附加最大流失'}


def read(name):return pd.read_csv(OUT/name)


def table(frame,columns=None,precision=3):
    frame=frame if columns is None else frame[columns]
    def cell(value):
        if isinstance(value,(float,np.floating)):
            return '—' if pd.isna(value) else f'{value:.{precision}f}'
        return str(value).replace('|','/').replace('\n',' ')
    columns=list(frame.columns);return '| '+' | '.join(columns)+' |\n| '+' | '.join(['---']*len(columns))+' |\n'+'\n'.join('| '+' | '.join(cell(v) for v in row)+' |' for row in frame.itertuples(index=False,name=None))+'\n'


def load_text(loadout):
    return '；'.join(f'{pos+1}号 {NAMES.get(kind,kind)}={value:.4g}' for pos,kind,value in json.loads(loadout))


def accept(row):
    wr,t,h=row.wr,row.turns,row.hp
    if row.difficulty==1:return wr>=.99 and 1<=t<=3 and h>=.85
    if row.difficulty==2:return .9<=wr<=.95 and 4<=t<=6 and .6<=h<=.75
    if row.difficulty==3:return .7<=wr<=.8 and 7<=t<=10 and .3<=h<=.5
    return .45<=wr<=.55 and 12<=t<=18 and .05<=h<=.2


def protocol():
    definitions=[('enemy_global_scan.csv',1),('enemy_joint_refinement.csv',1),('difficulty_holdout.csv',1),('d2_validation_refinement.csv',1),('d2_fresh_catalog_holdout.csv',1),('shared_macro_holdout.csv',1),('role_count_order_scan.csv',1),('role_count_holdout.csv',2),('common_stat_scan.csv',2),('mechanism_response_scan.csv',2),('four_top_search.csv',1),('four_top_holdout.csv',2),('four_top_scarcity.csv',2),('mainc_mechanism_scan.csv',2),('mainc_stat_scan.csv',2),('unique_share_scan.csv',2),('unique_controls_holdout.csv',2),('four_top_strength_holdout.csv',2),('crossflow_versatility.csv',2),('strategic_scenario_scan.csv',2),('strategic_loadout_scan.csv',2),('strategic_paths_holdout.csv',2),('heterogeneous_holdout.csv',2),('equipment_operating_validation.csv',2),('equipment_operating_fresh_holdout.csv',2),('unique_budget_response.csv',2),('unique_budget_fresh_controls.csv',2),('unique_normal_budget_fresh_holdout.csv',2),('counter_dose_validation.csv',2),('counter_balanced_fresh_holdout.csv',2),('embedding_mechanism_fresh_holdout.csv',2),('enemy_fixed_slice_contours.csv',1)]
    rows=[]
    for name,multiplier in definitions:
        frame=read(name);rows.append(dict(file=name,cells=len(frame),executions=int(frame.n.sum()*multiplier)))
    rows.append(dict(file='telemetry_features.csv.gz',cells=36000,executions=36000));frame=pd.DataFrame(rows);csv('execution_protocol.csv',frame);return int(frame.executions.sum())


def dimension_groups():
    rows=[]
    def group(name):
        if '_acceleration_' in name:return '血线加速度'
        if '_velocity_' in name:return '掉血速率'
        if '_bp_' in name:return '血线轨迹'
        if any(x in name for x in ('normal_','cast_','reach_','finite_','no_skill_')):return '技能覆盖与耗尽'
        if any(x in name for x in ('weak','initiative')):return '时空控制'
        if 'pure_true' in name:return '纯真伤通量'
        if 'physical' in name:return '直伤与暴击通量'
        if any(x in name for x in ('heal','lifesteal','death_lock')):return '恢复通量'
        return '流失与附加通量'
    for s in range(6):
        model=joblib.load(OUT/f'stage_S{s+1}_models.joblib');pca=model['pca'];k=model['k'];weights=(pca.components_[:k].T**2*pca.explained_variance_ratio_[:k]).sum(1);total=weights.sum()
        for name,value in pd.Series(weights,index=[group(x) for x in model['features']]).groupby(level=0).sum().sort_values(ascending=False).items():rows.append(dict(stage=s,dimension=name,retained_variance_share=value/total))
    frame=pd.DataFrame(rows);csv('physical_dimension_variance.csv',frame);return frame


def main():
    guides=Path(__file__).parent/'stage_guides';guides.mkdir(exist_ok=True);total=protocol();dimensions=dimension_groups()
    difficulty=read('difficulty_delivery_holdout.csv');difficulty['joint_target_met']=[accept(r) for r in difficulty.itertuples()];csv('difficulty_joint_acceptance.csv',difficulty)
    operating=read('equipment_operating_fresh_holdout.csv');coverage=read('ordinary_coverage_bounds.csv');unique=read('unique_normal_budget_fresh_holdout.csv');budget=read('unique_budget_fresh_controls.csv');roles=read('role_count_holdout.csv');ranges=read('common_stat_ranges.csv');discovery=read('per_stage_discovery.csv');counter=read('counter_balanced_fresh_holdout.csv');embedding=read('embedding_mechanism_fresh_holdout.csv');paths=read('strategic_path_acceptance.csv');exposure=read('equipment_owner_exposure.csv');demands=read('mainc_five_demands.csv')
    summary=difficulty.groupby(['stage','difficulty'])[['wr','turns','hp']].mean().reset_index();csv('difficulty_stage_summary.csv',summary)
    eq=operating.groupby('stage')[['strength','base_wr','wr','delta']].mean().reset_index();csv('equipment_stage_summary.csv',eq)
    tier=pd.DataFrame([dict(tier=f'T{k+1}',lower=lo,upper=hi) for k,(lo,hi) in enumerate(PROFILE['budgets'])])
    report=['# 六阶段战斗数值设计规范：自然技能预算与全员装备（2026-10-13）','本次按5/10/15/20/25/30人重做受自然属性预算影响的三项研究。双方均有对应人数的成员，逐人拥有四维、技能与一件装备，每队最多四件顶级装备；四维由技能生成器真实导出再加装备，未把总数强行设为阶段目标。36,000场全量遥测和以下可复现对战矩阵支持结论。','## 直接可用的设计决定',
    '- 全局技能四维预算采用下表候选；30人新技能库样本全部达到装备后主1000/副500，六流派均值约1107–1350/586–709。不同流派存在超额，预算并非全局最优。',
    '- 普通装备给全队提供静态四维，不依赖持有者发动技能；强化技能的装备按持有者的实际次数、顺位到达和命中统计设计。主C、保底、填充不能共用同一套技能增强预期。',
    '- 四件装备的搜索上限会将D4推到约98%–99%，应使用独立测试后的低强度配置。36个配置中22个落在80%–85%；逐配置胜率与区间均列出。',
    '- 角色预算集中本身在全队四维求和模型中没有收益；持有者个人属性放大才使集中预算产生收益。常规个人预算加单项机制也可提升胜率，避免把高额属性集中写成普遍必要条件。',
    '- D1已有全阶段可用的碾压配置；D2有明确参数，但只有部分逐流派配置同时满足原胜率、回合与血量目标，按实际偏差投放，不将其标为全部验收。',
    table(tier),f'属性分配：主维 {PROFILE["primary"]:.6f}，生成器固定副维 {PROFILE["secondary"]:.6f}，其余两维各 {(1-PROFILE["primary"]-PROFILE["secondary"])/2:.6f}。固定副维C→M、R→C、I→C、M→R，与六流派的配队副维不是同一个概念。偶数舍入及残差归属保留源码顺序。T2–T5预算接近，主要成长来自人数及技能阶位；这是当前联合达标候选的真实结果，不包装成已验证的长期经济梯度。',
    '## 测试与真实游戏的边界','技能取自3072条训练导出、3072条验证导出、3072条新技能库导出，全部使用同一冻结数值源码。成员BP按权威阶段总量均分，未纳入完整等级成长与生产卡池稀有度经济。参考编成是主C2、保底4、小阶段按人数裁剪，剩余填充；角色数量另做开放扫描。增加主C时会连带增加高阶技能供给，角色扫描收益同时包含这种资源变化。',
    '每回合己方只发动一个技能：按顺位先检查次数、回合及血线条件，再独立判定概率，首个成功即停止；遍历未成功才普攻。令实际可发动概率为 p_i(t)，则 P(第i位发动)=p_i(t)∏_{j<i}(1−p_j(t))，P(普攻)=∏_i(1−p_i(t))。有限技能在触发时消耗次数，包括随后未命中的情形。普通属性装备始终计入队伍属性，技能增强只作用于该持有者。',
    '已核对的衰减包括战力下降导致基础打击力降低、有限次数耗尽、条件覆盖变化、后排被前排截断和减益倒计时；原权威模型未给出额外的逐次技能倍率衰减公式，本研究未自行添加。开局护盾属于被动全队收益，位置不会影响生效，因此校准配置将它放到未被技能装备占用的后排位置。',
    '根模拟器未修改。研究管线按数学文档用防守方先机计算闪避、用有效坚韧结算流失；与原脚本这两处实现差异保留为公开适配。原脚本一致性另用600例严格匹配模式验证，37500局回归六流派极差13.4个百分点。固定流失、当前战力恢复、当前压制按源生成器实际效果独立校验。新增命中保底、附加流失等是待设计装备机制的实验通道，不宣称已在Unity实现。',
    '## 任务一：敌人投放','每个阶段和流派的D1–D4敌人、十维参数及实际指标都在阶段规范中。基础宏观函数如下：敌方MaxBP=α×阶段BP；满血基础打击力=0.135×β×阶段BP；敌方四维=敌人成员自然属性和×对应scale；γ是额外全域吸收，δ是每回合最大BP恢复，θ是先机偏移，μ影响技能倍率和发动率。β通过β/α补偿攻击，使生存通量与满血威胁通量独立。',
    '开放搜索包含原区间，并因小阶段D1所需低威胁扩展至α=0.06、β=0.015、μ=0.6。不是给败因硬编码阈值。终局体验目标仅作为拟合损失。γ/δ/θ及四维scale均可参与局部细化；敌方六流派分别参与全局选择。',
    '连续投放函数保存在 results/enemy_delivery_policy.json：在相邻人数节点间对正参数作对数线性插值，对γ/δ/θ作线性插值。六个实测节点是证据，节点间插值与人数范围外外推没有胜率保证。分流派敌人是正式研究输出；共享中位宏观参数另有144场景验证，不能默认对所有流派等效。',table(summary),
    f'按原始联合目标，D1/D2/D3/D4分别通过 {", ".join(str(int(difficulty[difficulty.difficulty==d].joint_target_met.sum()))+"/36" for d in (1,2,3,4))} 个配置。D2最终验证使用新技能库；原验证集反馈被明确视为调参信息。终局血量按全部对局计算，败局为0；不以只统计胜局的血量替代用户目标。',
    '## 任务二：自然短板与角色补强',table(discovery),'每阶段6000场：训练3600、验证1200、测试1200。输入不含胜负、流派、难度、参数、最终结果字段；采用全时序血线/速度/加速度、通量、覆盖、耗尽和未发动步长等派生特征。标准化及PCA仅用训练集，K-Means的2–8簇由验证集轮廓系数选择，测试集只评估。',
    '解释90%方差需要51–59个主成分，不能压缩成几个确定败因。部分阶段测试轮廓系数约0.08，簇的分离程度较弱；质心用真实物理特征及标准化偏移描述，不预设猝死/刮痧标签。相关性不是因果解释，完整轨迹聚类是战后分析，不是战前预测。',
    '下表将保留主成分的方差按原物理特征组归集：贡献=Σ(主成分解释率×该特征载荷²)，再按物理组求和及归一。物理组名只说明测量通道，不是预设败因。',table(dimensions),
    '角色补强采用原阵容、仅重新分配、仅持有者机制、两者合用四个配对对照。重新分配前后每个四维总预算守恒，机制额外增益另计。预算集中与个人属性放大联用时，测试的个人四维份额约5%–50%，放大系数25%–200%；其部分份额显著超过常规T6个人预算，是特殊角色预算设计实验，不能直接套入普通技能档位。',
    table(budget[budget.control=='both'].groupby('stage')[['share','value','base_wr','wr','delta']].mean().reset_index()),
    '另有保留普通生成器个人预算的单机制验证。阶段详细表给出机制量、常规份额、胜率提升与95%区间。总体提升目标与按原基线轨迹分簇的条件提升分开报告，簇编号在干预前固定，未按干预后结果重新分簇。条件比较另提供BH多重比较校正；样本很小的簇不能当成确认处方。',
    table(unique.groupby('stage')[['owner_share','base_wr','wr','delta']].mean().reset_index()),
    '## 任务三：装备数值与持有者','每个阶段同时提供：已测普通属性基准、达标覆盖下界、响应曲线下界/拐点、主C单件边际、四件持有者分配、独立验证、敌方装备应对及跨流派矩阵。所有技能装备数字均是持有者效果，不是全队每次行动都享受。',table(eq),
    '五维需求的对应证据：Scaling→四维有限差分、直伤与破防响应；Floor→免死、命中保底、失败概率递增、普攻补偿及败局负方差；Spike→暴击溢出真伤/过量治疗转盾响应与临界区间；Specialization→对手矩阵最佳/最差收益；Versatility→补破防/流失后的流派胜率极差。响应跃迁来自有限网格，不能宣称已证明数学相变。',
    '普通装备覆盖下界由独立阵容的实际裸装缺口计算：q=max(0,(Main目标−裸装Main)/(0.67N),(Sub目标−裸装Sub)/(0.33N))。表中的最大值覆盖已测样本，不保证未见卡池尾部；推荐响应上界是统计拐点，不是装备硬上限。常规基准仍采用实际完成战斗校准的q，任意降低q都应重新标定敌人。',
    '四大战略路径同时给出触发条件与实际结果：扩大克制按约65%基准场景搜索；绝地反制先测强档，再校准45%–55%档位；僵局以至少8回合场景验证；异质嵌入保持替换角色个人总属性和BP不变，再观察输出与实际新效果发动。胜率目标只用于测试验收，不参与败因聚类标签。',
    table(paths[paths.response=='none'].groupby('path')[['base_wr','wr','delta','eligible_trigger','meets_requested_result']].agg({'base_wr':'mean','wr':'mean','delta':'mean','eligible_trigger':'sum','meets_requested_result':'sum'}).reset_index()),
    table(counter.groupby('stage')[['base_wr','wr','strength']].mean().reset_index()),
    '敌方四件开局护盾会显著压低反制收益，这是实测对抗边界，不能把无敌方装备的胜率当作保证。counter_balanced_fresh_holdout.csv中31/36个新基准仍≤30%，23/36个反制配置进入45%–55%；条件与结果必须同时看。',
    table(embedding.groupby('stage')[['output_ratio','novel_effect_available_rate','novel_effect_activated_rate','pct_dr_change_mean']].mean().reset_index()),
    '异质嵌入的阶段平均输出损耗小于5%，但不是每个候选都通过。新机制在卡面出现与在实战发动分开记账，高阶段后排引入的新技能往往发动很少；敌方输出下降还包含战斗时长与击杀变化，不能全归为新增抗性。',
    '## 证据与复现',f'本次交付协议覆盖 {total:,} 次对战执行（含配对基线，未计未落盘的中断扫描，未重复计派生统计表）；其中36,000场保存逐回合双边状态与630,000条玩家成员记录。协议逐文件执行数量见 results/execution_protocol.csv。独立最终技能库不参与源预算候选的生成，装备/补强机制候选在它之前冻结。',
    '图：results/figures/contours_S*_wr.png、contours_S*_turns.png固定其他八维参数，是实际α/β二维切片，每单元64局；不是把十维散点压成假二维等高线。discovery_S*.png为PCA与相关性图，centroids_S*.png为质心差异，全量数值CSV同时保存。',
    '复现使用 run_all.ps1。源码快照、原始回合/持有者日志、参数网格、随机种子与结果均纳入成果包。模型与成果验证见 results/delivery_validation.json，完整文件SHA256见 DELIVERY_MANIFEST.json。',
    '根生成器在研究期间新增特效映射代码，数值前缀经比对一致；研究导出及附带可执行生成器使用冻结数值快照。根目录GUI及Unity独立生成路径不在本次数值研究中宣称已完成同步。旧归一化研究保留作为历史对照，本轮设计不以旧预设1000/500证明自然达标。',
    '原镜像修正前的 candidate_reachability 与 stat_optimization_training 不用于最终最优性论证。完整三任务实验与设计指导已经提供，未达体验目标、低分离簇及生产集成边界均保留，不给未经证实的统一承诺。']
    navigation='阶段指南：'+ ' / '.join(f'[S{s+1}：{STAGES[s][0]}人](stage_guides/S{s+1}_{STAGES[s][0]}_MEMBERS.md)' for s in range(6))
    report.insert(2,navigation+'。CSV及表格stage从0起，对应S1–S6，人数=5×(stage+1)。')
    report.append('所有未结束对局记为censored，未按剩余BP强定胜负。表中WR是已确认胜利占全部执行的比例；存在截尾时，真实最终WR区间为[WR,WR+censor]。D1–D4最终投放、四件装备最终测试及36000场遥测均无截尾；反制测试少量配置有≤0.167%的截尾，原CSV保留。')
    (Path(__file__).parent/'DESIGN_SPECIFICATION.md').write_text('\n\n'.join(report)+'\n',encoding='utf-8')
    for s in range(6):
        n,bp,main_goal,sub_goal,other,cap=STAGES[s];df=difficulty[difficulty.stage==s];eqs=operating[operating.stage==s].copy();eqs['配置']=eqs.loadout.map(load_text);us=unique[unique.stage==s].copy();us['机制']=us.kind.map(NAMES);cs=coverage[coverage.stage==s];rr=roles[roles.stage==s];centers=read(f'stage_S{s+1}_cluster_centroids.csv')
        sections=[f'# S{s+1}：{n}人阶段投放规范','## 基准',f'全队BP={bp:,}，主/副参照={main_goal}/{sub_goal}，技能阶位上限T{cap}。双方均为{n}个成员。参考编成主C2、保底min(4,N−2)、剩余填充；顶级装备最多4件。角色源属性按当前冻结生成器逐人合计，BP均分。',table(cs,['genre','raw_main_mean','raw_sub_mean','equipped_main_mean','equipped_sub_mean','reached','measured_equipment_points','coverage_integer_points']),
        '上述q是每名成员的普通装备总四维点数，主/副流派维度按67%/33%分配。coverage_integer_points是覆盖已测新卡池缺口的向上取整预算值，不是已独立验证的整数属性组合。实测基准为小数预算，可用于数学投放；整数化装备需要另做取整验证。',
        '## 任务一：D1–D4敌人参数与体验',table(df,['genre','difficulty','opponent',*PARAMS,'wr','wr_lo','wr_hi','turns','hp','joint_target_met'],4),
        'joint_target_met按原联合目标计算，仅用于验收。可先使用已测参数投放，按本阶段实际偏差定义体验档位；不能把仅有胜率达标视为回合/血量也达标。共享宏观方案见shared_macro_holdout.csv，连续公式见enemy_delivery_policy.json。',
        '## 任务二：PCA、质心与补强',table(discovery[discovery.stage==s]),table(dimensions[dimensions.stage==s]),table(centers,['cluster','n','wr','label']),
        '质心列是自然分簇的物理描述，未预设败因。低轮廓系数意味着分离较弱；PCA载荷、方差与完整相关性CSV位于results目录。',
        '### 普通常规个人预算的单机制补强',table(us,['genre','机制','value','owner_share','base_wr','wr','delta','delta_lo','delta_hi'],4),
        '这些是使用同一持有者机制通道得到的可设计原型，测试占用1件顶级装备，不等同于已在游戏中新增独特角色。激活型机制仍保留技能概率、门槛和限次。',
        '### 特殊角色预算集中与持有者属性放大',table(budget[(budget.stage==s)&(budget.control=='both')],['genre','share','value','base_wr','wr','delta','delta_lo','delta_hi'],4),
        'share为角色在四维原团队总预算中各维份额，value为个人属性额外放大比例；合用后的全队额外四维比例=share×value。仅重分配对照增益为0。特殊份额不属于原常规T档个人预算，应作为独特角色方案另记成本。各基线簇的条件干预结果及BH校正见unique_*clusters.csv及unique_cluster_multiple_comparison.csv。',
        '## 任务三：全员装备', '### 普通属性响应上下界',table(ranges[ranges.stage==s],['genre','axis','lower','upper']),
        'lower是当前有限扫描首次置信下界为正的位置，upper是响应拐点；两者是候选数值指导，未施加为属性硬上限，未替代本阶段已测普通装备基准。',
        '### 四件顶级装备独立投放',table(eqs,['genre','strength','配置','base_wr','wr','wr_lo','wr_hi','delta','delta_lo','delta_hi'],4),
        'strength乘以完整搜索上限的各项机制量，实际配置列已给出最终量。位置从1起；被动开局护盾移到未占用的后排位，技能装备保留实际持有者。每人仍只有一件装备，普通属性底座已包含在同一件装备中。',
        '### 主C五维响应与持有者覆盖',table(exposure[exposure.stage==s],['genre','role','casts_per_battle_owner','eligible_checks_per_owner','reach_checks_per_owner','personal_raw_stat_mean']),
        table(demands[demands.stage==s],['genre','kind','positive_lower','max_measured_gain','transition_lower','transition_upper','variance_floor_ratio_min']),
        'Floor方差比小于1意味着测得的负结果方差下降，须结合胜率、次数与实际发动看。Spike临界区间是有限网格的最大斜率区间，未证明真正的数学相变。Scaling单角色属性偏导见mainc_stat_derivatives.csv；全员属性偏导见stat_partial_derivatives.csv。',
        '### 四大战略路径',table(paths[(paths.stage==s)&(paths.response=='none')],['genre','path','base_wr','wr','delta','selection_base_turns','eligible_trigger','meets_requested_result']),
        table(counter[counter.stage==s],['genre','strength','kind','base_wr','wr','delta']),
        table(embedding[embedding.stage==s],['genre','foreign','position','output_ratio','delta','novel_effect_available_rate','novel_effect_activated_rate','pct_dr_change_mean']),
        'embedding position沿用CSV的0起索引，其他装备配置用1起索引。新效果实战发动与可用率分开；高阶段末位技能的覆盖可能很低。完整敌方none/shield/chance/dot四装备应对见strategic_paths_holdout.csv。极端构筑与跨流派胜率上下界见specialization_boundaries.csv、versatility_spread.csv。',
        '## 图与数据',f'![胜率固定切片](../results/figures/contours_S{s+1}_wr.png)',f'![时长固定切片](../results/figures/contours_S{s+1}_turns.png)',f'![PCA与相关性](../results/figures/discovery_S{s+1}.png)',f'![聚类质心](../results/figures/centroids_S{s+1}.png)','所有表均由build_report.py读取实测CSV生成，复现协议和限制见上一级DESIGN_SPECIFICATION.md。']
        player_four=read('player_four_stat_baseline.csv');enemy_four=read('enemy_absolute_delivery.csv')
        sections.insert(3,'标准玩家四维均值（真实调后源生成器训练库128组，装备底座已计入）：\n\n'+table(player_four[player_four.stage==s],['genre',*FIELDS,'raw_total','item_total']))
        sections.insert(8,'敌方绝对投放参考（验证技能库128组均值，无敌方普通装备；先机含θ）：\n\n'+table(enemy_four[enemy_four.stage==s],['genre','difficulty','opponent','max_bp','full_bp_base_hit','regen_per_round',*FIELDS]))
        (guides/f'S{s+1}_{n}_MEMBERS.md').write_text('\n\n'.join(sections)+'\n',encoding='utf-8')
    save_json(OUT/'design_report_manifest.json',dict(protocol_executions=total,stages=6,flows=6,all_three_tasks_reported=True,experience_targets_not_all_met=True,ordinary_budget_decimal=True,report_generated_from_measured_csv=True))
    print('Reports generated; protocol executions:',total)


if __name__=='__main__':main()
