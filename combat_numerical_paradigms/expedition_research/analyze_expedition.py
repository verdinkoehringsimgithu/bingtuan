"""Native survivor curves, independent-response forecasts and loot sensitivities."""
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import measure_response as lab
from run_bonds import atomic_json

ROOT=lab.OUT
OUT=ROOT/'report'


def table(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def model(prepared,profile):
    probability=[];hp=[];exposure=[];counts=[]
    width=max(len(prepared[f'{profile}:{x}']['trials']) for x in lab.GRID)
    for x in lab.GRID:
        p=prepared[f'{profile}:{x}'];wins=[r for r in p['trials'] if r['win']]
        probability.append(p['metrics']['win']);counts.append(len(wins))
        hp.append([r['hp'] for r in wins]+[0.]*(width-len(wins)))
        exposure.append([r['damage_exposure'] for r in wins]+[1.]*(width-len(wins)))
    return dict(p=np.array(probability),hp=np.array(hp),exposure=np.array(exposure),count=np.array(counts),width=width)


def predict(m,policy,stream,dungeon=False,adverse=.5,shock=1.,n=512):
    rng=np.random.default_rng(lab.seed('heldout-prediction',stream));wear=np.zeros(n);weights=np.ones(n);rows=[]
    grid=np.array(lab.GRID);loot=np.zeros(n);earned=0.
    for node in range(1,31):
        mass=float(weights.sum());before_loot=float(np.dot(weights,loot)/n)
        hi=np.searchsorted(grid,wear,side='right').clip(1,len(grid)-1);lo=hi-1
        t=((wear-grid[lo])/(grid[hi]-grid[lo])).clip(0,1)
        p=(1-t)*m['p'][lo]+t*m['p'][hi]
        rows.append(dict(node=node,conditional_wr=float(np.dot(weights,p)/mass) if mass>1e-100 else None,
            reach_probability=mass/n,mean_bp_cap=float(np.dot(weights,np.exp(-lab.PROFILES[policy['profile']][0]*wear))/mass) if mass>1e-100 else None,
            out_of_grid_mass=float(weights[wear>grid[-1]].sum()/n),
            loot_death_keep_0=before_loot,loot_death_keep_half=.5*(earned+before_loot),loot_death_keep_1=earned))
        use_high=rng.random(n)<np.divide(t*m['p'][hi],p,out=np.zeros(n),where=p>0)
        point=np.where(use_high,hi,lo);idx=(rng.random(n)*np.maximum(1,m['count'][point])).astype(int).clip(0,m['width']-1)
        pressure=1-m['hp'][point,idx] if policy['signal']=='end_hp' else m['exposure'][point,idx]
        fight=(rng.random(n)<.7) if dungeon else np.ones(n,dtype=bool)
        event_trigger=rng.random(n)<np.minimum(1.,policy['p0']+policy['p_pressure']*pressure)
        loss=policy['loss0']+policy['loss_pressure']*pressure
        delta=np.where(fight&event_trigger,-np.log1p(-loss),0.)
        if dungeon:
            delta+=np.where((~fight)&(rng.random(n)<adverse),-math.log1p(-(policy['loss0']+policy['loss_pressure']))*shock,0.)
        earned+=float(np.dot(weights,np.where(fight,p,0.))/n)
        weights*=np.where(fight,p,1.);loot+=fight.astype(int);wear+=delta
    return rows


def wilson(wins,n):
    if not n:return None,None
    p=wins/n;z=1.96;den=1+z*z/n;center=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return center-half,center+half


def horizon(rows,key='conditional_wr'):
    return next((r.get('node',r.get('battle')) for r in rows if r[key] is not None and r[key]<=.5),31)


def cohort(baseline):
    wr=baseline['win'];hp=baseline['winning_hp']
    if wr>.5 and hp is not None and hp<=.2:return 'low_margin_above_half'
    if wr>=.95 and (hp is None or hp>.2):return 'dominant'
    if wr<=.5:return 'already_at_or_below_half'
    return 'intermediate'


def main():
    OUT.mkdir(parents=True,exist_ok=True);confirmation=ROOT/'refined/confirmation'
    data=json.loads((confirmation/'summary.json').read_text(encoding='utf-8'))
    native_rows=[];forecasts=[];sensitivity=[];loot_rows=[];return_rows=[];cases=[];actual_censored=0;actual_count=0
    for cell in data['rows']:
        j=cell['job']
        with gzip.open(confirmation/'replicates'/f'{cell["key"]}.json.gz','rt',encoding='utf-8') as f:raw=json.load(f)
        cache={}
        for name,public in cell['result']['variants'].items():
            physical=raw['variants'][raw['variants'][name]['alias']] if 'alias'in raw['variants'][name] else raw['variants'][name]
            policy=public['policy'];baseline=public['baseline'];group=cohort(baseline)
            base=dict(stage=j['stage']+1,capacity=lab.STAGES[j['stage']][0],genre=j['genre'],gear=j['gear'],
                region=j['region'],policy=name,cohort=group,baseline_wr=baseline['win'],baseline_winning_hp=baseline['winning_hp'])
            encoded=json.dumps(policy,sort_keys=True)
            if encoded not in cache:
                m=model(raw['prepared'],policy['profile'])
                path=predict(m,policy,cell['key'])
                variants={(a,s):predict(m,policy,cell['key'],True,a,s,256) for a in (.25,.5,1.) for s in (1.,2.)}
                cache[encoded]=(path,variants)
            path,variants=cache[encoded]
            cases.append({**base,'forecast_half_battle':horizon(path),
                'native_half_battle':horizon(public['travel'],'wr'),
                'reach_battle_30':public['travel'][29]['reach_probability'],
                'reach_boss_at_30':public['dungeon'][29]['reach_probability']})
            for node in range(1,31):
                value=public['travel'][node-1];dd=public['dungeon'][node-1]
                lo,hi=wilson(value['wins'],value['entered'])
                rr=[route['rows'][node-1] for route in physical['travel'] if len(route['rows'])>=node]
                censored=sum(q['result']['censored'] for q in rr)
                if 'alias'not in raw['variants'][name]:actual_censored+=censored;actual_count+=len(rr)
                native_rows.append({**base,'battle':node,'entered':value['entered'],'wins':value['wins'],'censored':censored,
                    'conditional_wr':value['wr'],'upper_if_all_censored_win':(value['wins']+censored)/value['entered'] if value['entered'] else None,
                    'seed_wilson95_low':lo,'seed_wilson95_high':hi,
                    'reach_probability':value['reach_probability'],'mean_bp_cap':value['mean_bp_cap'],
                    'no_debuff_reach':baseline['win']**(node-1),'dungeon_reach':dd['reach_probability'],
                    'no_debuff_dungeon_reach':(.3+.7*baseline['win'])**(node-1)})
                forecasts.append({**base,**path[node-1]})
                for (adverse,shock),trajectory in variants.items():
                    sensitivity.append({**base,'adverse_given_event':adverse,'shock_multiplier':shock,**trajectory[node-1]})
            for at in (10,20,30):
                payouts={g:[] for g in (0.,.5,1.)}
                for route in physical['dungeon']:
                    earned=sum(r.get('result',{}).get('win',0) for r in route['rows'] if r['node']<at)
                    alive=len(route['rows'])>=at
                    for gamma in payouts:payouts[gamma].append(earned if alive else gamma*earned)
                for gamma,values in payouts.items():
                    loot_rows.append({**base,'boss_entry_node':at,'death_loot_retention_assumption':gamma,
                        'expected_retained_won_battles_proxy':sum(values)/len(values)})
            for outward in (2,3,5,8,10,12,15):
                for ratio in (0.,.5,1.):
                    back=math.ceil(outward*ratio);total=outward+back
                    if total>30:continue
                    at_turn=public['travel'][outward-1]['wins']/128
                    at_home=public['travel'][total-1]['wins']/128
                    return_rows.append({**base,'outward_battles':outward,'return_battles':back,
                        'return_encounter_ratio_assumption':ratio,'survive_outward':at_turn,
                        'whole_round_trip_survival':at_home,
                        'conditional_return_survival':at_home/at_turn if at_turn else None,
                        'no_debuff_conditional_return':baseline['win']**back})
    table(OUT/'native_travel_curves.csv',native_rows);table(OUT/'heldout_response_forecasts.csv',forecasts)
    table(OUT/'dungeon_event_sensitivity.csv',sensitivity);table(OUT/'dungeon_loot_sensitivity.csv',loot_rows)
    table(OUT/'return_trip_sensitivity.csv',return_rows)
    table(OUT/'case_horizons.csv',cases)
    stage=[]
    for s in range(1,7):
        for name in ('global_policy','stage_policy'):
            for group in ('dominant','low_margin_above_half','intermediate','already_at_or_below_half'):
                rows=[r for r in cases if r['stage']==s and r['policy']==name and r['cohort']==group]
                if not rows:
                    stage.append(dict(stage=s,capacity=lab.STAGES[s-1][0],policy=name,cohort=group,cases=0,
                        mean_forecast_half_battle=None,median_forecast_half_battle=None,
                        within_30_fraction=None,within_3_fraction=None,reach_battle_30=None,reach_boss_at_30=None))
                    continue
                stage.append(dict(stage=s,capacity=lab.STAGES[s-1][0],policy=name,cohort=group,cases=len(rows),
                    mean_forecast_half_battle=sum(r['forecast_half_battle'] for r in rows)/len(rows),
                    median_forecast_half_battle=float(np.median([r['forecast_half_battle'] for r in rows])),
                    within_30_fraction=sum(r['forecast_half_battle']<=30 for r in rows)/len(rows),
                    within_3_fraction=sum(r['forecast_half_battle']<=3 for r in rows)/len(rows),
                    reach_battle_30=sum(r['reach_battle_30'] for r in rows)/len(rows),
                    reach_boss_at_30=sum(r['reach_boss_at_30'] for r in rows)/len(rows)))
    table(OUT/'stage_horizons.csv',stage)
    regions=[]
    for s in range(1,7):
        for region in ('dominant','comfortable','hard','very_hard','clutch','low_margin'):
            rr=[r for r in cases if r['stage']==s and r['region']==region and r['policy']=='global_policy']
            regions.append(dict(stage=s,capacity=lab.STAGES[s-1][0],region=region,
                baseline_wr=sum(r['baseline_wr'] for r in rr)/len(rr),
                baseline_winning_hp=sum(r['baseline_winning_hp'] or 0 for r in rr)/len(rr),
                travel_30_reach=sum(r['reach_battle_30'] for r in rr)/len(rr),
                boss_entry_30_reach=sum(r['reach_boss_at_30'] for r in rr)/len(rr)))
    table(OUT/'regions_by_stage.csv',regions)
    thresholds=[]
    for loot in (1,3,5,10,20):
        for retention in (0.,.5,1.):
            x=(1-retention)*loot
            thresholds.append(dict(accumulated_loot_units=loot,next_fight_loot_units=1,
                defeat_retention_assumption=retention,one_fight_continue_break_even_win_rate=x/(1+x)))
    table(OUT/'retreat_break_even.csv',thresholds)
    selected=json.loads((ROOT/'refined/selected_policies.json').read_text(encoding='utf-8'))
    report(data,cases,stage,regions,selected,actual_count,actual_censored,return_rows)
    plot(native_rows,forecasts)
    sources=[confirmation/'summary.json',ROOT/'refined/selected_policies.json',Path(__file__)]
    sources += [p for p in (ROOT/'recovery_stress/summary.json',ROOT/'recovery_stress/stage_summary.csv',
        lab.HERE/'analyze_recovery.py') if p.exists()]
    atomic_json(OUT/'provenance.json',dict(sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        confirmation_signature=data['signature'],rows=dict(native_curves=len(native_rows),forecasts=len(forecasts),
        dungeon_sensitivity=len(sensitivity),loot_sensitivity=len(loot_rows),return_sensitivity=len(return_rows),cases=len(cases),stage=len(stage),regions=len(regions)),
        physical_actual_travel_battles=actual_count,censored_physical_travel_battles=actual_censored))
    print('expedition report generated:',len(cases),'policy cases;',actual_count,'native travel encounters;',actual_censored,'censored')


def report(data,cases,stages,regions,selected,actual_count,censored,return_rows):
    lines=['# 旅行与副本长期减益设计规范', '',
        '2026-10-22。正式口径：战后当前战力回满当前有效上限，长期减益保留；主动中途撤退保留全部战利品。'
        '不通过携带残血制造损耗。技能次数与战内临时状态每战按原引擎重建。', '',
        '## 可以使用的参数基准', '',
        '主矩阵定标候选：每次获胜后65%概率获得一次长期战力上限减损；损失比例为8%+20%×(1−获胜后战力比例)。'
        '每次按当前有效上限乘算。普通治疗仍能回满受限上限，完整休息清除长期减益作为研究对照；补给实际清除多少、消耗多少尚未定稿。', '',
        '例如满血获胜时，触发后上限乘0.92；10%剩余战力获胜时，触发后上限乘0.74。'
        '战后自动回满并不会恢复上限。敌人的战力与四维始终保持固定，不读取玩家减益来反向追平。', '',
        '只降低四维上限不能稳定限制优势队伍：在所测优势地区，四维仅保留约1.5%时，平均仍有82.6%获胜率；'
        '相同强度的战力上限减损则全部无法获胜。战力上限适合作为共通续航控制，四维作为地区差异或辅助。'
        '该结论来自实际技能和装备的反应，不等于所有四维减益在每种构筑里都弱。', '',
        '主矩阵未开启身份羁绊。面向含恢复羁绊的版本，优先用“min(1,本场实际累计承伤/本场有效战力上限)”'
        '替代终局损失比例作为压力信号，保留65%触发和8%＋20%压力降幅作为接入候选。'
        '恢复补测使用两档女仆长复合预算与农民果实，已进行配对原生连战；这个建议不等于混合羁绊已全部验证。'
        '两种信号的数据分开，下面主矩阵表仍是终局血量口径，不能直接冒充累计承伤版的六阶段结果。', '',
        '## 六阶段补给压力', '',
        '下表按独立人物/技能库确认：优势参考指初始获胜率至少95%且并非低余量胜利；'
        '险胜参考指初始获胜率高于50%，且获胜后的平均余量不超过20%。已经低于50%的遭遇单列，不能把原本就难打归功于减益。', '',
        '能力衰减战数来自独立真实战斗响应上的加权路径预测，保存真实连战到达率作核对。'
        '加权路径保留连续获胜的条件分布，避免到后期仅剩少量幸存者导致曲线失真；它仍有网格插值误差，不能宣称每条路径必定在该战数回城。', '',
        '| 人数上限 | 参考构筑 | 样本配置数 | 降到约50%的战数中位数 | 30战内比例 | 3战内比例 | 真实抵达第30战 |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    for r in stages:
        if r['policy']!='global_policy' or r['cohort']not in ('dominant','low_margin_above_half'):continue
        name='优势' if r['cohort']=='dominant' else '残血险胜'
        if not r['cases']:
            lines.append(f'| {r["capacity"]} | {name} | 0 | 未覆盖 | — | — | — |')
            continue
        value='>30' if r['median_forecast_half_battle']>30 else f'{r["median_forecast_half_battle"]:g}'
        lines.append(f'| {r["capacity"]} | {name} | {r["cases"]} | {value} | {r["within_30_fraction"]:.1%} | {r["within_3_fraction"]:.1%} | {r["reach_battle_30"]:.1%} |')
    lines+=['', '20/25/30人本轮没有同时满足“初始胜率高于50%＋胜后余量不超过20%”的确认样本，'
        '其残血险胜两三战目标尚未证实；固定高难参考仍已测试，参照名不能代替这个条件。', '',
        '不能保证所有初始阵容都落在同一战数：收集、装备、恢复、技能顺位仍然有意义。'
        '31代表在本轮30战观测窗内尚未到50%，不是实际在第31战达到。'
        '每个构筑128条真实旅行路径；每战顺位取对应减益状态附近的独立搜索结果，5人训练穷举120排列，较大队伍有限搜索，不保证全局最优。', '',
        '阶段专用候选亦已保存，独立确认中的达标比例见末列，未全部胜过通用候选。'
        '例如30人专用候选更温和，只有约三分之二优势参考在30战内降到50%；不能把校准入选当作最终目标达标。'
        '这些阶段候选仍来自无羁绊主矩阵。', '',
        '| 人数 | 长期减益对象 | 触发基础概率 | 压力指标 | 基础降幅 | 压力附加降幅 | 优势参考30战内比例 |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    for s in range(6):
        p=selected['stage_policies'][str(s)];name={'bp_only':'战力上限','stats_only':'四维','mixed':'战力＋半强度四维'}[p['profile']]
        signal='胜后损失比例' if p['signal']=='end_hp' else '承伤/上限（封顶1）'
        measured=next(r for r in stages if r['stage']==s+1 and r['policy']=='stage_policy' and r['cohort']=='dominant')
        lines.append(f'| {lab.STAGES[s][0]} | {name} | {p["p0"]:.0%} | {signal} | {p["loss0"]:.1%} | {p["loss_pressure"]:.0%} | {measured["within_30_fraction"]:.1%} |')
    lines+=['', '## 强恢复构筑与压力信号', '',
        '额外216格、623,767次执行，包含292,279场真实连战；女仆长半量/全量复合预算、农民标准果实，'
        '每格两种信号各64条路线。25人阶段的优势样本中，女仆长全量预算抵达第30战的比例，'
        '终局血量信号为25.1%，累计承伤信号为9.4%；农民为10.4%与0%。'
        '累计承伤能识别“战中消耗大、结束时又回满”的情形，同时保留恢复技能延长旅程的价值。', '',
        '抵达第30战与第30战单场胜率不同。补测同时保存独立战斗响应的能力衰减预测，'
        '逐阶段与复合预算见[恢复羁绊专表](RECOVERY_STRESS.md)。强构筑仍可能走得更远，'
        '现系数是设计起点，不是对全部阵容的硬性30战保证。']
    lines+=['', '## 回头还需要能走回补给点', '',
        '30战内衰减是连续战斗标尺，不是安全单程可走30战。若返程经过同一类地区、遭遇数与去程相同，'
        '走出去m战再走回m战，共要承受2m战减益。下表在优势构筑中条件于已经完成去程，给出实际回程成功率；'
        '不假设免费传送或到达危险状态后自动回城。', '',
        '| 人数 | 去程3战后返程3战 | 去程5战后返程5战 | 去程8战后返程8战 |',
        '| --- | --- | --- | --- |']
    for s in range(1,7):
        values=[]
        for m in (3,5,8):
            rr=[r for r in return_rows if r['stage']==s and r['policy']=='global_policy' and r['cohort']=='dominant'
                and r['outward_battles']==m and r['return_encounter_ratio_assumption']==1.]
            den=sum(r['survive_outward'] for r in rr)
            values.append(f'{sum(r["whole_round_trip_survival"] for r in rr)/den:.1%}' if den else '—')
        lines.append('| '+' | '.join([str(lab.STAGES[s-1][0])]+values)+' |')
    lines+=['', '各列分别条件于已经完成对应去程，因此更远一列可能只剩少量强构筑，出现条件返程率回升。'
        '这属于幸存者选择，不能解释为走得更远反而安全。', '',
        '返程遭遇为去程0/一半/相同三种假设的全表已保存。实际地图路线、遭遇与补给点确定后再换成真实分布。'
        '这组通用参数对部分阶段的往返路线很严厉，不能把“单场降到50%”直接当作安全返程提示时点。'
        '正式地图先按往返遭遇量确定补给间隔与损耗强度。完整休息作为补给点的状态重置参照；'
        '地点、资源消耗与是否可携带清除方式尚待接入大地图规则。']
    lines+=['', '## 副本深入与途中收益', '',
        '沿用70%战斗、30%事件；主确认中半数事件产生不利后果，即全部节点约15%是减益事件。'
        '一次不利事件按当前策略的最大单次降幅生效，通用候选为上限乘0.72。其他事件本轮不添加额外效果。'
        '另用已测战斗响应预测事件不利比例25%/50%/100%及冲击强度1/2倍，见敏感性表；'
        '这些敏感性组合不是各自重新执行的原生副本连战。', '',
        '把Boss安排在第10/20/30节点时，入口指标分别是抵达该节点的概率；'
        '之前9/19/29个节点是普通流程。本研究不把第30个普通模拟战斗算成Boss胜利，也不靠最后一战失败来限制途中搜刮。', '',
        '| 人数 | 固定地区参照 | 初始胜率 | 真实抵达第30战 | 抵达第30节点Boss入口 |',
        '| --- | --- | --- | --- | --- |']
    labels={'dominant':'优势参照','comfortable':'顺畅参照','hard':'难','very_hard':'很难','clutch':'高难参照','low_margin':'快速威胁参照'}
    for r in regions:
        lines.append(f'| {r["capacity"]} | {labels[r["region"]]} | {r["baseline_wr"]:.1%} | {r["travel_30_reach"]:.1%} | {r["boss_entry_30_reach"]:.1%} |')
    lines+=['', '初始参照名称不是对每个流派胜率或剩余血量的保证；存在回血与先机差异，实际数据已逐构筑输出。'
        '副本入口到达率降低，只说明无补给持续深入受到限制；无法单独证明玩家会主动撤退。'
        '途中收益暂用已经通过的普通战斗数作无价格代理，未设定真实掉率、金币或事件奖励。', '',
        '## 战利品结算决定撤退动机', '',
        '主动撤退保留全部战利品已确认。战败后保留比例尚未定，故仅列0/50%/100%敏感性，不新增掉落规则。'
        '若已有战利品价值L，下一战收益R，战败保留比例g，只考虑再打一战后退出，则继续的盈亏平衡胜率为'
        'p=(1−g)L/[R+(1−g)L]。这是单步比较，不是考虑所有未来奖励后的全局最优撤退策略。', '',
        '例如L=5R：战败全失时约83.3%才值得再战；战败保留一半时约71.4%；战败也全保留且无其他成本时，'
        '任何正胜率都仍有继续的收益。后一条件下，仅用减益能限制抵达深处的概率，不能制造纯收益上的主动撤退动机。'
        '实际掉落价值、Boss奖励、旅行时间和战败结算确定后，再算经济最优退出点。', '',
        '## 概率尾部与休息', '',
        '65%独立触发模型存在连续不触发：前两次均不触发约12.25%，前三次均不触发约4.29%。'
        '因此“多数险胜路径两三战产生压力”与“任何玩家第三战必退”不同。若产品要求硬性上限，需要另选每战基础损耗、'
        '严重消耗后保证触发或最长未触发保障；本轮没有把这些尚未确认的规则偷偷加入正式模型。', '',
        '完全休息应恢复上限并回满；一般回血只恢复当前战力。部分补给可按清除长期log损耗的比例作为可调参数，'
        '本轮未确定道具种类、售价、背包消耗与地图距离。30场战斗不等于30格，路程还需遭遇频率。', '',
        '## 复现与证据', '',
        f'正式修订确认矩阵{data["cells"]}格，执行{data["executed_battles"]:,}次原生战斗（含顺位准备与真实连战）。'
        f'实际旅行记录中{actual_count:,}场战斗有{censored}场120回合未结束；胜率表保留删失上界，未将超时冒充已知战败。', '',
        '- [全部逐格真实连战曲线](results/report/native_travel_curves.csv)、[独立响应路径预测](results/report/heldout_response_forecasts.csv)。',
        '- [六阶段压力分布](results/report/stage_horizons.csv)、[全部地区与难度](results/report/regions_by_stage.csv)。',
        '- [副本事件敏感性](results/report/dungeon_event_sensitivity.csv)、[战败战利品保留敏感性](results/report/dungeon_loot_sensitivity.csv)、[单步退出平衡点](results/report/retreat_break_even.csv)。',
        '- [往返遭遇敏感性](results/report/return_trip_sensitivity.csv)。',
        '- [候选参数与来源](results/refined/selected_policies.json)、[用户要求和研究边界](requirements.json)。',
        '- 原始逐场顺位、种子、损耗、事件与部分时序在`results/refined/confirmation/replicates/`。', '',
        '![旅行与副本压力](results/report/expedition_pressure.png)', '',
        '本轮研究层不修改Unity、生成器、人物标签、奖励或钱包。更换遭遇密度、加入混合羁绊或指定补给经济后，需要沿同一协议继续验证。']
    (lab.HERE/'DESIGN_GUIDE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def plot(native,forecasts):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    font=FontProperties(fname='C:/Windows/Fonts/msyh.ttc')
    plt.rcParams['axes.unicode_minus']=False
    fig,axes=plt.subplots(2,2,figsize=(13,8.8));colors={'dominant':'#2474b5','low_margin_above_half':'#cf633c'}
    names={'dominant':'优势参考','low_margin_above_half':'险胜参考'}
    for group,color in colors.items():
        a=[r for r in native if r['policy']=='global_policy' and r['cohort']==group]
        b=[r for r in forecasts if r['policy']=='global_policy' and r['cohort']==group]
        if not a:continue
        x=range(1,31);wr=[];reach=[];dungeon=[];control=[];cap=[]
        for k in x:
            rr=[r for r in a if r['battle']==k];pp=[r for r in b if r['node']==k]
            n=sum(r['entered'] for r in rr)
            wr.append(sum(r['wins'] for r in rr)/n if n else np.nan)
            reach.append(sum(r['reach_probability'] for r in rr)/len(rr))
            dungeon.append(sum(r['dungeon_reach'] for r in rr)/len(rr))
            control.append(sum(r['no_debuff_reach'] for r in rr)/len(rr))
            available=[(r['mean_bp_cap'],r['reach_probability']) for r in pp if r['mean_bp_cap']is not None]
            den=sum(weight for _,weight in available)
            cap.append(sum(value*weight for value,weight in available)/den if den else np.nan)
        axes[0,0].plot(x,wr,color=color,label=names[group]);axes[0,1].plot(x,reach,color=color,label=names[group])
        axes[0,1].plot(x,control,color=color,linestyle='--',alpha=.5)
        axes[1,0].plot(x,dungeon,color=color,label=names[group]);axes[1,1].plot(x,cap,color=color,label=names[group])
    titles=['真实连战：幸存者当次获胜率','抵达下一战概率（虚线：无长期减益）','抵达副本节点 / Boss入口概率','独立响应预测：幸存者有效战力上限']
    for ax,title in zip(axes.flat,titles):
        ax.set_title(title,fontproperties=font,fontsize=12);ax.set_xlabel('战斗序号 / 副本节点',fontproperties=font)
        ax.set_ylim(0,1.05);ax.grid(alpha=.2);ax.legend(prop=font,fontsize=9)
    axes[0,0].axhline(.5,color='#777',linestyle=':',linewidth=1)
    fig.suptitle('六阶段通用候选：每战回满有效上限，长期减益保留',fontproperties=font,fontsize=15)
    fig.tight_layout(rect=(0,0,.99,.96));fig.savefig(OUT/'expedition_pressure.png',dpi=160);plt.close(fig)


if __name__=='__main__':main()
