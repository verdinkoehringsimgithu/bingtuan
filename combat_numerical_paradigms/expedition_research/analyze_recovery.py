"""Audit compound journeys, replay sampled native battles and publish paired evidence."""
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

import recovery_stress as stress
from audit_research import check_manifest, equivalent
from analyze_expedition import model as response_model, predict, horizon
from confirm_paths import compact, draw
from order_search import snapshot, reordered
from run_bonds import atomic_json


def table(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader();writer.writerows(rows)


def main():
    root=stress.OUT; manifest=check_manifest(root/'manifest.json')
    data=json.loads((root/'summary.json').read_text(encoding='utf-8'))
    assert data['signature']==manifest['signature'] and data['cells']==len(data['rows'])==216
    cases=[]; curves=[]; states=[]; forecasts=[]; archives={}; replays=0; total=0; battles=0; censored=0
    for cell in data['rows']:
        j=cell['job']; job={**j,'key':cell['key']}; n=stress.lab.STAGES[j['stage']][0]
        path=root/'replicates'/(cell['key']+'.json.gz')
        archives[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        with gzip.open(path,'rt',encoding='utf-8') as f:raw=json.load(f)
        assert equivalent(raw['job'],job)
        # The frozen hash seed function stringifies its arguments. Preserve the
        # archived job's insertion order when rebuilding that exact stream.
        job=raw['job']
        mm,ii,enemy,ei,simulator,bond=stress.prepare(j)
        assert equivalent(snapshot(mm,ii),raw['members']) and equivalent(snapshot(enemy,ei),raw['enemy'])
        assert len(mm)==len(enemy)==n and sum(i.top for i in ii)==4
        assert len({m.person_id for m in mm})==n
        prep=0
        for x, point in raw['prepared'].items():
            plan=point['plan'];seeds=point['seeds'];rr=point['trials'];metrics=point['metrics']
            assert plan['searched_orders']==(120 if n==5 else 16)
            assert not set(seeds['train'])&set(seeds['test']) and not set(seeds['select'])&set(seeds['test'])
            expected=(120 if n==5 else 16)*2+3*4+(128 if float(x)==0 else 32)
            assert point['executed_battles']==expected
            for key in ('win','hp','censored','damage_exposure'):
                assert abs(metrics[key]-sum(r[key] for r in rr)/len(rr))<1e-12
            prep+=expected
            states.append(dict(stage=j['stage']+1,capacity=n,genre=j['genre'],model=j['model'],
                count=j['count'],region=j['region'],wear=float(x),bp_cap=math.exp(-float(x)),**metrics))
        assert prep==cell['result']['preparation_executions']
        count=0;cc=0
        response=response_model({f'bp_only:{x}':p for x,p in raw['prepared'].items()},'bp_only')
        for signal,routes in raw['routes'].items():
            assert len(routes)==64
            policy=dict(profile='bp_only',signal=signal,p0=.65,p_pressure=0.,loss0=.08,loss_pressure=.2)
            forecast=predict(response,policy,cell['key'])
            forecasts.extend(dict(stage=j['stage']+1,capacity=n,genre=j['genre'],model=j['model'],
                region=j['region'],signal=signal,**r) for r in forecast)
            for index, route in enumerate(routes):
                wear=0.
                for node,row in enumerate(route,1):
                    assert row['node']==node and row['wear_before']==wear
                    assert row['battle_seed']==stress.lab.seed('recovery-native',job,index,node)
                    assert row['event_roll']==stress.lab.seed('recovery-event',job,index,node)/(1<<64)
                    point=min(stress.lab.GRID,key=lambda x:(abs(x-wear),x))
                    assert equivalent(row['order'],raw['prepared'][str(point)]['plan']['order'])
                    delta=draw(policy,row['result'],row['event_roll']) if row['result']['win'] else 0.
                    assert row['wear_after']==wear+delta
                    if not row['result']['win']:assert node==len(route)
                    if j['genre']=='C_I' and index==0:
                        m,it=reordered(mm,ii,row['order'])
                        rr,trace,*_=simulator(m,enemy,row['battle_seed'],it,ei,p=j['macro'],enabled=(bond,),
                            factors=stress.trip_core.factors(stress.lab.PROFILES['bp_only'],wear),telemetry='trace' in row)
                        assert equivalent(compact(rr),row['result'])
                        if 'trace' in row:assert equivalent(trace,row['trace'])
                        replays+=1
                    wear+=delta;count+=1;cc+=row['result']['censored']
            for node, public in enumerate(cell['result']['curves'][signal],1):
                rows=[r[node-1] for r in routes if len(r)>=node]
                assert public['entered']==len(rows) and public['wins']==sum(r['result']['win'] for r in rows)
                assert abs(public['cap_sum']-sum(math.exp(-r['wear_before']) for r in rows))<1e-9
                curves.append(dict(stage=j['stage']+1,capacity=n,genre=j['genre'],model=j['model'],count=j['count'],
                    region=j['region'],signal=signal,**public,reach_probability=public['entered']/64,
                    win_rate=public['wins']/public['entered'] if public['entered'] else None))
            b=cell['result']['baseline']
            reach=lambda k:sum(len(r)>=k for r in routes)/64
            cases.append(dict(stage=j['stage']+1,capacity=n,genre=j['genre'],model=j['model'],
                count=j['count'],region=j['region'],signal=signal,baseline_wr=b['win'],
                winning_hp=b['winning_hp'],baseline_exposure=b['damage_exposure'],
                baseline_effective_heal=b['effective_heal'],reach10=reach(10),reach20=reach(20),reach30=reach(30),
                forecast_half_battle=horizon(forecast),
                survive30=sum(len(r)==30 and r[-1]['result']['win'] for r in routes)/64))
        assert count==cell['result']['journey_battles'] and cc==cell['result']['censored']
        assert count+prep==cell['result']['executed_battles']==raw['executed_battles']
        total+=count+prep;battles+=count;censored+=cc
    assert total==data['executed_battles']
    table(root/'case_evidence.csv',cases);table(root/'native_curves.csv',curves);table(root/'state_responses.csv',states)
    table(root/'response_forecasts.csv',forecasts)
    grouped=[]
    for stage in range(1,7):
        for model in stress.MODELS:
            for signal in ('end_hp','exposure'):
                for cohort in ('all','dominant'):
                    rr=[r for r in cases if r['stage']==stage and r['model']==model and r['signal']==signal
                        and (cohort=='all' or r['baseline_wr']>=.95)]
                    if not rr:continue
                    hh=sorted(r['forecast_half_battle'] for r in rr)
                    median=(hh[(len(hh)-1)//2]+hh[len(hh)//2])/2
                    grouped.append(dict(stage=stage,capacity=stress.lab.STAGES[stage-1][0],model=model,signal=signal,
                        cohort=cohort,cases=len(rr),**{k:sum(r[k] for r in rr)/len(rr) for k in
                            ('baseline_wr','baseline_exposure','reach10','reach20','reach30','survive30')},
                        forecast_half_battle_median=median,
                        forecast_within_30=sum(r['forecast_half_battle']<=30 for r in rr)/len(rr)))
    table(root/'stage_summary.csv',grouped)
    lines=['# 强恢复羁绊的长期减益压力测试','','2026-10-22。六阶段×六流派×两种固定敌方参照×三个复合效果预算，共216格。'
        '顶级装备最多四件；女仆长附加真伤方案半量/全量、农民标准果实；每个状态重新搜索顺位。'
        '身份数量取阶段可用真实人物与人数上限的较小者，未凭空生成同名人物。', '',
        f'执行{total:,}次模拟，含{battles:,}场真实连战；两种压力信号各64条最多30战路线，'
        f'共{216*128:,}条路线。{censored}场真实连战120回合删失；抽取C_I各格首条路线，{replays:,}场逐场精确复演。', '',
        '两种压力信号保持相同65%触发概率、8%基础+20%压力降幅、相同人物和对局/事件随机种子。'
        'end_hp=1−胜后战力比例；exposure=min(1,本场实际累计承伤/有效战力上限)。'
        '实际累计承伤包括战内恢复后再受伤的部分；两者都不携带战后残血，也不削弱治疗技能本身。', '',
        '本轮为既定候选的鲁棒性比较，未用这批最终数据重拟合系数；原通用候选与暴露量候选分别保留。'
        '全部身份/技能关联仍为研究抽样，并非生产人物已经绑定了这些技能。主矩阵未开启身份羁绊，此补测单独开启目标羁绊，敌方羁绊关闭；不代表23种混合羁绊已全部覆盖。', '',
        '| 人数 | 复合预算 | 优势样本数 | 初始胜率 | 胜后血量信号·到第30战 | 累计承伤信号·到第30战 |',
        '| --- | --- | --- | --- | --- | --- |']
    names={'maid_half':'女仆长半量','maid_full':'女仆长全量','farmer':'农民标准'}
    for stage in range(1,7):
        for model in stress.MODELS:
            rr=[r for r in grouped if r['stage']==stage and r['model']==model and r['cohort']=='dominant']
            a=next((r for r in rr if r['signal']=='end_hp'),None);b=next((r for r in rr if r['signal']=='exposure'),None)
            if a and b:lines.append(f'| {a["capacity"]} | {names[model]} | {a["cases"]} | {a["baseline_wr"]:.1%} | {a["reach30"]:.1%} | {b["reach30"]:.1%} |')
            else:lines.append(f'| {stress.lab.STAGES[stage-1][0]} | {names[model]} | 0 | — | — | — |')
    lines+=['','优势样本按初始胜率≥95%筛选，两种信号使用同一筛选集；每种仅六流派、两敌方参照，'
        '不可外推为所有玩家的概率。到第30战是前29战都胜利，不等同于第30战单场胜率。', '',
        '## 单场能力衰减标尺', '',
        '另以独立战斗种子测出的13个损耗状态建立响应路径预测，保持幸存者权重与胜利后的压力分布。'
        '这是插值预测，不是把上表到达率误当作单场胜率。31表示30战窗口内未到50%。', '',
        '| 人数 | 复合预算 | 血量信号·到50%中位战数 | 承伤信号·到50%中位战数 | 承伤信号·30战内构筑比例 |',
        '| --- | --- | --- | --- | --- |']
    for stage in range(1,7):
        for model in stress.MODELS:
            rr=[r for r in grouped if r['stage']==stage and r['model']==model and r['cohort']=='dominant']
            a=next((r for r in rr if r['signal']=='end_hp'),None);b=next((r for r in rr if r['signal']=='exposure'),None)
            if a and b:
                show=lambda x:'>30' if x>30 else f'{x:g}'
                lines.append(f'| {a["capacity"]} | {names[model]} | {show(a["forecast_half_battle_median"])} | {show(b["forecast_half_battle_median"])} | {b["forecast_within_30"]:.1%} |')
    lines+=['',
        '需要更强的地区约束时，见[较强损耗备选档](STRONG_PRESSURE.md)。这是同批强恢复构筑的配对强度探索，'
        '不把它当成所有普通地区的默认值，也不按身份单独惩罚。', '',
        '[逐格配对结果](results/recovery_stress/case_evidence.csv)、[逐战到达率](results/recovery_stress/native_curves.csv)、'
        '[固定损耗战斗响应](results/recovery_stress/state_responses.csv)、[六阶段汇总](results/recovery_stress/stage_summary.csv)、'
        '[能力衰减预测](results/recovery_stress/response_forecasts.csv)。', '',
        '复现：先运行`verify_bond_trip.py`，再运行`recovery_stress.py --workers 6`与`analyze_recovery.py`。'
        '保存了全部路线、人物/技能/装备、种子、逐状态顺位、源哈希、事件账本与选取路线的逐回合遥测。']
    (stress.lab.HERE/'RECOVERY_STRESS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    atomic_json(root/'audit.json',dict(status='passed',cells=data['cells'],executed_battles=total,
        actual_journey_battles=battles,physical_journeys=216*128,censored_actual_battles=censored,
        exact_saved_battle_replays=replays,archive_sha256=archives,
        summary_sha256=hashlib.sha256((root/'summary.json').read_bytes()).hexdigest(),
        forecast_source_sha256=hashlib.sha256((stress.lab.HERE/'analyze_expedition.py').read_bytes()).hexdigest(),
        analyzer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    print('recovery audit passed:',total,'executions;',replays,'exact replays')


if __name__=='__main__':main()
