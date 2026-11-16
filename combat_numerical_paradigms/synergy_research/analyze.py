"""Evidence tables, temporal discovery and practical six-stage specification."""
import argparse
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

import numpy as np
import pandas as pd

from settings import HERE,ROOT,IDENTITIES,CN,DEFAULTS

FORMULAS={
 'academy':'学生经验倍率=1+0.12×老师人数×g；老师基础直伤倍率=1+0.0015×学生等级总和×g',
 'military':'占比r<0.5无效；否则强制命中率=min(1,0.75×[0.25+0.75×(2r−1)]×g)',
 'mage':'连续同原生类型使该类型百分比附加效果累计+4%×q×g；类型切换使队伍直伤累计+4%×q×g',
 'cult':'拜火教成员直伤倍率=1+0.035×比自身阶级低的上阵教徒数×g',
 'fighter':'全队输出倍率=1+0.025×q×g×(当前回合−1)',
 'hunter':'减伤前直伤的0.35×q×g转入未来3回合真伤，从下一回合初分期结算',
 'heroine':'侠女直伤倍率=1+0.035×q×g×已首次发动技能的不同侠女人数；本次结算后新增接力层',
 'maid':'首位女仆无条件、100%、无限次发动；候选A基础直伤倍率=1+1.8×q×g，候选B附带8%×q×g恢复，候选C附带8%×q×g护盾',
 'lady':'强化前ceil(淑女人数/3)个位置，基础直伤增加25%×q×g',
 'scholar':'每次学者攻击后以min(1,30%×q×g)概率恢复随机可用队友1次技能机会',
 'sage':'己方施加负面幅度×(1+25%×q×g)，收到负面幅度×(1−25%×q×g)，持续时间不变',
 'engineer':'装备静态四维额外贡献25%×q×g；每次工程师技能使该比例再加3.5%×q×g，下回合生效',
 'sword':'第一次追加概率50%×q×g，每次递归×0.5，最多3次追加、整链最多4次技能；完整效果且消耗次数',
 'ninja':'初始绝对闪避12%×q×g；每次忍者技能再加2.5%×q×g，下回合生效；实验上限65%',
 'adventurer':'本场目标候选：命中、暴击、有效技能治疗、施加流失、施加削弱；每完成一种，冒险者基础直伤+6%×q×g',
 'sailor':'每一种不同上阵身份，为每维增加[上阵角色平均裸装四维总预算×0.006×q×g]',
 'gang':'帮派顺位的攻击替换成普通攻击，倍率=1+65%×q×g；不执行原技能与附加效果，不消耗其技能次数',
 'merchant':'开局一次：最低维增加最高维×30%×q×g；并列最低按勇气/坚韧/先机/魔力顺序选一维',
 'farmer':'全队共享果实；初次农民攻击种植，5回合成熟；未熟攻击加速1回合，已熟攻击收获；候选价值=最大BP×12%×q×g×(1+0.15×成熟后等待回合)',
 'thief':'每次盗贼攻击转移敌方当时有效四维的1.5%×q×g，逐维扣除并等量加入己方，仅本场',
 'rich':'每次富翁攻击产生1G×g，本场每G额外全域减伤2.5%×g，实验上限60%；G是待兑换的研究金币单位',
 'worker':'装备免死结算后若仍受致命伤，每场全队一次保留1BP并恢复最大BP的20%×q×g',
 'killer':'杀手技能命中施加恢复压制60%×q×g；仅被敌方下一次实际发动的技能消耗，包括该技能没有恢复或未命中时',
}
PARAMS={
 'academy':('teacher_damage','teacher_xp'),'military':('military_hit',),'mage':('mage_pct','mage_damage'),
 'cult':('cult',),'fighter':('fighter',),'hunter':('hunter','hunter_turns'),'heroine':('heroine',),
 'maid':('maid_power',),'lady':('lady','lady_slots'),'scholar':('scholar',),'sage':('sage_out','sage_in'),
 'engineer':('engineer_base','engineer_cast'),'sword':('sword','sword_decay'),
 'ninja':('ninja_base','ninja_cast','ninja_cap'),'adventurer':('adventurer',),'sailor':('sailor',),
 'gang':('gang',),'merchant':('merchant',),'farmer':('farmer_value','farmer_wait'),
 'thief':('thief',),'rich':('rich_dr','rich_cap'),'worker':('worker',),'killer':('killer',),
}
SKILL_GUIDANCE={
 'academy':'学生维持原技能供给；老师优先无苛刻条件的直伤技能。经验收益单独计账，不转成当场免费等级。',
 'military':'保留六类队伍配置；重点供应非暴击仍有价值的技能。强制命中不能被误做发动率。',
 'mage':'同类型连续与两类型切换均可编排；使用原生勇气/坚韧/先机/魔力类型，不把六种队伍组合代号附会为单技能类型。',
 'cult':'保证低阶教徒供给与高阶技能核心；不要把低角色等级误当低稀有度。',
 'fighter':'提供重复使用、能进入中后期的技能，同时保留短局不占优的代价。',
 'hunter':'优先比较高倍率直伤与带恢复技能，不额外给勇气属性添加穿透规则。',
 'heroine':'增加早期可达的有限次技能，降低前排永久截断；每位首次释放的价值高于同一人反复出手。',
 'maid':'原随机技能被女仆长专用候选覆盖；不能通过原技能的回合/血线/概率/次数限制破坏确定性节点。',
 'lady':'前位主C承担技能装备价值；后位淑女可承担静态属性装备，不要求淑女实际出手才提供位置强化。',
 'scholar':'先保证前面队友能消耗次数，再让学者出手；纯学者且无人消耗次数时，恢复系数再高也可能无效。',
 'sage':'提高已有削弱/虚弱/流失技能的出现倾向；被动抵抗不依赖贤者出手。',
 'engineer':'提高无门槛、可重复发动技能的供给倾向；仍保持原阶位倍率—概率交换，不额外赠送更高倍率。',
 'sword':'提供次数充足且有不同剑士可接力的技能；额外释放检查次数与条件，使用羁绊递归概率，不再叠一次普通发动率。',
 'ninja':'提高早期、可重复发动技能的供给倾向；增长在整个当前回合结束后生效。',
 'adventurer':'提供互补目标手段，目标清单是候选，不把未发生的效果计为完成。',
 'sailor':'不锁技能类型，主要价值来自不同身份的混编；职业字段不重新引入。',
 'gang':'原技能不执行；用独立的帮派攻击判定记录。原回血技能与原附加效果均不能漏出。',
 'merchant':'开局被动不依赖技能发动；无需为身份强制分配高发动技能。',
 'farmer':'增加可重复、早期可用的攻击，兼顾催熟与收获；队伍仅一个果实，不能按人数自动结算多颗。',
 'thief':'重复出手机会影响累计偷取；属性转移逐次守恒，不修改永久角色数据。',
 'rich':'重复出手机会同时影响金币与减伤；结算收益必须报告战斗时长、失败收益和重复挑战暴露面。',
 'worker':'一次性全队保命不依赖社畜主动出手，后排静态装备仍有价值。',
 'killer':'提供能在敌方关键恢复技能之前命中的技能；效果限定下一次技能，不扩成持续禁疗。',
}


def mdtable(frame,cols=None):
    if cols:frame=frame[cols]
    rows=['| '+' | '.join(map(str,frame.columns))+' |','| '+' | '.join(['---']*len(frame.columns))+' |']
    for row in frame.itertuples(index=False,name=None):
        rows.append('| '+' | '.join('—' if isinstance(v,(float,np.floating)) and not np.isfinite(v) else f'{v:.3f}' if isinstance(v,float) else str(v) for v in row)+' |')
    return '\n'.join(rows)


def load(output,only_phase=None):
    manifest=json.loads((output/'input_manifest.json').read_text(encoding='utf-8'))
    db=sqlite3.connect(output/'checkpoints.sqlite')
    phases=defaultdict(list)
    query='SELECT key,phase,job,result FROM cells WHERE signature=?';params=[manifest['signature']]
    if only_phase is not None:query+=' AND phase=?';params.append(only_phase)
    for key,phase,job,result in db.execute(query,params):
        merged=dict(key=key,**json.loads(job),**json.loads(result))
        phases[phase].append({sys.intern(k):v for k,v in merged.items()})
    db.close()
    return phases,manifest


def aggregate(rows,keys):
    frame=pd.DataFrame(rows)
    if frame.empty:return frame
    records=[]
    for group,sub in frame.groupby(keys,dropna=False):
        if not isinstance(group,tuple):group=(group,)
        count=int(sub.trials.sum())
        # These are stratified paired trial results, not independent generated
        # skills; uncertainty below concerns the sampled battle mixture only.
        delta=float(np.average(sub.delta_wr,weights=sub.trials))
        # Reconstruct second moment from paired Bernoulli discordance counts.
        second=(sub.reversals.sum()+sub.regressions.sum())/count
        se=np.sqrt(max(0,second-delta*delta)/max(1,count-1))
        record=dict(zip(keys,group));record.update(n=count,delta=delta,ci_low=delta-1.96*se,ci_high=delta+1.96*se)
        numeric=['base_win','new_win','new_turns','base_turns','new_hp','new_censored','composition_delta','total_delta',
                 'fit_with_bond_delta','fit_without_bond_delta','fit_interaction','interaction_delta',
                 'new_m_sword_extras','new_m_scholar_restored','new_m_engineer_casts','new_m_ninja_casts',
                 'new_m_fruit_harvest','new_m_coins','new_coins','new_m_worker_procs','new_m_rich_saved','new_m_hunter_true',
                 'new_m_force_hit','new_m_absolute_dodges','new_m_killer_marks','new_m_killer_healing_prevented',
                 'new_m_mage_same','new_m_mage_switch','new_normal_rate','new_teacher_xp_multiplier']
        for name in numeric:
            if name in sub:record[name]=float(np.average(sub[name].fillna(0),weights=sub.trials))
        records.append(record)
    return pd.DataFrame(records)


def save_csv(output,name,frame):
    frame.to_csv(output/name,index=False,encoding='utf-8-sig')


def discovery(output,rows):
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    extracted=[]
    for index,job in enumerate(rows):
        path=output/'telemetry'/(job['key']+'.json.gz')
        if not path.exists():continue
        with gzip.open(path,'rt',encoding='utf-8') as f:traces=json.load(f)
        for trace in traces:
            turns=trace['rounds']
            if not turns:continue
            feature={}
            for side in ('p','e'):
                bp=np.array([turns[0][side+'_bp_start']]+[r[side+'_bp_end'] for r in turns])
                vel=np.diff(bp);acc=np.diff(np.r_[0.,vel])
                for name,values in (('bp',bp),('velocity',vel),('acceleration',acc)):
                    for i,x in enumerate(np.interp(np.linspace(0,1,8),np.linspace(0,1,len(values)),values)):
                        feature[sys.intern(f'{side}_{name}_{i}')]=float(x)
                for key in ('physical','physical_crit','pure_true','pure_true_crit','self_heal','lifesteal','max_dot','lost_dot',
                            'fixed_dot','current_pressure','backlash','execute','overflow_true',
                            'hunter_true','fruit_damage','fruit_heal','death_lock','shield_saved','rich_saved','thief_stolen'):
                    feature[sys.intern(f'{side}_{key}_flux')]=sum(r[side+'_metrics'].get(key,0) for r in turns)/(5*(job['stage']+1))/len(turns)
                for key in ('skill_casts','normal_casts','misses','sword_extras','scholar_restored','engineer_casts','ninja_casts'):
                    feature[sys.intern(f'{side}_{key}_rate')]=sum(r[side+'_metrics'].get(key,0) for r in turns)/len(turns)
                left=[r[side+'_finite_left'] for r in turns]
                feature[sys.intern(side+'_finite_start')]=left[0];feature[sys.intern(side+'_finite_end')]=left[-1]
            identity=tuple(sorted((m['person_id'],m['skill']['id']) for m in trace['members']))
            group=int(hashlib.sha256(repr(identity).encode()).hexdigest()[:8],16)%10
            extracted.append(dict(stage=job['stage']+1,split=0 if group<6 else 1 if group<8 else 2,
                                  win=trace['result']['win'],**feature))
        if (index+1)%1000==0:print(f'Temporal extraction: {index+1}/{len(rows)} cells',flush=True)
    frame=pd.DataFrame(extracted)
    del extracted
    frame.to_csv(output/'trajectory_features.csv.gz',index=False,compression='gzip')
    save_csv(output,'feature_outcome_correlation.csv',frame.drop(columns=['stage','split']).corr().reset_index(names='feature'))
    summaries=[];centroids=[];loadings=[];variance=[]
    for stage,sub in frame.groupby('stage'):
        columns=[c for c in sub if c not in ('stage','split','win') and sub.loc[sub.split==0,c].std()>1e-12]
        scaler=StandardScaler().fit(sub.loc[sub.split==0,columns])
        values=scaler.transform(sub[columns]);train=values[sub.split==0];val=values[sub.split==1];test=values[sub.split==2]
        pca=PCA(n_components=.9,svd_solver='full').fit(train)
        z=pca.transform(values);zt=z[sub.split==0];zv=z[sub.split==1];ze=z[sub.split==2]
        best=None
        for k in range(2,7):
            model=KMeans(n_clusters=k,random_state=13,n_init=5).fit(zt)
            labels=model.predict(zv)
            score=silhouette_score(zv,labels,sample_size=min(1000,len(zv)),random_state=13) if len(set(labels))>1 else -1
            if best is None or score>best[0]:best=(score,model)
        score,model=best;labels=model.predict(z);test_labels=model.predict(ze)
        test_score=silhouette_score(ze,test_labels,sample_size=min(1000,len(ze)),random_state=13) if len(set(test_labels))>1 else -1
        summaries.append(dict(stage=int(stage),battles=len(sub),features=len(columns),pca_k90=pca.n_components_,
                              clusters=model.n_clusters,validation_silhouette=score,test_silhouette=test_score,
                              train=int(sum(sub.split==0)),validation=int(sum(sub.split==1)),test=int(sum(sub.split==2))))
        for k,v in enumerate(pca.explained_variance_ratio_):variance.append(dict(stage=stage,component=k+1,variance=v))
        for k,vector in enumerate(pca.components_):
            for name,v in zip(columns,vector):loadings.append(dict(stage=stage,component=k+1,feature=name,loading=v))
        for k in range(model.n_clusters):
            cluster=sub.iloc[np.flatnonzero(labels==k)]
            for name in columns:centroids.append(dict(stage=stage,cluster=k,feature=name,mean=cluster[name].mean(),n=len(cluster)))
    for name,records in (('pca_summary.csv',summaries),('pca_variance.csv',variance),('pca_loadings.csv',loadings),('cluster_centroids.csv',centroids)):
        save_csv(output,name,pd.DataFrame(records))
    return summaries


def plot(output,phases):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif']=['Microsoft YaHei','SimHei','DejaVu Sans']
    plt.rcParams['axes.unicode_minus']=False
    confirm=aggregate(phases['confirmation'],['stage','bond'])
    table=confirm.pivot(index='bond',columns='stage',values='delta').reindex(IDENTITIES)
    fig,ax=plt.subplots(figsize=(10,12));im=ax.imshow(table.values*100,cmap='RdBu',vmin=-25,vmax=25,aspect='auto')
    ax.set_xticks(range(6),['5人','10人','15人','20人','25人','30人'])
    ax.set_yticks(range(len(table)),[CN[k] for k in table.index])
    for y in range(len(table)):
        for x in range(6):
            value=table.iloc[y,x]
            if np.isfinite(value):ax.text(x,y,f'{value*100:+.1f}',ha='center',va='center',fontsize=8)
    ax.set_title('独立确认：同阵容启用羁绊的胜率变化（百分点）\n未定技能使用已注明的实验候选效果')
    fig.colorbar(im,ax=ax,label='胜率变化／百分点');fig.tight_layout();fig.savefig(output/'stage_effect_heatmap.png',dpi=150);plt.close(fig)
    screen=pd.DataFrame(phases['screen']);screen['gain']=screen.config.map(lambda x:x.get('gain',1.))
    fig,axes=plt.subplots(2,3,figsize=(15,9),sharey=True)
    for s,ax in enumerate(axes.flat):
        for key in ('sword','ninja','gang','scholar','engineer','rich'):
            sub=screen[(screen.stage==s)&(screen.bond==key)&(screen.gain==1.)].groupby('count').delta_wr.mean()
            ax.plot(sub.index,sub.values*100,'o-',label=CN[key])
        ax.axhline(0,color='gray',lw=.7);ax.set_title(f'{5*(s+1)}人阶段');ax.set_xlabel('上阵身份人数');ax.set_ylabel('同阵容胜率变化／百分点')
    axes[0,0].legend(fontsize=8);fig.tight_layout();fig.savefig(output/'count_response.png',dpi=150);plt.close(fig)
    robust=pd.DataFrame(phases['robustness']);fitted=robust[robust.get('skill_fit',False)==True]
    fits=aggregate(fitted.to_dict('records'),['bond']).sort_values('fit_with_bond_delta')
    fig,ax=plt.subplots(figsize=(11,9));ax.barh([CN[k] for k in fits.bond],fits.fit_with_bond_delta*100)
    ax.axvline(0,color='gray');ax.set_xlabel('保持四维预算：技能供给偏好带来的胜率变化／百分点')
    ax.set_title('身份技能投放候选：现有生成技能中提高适配技能的出现倾向')
    fig.tight_layout();fig.savefig(output/'skill_supply_response.png',dpi=150);plt.close(fig)


def report(output,phases,manifest,pca):
    summary={phase:dict(cells=len(rows),battle_executions=sum(r['executed_battles'] for r in rows),
                        telemetry_battles=sum(r.get('trace_battles',0) for r in rows)) for phase,rows in phases.items()}
    selected=json.loads((output/'selected_coefficients.json').read_text(encoding='utf-8'))
    chosen={(r['stage'],r['bond']):r for r in selected if r['soft_delta_reference']==.1}
    confirm=aggregate(phases['confirmation'],['stage','bond']);save_csv(output,'confirmation_by_stage_identity.csv',confirm)
    save_csv(output,'confirmation_by_flow.csv',aggregate(phases['confirmation'],['stage','bond','genre']))
    save_csv(output,'confirmation_by_order.csv',aggregate(phases['confirmation'],['stage','bond','placement']))
    save_csv(output,'confirmation_by_count.csv',aggregate(phases['confirmation'],['stage','bond','count']))
    save_csv(output,'confirmation_by_difficulty.csv',aggregate(phases['confirmation'],['stage','bond','difficulty']))
    save_csv(output,'pair_interactions.csv',aggregate(phases['pairs'],['stage','bond']))
    robust=[r for r in phases['robustness'] if r.get('skill_fit')]
    fitted=aggregate(robust,['stage','bond']);save_csv(output,'skill_supply_by_stage.csv',fitted)
    fitted_all=aggregate(robust,['bond']);save_csv(output,'skill_supply_all.csv',fitted_all)
    stage_dir=HERE/'stage_guides';stage_dir.mkdir(exist_ok=True)
    records=[]
    for s in range(6):
        text=[f'# S{s+1}／{5*(s+1)}人身份羁绊规范候选','',
              '> 2026-10-20顺位复核更新：最新六阶段实测见[最优顺位设计指南](../OPTIMAL_ORDER_DESIGN_GUIDE.md)。本表保留预设顺位的历史数据与候选系数，请结合新测结果及其适用范围读取。','',
              '状态：研究实现与独立抽样确认，尚未接入Unity。q(n)=n/(n+4)，g为强度系数；所有百分比以小数存储。',
              '系数仅从验证集选择；独立确认使用另一技能库与新阵容种子。10个百分点为软校准参照，5/20个百分点方案另存，不是验收限制。','']
        for key in IDENTITIES:
            entry=chosen.get((s,key))
            if entry is None:
                text.extend([f'## {CN[key]}','', '当前阶段参考稀有度上限内没有角色可组，不强造该阶段投放。','']);continue
            cfg={**DEFAULTS,**entry['config']};g=cfg.get('gain',1.)
            measured=confirm[(confirm.stage==s)&(confirm.bond==key)].iloc[0]
            row=dict(stage=s+1,members_cap=5*(s+1),bond=key,identity=CN[key],config=entry['config'],
                     tested_count=entry['count'],formula=FORMULAS[key],**{k:float(measured[k]) for k in ('delta','ci_low','ci_high','base_win','new_win','new_turns','new_censored','total_delta','composition_delta')})
            records.append(row)
            text.extend([f'## {CN[key]}','',FORMULAS[key]+'。','',
                         f"阶段覆盖人数参照：{entry['count']}人；g={g:g}；覆盖参数：`{json.dumps(entry['config'],ensure_ascii=False)}`。未列字段使用主规范候选表。",
                         f"独立确认同阵容胜率变化 {measured.delta*100:+.2f} 个百分点（配对抽样95%区间 {measured.ci_low*100:+.2f}～{measured.ci_high*100:+.2f}）；换人总变化 {measured.total_delta*100:+.2f} 个百分点。",
                         f"启用前/后胜率 {measured.base_win:.1%}/{measured.new_win:.1%}，平均 {measured.new_turns:.2f} 回合，截尾 {measured.new_censored:.2%}。",'',SKILL_GUIDANCE[key],''])
        (stage_dir/f'S{s+1}_{5*(s+1)}_MEMBERS.md').write_text('\n'.join(text),encoding='utf-8')
    (output/'recommended_design.json').write_text(json.dumps(dict(defaults=DEFAULTS,count_curve='n/(n+4)',stage_candidates=records,execution_summary=summary),ensure_ascii=False,indent=2),encoding='utf-8')
    matrix=confirm.pivot(index='bond',columns='stage',values='delta').reindex(IDENTITIES)*100
    matrix.index=[CN[k] for k in matrix.index];matrix.columns=['5人','10人','15人','20人','25人','30人'];matrix=matrix.reset_index(names='羁绊')
    input_table=pd.DataFrame([dict(羁绊=CN[k],基础候选=FORMULAS[k]) for k in IDENTITIES])
    fit_table=fitted_all[['bond','fit_with_bond_delta','fit_without_bond_delta','fit_interaction']].copy()
    fit_table['bond']=fit_table.bond.map(CN)
    for c in fit_table.columns[1:]:fit_table[c]*=100
    fit_table.columns=['身份','有羁绊时技能供给收益pp','无羁绊时技能供给收益pp','额外交互pp']
    pair=aggregate(phases['pairs'],['bond']).sort_values('interaction_delta',ascending=False)
    pair['组合']=pair.bond.map(lambda x:'＋'.join(CN[k] for k in x.split('+')))
    pair['交互pp']=pair.interaction_delta*100
    positive=pair[['组合','交互pp']].head(8);negative=pair[['组合','交互pp']].tail(8)
    text=[
        '# 六阶段身份羁绊数值设计规范（研究候选，2026-10-15）','',
        '> 2026-10-20顺位复核更新：23项已按现有人物供给补齐六阶段复核，见[最优顺位设计指南](OPTIMAL_ORDER_DESIGN_GUIDE.md)。本报告保留预设顺位的历史数据与候选系数，读取时请结合新测结果及适用范围。','',
        '**直接使用方式**：机制以用户确认的23项设计为准；数值从本报告和六阶段表读取。Unity生产代码、生成器和人物标注未被本研究修改。',
        '女仆长技能、农民收获、冒险目标以及淑女的具体强化尚有设计空间；本轮比较的是明确记录的候选，不将候选冒充用户已定效果。','',
        '## 研究执行与证据','',
        mdtable(pd.DataFrame([dict(阶段=k,参数单元=v['cells'],对战执行=v['battle_executions'],遥测对战=v['telemetry_battles']) for k,v in summary.items()])),
        '',f"合计 {sum(v['battle_executions'] for v in summary.values()):,} 次对战执行；同一参数单元的基线、机制、换人参照、交互消融分别计次。仅计算当前输入签名已落盘的完成单元，不计失败、中断、早期源版本和统计派生。",'',
        '双方均有阶段对应数量的成员。真实标签限定身份、阶级和唯一人物数量；每个角色技能来自冻结的真实生成器导出，1～30级四维逐人计算，每人一件装备、最多四件顶级装备。',
        '人物标签没有生产技能绑定，因此身份—技能关联是研究随机赋值；不能把本次阵容称为已经上线的角色技能表。人物数量不是抽取概率，未模拟真实收集经济。','',
        '主检验：同一批人物、等级、四维、装备和顺位，仅启用或关闭羁绊；另设不限制身份的换人参照，分别报告机制收益、换人代价和总收益。NPC宏观参数来自既有难度标尺，但成员改按真实人物阶级抽样，旧胜率不直接继承；本轮重新记录基线。敌人不随羁绊追平。',
        '训练扫描、验证校准、独立技能库确认分开；新增随机事件按战斗/回合/成员/通道寻址，以减少配对比较中的随机漂移。细胞内样本较少，主结论读取跨流派、难度与顺位聚合。',
        '配对95%区间描述当前等权样本混合的抽样不确定性；多个场景可能共享技能或阵容，不代表真实玩家总体置信区间。','',
        '## 结算规范','',
        '1. 正常行动仍从前到后检查技能，首个成功后停止；剑士额外完整技能为明确例外。有限次技能发动即消耗，包括随后未命中。',
        '2. 女仆长取首位女仆；100%发动、无限次、无回合/血线限制、不可封印。研究核心尚无其他身份施加封印的机制，未声称完成封印系统测试。',
        '3. 剑士对另一名仍满足条件且有次数的剑士追加完整技能，使用羁绊追加概率、不重复普通发动率；概率逐次衰减，最多3次追加/总4次。这个计数是对用户原句的实现候选解释。',
        '4. 军人强制命中 > 绝对闪避 > 普通暴击必中 > 普通闪避；绝对闪避仅阻挡攻击，既有持续效果继续。此优先级是供接入的结算规范候选。',
        '5. 工程师、忍者的成长暂存，到双方整个回合结束才提交；当回合后手与剑士递归均不能提前享受该增长。',
        '6. 猎手从直伤减伤前值拆分，扣掉即时部分，下一回合开始分期；后续不再次暴击、乘先手或重复魔力放大。额外全域吸收/护盾仍属于独立结算层。',
        '7. 学者智能候选仅包含已经消耗有限次数的其他队友，排除无限次女仆长；不设用户未要求的整场恢复额度或单技能恢复次数限制。',
        '8. 帮派原技能不执行、不消耗次数，变为普通攻击。研究候选保留生成技能的发动率作为该顺位攻击的概率，解除原回合/血线门槛；这一未定判定细节需在正式接入时固定。',
        '9. 行商开局对原始最低维增加一次；并列选择顺序固定。盗贼从敌方当前有效四维逐维扣除、等量加入己方，仅存本场，不做永久窃取。',
        '10. 农民只有一颗共享果实；种植5回合后成熟，其他未熟攻击加速。研究候选每次加速1回合，收获后下一次攻击可重新种植；收获价值与等待线性增长。',
        '11. 富翁金币仅累计本场产生的研究单位G；战后可记录该数量，但未接入钱包，未给出真实金币价格或经济平衡保证。',
        '12. 社畜全队每场一次救援；研究候选优先保留原装备免死，再检查社畜。杀手标记仅由下一次技能消耗，没有恢复或未命中也消耗，不持续到下次治疗。',
        '13. 攻击事件与命中事件分开：研究候选中学者、农民、盗贼、富翁按实际攻击尝试触发，杀手按技能命中触发；剑士追加也产生完整攻击事件。','',
        '研究范围解释：拜火教本轮强化高阶教徒本人的技能；贤者本轮覆盖原生虚弱、四维削弱与流失的幅度；冒险者本轮使用全队共享的5项目标候选。这些是用于可复现测试的具体范围，不冒充用户已经补充过的限定。','',
        '## 数值投放候选','',
        'q(n)=n/(n+4)，n是对应身份上阵人数；该人数曲线是设计候选，不是从数据证明的唯一公式。除军人50%门槛外，不擅自增加3/6/9解锁限制。',
        '下面为基础参数，阶段表给出实测校准后的覆盖值或g。g只乘公式明确标注的项，概率夹在0～1；上限、持续回合与覆盖位置不自动乘g。','',
        mdtable(input_table),'',
        '## 六阶段独立确认：机制胜率变化（百分点）','',mdtable(matrix),'',
        '每格混合当前阶段两种覆盖人数、前/后顺位、难/非常难和六类队伍。换人代价、逐流派范围和配对区间见CSV与stage_guides，不能把单格均值解释为所有阵容收益。',
        '校准以10个百分点为软参照选择可玩起点，允许机制差异；另有5/20个百分点系数表。没有强制统一胜率、回合数或终局血量。','',
        '## 身份技能投放','',
        '初步诊断在全队同阶位、同原生属性类型的既有生成技能中，提高各自适配候选的出现倾向，保留个人四维与装备。这个试验可能同时优化其他身份，因此不能把全部收益归因于目标身份；后面的单身份供给补充试验用于隔离。取排序前四分之一的多个样本，不克隆一个最佳技能。',
        '这是一组可复用的生成偏好，不代表已经推导出独立的新技能倍率/概率预算。若以后改动数值区间，必须保留原生成器的倍率—概率—条件—次数交换关系重新测试。','',
        mdtable(fit_table),'',
        *[f"- **{CN[key]}**：{SKILL_GUIDANCE[key]}" for key in IDENTITIES],'',
        '## 双羁绊交互','',
        '交互量=同时启用−只启用A−只启用B+全部关闭，使用完全相同的混合阵容。每个组合均覆盖可用的六阶段和六流派；每格样本少，表用于发现复测重点。',
        '较正的组合：','',mdtable(positive),'','较负的组合：','',mdtable(negative),'',
        '全部23项还做随机真实身份混编、双方同时启用对照；这不等同已经搜索全部最优阵容，不能以单身份平衡替代混合队复测。','',
        '## 全量时序分析','',mdtable(pd.DataFrame(pca)),'',
        '输入仅为双边血线、速率、加速度、伤害/恢复通量、技能次数与出手率等物理特征；不放入身份、胜负、难度等标签。胜负仅进入单独相关性表。',
        '按阵容稳定标识分训练/验证/测试，标准化与PCA仅拟合训练集，K-Means簇数由验证轮廓系数选择。簇质心按物理特征输出，不预设猝死、刮痧等胜负类别。',
        '轮廓系数较低时只作为探索性物理分组，不据此宣称已经发现清晰、稳定的败因类别；本轮数值建议主要来自配对干预与消融。',
        '时序插值与完整战后轨迹用于设计诊断，不当作战前预测器。','',
        '## 使用边界与待完成设计','',
        '女仆长三种候选、农民三种收获候选、猎手2/3/4回合与剑士不同衰减分别有实验结果；效果尚未定稿时，候选之间不能互相套用结论。',
        '学生经验为倍率解析与实际学生等级下的战斗测试；尚无等级经验成本和奖励经济，不能声称培养耗时已经平衡。',
        '富翁经济单位与真实基础奖励的兑换、失败结算、逃跑结算及可重复刷取仍需经济数据；本轮只报告实际攻击数和产币量。',
        '正常敌人不包含所有羁绊，军人对忍者、杀手对恢复女仆、猎手对富翁、贤者对贤者另有针对性实验。',
        '六阶段缺失身份按真实卡池报告，例如S1没有贤者；不造出不存在的低阶角色，不因而强制修改人物标签。',
        '原37500局回归日志、零羁绊精确一致性、机制行为校验与输入哈希均保存。后续正式Unity集成需要对照此结算层再做逐事件一致性检查。','',
        '![六阶段变化](results/stage_effect_heatmap.png)','',
        '![人数响应](results/count_response.png)','',
        '![技能供给响应](results/skill_supply_response.png)','',
        '复现入口：run_all.ps1；断点数据库：results/checkpoints.sqlite；机器可读规范：results/recommended_design.json。',
    ]
    (HERE/'DESIGN_SPECIFICATION.md').write_text('\n'.join(text),encoding='utf-8')
    (output/'execution_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=HERE/'results');p.add_argument('--skip-discovery',action='store_true');args=p.parse_args()
    phases,manifest=load(args.output)
    required={'screen','holdout','pairs','robustness','variants','calibration','confirmation'}
    if not required.issubset(phases):raise RuntimeError('Incomplete phases: '+str(required-set(phases)))
    pca=discovery(args.output,phases['holdout']) if not args.skip_discovery else pd.read_csv(args.output/'pca_summary.csv').to_dict('records')
    report(args.output,phases,manifest,pca);plot(args.output,phases)
    print('Design specification, six stage guides, tables and plots written',flush=True)


if __name__=='__main__':main()
