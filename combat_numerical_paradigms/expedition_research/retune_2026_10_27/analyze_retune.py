"""Audit fresh static and progressive journeys; expose safety/depth tradeoffs."""
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics

import numpy as np
import confirm_policies as study
import progressive_paths as progressive
from audit_research import check_manifest,equivalent
from state_contract import ExpeditionState
from supply_adapter import restore_missing_caps
from run_bonds import atomic_json

OUT=study.fit.OUT/'report'


def mean(rows,key):return sum(r[key] for r in rows)/len(rows)


def table(name,rows):
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def predict(raw,condition,is_progressive=False):
    grid=np.array(study.GRID);prob=[];ex=[];counts=[]
    for x in study.GRID:
        rows=raw['prepared'][str(x)]['trials'];wins=[r for r in rows if r['win']]
        prob.append(len(wins)/len(rows));counts.append(len(wins))
        ex.append([r['damage_exposure'] for r in wins]+[1.]*(96-len(wins)))
    prob=np.array(prob);counts=np.array(counts);ex=np.array(ex)
    n=512;rng=np.random.default_rng(study.old.seed('retune-forecast',raw['job']))
    wear=np.zeros(n);weights=np.ones(n);counter=0;result=[]
    for node in range(1,31):
        hi=np.searchsorted(grid,wear,side='right').clip(1,len(grid)-1);lo=hi-1
        t=((wear-grid[lo])/(grid[hi]-grid[lo])).clip(0,1);p=(1-t)*prob[lo]+t*prob[hi]
        mass=weights.sum()
        result.append(dict(battle=node,conditional_wr=float(np.dot(weights,p)/mass) if mass>1e-100 else None,
            reach=float(mass/n),mean_bp_cap=float(np.dot(weights,np.exp(-wear))/mass) if mass>1e-100 else None,
            out_of_grid_mass=float(weights[wear>grid[-1]].sum()/n)))
        point=np.where(rng.random(n)<np.divide(t*prob[hi],p,out=np.zeros(n),where=p>0),hi,lo)
        pos=(rng.random(n)*np.maximum(1,counts[point])).astype(int).clip(0,95)
        policy=study.ORIGINAL if is_progressive and counter>=6 else condition['policy']
        loss=policy['l0']+policy['l1']*ex[point,pos]
        wear+=np.where(rng.random(n)<policy['p'],-np.log1p(-loss),0.);weights*=p;counter+=1
        if node==condition['at']:
            f=np.exp(-wear);wear=-np.log(f+condition['rest']*(1-f))
            if condition['rest']==1.:counter=0
    return result


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    manifest=check_manifest(study.OUT/'manifest.json');pm=check_manifest(progressive.OUT/'manifest.json')
    data=json.loads((study.OUT/'summary.json').read_text(encoding='utf-8'))
    pd=json.loads((progressive.OUT/'summary.json').read_text(encoding='utf-8'));pc={r['key']:r for r in pd['rows']}
    assert data['signature']==manifest['signature'] and pd['signature']==pm['signature']
    assert len(data['rows'])==len(pd['rows'])==144
    cases=[];curves=[];forecasts=[];returns=[];states=[];archives={};count=0;native=0;replays=0;censored=0
    progressive_count=0;coverage=set()
    for cell in data['rows']:
        path=study.OUT/'replicates'/(cell['key']+'.json.gz')
        with gzip.open(path,'rt',encoding='utf-8') as f:raw=json.load(f)
        archives[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        j=raw['job'];assert equivalent({k:v for k,v in j.items() if k!='key'},cell['job'])
        mm,gears,enemy,ei,sim=study.prepare(j);n=len(mm)
        assert all(equivalent(v,study.old.snapshot(mm,gears[g])) for g,v in raw['members'].items())
        assert equivalent(raw['enemy'],study.old.snapshot(enemy,ei)) and len(enemy)==n==study.old.lab.STAGES[j['stage']][0]
        assert all(sum(it.top for it in items)==4 for items in gears.values())
        coverage.add((j['stage'],j['genre'],j['mix']))
        prep=0
        for x,p in raw['prepared'].items():
            tests=96 if float(x)==0 else 24
            expected=2*((120 if n==5 else 16)*2+12+tests)
            assert p['executed_battles']==expected and len(p['trials'])==tests;prep+=expected
            assert not set(p['seeds']['train'])&set(p['seeds']['test']) and not set(p['seeds']['select'])&set(p['seeds']['test'])
            assert all(q['searched_orders']==(120 if n==5 else 16) for q in p['plans'].values())
        assert prep==cell['result']['preparation_executions']
        baseline=mean(raw['prepared']['0']['trials'],'win')
        assert baseline==cell['result']['baseline_wr']
        base=dict(stage=j['stage']+1,capacity=n,genre=j['genre'],mix=j['mix'],baseline_wr=baseline,
                  dominant=baseline>=.95)
        for x,p in raw['prepared'].items():
            states.append(dict(**base,wear=float(x),bp_cap=math.exp(-float(x)),wr=mean(p['trials'],'win'),
                censored=mean(p['trials'],'censored'),gear=p['chosen']))
        pp=progressive.OUT/'replicates'/(cell['key']+'.json.gz')
        with gzip.open(pp,'rt',encoding='utf-8') as f:pr=json.load(f)
        archives[str(pp)]=hashlib.sha256(pp.read_bytes()).hexdigest()
        assert pr['parent_sha256']==hashlib.sha256(path.read_bytes()).hexdigest() and equivalent(pr['job'],j)
        variants={**raw['variants'],**pr['variants']};conditions=study.conditions(j['new_policy'])
        for name,rest in progressive.CONDITIONS.items():conditions[name]=dict(policy=j['new_policy'],at=6 if rest else 0,rest=rest)
        control6=sum(len(r['rows'])>=6 and r['rows'][5]['result']['win'] for r in variants['control'])/32
        original_count=0;extra_count=0;case_censored={}
        for name,routes in variants.items():
            assert len(routes)==32;condition=conditions[name];is_prog=name.startswith('progressive')
            actual=0;cc=0
            for index,route in enumerate(routes):
                state=ExpeditionState('research-troop');counter=0
                for node,row in enumerate(route['rows'],1):
                    assert node==row['node'] and state.wear[0]==row['wear_before']
                    point=min(study.GRID,key=lambda x:(abs(x-state.wear[0]),x));choice=raw['prepared'][str(point)]
                    assert row['gear']==choice['chosen'] and equivalent(row['order'],choice['order'])
                    bs=study.old.seed('retune-journey',j,index,node);roll=study.old.seed('retune-loss',j,index,node)/(1<<64)
                    assert bs==row['battle_seed'] and roll==row['event_roll']
                    r=row['result']
                    if node==1:assert equivalent(r,variants['control'][index]['rows'][0]['result'])
                    if j['genre']=='C_I' and index==0:
                        m,it=study.old.reordered(mm,gears[row['gear']],row['order'])
                        q,t,*_=sim(m,enemy,bs,it,ei,p=j['macro'],enabled=study.old.MIXES[j['mix']],
                            factors=state.factors,telemetry='trace'in row)
                        assert equivalent(study.project(q),r)
                        if 'trace'in row:assert equivalent(t,row['trace'])
                        replays+=1
                    policy=study.ORIGINAL if is_prog and counter>=6 else condition['policy']
                    if is_prog:assert counter==row['counter_before']
                    loss=policy['l0']+policy['l1']*r['damage_exposure'] if roll<policy['p'] else 0.
                    if r['win']:
                        state.apply_loss(f'battle:{node}',(loss,0.,0.,0.,0.),'victory');counter+=1
                    assert state.wear[0]==row['wear_after_battle']
                    if r['win'] and node==condition['at']:
                        restore_missing_caps(state,f'supply:{node}',(condition['rest'],)*5)
                        if condition['rest']==1.:counter=0
                    assert state.wear[0]==row['wear_after']
                    if is_prog:assert counter==row['counter_after']
                    if not r['win']:assert node==len(route['rows'])
                    actual+=1;cc+=r['censored']
                assert equivalent(state.to_dict(),route['state'])
                if is_prog:assert counter==route['counter']
            if is_prog:extra_count+=actual
            else:original_count+=actual
            censored+=cc;case_censored[name]=cc
            public=(pc[cell['key']]['result'] if is_prog else cell['result'])['variants'][name]
            s6=sum(len(r['rows'])>=6 and r['rows'][5]['result']['win'] for r in routes)/32
            reach30=sum(len(r['rows'])==30 for r in routes)/32
            assert public['survive6']==s6 and public['reach30']==reach30 and public['censored']==cc
            prediction=predict(raw,condition,is_prog)
            half=next((r['battle'] for r in prediction if r['conditional_wr'] is not None and r['conditional_wr']<=.5),31)
            cases.append(dict(**base,variant=name,survive6=s6,control_survive6=control6,
                relative_survive6=s6/control6 if control6 else None,reach20=sum(len(r['rows'])>=20 for r in routes)/32,
                reach30=reach30,forecast_half=half,forecast_wr30=prediction[-1]['conditional_wr'],
                forecast_out_of_grid30=prediction[-1]['out_of_grid_mass'],native_censored=cc))
            forecasts.extend(dict(**base,variant=name,**r) for r in prediction)
            for node in range(1,31):
                rr=[r['rows'][node-1] for r in routes if len(r['rows'])>=node];wins=sum(q['result']['win'] for q in rr)
                curves.append(dict(**base,variant=name,battle=node,entered=len(rr),wins=wins,
                    reach=len(rr)/32,conditional_wr=wins/len(rr) if rr else None,
                    bp_cap_sum=sum(math.exp(-q['wear_before']) for q in rr)))
            if name in ('control','original','revised','progressive'):
                for outward in range(1,16):
                    survive=lambda k:sum(len(r['rows'])>=k and r['rows'][k-1]['result']['win'] for r in routes)/32
                    out=survive(outward);home=survive(outward*2)
                    returns.append(dict(**base,variant=name,outward=outward,return_battles=outward,
                        whole_trip=home,conditional_return=home/out if out else None))
        assert original_count==cell['result']['native_battles'] and prep+original_count==cell['result']['executed_battles']
        assert extra_count==pr['executed_battles']==pc[cell['key']]['result']['executed_battles']
        count+=prep+original_count;progressive_count+=extra_count;native+=original_count+extra_count
    assert len(coverage)==144 and count==data['executed_battles'] and progressive_count==pd['executed_battles']
    for name,rr in {'case_evidence.csv':cases,'native_curves.csv':curves,'response_forecasts.csv':forecasts,
        'return_evidence.csv':returns,'dense_state_responses.csv':states}.items():table(name,rr)
    groups=[]
    for s in range(1,7):
        for name in conditions:
            for cohort in ('all','dominant'):
                rr=[r for r in cases if r['stage']==s and r['variant']==name and (cohort=='all' or r['dominant'])]
                if not rr:continue
                ratios=[r['relative_survive6'] for r in rr if r['relative_survive6']is not None]
                groups.append(dict(stage=s,capacity=study.old.lab.STAGES[s-1][0],variant=name,cohort=cohort,cases=len(rr),
                    baseline_wr=mean(rr,'baseline_wr'),survive6=mean(rr,'survive6'),
                    relative_survive6=sum(ratios)/len(ratios) if ratios else None,
                    reach20=mean(rr,'reach20'),reach30=mean(rr,'reach30'),
                    forecast_half_median=statistics.median(r['forecast_half'] for r in rr),
                    forecast_within30=sum(r['forecast_half']<=30 for r in rr)/len(rr)))
    table('stage_summary.csv',groups)
    audit=dict(status='passed',cells=144,static_executions=count,progressive_executions=progressive_count,
        total_executions=count+progressive_count,actual_native_journey_battles=native,
        physical_journeys=144*10*32,exact_saved_battle_replays=replays,censored_native_journeys=censored,
        archive_sha256=archives,sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (Path(__file__),study.OUT/'summary.json',progressive.OUT/'summary.json',study.fit.OUT/'selected.json')})
    atomic_json(study.fit.OUT/'audit.json',audit)
    report(groups,audit)
    plot(groups)
    print('retune audit passed',audit['total_executions'],'executions',replays,'exact replays',flush=True)


def report(groups,audit):
    policies=json.loads((study.fit.OUT/'selected.json').read_text(encoding='utf-8'))['stage_policies']
    lines=['# 六阶段旅行节奏：静态重标定与分段候选','','2026-10-27。144个全新人物技能对照配置，'
        '六阶段×六流派×四组混合身份；每格四件顶级、两种归属候选、密集低损耗状态重新排阵。'
        '阶段参数仅从旧校准数据选择，未使用本批最终结果调整系数。分段候选为另行声明的同批配对探索。', '',
        f'执行{audit["total_executions"]:,}次原生模拟（含搜索），其中{audit["actual_native_journey_battles"]:,}场实际连战，'
        f'{audit["physical_journeys"]:,}条路线；{audit["exact_saved_battle_replays"]:,}场保存对局精确复演。'
        f'{audit["censored_native_journeys"]}场120回合删失，路线在非胜利时停止，原始删失标记保留。', '',
        '## 新阶段温和档', '',
        '令P=min(1,本场累计实际承伤/本场有效战力上限)。获胜后以p概率获得长期损耗，'
        '触发后上限乘(1−l0−l1×P)。战后仍回满有效上限，原生战内状态每战重建。', '',
        '| 人数 | 触发概率p | 基础损失l0 | 承伤附加系数l1 |',
        '| --- | --- | --- | --- |']
    for s in range(6):
        p=policies[str(s)];lines.append(f'| {study.old.lab.STAGES[s][0]} | {p["p"]:.0%} | {p["l0"]:.2%} | {p["l1"]:.1%} |')
    lines+=['','这些是待确认的校准候选，不因被选中就视为所有目标达标。原档为p=65%、l0=8%、l1=20%。', '',
        '## 前6战完整生存与持续深入', '',
        '以下仅汇总本批初始胜率至少95%的参考构筑；无旅行损耗是同一阵容和同一随机流的原生对照。'
        '6战可以解释为同类地区去程3战＋回程3战，尚未指定实际地图距离。', '',
        '| 人数 | 构筑数 | 无损耗S6 | 原档S6 | 温和档S6 | 分段档S6 | 温和档30战内到50%比例 | 分段档30战内到50%比例 |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |']
    get=lambda s,name:next(r for r in groups if r['stage']==s and r['variant']==name and r['cohort']=='dominant')
    for s in range(1,7):
        a=get(s,'control');b=get(s,'original');c=get(s,'revised');d=get(s,'progressive')
        lines.append(f'| {a["capacity"]} | {a["cases"]} | {a["survive6"]:.1%} | {b["survive6"]:.1%} | {c["survive6"]:.1%} | {d["survive6"]:.1%} | {c["forecast_within30"]:.1%} | {d["forecast_within30"]:.1%} |')
    lines+=['','S6为真实原生连战结果。“到50%”使用密集状态独立战斗响应的加权路径预测，'
        '包含网格插值，不是把抵达第30战的概率当成第30战单场胜率。31表示观测窗内未到，不代表第31战达标。', '',
        '分段档：上次完整休息后前6场胜利按温和档投放，第7场起用原档。换人、换装、退场不重置计程；'
        '完整休息重置，半额补给只恢复缺失上限。本规则是研究备选，未进入正式游戏。', '',
        '## 补给提前与减轻损耗的对照', '',
        '| 人数 | 原档无补给·抵达20战 | 原档2战后全清 | 原档6战后全清 | 温和档6战后全清 | 温和档6战后补回半数缺失上限 | 分段档6战后全清 |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    for s in range(1,7):
        names=('original','original_early','original_late','revised_full','revised_partial','progressive_full')
        lines.append('| '+' | '.join([str(study.old.lab.STAGES[s-1][0])]+[f'{get(s,n)["reach20"]:.1%}' for n in names])+' |')
    lines+=['','补给为固定胜利节点的一次免费对照，不代表真实地图存在这些免费点。'
        '半额明确指补回50%缺失上限，和上一轮“清除一半log损耗”不是同一配置。'
        '完整休息清除长期损耗并重置分段计程；静态档没有计程规则。', '',
        '## 数据边界', '',
        '原生路线每格每变体32条；单场响应0损耗96次、其余24次。5人训练穷举120顺位，'
        '较大队伍16候选，装备归属仅两种启发式，不证明全局最优。相同人物的重复ROLL不能算独立玩家。'
        '未指定战败结算、补给价格、遇敌密度，未修改Unity数值核心或敌方。'
        '20/25/30人专门残血险胜2～3战目标不属于本批轻松地区确认，仍不可宣称覆盖。', '',
        '[逐格真实结果与能力预测](results/report/case_evidence.csv)、[六阶段汇总](results/report/stage_summary.csv)、'
        '[真实连战曲线](results/report/native_curves.csv)、[密集状态响应](results/report/dense_state_responses.csv)、'
        '[预测曲线](results/report/response_forecasts.csv)、[完整往返](results/report/return_evidence.csv)。', '',
        '![旅行节奏比较](results/report/retune_comparison.png)']
    (study.fit.HERE/'DESIGN_GUIDE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def plot(groups):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    font=FontProperties(fname='C:/Windows/Fonts/msyh.ttc')
    fig,axes=plt.subplots(1,2,figsize=(12,4.6));x=np.arange(6)
    for k,(name,label) in enumerate((('original','原档'),('revised','温和档'),('progressive','分段候选'))):
        rr=[next(r for r in groups if r['stage']==s and r['variant']==name and r['cohort']=='dominant') for s in range(1,7)]
        axes[0].bar(x+(k-1)*.25,[r['survive6'] for r in rr],width=.25,label=label)
        axes[1].bar(x+(k-1)*.25,[r['forecast_within30'] for r in rr],width=.25,label=label)
    for ax,title in zip(axes,('真实连战：完整前6战存活率','独立响应预测：30战内到50%的构筑比例')):
        ax.set_title(title,fontproperties=font);ax.set_xticks(x,[5,10,15,20,25,30]);ax.set_xlabel('人数上限',fontproperties=font)
        ax.set_ylim(0,1.05);ax.grid(axis='y',alpha=.2)
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,prop=font,ncol=3,loc='upper center',bbox_to_anchor=(.5,1.01))
    fig.tight_layout(rect=(0,0,1,.91));fig.savefig(OUT/'retune_comparison.png',dpi=160);plt.close(fig)


if __name__=='__main__':main()
