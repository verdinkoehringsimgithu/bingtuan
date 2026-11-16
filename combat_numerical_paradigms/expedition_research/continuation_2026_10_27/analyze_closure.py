"""Audit native supply journeys and report mixed-bond/return-risk evidence."""
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics

import study_closure as study
from audit_research import check_manifest,equivalent
from state_contract import ExpeditionState,victory_losses
from run_bonds import atomic_json

OUT=study.OUT/'report'


def table(name,rows):
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def average(rows,key):return sum(r[key] for r in rows)/len(rows)


def rate(point):return average(point['trials'],'win')


def paired(left,right):
    values=[a['win']-b['win'] for a,b in zip(left,right)]
    return dict(delta=sum(values)/len(values),paired_seed_se=statistics.stdev(values)/math.sqrt(len(values)))


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    manifest=check_manifest(study.OUT/'manifest.json')
    summary=json.loads((study.OUT/'summary.json').read_text(encoding='utf-8'))
    assert len(summary['rows'])==summary['cells']==576 and summary['signature']==manifest['signature']
    cases=[];states=[];curves=[];returns=[];risks=[];gear_rows=[];effects=[];diagnostics=[]
    counts=0;native=0;censored=0;replays=0;archives={};coverage=set()
    for cell in summary['rows']:
        path=study.OUT/'replicates'/(cell['key']+'.json.gz');archives[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        with gzip.open(path,'rt',encoding='utf-8') as f:raw=json.load(f)
        j=raw['job'];assert equivalent({k:v for k,v in j.items() if k!='key'},cell['job'])
        mm,gears,enemy,ei,simulate=study.prepare(j);n=len(mm)
        coverage.add((j['stage'],j['genre'],j['pool'],j['mix'],j['region']))
        assert all(equivalent(snapshot,study.snapshot(mm,gears[name])) for name,snapshot in raw['members'].items())
        assert equivalent(raw['enemy'],study.snapshot(enemy,ei)) and len(enemy)==n==study.lab.STAGES[j['stage']][0]
        assert len({m.person_id for m in mm})==n and all(sum(it.top for it in items)==4 for items in gears.values())
        base=dict(stage=j['stage']+1,capacity=n,genre=j['genre'],pool=j['pool'],mix=j['mix'],region=j['region'])
        baseline=raw['prepared']['0'];wr=rate(baseline);won=[r for r in baseline['trials'] if r['win']]
        winning_hp=average(won,'hp') if won else None
        group='low_margin' if wr>.5 and winning_hp is not None and winning_hp<=.2 else 'dominant' if wr>=.95 else 'other'
        base.update(cohort=group,baseline_wr=wr)
        count=0
        for kind,points in (('prepared',raw['prepared']),('ablation',raw['ablation'])):
            for label,p in points.items():
                wear=float(label) if kind=='prepared' else 0
                test_count=96 if wear==0 else 24
                expected=2*((120 if n==5 else 16)*2+12+test_count)
                assert p['executed_battles']==expected and len(p['trials'])==test_count
                count+=expected
                assert not set(p['seeds']['test'])&set(p['seeds']['train']) and not set(p['seeds']['test'])&set(p['seeds']['select'])
                assert equivalent(p['order'],p['plans'][p['chosen']]['order'])
                for gear,plan in p['plans'].items():
                    assert plan['searched_orders']==(120 if n==5 else 16)
                    assert sorted(plan['order'])==list(range(n))
                expected_gear=max(gears,key=lambda g:(tuple(p['plans'][g]['selection']),g=='original'))
                assert p['chosen']==expected_gear
                assert equivalent(p['trials'],p['alternative_trials'][p['chosen']])
                if kind=='prepared':
                    states.append(dict(**base,wear=wear,bp_cap=math.exp(-wear),wr=rate(p),
                        winning_hp=average([r for r in p['trials'] if r['win']],'hp') if any(r['win'] for r in p['trials']) else None,
                        selected_gear=p['chosen'],mean_turns=average(p['trials'],'turns'),
                        censored=average(p['trials'],'censored')))
                    gear_rows.append(dict(**base,wear=wear,chosen=p['chosen'],
                        original_wr=average(p['alternative_trials']['original'],'win'),
                        reassigned_wr=average(p['alternative_trials']['reassigned'],'win'),
                        **paired(p['alternative_trials']['reassigned'],p['alternative_trials']['original'])))
                    # Only valid native metric keys are published. worker_saves
                    # in the raw projection is unavailable (native key is
                    # worker_procs); it must not be interpreted as zero procs.
                    for metric in ('scholar_restored','engineer_casts','absolute_dodges','fruit_harvest','maid_casts'):
                        diagnostics.append(dict(**base,wear=wear,metric=metric,value=sum(r['metrics'][metric] for r in p['trials'])/len(p['trials'])))
        bonds=study.MIXES[j['mix']];off=raw['ablation']['off'];a=raw['ablation'][bonds[0]];b=raw['ablation'][bonds[1]]
        interactions=[q['win']-x['win']-y['win']+z['win'] for q,x,y,z in zip(baseline['trials'],a['trials'],b['trials'],off['trials'])]
        effects.append(dict(**base,off_wr=rate(off),first_only_wr=rate(a),second_only_wr=rate(b),both_wr=wr,
            interaction=sum(interactions)/len(interactions),interaction_seed_se=statistics.stdev(interactions)/math.sqrt(len(interactions)),
            both_vs_off=wr-rate(off)))
        journey_count=0;case_censored=0
        for removal,routes in raw['routes'].items():
            assert len(routes)==32
            for index,route in enumerate(routes):
                state=ExpeditionState('research-troop')
                for node,row in enumerate(route['rows'],1):
                    assert node==row['node'] and state.wear[0]==row['wear_before']
                    assert row['battle_seed']==study.seed('journey',j,index,node)
                    roll=study.seed('loss',j,index,node)/(1<<64);assert roll==row['event_roll']
                    point=min(study.GRID,key=lambda x:(abs(x-state.wear[0]),x));p=raw['prepared'][str(point)]
                    assert row['gear']==p['chosen'] and equivalent(row['order'],p['order'])
                    r=row['result']
                    if j['genre']=='C_I' and index==0:
                        m,it=study.reordered(mm,gears[row['gear']],row['order'])
                        q,t,*_=simulate(m,enemy,row['battle_seed'],it,ei,p=j['macro'],enabled=bonds,
                            factors=state.factors,telemetry='trace' in row)
                        assert equivalent(study.public_result(q),r)
                        if 'trace' in row:assert equivalent(t,row['trace'])
                        replays+=1
                    if r['win']:state.apply_loss(f'battle:{node}',victory_losses(r['hp'],r['damage_exposure'],roll),'victory')
                    assert state.wear[0]==row['wear_after_battle']
                    if r['win'] and node==6 and float(removal):state.supply('supply:6',(float(removal),)*5)
                    assert state.wear[0]==row['wear_after']
                    if not r['win']:assert node==len(route['rows'])
                    journey_count+=1;case_censored+=r['censored']
                assert equivalent(state.to_dict(),route['state'])
            for node in range(1,31):
                rr=[r['rows'][node-1] for r in routes if len(r['rows'])>=node];wins=sum(r['result']['win'] for r in rr)
                curves.append(dict(**base,removal=float(removal),battle=node,entered=len(rr),wins=wins,
                    reach=len(rr)/32,conditional_wr=wins/len(rr) if rr else None,
                    cap_sum=sum(math.exp(-r['wear_before']) for r in rr),censored=sum(r['result']['censored'] for r in rr)))
            reached6=[r for r in routes if len(r['rows'])>=6 and r['rows'][5]['result']['win']]
            reach30=sum(len(r['rows'])==30 for r in routes)/32
            assert reach30==cell['result']['reach30'][removal]
            cases.append(dict(**base,winning_hp=winning_hp,removal=float(removal),reach_supply=len(reached6)/32,
                reach10=sum(len(r['rows'])>=10 for r in routes)/32,reach20=sum(len(r['rows'])>=20 for r in routes)/32,
                reach30=reach30,survive30=sum(len(r['rows'])==30 and r['rows'][-1]['result']['win'] for r in routes)/32,
                mean_won_battles=sum(sum(q['result']['win'] for q in r['rows']) for r in routes)/32))
            if float(removal)==0:
                def survival(k):return sum(len(r['rows'])>=k and r['rows'][k-1]['result']['win'] for r in routes)/32
                ret=[]
                for outward in range(1,16):
                    out=survival(outward);home=survival(outward*2)
                    result=dict(**base,outward_battles=outward,return_battles=outward,
                        survive_outward=out,whole_trip_survival=home,conditional_return=home/out if out else None)
                    ret.append(result);returns.append(result)
                for threshold in (.8,.9,.95):
                    safe=[r['outward_battles'] for r in ret if r['whole_trip_survival']>=threshold]
                    risks.append(dict(**base,whole_trip_success_target=threshold,
                        max_tested_outward_battles=max(safe,default=0),scope='same region, equally many return encounters; seed estimate'))
        assert journey_count==cell['result']['native_journey_battles'] and case_censored==cell['result']['censored']
        assert count+journey_count==raw['executed_battles']==cell['result']['executed_battles']
        counts+=count+journey_count;native+=journey_count;censored+=case_censored
    assert len(coverage)==576 and counts==summary['executed_battles']
    tables={'case_evidence.csv':cases,'state_responses.csv':states,'native_curves.csv':curves,
        'return_evidence.csv':returns,'return_risk_targets.csv':risks,'equipment_ownership.csv':gear_rows,
        'bond_interactions.csv':effects,'mechanism_diagnostics.csv':diagnostics}
    for name,rows in tables.items():table(name,rows)
    groups=[]
    for s in range(1,7):
        for mix in study.MIXES:
            for region in ('dominant','clutch'):
                for removal in (0.,.5,1.):
                    rr=[r for r in cases if r['stage']==s and r['mix']==mix and r['region']==region and r['removal']==removal]
                    groups.append(dict(stage=s,capacity=study.lab.STAGES[s-1][0],mix=mix,region=region,removal=removal,
                        cells=len(rr),**{k:average(rr,k) for k in ('baseline_wr','reach_supply','reach10','reach20','reach30','mean_won_battles')}))
    table('stage_supply_summary.csv',groups)
    intensity=[]
    for factor in (.2,.4,.6,.8):
        for removal in (.25,.5,.75,1.):
            intensity.append(dict(before_cap=factor,log_wear_removed=removal,after_cap=factor**(1-removal),
                restored_cap_percentage_points=(factor**(1-removal)-factor)*100,
                half_missing_cap_reference=factor+.5*(1-factor)))
    table('supply_semantics.csv',intensity)
    provenance=dict(status='passed',cells=576,executed_battles=counts,actual_journey_battles=native,
        physical_journeys=576*96,censored_actual_battles=censored,exact_saved_battle_replays=replays,
        archives=archives,table_rows={k:len(v) for k,v in tables.items()},
        sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (Path(__file__),study.OUT/'summary.json',study.HERE/'PROTOCOL.md',study.OUT/'contract_verification.json')})
    atomic_json(study.OUT/'audit.json',provenance)
    report(groups,cases,effects,gear_rows,risks,provenance)
    plot(curves)
    print('closure audit passed:',counts,'executions;',native,'native journey battles;',replays,'exact replays',flush=True)


def report(groups,cases,effects,gear_rows,risks,audit):
    names={'engineer_scholar':'工程师＋学者','ninja_worker':'忍者＋社畜',
           'farmer_scholar':'农民＋学者','maid_engineer':'女仆＋工程师'}
    lines=['# 补给与混合身份实测','','2026-10-27。六阶段、六流派、两套独立人物技能池、四组身份、两个固定地区参照，共576格。'
        '每人一件装备、四件顶级；同一装备种类/数值在两种归属间选择，再优化顺位，最终种子独立测试。'
        '5人训练穷举120顺位，较大队伍有限16候选，不保证全局最优。', '',
        f'共{audit["executed_battles"]:,}次执行（含顺位/归属搜索），其中{audit["actual_journey_battles"]:,}场真实连战，'
        f'{audit["physical_journeys"]:,}条路线，{audit["exact_saved_battle_replays"]:,}场保存路线精确复演。'
        f'真实连战有{audit["censored_actual_battles"]}场120回合删失，路径在非胜利处停止；原始数据保留删失标记，不冒充已知战败。', '',
        '## 补给究竟解决什么', '',
        '下表为初始单场胜率至少95%的参考构筑，按实际数据筛选；固定地区名不代替胜率。'
        '三列为同一批构筑、相同战斗随机流；第6战胜利后执行一次补给。补给之前失败的路线保留在分母里，'
        '不把只有幸存者能用到的补给收益夸大。这里的补给免费只是隔离效果的实验条件，不是正式经济设定。', '',
        '| 人数 | 优势构筑数 | 无补给抵达第20战 | 清除50%损耗抵达第20战 | 全清抵达第20战 | 能抵达补给的比例 |',
        '| --- | --- | --- | --- | --- | --- |']
    for s in range(1,7):
        rr={r:[x for x in cases if x['stage']==s and x['removal']==r and x['cohort']=='dominant'] for r in (0.,.5,1.)}
        assert all(len(rr[r])==len(rr[0.]) for r in rr)
        if rr[0.]:lines.append('| '+' | '.join([str(study.lab.STAGES[s-1][0]),str(len(rr[0.]))]+
            [f'{average(rr[r],"reach20"):.1%}' for r in (0.,.5,1.)]+[f'{average(rr[0.],"reach_supply"):.1%}'])+' |')
    lines+=['','“清除50%损耗”本轮指清除一半log损耗：上限剩50%时会恢复到约70.7%，不是75%。'
        '如果产品希望“补回一半缺失上限”，应单独使用 F新=F旧+50%×(1−F旧)；两种含义不能共用一个未注明的百分比字段。', '',
        '## 混合身份与装备机会成本', '',
        '两项单独开启和双开都重新选择归属、搜索顺位，仍使用同一人物技能和装备种类。'
        '交互=双开−第一项单开−第二项单开＋双关闭，包含玩家重新编排后的实际收益，不是固定顺位的纯机制偏导。', '',
        '| 组合 | 双关闭胜率 | 双开胜率 | 配对交互 | 重新分配装备的平均差值 |',
        '| --- | --- | --- | --- | --- |']
    for mix in study.MIXES:
        rr=[r for r in effects if r['mix']==mix];gg=[r for r in gear_rows if r['mix']==mix and r['wear']==0]
        lines.append(f'| {names[mix]} | {average(rr,"off_wr"):.1%} | {average(rr,"both_wr"):.1%} | {average(rr,"interaction")*100:+.2f}个百分点 | {average(gg,"delta")*100:+.2f}个百分点 |')
    lines+=['','均值按六阶段、六流派、两抽样池、两地区等权；接入系数必须继续看逐阶段和逐构筑明细。'
        '女仆用复合半量预算；每身份人数取阶段上限一半与真实供给的较小值。未激活的填充身份不参与羁绊。'
        '装备重新分配候选不一定优于原归属，因此由选择种子决定用哪一个，最终测试胜率不能反过来选。', '',
        '## 返程优先于固定深度', '',
        '返程表假设回程遭遇与去程数量相同、同一固定地区，损耗持续累计；没有免费传送假设。'
        '80%/90%/95%是设计者可选的完整往返成功率目标。达到目标的最大去程战数由真实路线前缀估计，'
        '0表示本批32条种子路径没有支持至少一去一回的证据，不表示禁止玩家出门。', '',
        '| 人数 | 优势构筑·80%往返目标中位去程战数 | 90%目标 | 95%目标 |',
        '| --- | --- | --- | --- |']
    for s in range(1,7):
        values=[]
        for target in (.8,.9,.95):
            rr=[r['max_tested_outward_battles'] for r in risks if r['stage']==s and r['cohort']=='dominant' and r['whole_trip_success_target']==target]
            values.append(f'{statistics.median(rr):g}' if rr else '—')
        lines.append('| '+' | '.join([str(study.lab.STAGES[s-1][0])]+values)+' |')
    lines+=['','这些间隔是固定遭遇环境下的风险标尺，不是地图格数或正式补给点间距。真实敌方组合、遭遇密度、'
        '玩家补给选择、返程事件还需要地图调用方提供；每格仅32条路径，尾部概率不宜过度解读。', '',
        '## 数据与接入边界', '',
        '[状态/归属实测](results/report/state_responses.csv)、[混合交互](results/report/bond_interactions.csv)、'
        '[装备归属](results/report/equipment_ownership.csv)、[真实连战](results/report/native_curves.csv)、'
        '[返程证据](results/report/return_evidence.csv)、[风险目标](results/report/return_risk_targets.csv)、'
        '[逐格补给结果](results/report/case_evidence.csv)、[补给百分比语义](results/report/supply_semantics.csv)。', '',
        '主状态规范见[接入建议](INTEGRATION_SPEC.md)。本轮没有修改Unity、人物标签、技能生成器或钱包。'
        '战败结算仍未指定；20/25/30人残血险胜两三战缺口没有被本轮混合身份测试自动补齐。'
        'raw中的worker_saves为不可用的旧投影字段，原生字段叫worker_procs；本报告不据此宣称社畜未触发，'
        '也不把未记录的触发量当零。社畜的胜率开关和实际战斗逻辑已参加完整测试。', '',
        '![补给与连战](results/report/supply_pressure.png)']
    (study.HERE/'DESIGN_GUIDE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def plot(curves):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    font=FontProperties(fname='C:/Windows/Fonts/msyh.ttc')
    fig,axes=plt.subplots(2,2,figsize=(12,8))
    for ax,(mix,name) in zip(axes.flat,{'engineer_scholar':'工程师＋学者','ninja_worker':'忍者＋社畜',
        'farmer_scholar':'农民＋学者','maid_engineer':'女仆＋工程师'}.items()):
        for removal,label in ((0.,'无补给'),(.5,'第6战后清除50%损耗'),(1.,'第6战后全清')):
            rr=[r for r in curves if r['mix']==mix and r['cohort']=='dominant' and r['removal']==removal]
            if not rr:continue
            yy=[average([r for r in rr if r['battle']==n],'reach') for n in range(1,31)]
            ax.plot(range(1,31),yy,label=label)
        ax.axvline(6,color='#999',linestyle=':',linewidth=1)
        ax.set_title(name,fontproperties=font);ax.set_ylim(0,1.03);ax.grid(alpha=.2)
        ax.set_xlabel('战斗序号',fontproperties=font);ax.set_ylabel('抵达该战概率',fontproperties=font)
        ax.legend(prop=font,fontsize=8)
    fig.suptitle('初始胜率至少95%的构筑：一次补给的实际路线收益',fontproperties=font,fontsize=14)
    fig.tight_layout();fig.savefig(OUT/'supply_pressure.png',dpi=160);plt.close(fig)


if __name__=='__main__':main()
