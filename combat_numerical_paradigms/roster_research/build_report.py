"""Generate stage design references from measured tables, never invented values."""
from run_study import *
from equipment_study import MECHANIC_VALUES

LABELS={'skill_damage':'持有者技能直伤倍率增量','skill_pierce':'持有者技能破防基底增量','skill_crit':'持有者技能暴击基底增量及溢出转纯真伤','skill_heal':'持有者恢复/吸血比例增幅','skill_dot':'持有者流失比例增幅','skill_chance':'持有者发动率绝对增量','extra_use':'持有者有限技能增加次数','cast_ramp':'持有者每次发动递增直伤','chance_ramp':'持有者连续失败递增发动率','overheal_shield':'持有者过量恢复转护盾','opening_shield':'开局全队战力护盾比例','death_lock':'致死后锁血比例，每件限一次','owner_stats':'持有者自身四维增幅','normal_damage':'抽到持有者普攻时增伤','cleanse':'持有者技能命中后移除减益数量'}
AXIS={'courage':'勇气','resilience':'坚韧','initiative':'先机','magic':'魔力','theme':'主副属性2:1','balanced':'四维均分','bp':'战力'}
ROLES={'carry':'主C模板','backup':'保底模板','filler':'填充模板'}
def pct(x):return f'{100*x:.1f}%'
def num(x):return '未检出' if pd.isna(x) else f'{x:.3g}'
def table(headers,rows):return '\n'.join(['| '+' | '.join(map(str,headers))+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])+'\n'
def link(path):return f'[{path.name}]({path.resolve().as_posix()})'
def read(q,name):return pd.read_csv(q/name)

def build(q):
    root=q.parent;book=root/'DESIGN_SPECIFICATION.md';out=root/'stage_guides';out.mkdir(exist_ok=True)
    operating=read(q,'common_operating_points.csv');ranges=read(q,'common_stat_recommendations.csv');enemy=read(q,'equipped_difficulty_holdout.csv');four=read(q,'operating_four_item_holdout.csv');loads=read(q,'operating_four_item_loadouts.csv')
    discovery=read(q,'per_stage_discovery_summary.csv');unique=read(q,'unique_stage_cluster_holdout.csv');expanded=read(q,'expanded_role_count_holdout.csv');paths=read(q,'strategic_path_reference_checks.csv');responses=read(q,'operating_mechanic_responses.csv');channels=read(q,'heterogeneous_channel_holdout.csv');regular=read(q,'regular_four_item_holdout.csv');regularloads=read(q,'regular_four_item_loadouts.csv');versatile=read(q,'versatility_flow_ranges.csv')
    guide=['# 六阶段战团数值设计规范：逐角色阵容与装备实测','',
        '本次三项任务均按 S1～S6、六大流派重新测试。每边按对应阶段人数构造完整成员列表；成员具有自身四维、战力、技能条件、发动率、独立次数与一件装备。每回合从队首逐个独立判定，首个成功技能结束技能搜索；全未成功才由随机成员普攻。战斗使用共享全队战力和合计四维，成员贡献通过拥有者记账。',
        '这份规范可以直接用于数值配表的首轮参考；所有推荐旁边提供实测区间、独立复测和适用阵容。顶级装备数量上限为4，与主C模板数量分别扫描。','',
        '## 测试边界与数值单位','',
        '阵容是由原始模拟器四技能组合、当前技能生成器及六阶段预算构造的可复现基准成员库；不是生产角色全集的随机抽卡样本。所有成员、技能、门槛、顺位和装备已导出到 '+link(q/'operating_roster_equipment_configs.json')+'。主C模板使用原生高阶/条件技能，保底模板使用原生常态技能并保持可重复发动，填充模板携带T1技能及较高个体属性权重。低阶段技能参数按全局阶位配方投影；不把该投影当作所有实际角色的最终配表。',
        '研究结算采用01数学文档规定的受击者先机闪避与有效坚韧流失减伤；原始Python对应两处存在不同取值，因此另设保持原始行为的对照模式。原文件未修改。600场对照与原生37,500场回归保存于 '+link(q/'final_model_checks.json')+'、'+link(q/'native_37500_regression.txt')+'。研究统计到120回合仍存活记为删失，单列报告；不把战力比较强行记为真实胜利。',
        '胜率均为胜场/全部场次；终局战力默认全样本，败局计0；胜局战力单独换算展示。增加发动率0.1是+10个百分点；倍率增量0.3是×1.3；四维均分装备“8点”指每维2点。CSV中stage为0～5，报告与完整阵容JSON为S1～S6。',
        '模型预算合计四维保留10位、战力6位，防止守恒重分配的浮点余差改变同速抛硬币。持续伤害保留原始施放者归属。技能激活即耗次数，未命中也耗次数；条件门槛不被概率/次数装备绕过。','',
        '## 概率与装备投放公式','',
        r'令 $a_j(t)$ 表示条件和次数均可用，$p_j(t)$ 为当回合发动率，则 $q_j(t)=a_jp_j\prod_{k<j}(1-a_kp_k)$，普攻概率为 $\prod_j(1-a_jp_j)$。',
        '技能强化的收益取决于拥有者实际成功释放概率、命中及剩余次数，并通过完整战斗复测得到；不能按人数平均折损。后排成员即使从未发动技能，其装备四维和战力仍完整计入全队。例：4个可用且各30%发动率的技能，总覆盖率为75.99%，各顺位实际释放概率为30%、21%、14.7%、10.29%。','',
        '每个成员只占一件装备槽。这里的一件顶级装备可同时保留普通装备基础属性并附带一个测试机制；不会叠加第二件普通装备。4件顶级属性基础与其余N−4件普通属性均计入总预算。开局盾和免死属于不等待自身技能的通道；护盾按全队战力比例计价，其数值规模与个人四维增幅不可直接用同一百分比比较。','',
        '## 六阶段的直接投放参考','',
        '常规预算取起效参考与饱和参考的几何中点；没有检出起效参考时取饱和值1/4。这是本轮选择的可复测工作点，不是优化证明或价格体系。敌人随后针对该工作点重新校准。优先使用下表和分阶段详表，饱和值用于控制膨胀边界。','']
    rows=[]
    for s in range(6):
        op=operating[operating.stage==s];d3=enemy[(enemy.stage==s)&(enemy.difficulty==3)];d4=enemy[(enemy.stage==s)&(enemy.difficulty==4)];f=four[(four.stage==s)&(four.difficulty==4)];disc=discovery[discovery.stage==s].iloc[0]
        rows.append([f'S{s+1}/{STAGES[s][0]}人',f'{op.points.min():.2f}～{op.points.max():.2f}',pct(d3.wr.mean()),pct(d4.wr.mean()),f'{d4.turns.mean():.1f}',pct(f.wr.mean()),f'+{100*f.delta.mean():.1f}个百分点',f'{int(disc.pca_k90)}/{int(disc.clusters)}'])
    guide += [table(['阶段','单件常规四维总点数范围','D3胜率','D4胜率','D4回合','四顶级后D4','四顶级提升','PCA90%/簇数'],rows),
        '四件最强组合在本轮D4上总体超过原80%～85%参考，说明这些数值是强机制边界测试。进一步实测同一四件组合的机制强度0/25/50/75/100%五档，在每流派800组配对训练后选择最接近82.5%的档位，再独立1200组配对验证。次数/净化数量按整数结算，降低强度不等于线性降低收益。单件普通属性上限同样是饱和参考，不建议直接将全队每件装备配置到上限。',
        table(['阶段','较低顶级强度后D4 WR','较普通基准增益','独立复测范围'],[[f'S{s+1}',pct(regular[regular.stage==s].wr.mean()),f'+{100*regular[regular.stage==s].delta.mean():.1f}个百分点',f'{pct(regular[regular.stage==s].wr.min())}～{pct(regular[regular.stage==s].wr.max())}'] for s in range(6)]),
        '该较低强度档位是原80%～85%目标的接近参考；表中所有偏离均保留，阶段平均不代表每流派同时达标。两套具体装备配置均可直接复现。',
        'D1/D2保留作为较轻投放参考；当前搜索主要围绕胜率和回合校准，并未同时拟合全部终局血量目标。每流派的实际回合与胜局血量在阶段表展开，不能以平均胜率代替这些指标。','',
        '## 敌人宏观投放公式','',
        r'$BP_e=\alpha BP_s$；敌人攻击基底为 $(\beta/\alpha)(0.09BP_e+0.045BP_e(t))$；额外吸收后伤害乘 $(1-\gamma)$；回合末存活恢复 $\delta BP_e$；有效先机基底 $\max(0,I_s+\theta)$；技能发动率截断为 $\min(1,\mu p)$，非恢复技能倍率乘 $\mu$。',
        'β/α分离了加血与提高打击力；不分离会把血量提升同时误算成攻击提升。γ为额外宏观吸收层，区别于坚韧原生减伤。原始高维扫描覆盖用户给出的六维范围；装备工作点校准将β扩展到[0.05,4]，其余轴保留原范围。双方均有完整阶段人数，敌方技能谱由opponent代号指定。',
        r'全流派共用连续解析形式：$f_g(x,y)=\sum_{s,d}h_s(x)h_d(y)p_{g,s,d}$，$h_k(z)=\max(0,1-|z-k|)$，$x=N/5-1$，$y=D-1$。在实测节点上精确等于投放表，各流派不同的参数节点保存在 '+link(q/'continuous_equipped_delivery.json')+'。',
        '这种连续标尺保留技能谱的离散选择；节点之间的插值是调参工具，只有六个实际编制阶段被独立测试。早期二次拟合在continuous_delivery_by_flow.json，供比较，不代替最终装备工作点标尺。攻防等高线是固定其余四轴与技能谱的条件截面，全六维原始扫描仍保留。','',
        '## 短板挖掘与独特角色阶梯','',
        '每阶段4,800场，共28,800场D3/D4完整遥测、294,212回合、504,000条玩家成员归属记录。聚类从物理时序特征生成，胜负、阶段、流派、敌人参数和终局标签不作为输入；胜率仅在簇生成后关联展示。逐阶段标准化/PCA/K-Means按训练70%、留出30%运行，K由留出轮廓系数在2～8中选择。PCA以90%累积解释率作为降维规模参考。',
        '这些是整场战斗的事后统计维度。包含血线全过程，因此与胜负相关性不能作为开战预测准确率或因果证明。轮廓系数约0.11～0.23，表示簇间存在连续重叠，不宜把簇名称变成硬性玩法标签。每阶段质心、主要偏离特征、样本量、独立补强效果均在阶段详表。',
        '独特角色测试先在全队四维总预算不变下调整1号位占比，再加一个拥有者机制。预算占比扫描0.5/N、1/N、2/N、4/N，上限80%；其他成员按比例扣回。owner_stats机制额外增加拥有者四维，增量成本另计；盾/免死不依赖该角色释放，技能强化依赖释放。测试用一件顶级装备表达该机制，若转为角色固有机制需要重新核对成本。','',
        '同一共享四维预算下，单纯重新分配到个体不应改变无装备战斗能力。它主要改变个人比例属性装备的收益；不存在凭“单体占比大”自动放大全队技能的通道。当前选出的许多0.5/N为扫描下边界，只能称最小已测成本，不构成证明真实最优占比。','',
        '## 五维装备需求与四条交互路径','',
        table(['需求','实测证据与应用'],[
            ['变强','stat_partial_derivatives.csv：每件/全队点数胜率偏导；operating_mechanic_responses.csv：工作点技能倍率、破防、概率响应。'],
            ['兜底','death_lock、normal_damage、skill_crit：免死、普攻补偿、暴击必中通道；同时记录负战力差平方downside，避免仅看均值。'],
            ['质变','溢出暴击转纯真伤、过量恢复转盾：five_dimension_mechanism_evidence.csv给出最大响应相邻区间；不是数学上已证明的相变临界点。'],
            ['特化','各流派/敌技能谱的最大收益、最差收益及独立反制路径；优势/劣势保留实测区间。'],
            ['泛用性','四维跨属性扫描和异质单体植入；同时复测输出及治疗/控制/流失等通道，收益不能由名称推断。']]),
        '全机制宽范围初扫在饱和普通属性背景下进行，适合识别数值边界；最终装备选择依据较低常规预算的1620格机制复测及逐顺位分配搜索。拥有者装备15种，每种5个强度、3种分配优先级；4件组合用顺序贪心搜索，其独立胜率为可复测结果，不宣称穷举全局最优。',
        '三个战局参考分别校准到约65%、28%、50%后复测，可能出现离散跳变和留出偏差。优势目标≥92%且敌翻盘率<5%、反制目标45%～55%、胶着≥8回合且提升≥30个百分点仅用于最后对照；并未成为聚类类别。反制超过55%表示当前配置更强，不能冒充均势。敌人亦给4件顶级装备复测，敌翻盘率直接以1−玩家胜率记录。异质路径只替换一个成员，总个人四维点数和个人战力守恒，提供新通道变化及输出比例，输出保留与新抗性须分别检查。','']
    summary=[]
    for s in range(6):
        for path in ('advantage','counter','stalemate'):
            sub=paths[(paths.stage==s)&(paths.path==path)]
            summary.append([f'S{s+1}',{'advantage':'扩大克制','counter':'绝地反制','stalemate':'僵局破局'}[path],pct(sub.base_wr.mean()),pct(sub.wr.mean()),f'{100*sub.delta.mean():+.1f}个百分点',f'{sub.base_turns.mean():.1f}',f'{sub.reference_met.sum()}/6'])
    guide += [table(['阶段','路径','基准胜率','装备后','增益','基准回合','原参考同时满足'],summary),
        '## 分阶段配表与证据入口','']
    for s in range(6):
        n,bp,main,sub,other,tier=STAGES[s];sp=out/f'S{s+1}_{n}_MEMBERS.md';guide.append(f'- S{s+1}（{n}人）：'+link(sp))
        doc=[f'# S{s+1}：{n}人阶段数值设计参考','',f'全队未装备战力{bp:,}；主属性{main}、副属性{sub}、另两维各{other}；技能阶位上限T{tier}。双方均为{n}成员。','', '## 一：阵容工作点与敌方投放','',
             '下表模板数量用于复现当前技能供应；角色的实际战略贡献还要结合拥有者释放分布。保底优先顺位是条件技能被早期遮挡时的实测选择，不应直接当作所有角色的通用排序。主C模板数量可高于4；顶级装备仍不超过4。','']
        op=operating[operating.stage==s].sort_values('genre');rows=[]
        for r in op.itertuples():rows.append([r.genre,f'{r.carry}/{r.backup}/{n-r.carry-r.backup}',r.order,AXIS[r.axis],num(r.points),num(r.points*n),f'{num(r.lower)}～{num(r.upper)}'])
        doc.append(table(['流派','主C/保底/填充','顺位策略','常规属性轴','每件点数','全队点数','起效～饱和参考'],rows))
        doc+=['default=主C模板在前；backup_first=保底模板在前。常规属性按每人一件计算，4件顶级装备继承同样基础属性。扩展阵容扫描把主C模板数量开放至全队人数；下表是固定总预算、不同技能数量的独立裸装复测，不能与上表的装备工作点效果直接相加。','']
        rows=[]
        for r in expanded[(expanded.stage==s)&(expanded.difficulty==4)].sort_values('genre').itertuples():rows.append([r.genre,f'{r.carry}/{r.backup}/{r.filler}',pct(r.base_wr),pct(r.wr),f'{100*r.delta:+.1f}',pct(r.normal_rate)])
        doc.append(table(['流派','扩展主C/保底/填充','原基准WR','扩展WR','增益百分点','普攻占比'],rows))
        doc+=['大量高阶模板本身构成技能供给增强；后排高阶模板也可能几乎不施放。具体成员策略身份应以expected_cast/实际casts及耗尽后接替贡献判断，模板数量不是必须购买的主C数量。','']
        rows=[]
        for r in enemy[enemy.stage==s].sort_values(['genre','difficulty']).itertuples():
            wh=r.hp/r.wr if r.wr and r.censor==0 else np.nan
            rows.append([r.genre,f'D{r.difficulty}',r.opponent,*[num(getattr(r,k)) for k in MACRO_NAMES],pct(r.wr),f'{r.turns:.1f}',pct(r.hp),num(wh*100)+'%'])
        doc.append(table(['流派','难度','敌技能谱','α','β','γ','δ','θ','μ','WR','回合','全样本末BP','胜局末BP'],rows))
        doc+=['胜率每格800场独立复测；置信区间/删失见 '+link(q/'equipped_difficulty_holdout.csv')+'。各流派配套困难场景保留离散敌技能谱。','',
              f'![胜率条件等高线]({(q/"figures"/f"conditional_wr_S{s+1}.png").as_posix()})',f'![回合条件等高线]({(q/"figures"/f"conditional_turns_S{s+1}.png").as_posix()})','',
              '## 二：时序短板与独特角色补强','']
        dr=discovery[discovery.stage==s].iloc[0];doc.append(f'本阶段4,800场；PC1解释{pct(dr.pc1_variance)}，{int(dr.pca_k90)}个主成分解释90%，自动选出{int(dr.clusters)}簇，留出轮廓系数{dr.silhouette:.3f}。')
        model=joblib.load(q/f'stage_S{s+1}_models.joblib');k=model['k'];pca=model['pca'];contrib=(pca.components_[:k]**2*pca.explained_variance_ratio_[:k,None]).sum(0);order=np.argsort(contrib)[::-1][:10]
        doc+=['',table(['特征','保留主成分方差贡献'],[[model['features'][i],f'{contrib[i]:.5f}'] for i in order])]
        descriptions=read(q,f'stage_S{s+1}_cluster_descriptions.csv');doc+=['',table(['簇','样本','事后WR','质心最高偏离（标准差）'],[[int(r.cluster),r.n,pct(r.wr),r.label] for r in descriptions.itertuples()])]
        rows=[]
        for r in unique[unique.stage==s].itertuples():rows.append([int(r.cluster),LABELS[r.kind],num(r.value),pct(r.share),r.n,pct(r.base_wr),pct(r.wr),f'{100*r.delta:+.1f}',f'[{100*r.delta_lo:+.1f},{100*r.delta_hi:+.1f}]'])
        doc+=['',table(['目标簇','单体补强通道','强度','四维预算占比','留出场数','原WR','补强WR','增益百分点','95%配对区间'],rows),
              '以上占比是1号位对每一维总预算的占比；不是额外增加这些预算。补强选择只用训练样本，效果仅用未参与选择的簇留出样本；部分簇达不到20～30个百分点或超过该区间，全部实数保留。',
              f'![技能队列衰减]({(q/"figures"/f"skill_queue_decay_S{s+1}.png").as_posix()})',
              '图中每回合仅统计仍在战斗的样本，同时保留at_risk数量；后期曲线含存活者选择效应。有限技能余量、门槛、每位被检索/释放概率和普攻漂移均可在原始遥测复核。','',
              '## 三：全成员装备属性与四顶级配置','']
        rows=[]
        for r in ranges[ranges.stage==s].sort_values(['genre','axis']).itertuples():rows.append([r.genre,AXIS[r.axis],num(r.recommended_lower),num(r.recommended_upper),num(r.whole_team_upper),num(r.scanned_max),f'{100*r.max_measured_gain:+.1f}'])
        doc+=['单件纯属性轴扫描；theme/balanced为总点数，不是每维点数。未检出只表示这轮扫描没有一致的正向起效信号。起效参考根据D3/D4配对区间均值筛选，不能当作合并后严格95%置信界；饱和参考是资源归一化响应拐点，末端仍有收益须查看原曲线。','',table(['流派','单件属性轴','起效参考','饱和参考','全队饱和','单件扫描最大','最大增益百分点'],rows)]
        configs=json.loads((q/'operating_roster_equipment_configs.json').read_text(encoding='utf-8'));bygenre={r['genre']:r for r in configs if r['stage']==s+1};rows=[]
        for r in regularloads[regularloads.stage==s].sort_values('genre').itertuples():
            text=[f'{pos+1}号：{LABELS[kind]}={num(value)}' for pos,kind,value in json.loads(r.loadout)]
            h=regular[(regular.stage==s)&(regular.genre==r.genre)].iloc[0]
            rows.append([r.genre,num(r.strength_scale),'<br>'.join(text),pct(h.base_wr),pct(h.wr),f'{100*h.delta:+.1f}',f'[{100*h.delta_lo:+.1f},{100*h.delta_hi:+.1f}]'])
        doc+=['','优先考虑的较低顶级强度档位：',table(['流派','强度比例','四件属性','D4普通基准','D4四顶级','增益百分点','95%配对区间'],rows),
              '每格1,200组独立配对复测，成员与基础属性详见 '+link(q/'regular_roster_equipment_configs.json')+'。以下另列最强已测组合，供参考机制上沿。','']
        rows=[]
        for r in loads[loads.stage==s].sort_values('genre').itertuples():
            config=bygenre[r.genre];text=[]
            for pos,kind,value in json.loads(r.loadout):text.append(f'{pos+1}号({ROLES[config["members"][pos]["role"]]})：{LABELS[kind]}={num(value)}')
            h=four[(four.stage==s)&(four.genre==r.genre)&(four.difficulty==4)].iloc[0]
            rows.append([r.genre,'<br>'.join(text),pct(h.base_wr),pct(h.wr),f'{100*h.delta:+.1f}',f'[{100*h.delta_lo:+.1f},{100*h.delta_hi:+.1f}]'])
        doc+=['',table(['流派','四件分配（每个顺位一件）','D4普通基准','D4四顶级','增益百分点','95%配对区间'],rows),
             '每格1,200场独立配对复测。属性强化、概率、增加次数等强度应按各通道独立预算管理；上表是扫描选出的强组合，供确定上沿和分配优先级。填充角色优先普通四维/战力，等待技能发动的装备是否值得占用顶级库存，直接看其成功释放概率和下表拥有者分配效应。','']
        rows=[]
        for g,rs in responses[responses.stage==s].groupby('genre'):
            for allocation in ('front','backup','filler'):
                r=rs[rs.allocation==allocation].sort_values('delta',ascending=False).iloc[0];rows.append([g,allocation,LABELS[r.kind],num(r.value),f'{100*r.delta:+.1f}',pct(r.wr)])
        doc.append(table(['流派','四件分配优先级','该优先级最佳已测机制','强度','增益百分点','工作点D4 WR'],rows))
        doc+=['front=按主C→保底→填充优先；backup=保底→主C→填充；filler=填充→保底→主C。候选角色不足4时补至4，不代表总是四个填充角色都持有顶级装。','']
        doc+=['跨流派泛用性复测使用统一敌人宏观参数α=1.3、β=1.1、γ=δ=θ=0、μ=1；对全部6种敌技能谱各240组配对，测试常规四顶级组合相对仅普通属性的收益与胜率极差。该统一探针对局未逐格校准难度，因此保留真实优势/劣势分布。','',table(['流派','普通属性均值','四顶级均值','普通属性最低～最高','四顶级最低～最高','极差变化百分点'],[[r.genre,pct(r.base_mean),pct(r.equipped_mean),f'{pct(r.base_min)}～{pct(r.base_max)}',f'{pct(r.equipped_min)}～{pct(r.equipped_max)}',f'{100*r.range_change:+.1f}'] for r in versatile[versatile.stage==s].itertuples()])]
        hs=channels[channels.stage==s];rows=[]
        for r in hs.itertuples():
            change={c:getattr(r,c) for c in hs if c.startswith('change_')};top=sorted(change,key=lambda x:abs(change[x]),reverse=True)[:3]
            rows.append([r.genre,r.foreign,r.position,pct(r.base_win),pct(r.win),f'{100*r.output_ratio:.1f}%', '; '.join(f'{c.replace("change_","")}={change[c]:+.4f}' for c in top)])
        doc+=['异质单体选择后再次使用320组独立配对战斗记录通道，以下通道变化的正负须结合治疗、敌伤害、控制覆盖分别解释；不能把任意非零变化自动命名为新抗性。','',table(['原流派','嵌入流派','位置','原WR','嵌入WR','输出比例','主要通道变化'],rows)]
        import re
        sp.write_text(re.sub(r'\n{3,}','\n\n','\n\n'.join(doc)).replace('\\\\','\\'),encoding='utf-8')
    guide+=['', '## 重现与数据索引','',
            '运行方式见 '+link(root/'README.md')+'；完整流程支持多进程、本地导出和已完成阶段复用。结果核验见 '+link(q/'final_model_checks.json')+'。',
            table(['证据','文件'],[[x,link(q/y)] for x,y in (
                ('六维全域扫描','enemy_global_scan.csv'),('最终敌方配表','equipped_difficulty_candidates.csv'),('完整概率/次数遥测','owner_probability_decay.csv'),('每回合技能衰减','skill_decay_by_round.csv'),
                ('相关性矩阵','feature_correlations.csv'),('全局PCA','pca_variance.csv'),('属性偏导','stat_partial_derivatives.csv'),('常规属性范围','common_stat_recommendations.csv'),('机制上下沿','mechanic_recommendations.csv'),
                ('常规预算机制复测','operating_mechanic_responses.csv'),('顶级强度五档曲线','four_item_strength_curves.csv'),('较低顶级预算复测','regular_four_item_holdout.csv'),('跨流派泛用性矩阵','versatility_all_flow_matrix.csv'),('战略目标对照','strategic_path_reference_checks.csv'),('敌四件装备反制','enemy_counter_equipment_by_stage.csv'),('异质通道独立复测','heterogeneous_channel_holdout.csv'))]),
            '报告中的上下限是有限网格的经验参考，不是价格、稀有度、掉率或跨所有敌人配置的全局上限。技能保底、概率衰减与普通属性完整计入后，输出一组具体装备/角色建议应始终带上阶段、阵容顺位、敌技能谱和宏观参数。']
    import re
    book.write_text(re.sub(r'\n{3,}','\n\n','\n\n'.join(guide)).replace('\\\\','\\'),encoding='utf-8')
    return book

def main():
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=8);p.add_argument('--output',default=str(Path(__file__).parent/'results'));args=p.parse_args();q=Path(args.output).resolve();book=build(q)
    print(str(book),flush=True)

if __name__=='__main__':main()
