"""Exact audit, precision checks and numerical guidance for remaining gaps."""
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics

from common import *
import stage25 as s25
import hard_regions as hard
import roster25

REPORT=OUT/'report'


def table(name,rows):
    with (REPORT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def load(path):return json.loads(path.read_text(encoding='utf-8'))


def mean(rows,key):return sum(r[key] for r in rows)/len(rows)


def precision(label,j,trials):
    wins=[r for r in trials if r['win']];n=len(trials);p=len(wins)/n;z=1.96;den=1+z*z/n
    center=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    hp=mean(wins,'hp') if wins else None
    hp_se=statistics.stdev(r['hp'] for r in wins)/math.sqrt(len(wins)) if len(wins)>1 else None
    low=center-half;upper=hp+1.96*hp_se if hp_se is not None else None
    return dict(label=label,stage=j['stage']+1,capacity=old.lab.STAGES[j['stage']][0],genre=j['genre'],gear=j['gear'],pool=j['pool'],
        trials=n,wr=p,wr_wilson95_low=low,wr_wilson95_high=center+half,winning_hp=hp,
        winning_hp_mean95_high=upper,point_target=p>.5 and hp is not None and hp<=.2,
        separate_95_bounds_pass=low>.5 and upper is not None and upper<=.2)


def main():
    REPORT.mkdir(parents=True,exist_ok=True);executions=0;native=0;replays=0;censored=0;archives={}
    stage_cases=[];hard_cases=[];precision_rows=[];probes=[];stage_states=[]
    check_manifest(s25.ROOT/'manifest.json');data=load(s25.ROOT/'summary.json');assert data['cells']==48
    selected=load(s25.ROOT/'selected.json')
    for path,digest in selected['calibration_archives'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
    candidates=selected['calibration_candidates'];ok=[r for r in candidates if r['coverage']>=.9]
    chosen=min(ok,key=lambda r:(r['expected_zero_exposure_log_loss'],r['policy']['l0'])) if ok else max(candidates,key=lambda r:r['coverage'])
    assert chosen['policy']==selected['tail']
    stage_native=0
    for cell in data['rows']:
        path=s25.ROOT/'replicates'/(cell['key']+'.json.gz');archives[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        with gzip.open(path,'rt',encoding='utf-8') as f:raw=json.load(f)
        j=raw['job'];mm,gears,enemy,ei,sim=previous.prepare(j)
        assert all(equivalent(v,old.snapshot(mm,gears[g])) for g,v in raw['members'].items())
        assert equivalent(raw['enemy'],old.snapshot(enemy,ei))
        prep=0
        for x,p in raw['prepared'].items():
            tests=96 if float(x)==0 else 24;expected=2*(32+12+tests)
            assert p['executed_battles']==expected;prep+=expected
            assert not set(p['seeds']['train'])&set(p['seeds']['test'])
            stage_states.append(dict(genre=j['genre'],mix=j['mix'],pool=j['pool'],wear=float(x),wr=mean(p['trials'],'win')))
        baseline=mean(raw['prepared']['0']['trials'],'win');case_native=0
        for name,routes in raw['variants'].items():
            cond=s25.conditions(j['tail'])[name];assert len(routes)==32
            for index,route in enumerate(routes):
                state=ExpeditionState('research-troop');counter=0
                for node,q in enumerate(route['rows'],1):
                    assert node==q['node'] and q['wear_before']==state.wear[0] and q['counter_before']==counter
                    point=min(previous.GRID,key=lambda x:(abs(x-state.wear[0]),x));choice=raw['prepared'][str(point)]
                    assert q['gear']==choice['chosen'] and equivalent(q['order'],choice['order'])
                    assert q['battle_seed']==old.seed('stage25-journey',j,index,node)
                    roll=old.seed('stage25-loss',j,index,node)/(1<<64);assert roll==q['event_roll']
                    if j['genre']=='C_I' and index==0:
                        m,it=old.reordered(mm,gears[q['gear']],q['order'])
                        r,t,*_=sim(m,enemy,q['battle_seed'],it,ei,p=j['macro'],enabled=old.MIXES[j['mix']],
                            factors=state.factors,telemetry='trace'in q)
                        assert equivalent(previous.project(r),q['result'])
                        if 'trace'in q:assert equivalent(t,q['trace'])
                        replays+=1
                    policy=cond['prefix'] if counter<6 else cond['tail'];r=q['result']
                    loss=policy['l0']+policy['l1']*r['damage_exposure'] if roll<policy['p'] else 0.
                    if r['win']:state.apply_loss(f'battle:{node}',(loss,0.,0.,0.,0.),'victory');counter+=1
                    assert state.wear[0]==q['wear_after_battle']
                    if r['win'] and node==6 and cond['rest']:
                        restore_missing_caps(state,'supply:6',(cond['rest'],)*5)
                        if cond['reset']:counter=0
                    assert q['wear_after']==state.wear[0] and q['counter_after']==counter
                    if not r['win']:assert node==len(route['rows'])
                    censored+=r['censored'];case_native+=1
                assert equivalent(state.to_dict(),route['state']) and route['counter']==counter
            forecast=s25.forecast(raw,cond['tail']) if name in ('old','revised') else None
            row=dict(genre=j['genre'],mix=j['mix'],pool=j['pool'],variant=name,baseline_wr=baseline,
                s6=sum(len(r['rows'])>=6 and r['rows'][5]['result']['win'] for r in routes)/32,
                reach20=sum(len(r['rows'])>=20 for r in routes)/32,reach30=sum(len(r['rows'])==30 for r in routes)/32,
                half_forecast=forecast['half'] if forecast else None)
            assert row['s6']==cell['result']['variants'][name]['s6'] and row['reach30']==cell['result']['variants'][name]['reach30']
            stage_cases.append(row)
        assert prep+case_native==cell['result']['executed_battles']==raw['executed_battles']
        stage_native+=case_native
    executions+=data['executed_battles'];native+=stage_native
    for phase in ('calibrate','confirm'):check_manifest(hard.ROOT/(phase+'_manifest.json'))
    calibration=load(hard.ROOT/'calibrate.json');assert calibration['cells']==216
    for cell in calibration['rows']:
        assert cell['result']['executed_battles']==12*68
        for point in cell['result']['cases']:
            assert abs(point['metrics']['wr']-mean(point['trials'],'win'))<1e-12
            assert not set(point['seeds']['train'])&set(point['seeds']['test'])
    executions+=calibration['executed_battles']
    confirmation=load(hard.ROOT/'confirm.json');assert confirmation['cells']==144
    raw_by_key={}
    for cell in confirmation['rows']:
        path=hard.ROOT/'replicates'/(cell['key']+'.json.gz');archives[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        with gzip.open(path,'rt',encoding='utf-8') as f:raw=json.load(f)
        raw_by_key[cell['key']]=raw;j=raw['job'];mm,ii,enemy,ei,sim=hard.prepare(j,j['pool'],'final')
        assert equivalent(raw['members'],old.snapshot(mm,ii)) and equivalent(raw['enemy'],old.snapshot(enemy,ei))
        assert len(mm)==len(enemy)==old.lab.STAGES[j['stage']][0]
        assert sum(it.top for it in ii)==(4 if j['gear']=='four_top' else 0)
        assert sum(p['executed_battles'] for p in raw['prepared'].values())==444
        p=precision(cell['key'],j,raw['prepared']['0']['trials']);hard_cases.append(p)
        case_native=0
        for name,routes in raw['journeys'].items():
            for index,route in enumerate(routes):
                wear=0.
                for node,q in enumerate(route,1):
                    assert node==q['node'] and q['wear_before']==wear
                    assert q['battle_seed']==old.seed('hard-native',j,j['pool'],index,node)
                    roll=old.seed('hard-loss',j,j['pool'],index,node)/(1<<64);assert q['event_roll']==roll
                    point=min(hard.GRID,key=lambda x:(abs(x-wear),x))
                    assert equivalent(q['order'],raw['prepared'][str(point)]['plan']['order'])
                    if j['genre']=='C_I' and index==0:
                        m,it=hard.reordered(mm,ii,q['order'])
                        r,t,*_=sim(m,enemy,q['battle_seed'],it,ei,p=j['macro'],enabled=hard.ENABLED,
                            factors=(math.exp(-wear),1.,1.,1.,1.),telemetry='trace'in q)
                        assert equivalent(hard.project(r),q['result'])
                        if 'trace'in q:assert equivalent(t,q['trace'])
                        replays+=1
                    r=q['result'];policy=raw['policies'][name]
                    loss=policy['l0']+policy['l1']*r['damage_exposure'] if roll<policy['p'] else 0.
                    if r['win']:wear-=math.log1p(-loss)
                    assert q['wear_after']==wear
                    if not r['win']:assert node==len(route)
                    case_native+=1;censored+=r['censored']
            probe=dict(label=cell['key'],capacity=old.lab.STAGES[j['stage']][0],genre=j['genre'],gear=j['gear'],variant=name,
                survive3=sum(len(r)==3 and r[-1]['result']['win'] for r in routes)/64)
            for node in (2,3):
                entered=[r[node-1] for r in routes if len(r)>=node]
                probe[f'entered{node}']=len(entered);probe[f'conditional_wr{node}']=sum(q['result']['win'] for q in entered)/len(entered) if entered else None
            assert probe['survive3']==cell['result']['survive3'][name];probes.append(probe)
        assert case_native==cell['result']['native_battles'] and 444+case_native==cell['result']['executed_battles']
        native+=case_native
    executions+=confirmation['executed_battles']
    extension=load(hard.ROOT/'baseline_extension.json')
    for c in extension['rows']:
        raw=raw_by_key[c['key']];j=c['job'];assert len(c['trials'])==len(c['seeds'])==512
        assert c['parent_archive_sha256']==archives[str(hard.ROOT/'replicates'/(c['key']+'.json.gz'))]
        mm,ii,enemy,ei,sim=hard.prepare(j,j['pool'],'final');m,it=hard.reordered(mm,ii,c['order'])
        r,*_=sim(m,enemy,c['seeds'][0],it,ei,p=j['macro'],enabled=hard.ENABLED)
        assert equivalent(hard.project(r),c['trials'][0]);replays+=1
        precision_rows.append(precision(c['key'],j,c['trials']))
    executions+=extension['executed_battles']
    for label,root,module in (('local25',OUT/'local25',None),('terminal25',OUT/'terminal25',None),('roster25',OUT/'roster25',roster25)):
        result=load(root/'results.json')
        for path,digest in result['sources'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
        executions+=result['executed_battles']
        if 'confirmation'not in result:continue
        c=result['confirmation'];j=result['selected']['job'];trials=c['trials'];precision_rows.append(precision(label,j,trials))
        mm,ii,enemy,ei,sim=module.prepare(j) if module else hard.prepare(j,j['pool'],'final')
        order=c['order'] if 'order'in c else result['selected']['result']['plan']['order'];m,it=hard.reordered(mm,ii,order)
        r,*_=sim(m,enemy,c['seeds'][0],it,ei,p=j['macro'],enabled=hard.ENABLED)
        assert equivalent(hard.project(r),trials[0]);replays+=1;native+=c['native_battles']
        for name,routes in c['journeys'].items():
            for index,route in enumerate(routes):
                wear=0.
                for q in route:
                    assert q['wear_before']==wear
                    policy=c['policies'][name];loss=policy['l0']+policy['l1']*q['result']['damage_exposure'] if q['event_roll']<policy['p'] else 0.
                    if q['result']['win']:wear-=math.log1p(-loss)
                    assert q['wear_after']==wear
                    if not q['result']['win']:assert q['node']==len(route)
                    if index==0:
                        m,it=hard.reordered(mm,ii,q['order']);rr,t,*_=sim(m,enemy,q['battle_seed'],it,ei,p=j['macro'],enabled=hard.ENABLED,
                            factors=(math.exp(-q['wear_before']),1.,1.,1.,1.),telemetry='trace'in q)
                        assert equivalent(hard.project(rr),q['result'])
                        if 'trace'in q:assert equivalent(t,q['trace'])
                        replays+=1
                    censored+=q['result']['censored']
            probe=dict(label=label,capacity=25,genre=j['genre'],gear=j['gear'],variant=name,
                survive3=sum(len(r)==3 and r[-1]['result']['win'] for r in routes)/64)
            for node in (2,3):
                entered=[r[node-1] for r in routes if len(r)>=node]
                probe[f'entered{node}']=len(entered);probe[f'conditional_wr{node}']=sum(q['result']['win'] for q in entered)/len(entered) if entered else None
            probes.append(probe)
    for name,rows in {'stage25_cases.csv':stage_cases,'stage25_states.csv':stage_states,'hard_cases_96.csv':hard_cases,
        'independent_precision.csv':precision_rows,'three_battle_probes.csv':probes}.items():table(name,rows)
    audit=dict(status='passed',executed_battles=executions,native_journey_battles=native,
        exact_saved_battle_replays=replays,censored_journey_battles=censored,archives=archives,
        source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (Path(__file__),s25.ROOT/'summary.json',hard.ROOT/'calibrate.json',hard.ROOT/'confirm.json',
             hard.ROOT/'baseline_extension.json',OUT/'local25/results.json',OUT/'terminal25/results.json',OUT/'roster25/results.json')})
    atomic_json(OUT/'audit.json',audit)
    report(stage_cases,precision_rows,probes,audit)
    usable=[]
    for capacity,genre,label in ((20,'C_R',None),(25,'C_I','roster25'),(30,'C_R',None)):
        p=next(r for r in precision_rows if r['capacity']==capacity and r['genre']==genre
            and ((label is None and r['point_target']) or r['label']==label))
        if label:
            result=load(OUT/'roster25/results.json');j=result['selected']['job'];c=result['confirmation']
            members=c['members'];enemy=c['enemy'];order=result['selected']['result']['plan']['order']
        else:
            raw=raw_by_key[p['label']];j=raw['job'];members=raw['members'];enemy=raw['enemy'];order=raw['prepared']['0']['plan']['order']
        usable.append(dict(capacity=capacity,genre=genre,scope='specific fixed-roster difficulty reference; not universal NPC',
            baseline=p,macro=j['macro'],npc_genre=j['enemy_genre'],npc_supply=j['profile'],player=members,enemy=enemy,order=order,
            enabled_player_bonds=list(hard.ENABLED),enemy_bonds=[],
            classification='near-even high pressure; not credited as crossing 50%' if capacity==25 else 'low-terminal-margin reference'))
    atomic_json(OUT/'usable_references.json',dict(references=usable,scope='research candidates, exact snapshots'))
    plot(stage_cases,precision_rows,probes)
    print('gaps audit passed',executions,'executions',replays,'exact replays',flush=True)


def report(stage_cases,precision_rows,probes,audit):
    lines=['# 25人后段与高阶段险胜：补测结论','','2026-10-27。旧研究输入保留；25人后段用旧响应校准、48套新人物配置确认。'
        '高阶段固定NPC按真实生成技能供给，玩家实际身份启用已有23项候选效果，敌方羁绊关闭；女仆半量、果实标准。', '',
        f'本轮{audit["executed_battles"]:,}次原生执行（含搜索/配对重复），'
        f'{audit["native_journey_battles"]:,}场真实连战、{audit["exact_saved_battle_replays"]:,}场保存数据精确复演。'
        '额外种子不是额外人物；失败校准、96场边缘结果及独立种子反证均保留。', '',
        '## 25人后段建议', '',
        '前6胜保留温和档：65%概率、0.5%＋2.5%×承伤压力。第7胜后单次损耗仍为8%＋20%×承伤压力，'
        '触发概率由65%提高到85%。P=min(1,累计实际承伤/有效上限)。本轮只改旅行减益概率，不改技能或敌方。', '',
        '| 对照 | 前6战完整存活 | 抵达第20战 | 抵达第30战 | 30战内到50%的预测覆盖 |',
        '| --- | --- | --- | --- | --- |']
    names={'control':'无损耗','old':'旧分段65%后段','revised':'新85%后段','full_reset':'6战全清＋重置计程',
           'clear_only':'6战仅全清','half_only':'6战补回50%缺失上限'}
    for name,title in names.items():
        rr=[r for r in stage_cases if r['variant']==name]
        h=[r for r in rr if r['half_forecast']is not None]
        coverage=f'{sum(r["half_forecast"]<=30 for r in h)/len(h):.1%}' if h else '未单列预测'
        lines.append(f'| {title} | {mean(rr,"s6"):.1%} | {mean(rr,"reach20"):.1%} | {mean(rr,"reach30"):.1%} | {coverage} |')
    lines+=['','“到50%”是独立战斗响应的加权路径预测，与原生抵达率分开。'
        '全清与重置计程已拆开比较，因此不能把完整休息全部收益归因于回复上限。'
        '固定第6胜免费补给仅是对照，未确定正式位置/资源成本。', '',
        '## 真实终局低余量的独立复核', '',
        '以下是追加独立种子的全部复核结果；目标沿用胜率点估计>50%且获胜后平均余量<=20%。'
        '另列胜率Wilson95%下界与胜后平均余量近似95%上界，避免96场边缘点被当作稳定通过。', '',
        '| 人数 | 流派 | 装备 | 种子数 | 胜率 | 胜率95%下界 | 胜后余量 | 余量均值95%上界 | 原目标点估计通过 |',
        '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for r in precision_rows:
        gear='普通' if r['gear']=='basic' else '四顶级'
        lines.append(f'| {r["capacity"]} | {r["genre"]} | {gear} | {r["trials"]} | {r["wr"]:.1%} | {r["wr_wilson95_low"]:.1%} | {r["winning_hp"]:.1%} | {r["winning_hp_mean95_high"]:.1%} | {"是" if r["point_target"] else "否"} |')
    lines+=['','95%区间针对同一固定人物/技能/敌方与顺位下的随机对战，不是玩家总体置信区间。'
        '25人局部参数和扩大真实阵容属于后续探索，均单独协议/源哈希，不能算主确认自动通过。', '',
        '25人C_I普通装备的2048种子结果为约49%胜率、约20%胜后余量，可定位为“均势高压参考”。'
        '严格大于50%是本研究用于避免错误归因的筛选门槛，不是必须强迫所有困难场景满足的产品规则。'
        '该参考不计入“原本高于50%、因减益降到50%”验证，已有危险和减益新增危险分开报告。', '',
        '## 两三战的补给压力', '',
        '| 参考（25人为均势高压） | 无损耗连赢3战 | 即时损耗连赢3战 | 温和前段连赢3战 | 即时损耗第二战条件胜率 |',
        '| --- | --- | --- | --- | --- |']
    for r in precision_rows:
        if not r['point_target'] and r['label']!='roster25':continue
        rr={p['variant']:p for p in probes if p['label']==r['label']}
        if len(rr)!=3:continue
        q=rr['immediate']['conditional_wr2'];qtext=f'{q:.1%}' if q is not None else '无存活样本'
        lines.append(f'| {r["capacity"]}人 {r["genre"]} | {rr["control"]["survive3"]:.1%} | {rr["immediate"]["survive3"]:.1%} | {rr["grace"]["survive3"]:.1%} | {qtext} |')
    lines+=['','连赢3战概率与第三战单场胜率不是同一指标；本来就低于50%的参考不会算作减益成果。'
        '每组64条路径，第二/三战条件率的分母是实际存活者，尾部样本较少。'
        '这些结果支持把“轻松出行前段”与“危险地区即时压力”作为不同投放候选；'
        '不能将前6战温和规则无条件套入所有高难地区。', '',
        '[25人逐格](results/report/stage25_cases.csv)、[全部96场高难参考](results/report/hard_cases_96.csv)、'
        '[独立精度核对](results/report/independent_precision.csv)、[三战对照](results/report/three_battle_probes.csv)、'
        '[三阶段可复现NPC与玩家快照](results/usable_references.json)。', '',
        '![补测结果](results/report/gaps_summary.png)', '',
        '本轮仍未修改Unity、实际奖励或钱包。固定NPC参数和真实技能快照在results/hard_regions/；'
        '针对具体流派/编成找到的困难场景不代表全流派统一难度。']
    (HERE/'DESIGN_GUIDE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def plot(stage_cases,precision_rows,probes):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    font=FontProperties(fname='C:/Windows/Fonts/msyh.ttc')
    fig,axes=plt.subplots(1,2,figsize=(12,4.8))
    variants=('old','revised','full_reset','clear_only');labels=('旧后段','85%后段','全清＋重置','仅全清')
    axes[0].bar(range(4),[mean([r for r in stage_cases if r['variant']==v],'reach20') for v in variants])
    axes[0].set_xticks(range(4),labels,fontproperties=font);axes[0].set_title('25人：抵达第20战的真实概率',fontproperties=font)
    chosen=[next(r for r in precision_rows if r['capacity']==20 and r['genre']=='C_R' and r['point_target']),
        next(r for r in precision_rows if r['label']=='roster25'),
        next(r for r in precision_rows if r['capacity']==30 and r['genre']=='C_R' and r['point_target'])]
    for offset,(name,label) in enumerate((('control','无损耗'),('immediate','即时损耗'),('grace','温和前段'))):
        values=[next(p['survive3'] for p in probes if p['label']==r['label'] and p['variant']==name) for r in chosen]
        axes[1].bar([i+(offset-1)*.25 for i in range(3)],values,width=.25,label=label)
    axes[1].set_xticks(range(3),['20人 C_R','25人 C_I','30人 C_R'],fontproperties=font)
    axes[1].set_title('具体高压参考：连赢3战概率',fontproperties=font);axes[1].legend(prop=font)
    for ax in axes:ax.set_ylim(0,1.03);ax.grid(axis='y',alpha=.2)
    fig.tight_layout();fig.savefig(REPORT/'gaps_summary.png',dpi=160);plt.close(fig)


if __name__=='__main__':main()
