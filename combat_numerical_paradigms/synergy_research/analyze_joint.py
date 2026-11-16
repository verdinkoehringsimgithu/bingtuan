"""Summarize independently confirmed identity/skill/equipment and counter data."""
import argparse
from collections import defaultdict
import csv
import gzip
import hashlib
import json
from pathlib import Path
import statistics

import numpy as np
from settings import HERE, CN, IDENTITIES, DEFAULTS
from run_bonds import atomic_json

POLICY_CN={'random':'随机','repeatable':'重复出手','throughput':'吞吐','matched':'全队身份适配'}
DIFFICULTY={'hard':'困难','extremely_hard':'非常难'}
CAST_GEAR={'skill_damage','skill_pierce','skill_crit','skill_heal','skill_dot','cast_ramp','extra_use','overheal_shield'}
SUPPLY_RULES={
    'academy':'按老师实际基础直伤与学生等级总和核算；恢复技能也按既有攻击管线测试。学生经验另做经济标定。',
    'military':'保留能多次实际释放的攻击技能；强制命中只属于军人技能，按人数上限占比核算。',
    'mage':'同时保留相同原生属性连续释放、两种属性交替的选择；不要只追求单个最高倍率。',
    'cult':'必须保留低阶教徒与高阶技能的阶差；低阶预算与高阶出手收益分开记账。',
    'fighter':'主要价值随回合增长，整队技能提升与羁绊额外收益须拆开。',
    'hunter':'按折前直伤与未来真伤兑现量定价；不能把已排期真伤全部当作本回合收益。',
    'heroine':'保留多人完成首次施法的路线，有限次技能可让出顺位；重复同一位不能继续叠首次层。',
    'maid':'女仆长原技能的概率/限次/门槛不决定替代技能；关键是其前方释放完毕的节奏。装备应按替代后的技能检查。',
    'lady':'前排强化位置给实际输出技能，不能只看原角色阶位；所有候选仍需重新排阵。',
    'scholar':'需要前方队友实际消耗有限次数；学者可重复出手和恢复目标可用性一起检查。',
    'sage':'保留可施加负面的技能，同时覆盖敌方负面压力；普通无负面场不能单独用于定价。',
    'engineer':'保留能实际反复施法的候选；属性装备即使装备者未出手也计入基数，增长下回合起生效。',
    'sword':'至少两名剑士，完整追加技能需有剩余次数与合法条件；重复施法与有限次高收益都应保留。',
    'ninja':'保留可重复施法候选；开局闪避与施法后下回合增长分开核算，受既有上限约束。',
    'adventurer':'目标覆盖依赖暴击、恢复、流失、负面等实际事件；高吞吐不保证完成更多目标。',
    'sailor':'身份多样性提供开局属性；无需为了被动生效把水手固定放前排。',
    'gang':'替代为普通攻击后，原技能倍率和子效果不再生效；实际出手概率与普通攻击装备更相关。',
    'merchant':'开局一次性补最低属性，不依赖行商出手；装备应优先看全队预算和真实机制适配。',
    'farmer':'共用果实需经历播种、加速、成熟、收获；保留稳定出手机会，不按每人独立果实计收益。',
    'thief':'攻击机会决定本场四维转移次数，需同时记录目标属性下降后的边际变化。',
    'rich':'攻击产生本场金币与减伤，保留重复出手机会；战后金币仍需独立经济标定。',
    'worker':'一次保命不要求社畜施法；不能把技能自身提升全部归给保命机制。',
    'killer':'保留命中且能持续施放的技能；减疗只作用于对手下一次技能，注意其是否真正恢复。',
}


def avg(xs):
    xs=list(xs);return statistics.mean(xs) if xs else 0.


def write_csv(path, rows):
    if not rows:return
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def physical(raw,entry):
    return raw['variants'][entry['alias']] if 'alias' in entry else entry


def trials_mean(rows,field,namespace=None):
    return avg((r[namespace].get(field,0.) if namespace else r[field]) for r in rows)


def diagnostic(rows, roster, plan, enemy, max_bp):
    arranged=[roster[i] for i in plan['order']]
    cast_items=[i for i,m in enumerate(arranged) if m['item']['top'] and m['item']['kind'] in CAST_GEAR]
    unused=avg(avg(r['owner_casts'][i]==0 for i in cast_items) for r in rows) if cast_items else 0.
    damage=max(1e-9,trials_mean(rows,'hunter_scheduled','metrics'))
    return dict(cast_gear_count=len(cast_items),uncast_cast_gear_fraction=unused,
        skill_casts=trials_mean(rows,'skill_casts','metrics'),
        force_hit=trials_mean(rows,'force_hit','metrics'),absolute_dodges=trials_mean(rows,'absolute_dodges','enemy_metrics'),
        killer_marks=trials_mean(rows,'killer_marks','metrics'),
        prevented_request_fraction=trials_mean(rows,'enemy_prevented_request_fraction'),
        enemy_heal_fraction=avg(sum(r['enemy_metrics'].get(k,0.) for k in ('self_heal','lifesteal','macro_heal'))/max_bp for r in rows),
        hunter_realized_fraction=trials_mean(rows,'hunter_true','metrics')/max_bp,
        hunter_realized_to_scheduled=trials_mean(rows,'hunter_true','metrics')/damage,
        engineer_casts=trials_mean(rows,'engineer_casts','metrics'),
        ninja_casts=trials_mean(rows,'ninja_casts','metrics'),
        scholar_restored=trials_mean(rows,'scholar_restored','metrics'),
        fruit_harvest=trials_mean(rows,'fruit_harvest','metrics'),
        sword_extras=trials_mean(rows,'sword_extras','metrics'),
        enemy_debuff_damage_fraction=avg(sum(r['enemy_metrics'].get(k,0.) for k in ('max_dot','lost_dot','fixed_dot'))/sum(m['bp'] for m in roster) for r in rows))


def raw_cells(out,phase):
    data=json.loads((out/(phase+'.json')).read_text(encoding='utf-8'))
    for cell in data['rows']:
        with gzip.open(out/'replicates'/(cell['key']+'.json.gz'),'rt',encoding='utf-8') as f:raw=json.load(f)
        yield cell,raw


def counters(out):
    rows=[]
    for cell,raw in raw_cells(out,'counters'):
        j=cell['job'];entry=raw['variants'][0];metrics={}
        common=dict(stage=j['stage']+1,capacity=(j['stage']+1)*5,bond=j['bond'],identity=CN[j['bond']],genre=j['genre'],difficulty=j['difficulty'],count=j['count'])
        for o,enemy in zip(entry['outcomes'],raw['enemies']):
            max_bp=sum(m['bp']+m['item']['bp'] for m in enemy['members'])*enemy['macro'][0]
            d=diagnostic(o['trials']['on'],entry['snapshot'],o['plans']['on'],enemy,max_bp)
            metrics[o['name']]={**{f'{k}_wr':o['metrics'][k]['win'] for k in ('on','off','off_at_on')},
                'practical_gain':o['differences']['practical']['mean'],'mechanical_gain':o['differences']['mechanical']['mean'],
                'off_censored':o['metrics']['off']['censored'],
                'gain_censor_low':o['differences']['practical']['mean']-o['metrics']['off']['censored'],
                'gain_censor_high':o['differences']['practical']['mean']+o['metrics']['on']['censored'],
                'censored':o['metrics']['on']['censored'],'turns':o['metrics']['on']['turns'],**d}
            metrics[o['name']]['off_enemy_absolute_dodges']=trials_mean(o['trials']['off'],'absolute_dodges','enemy_metrics')
            trace=o['traces']['on'][0]
            metrics[o['name']]['trace_enemy_negative_skill_casts']=sum(
                t['e_owner'] is not None and t['e_metrics'].get('skill_casts',0)>0 and
                enemy['members'][t['e_owner']]['skill']['sub_effect_name'] in
                ('虚弱压制','四维削弱','最大流失','已损流失','固定流失') for t in trace)
        control,challenge=metrics['control'],metrics['challenge']
        rows.append({**common,**{f'{state}_{k}':v for state,m in metrics.items() for k,v in m.items()},
                     'interaction':challenge['practical_gain']-control['practical_gain']})
    write_csv(out/'counter_evidence.csv',rows)
    return rows


def counter_guide(rows,summary,out):
    import joint_research as lab
    completed=json.loads((out/'counters.json').read_text(encoding='utf-8'))
    validation=json.loads((out/'validation.json').read_text(encoding='utf-8'))['phases']['counters']
    cfg=lab.configs(); lines=['# 身份专门克制场景：六阶段实测','',
        f'2026-10-20；{completed["cells"]}个单元、{completed["executed_battles"]:,}次研究执行，含{validation["heldout_executions"]:,}次最终配对确认执行。已按保存种子精确复现{validation["replayed"]}场及其逐回合遥测。6阶段、6流派、困难/非常难；贤者5人阶段无人物供给。',
        '', '沿用现有候选系数，在双方成员、技能与预算明确的场景里，分别搜索己方开启/关闭羁绊的顺位。以下各格对六流派、两档难度等权平均，不混同为玩家总体胜率。',
        '', '| 身份 | 人数上限 | 身份人数 | 对照收益 | 挑战收益 | 交互差 | 挑战关闭→开启胜率 | 未结束比例 |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for key in ('military','killer','sage','hunter'):
        for s in range(6):
            group=[r for r in rows if r['bond']==key and r['stage']==s+1]
            if not group:continue
            mean=lambda k:avg(r[k] for r in group)
            lines.append(f'| {CN[key]} | {(s+1)*5} | {group[0]["count"]} | {mean("control_practical_gain")*100:+.2f}pp | {mean("challenge_practical_gain")*100:+.2f}pp | {mean("interaction")*100:+.2f}pp | {mean("challenge_off_wr"):.1%}→{mean("challenge_on_wr"):.1%} | {mean("challenge_censored"):.2%} |')
    lines += ['', '## 流派适配','',
        '以下为挑战场开启−关闭的实用收益，跨该身份可用阶段与两档难度等权平均。',
        '', '| 身份 | C_I | C_R | M_I | M_R | M_C | R_I |','| --- | --- | --- | --- | --- | --- | --- |']
    for key in ('military','killer','sage','hunter'):
        cells=[]
        for g in lab.GENRES:
            cells.append(f'{100*avg(r["challenge_practical_gain"] for r in rows if r["bond"]==key and r["genre"]==g):+.2f}pp')
        lines.append('| '+CN[key]+' | '+' | '.join(cells)+' |')
    lines += ['', '猎手在这批样本中与C_I/C_R/R_I的适配好于M_I/M_R/M_C。当前实现按raw_dmg的比例排期，转换段不再走原直接命中的pure-true增幅分支。若该段原伤害为raw×T、转换比例为f，忽略护盾、封顶并假设未来全部兑现，则转后该段合计为raw×[(1−f)T+f]；T>1时本身已有差额，尚未计入延迟代价。未穿透直接命中则可能通过折前转换绕过减伤获益。这是当前“折前转换”候选的明确结算口径，不应误写为所有已是真伤的部分只发生时间平移。',
        '', '这里的构筑对比尚未把所有因素逐一隔离。先保留分流派指导，下一轮再单独测试转换比例和结算时长；不要因为全流派均值不高而统一抬高转换比例。']
    m=summary['military'];k=summary['killer'];s=summary['sage'];h=summary['hunter']
    lines += ['', '## 可直接采用的设计定位','',
        f'军人定位为命中稳定与绝对闪避反制。挑战场开启后胜率增加{m["challenge_practical_gain"]*100:.2f}pp；敌方绝对闪避从每场{m["challenge_off_enemy_absolute_dodges"]:.3f}次变为{m["challenge_absolute_dodges"]:.3f}次。无忍者的对照仍有{m["control_practical_gain"]*100:.2f}pp收益，因为强制命中也会绕过普通闪避。采用人数占上限50%的既有门槛，不将这一效果只按绝对闪避对局定价。',
        '', f'杀手定位为打断下一次恢复，而非常驻减疗。无恢复对照收益为{k["control_practical_gain"]*100:+.2f}pp，恢复挑战120回合内获胜率收益为{k["challenge_practical_gain"]*100:+.2f}pp；若未结束对局的最终胜负完全未知，收益界为[{k["challenge_gain_censor_low"]*100:+.2f}, {k["challenge_gain_censor_high"]*100:+.2f}]pp。每场削减的恢复请求为敌方最大战力的{k["challenge_prevented_request_fraction"]:.2%}。该计数在过量治疗封顶前，不等于实际多扣了同样的血。普通攻击不消耗标记，下一次真实技能即使不回血也会消耗。技能投放应保留高命中、可持续的攻击候选，与对手恢复技能顺序共同定价。',
        '', f'贤者定位为负面效果环境中的双向调节。挑战场收益{s["challenge_practical_gain"]*100:+.2f}pp，高于对照的{s["control_practical_gain"]*100:+.2f}pp；需要将己方负面技能供给与敌方压力同时放进校准。此处敌方更换同阶同原生属性负面技能，不能声称收益只由抗性一项贡献。',
        '', f'猎手定位为延迟兑现的减伤前转换。高坚韧场收益{h["challenge_practical_gain"]*100:+.2f}pp；实际结算真伤为敌方最大战力的{h["challenge_hunter_realized_fraction"]:.2%}/场，各格平均结算/已排期比例{h["challenge_hunter_realized_to_scheduled"]:.2%}。战斗提前结束会使后续真伤来不及发生，应按完整伤害时序测试，不将转换量全部视为即时收益。高坚韧场保持裸四维总预算不变，其他三项同时减少。',
        '', '## 本轮系数起点与真实生效比例','',
        '下表是本轮实测的候选参数及其在本次身份人数下的名义效果，不是新一轮系数寻优结果。人数响应q=n/(n+4)沿用研究候选；猎手3回合、贤者只影响负面幅度等也是已声明测试口径。',
        '', '| 人数上限 | 军人强制命中概率 | 杀手下一技能减疗 | 贤者施加/承受幅度调整 | 猎手折前转换 |',
        '| --- | --- | --- | --- | --- |']
    for stage in range(6):
        values={}
        for key in ('military','killer','sage','hunter'):
            if (stage,key) not in cfg:continue
            c={**DEFAULTS,**cfg[(stage,key)]};n=lab.count_for(stage,key);q=n/(n+c['count_k']);gain=c.get('gain',1.)
            if key=='military':values[key]=f'{min(1,c["military_hit"]*(.25+.75*(2*n/((stage+1)*5)-1))*gain):.2%}'
            elif key=='killer':values[key]=f'{min(1,c["killer"]*q*gain):.2%}'
            elif key=='sage':values[key]=f'+{c["sage_out"]*q*gain:.2%} / −{min(1,c["sage_in"]*q*gain):.2%}'
            else:values[key]=f'{min(1,c["hunter"]*q*gain):.2%}'
        lines.append(f'| {(stage+1)*5} | {values.get("military","—")} | {values.get("killer","—")} | {values.get("sage","—")} | {values.get("hunter","—")} |')
    lines += ['', '下一步优先复核阶段间波动大的格子，并扩充独立人物/技能抽样和人数比例；不要仅按总均值抬高全局系数。恢复NPC使用恢复型女仆长研究候选，其正式效果仍未定。超过120回合未结束单独记为删失，不自动当作敌方获胜。',
        '', '逐格证据[counter_evidence.csv](results/joint/counter_evidence.csv)，汇总[counter_summary.json](results/joint/counter_summary.json)，完整性与重放[validation.json](results/joint/validation.json)。']
    (HERE/'COUNTER_DESIGN_GUIDE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def confirmation(out):
    selected=json.loads((out/'selected_supply.json').read_text(encoding='utf-8'))
    rows=[];variant_rows=[];budget_rows=[];equipment_rows=[]
    for cell,raw in raw_cells(out,'confirm'):
        j=cell['job'];states={}
        base=dict(stage=j['stage']+1,capacity=5*(j['stage']+1),bond=j['bond'],identity=CN[j['bond']],genre=j['genre'],difficulty=j['difficulty'],count=j['count'])
        for entry in raw['variants']:
            v=entry['variant']
            if v.get('scale',1.) != 1.:continue
            p=physical(raw,entry);o=p['outcomes'][0];enemy=raw['enemies'][0]
            max_bp=sum(m['bp']+m['item']['bp'] for m in enemy['members'])*enemy['macro'][0]
            d=diagnostic(o['trials']['on'],p['snapshot'],o['plans']['on'],enemy,max_bp)
            record={**base,**v,'on_wr':o['metrics']['on']['win'],'off_wr':o['metrics']['off']['win'],
                'practical_gain':o['differences']['practical']['mean'],'mechanical_gain':o['differences']['mechanical']['mean'],
                'turns':o['metrics']['on']['turns'],'normal_rate':o['metrics']['on']['normal_rate'],
                'censored':o['metrics']['on']['censored'],**d}
            states[(v['gear'],v['policy'])]=(record,o,p)
        for (gear,policy),(record,o,p) in states.items():
            variant_rows.append(record)
        for gear in ('basic','four_top'):
            policy=selected[f'{j["stage"]}:{j["bond"]}:{gear}']
            b,bo,bp=states[(gear,'random')];c,co,cp=states[(gear,policy)]
            ds=[a['win']-r['win'] for a,r in zip(co['trials']['on'],bo['trials']['on'])]
            mean=avg(ds);se=(sum((x-mean)**2 for x in ds)/(len(ds)-1)/len(ds))**.5
            target=set(IDENTITIES[j['bond']]); own=[m for m in cp['snapshot'] if m['identity'] in target]
            rows.append({**base,'gear':gear,'policy':policy,'random_wr':b['on_wr'],'selected_wr':c['on_wr'],
                         'supply_gain':mean,'paired_roll_se':se,
                         'supply_censor_low':mean-b['censored'],'supply_censor_high':mean+c['censored'],
                         'supply_interaction':c['practical_gain']-b['practical_gain'],
                         'random_bond_gain':b['practical_gain'],'selected_bond_gain':c['practical_gain'],
                         'selected_turns':c['turns'],'selected_normal_rate':c['normal_rate'],
                         'selected_censored':c['censored'],'uncast_cast_gear_fraction':c['uncast_cast_gear_fraction'],
                         'cast_gear_count':c['cast_gear_count'],
                         'skill_casts':c['skill_casts'],'engineer_casts':c['engineer_casts'],'ninja_casts':c['ninja_casts'],
                         'scholar_restored':c['scholar_restored'],'fruit_harvest':c['fruit_harvest'],'sword_extras':c['sword_extras'],
                         'target_mean_chance':avg(m['skill']['trigger_chance'] for m in own),
                         'target_repeatable_fraction':avg(m['skill']['times_limit']>=999 or m['skill']['times_limit']<=0 for m in own),
                         'target_gated_fraction':avg(any(m['skill'][k] for k in ('turn_cond1','turn_cond2','self_bp_cond2','enemy_bp_cond2')) for m in own)})
        for policy_type in ('random','selected'):
            ps={e:('random' if policy_type=='random' else selected[f'{j["stage"]}:{j["bond"]}:{e}']) for e in ('basic','four_top')}
            b=states[('basic',ps['basic'])][0];t=states[('four_top',ps['four_top'])][0]
            equipment_rows.append({**base,'supply_comparison':policy_type,'basic_wr':b['on_wr'],'four_top_wr':t['on_wr'],
                                   'equipment_gain':t['on_wr']-b['on_wr'],'bond_equipment_interaction':t['practical_gain']-b['practical_gain'],
                                   'uncast_cast_gear_fraction':t['uncast_cast_gear_fraction']})
        if j['bond']=='academy' and j['difficulty']=='hard':
            for m in raw['variants'][0]['snapshot']:
                budget_rows.append(dict(stage=j['stage']+1,genre=j['genre'],tier=m['skill']['tier'],level=m['level'],
                    member_stats=sum(m['stats']),common_equipment_stats=sum(m['item']['stats'])))
    write_csv(out/'supply_confirmation_evidence.csv',rows)
    write_csv(out/'joint_variant_evidence.csv',variant_rows)
    write_csv(out/'equipment_confirmation_evidence.csv',equipment_rows)
    write_csv(out/'member_budget_examples.csv',budget_rows)
    return rows,equipment_rows,variant_rows


def cluster_interval(rows,key):
    groups=defaultdict(list)
    for r in rows:groups[(r['stage'],r['genre'])].append(r[key])
    values=np.array([avg(v) for v in groups.values()]);rng=np.random.default_rng(20261020)
    boot=values[rng.integers(0,len(values),size=(2000,len(values)))].mean(axis=1)
    return dict(mean=avg(values),low=float(np.quantile(boot,.025)),high=float(np.quantile(boot,.975)),roster_cells=len(values))


def plot_heatmap(rows,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    fonts={f.name for f in font_manager.fontManager.ttflist}
    plt.rcParams['font.family']=['Microsoft YaHei' if 'Microsoft YaHei' in fonts else 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus']=False
    matrix=np.full((len(IDENTITIES),6),np.nan)
    for i,key in enumerate(IDENTITIES):
        for s in range(1,7):
            group=[r['supply_gain'] for r in rows if r['bond']==key and r['stage']==s and r['gear']=='four_top']
            if group:matrix[i,s-1]=100*avg(group)
    fig,ax=plt.subplots(figsize=(10,12));bound=max(5,float(np.nanmax(abs(matrix))))
    im=ax.imshow(matrix,cmap='RdBu',vmin=-bound,vmax=bound,aspect='auto')
    ax.set(xticks=range(6),xticklabels=['5人','10人','15人','20人','25人','30人'],
           yticks=range(len(IDENTITIES)),yticklabels=[CN[k] for k in IDENTITIES],
           title='身份技能供给：四件顶级装备下独立确认收益（百分点）')
    for (y,x),v in np.ndenumerate(matrix):
        ax.text(x,y,'—' if np.isnan(v) else f'{v:+.1f}',ha='center',va='center',fontsize=9,
                color='white' if abs(v)>bound*.6 else 'black')
    fig.colorbar(im,ax=ax,label='相对随机供给胜率变化 / pp',shrink=.6)
    fig.tight_layout();fig.savefig(out/'supply_stage_heatmap.png',dpi=160);plt.close(fig)


def stage_guides(rows,out):
    folder=HERE/'joint_stage_guides';folder.mkdir(exist_ok=True);evidence=[]
    for s in range(1,7):
        lines=[f'# {s*5}人阶段：身份技能与装备投放','',
            '验证集按身份与装备档跨六流派选择供给；下表为新人物/技能抽样、困难与非常难的独立确认均值。每格包含六种流派，不用某个预设顺位代替玩家排阵。所有效果仍使用已声明研究候选。',
            '', '| 身份 | 人数 | 普通装备：候选 / 供给收益 | 四顶级：候选 / 供给收益 | 四顶级：羁绊交互 |',
            '| --- | --- | --- | --- | --- |']
        for key in IDENTITIES:
            groups={gear:[r for r in rows if r['stage']==s and r['bond']==key and r['gear']==gear] for gear in ('basic','four_top')}
            if not groups['basic']:
                lines.append(f'| {CN[key]} | — | 无现有人物供给 | — | — |');continue
            for gear,rr in groups.items():
                policy=rr[0]['policy'];assert all(r['policy']==policy for r in rr)
                evidence.append(dict(stage=s,capacity=s*5,bond=key,identity=CN[key],gear=gear,policy=policy,count=rr[0]['count'],
                    cells=len(rr),supply_gain=avg(r['supply_gain'] for r in rr),
                    supply_interaction=avg(r['supply_interaction'] for r in rr),
                    selected_bond_gain=avg(r['selected_bond_gain'] for r in rr),
                    selected_mean_chance=avg(r['target_mean_chance'] for r in rr),
                    selected_repeatable_fraction=avg(r['target_repeatable_fraction'] for r in rr),
                    selected_gated_fraction=avg(r['target_gated_fraction'] for r in rr),
                    selected_censored=avg(r['selected_censored'] for r in rr)))
            b=groups['basic'];t=groups['four_top']
            lines.append(f'| {CN[key]} | {b[0]["count"]} | {POLICY_CN[b[0]["policy"]]} / {100*avg(r["supply_gain"] for r in b):+.2f}pp | {POLICY_CN[t[0]["policy"]]} / {100*avg(r["supply_gain"] for r in t):+.2f}pp | {100*avg(r["supply_interaction"] for r in t):+.2f}pp |')
        lines += ['', '候选收益为负说明验证集选型未在这批独立构筑中复现，应保留随机投放，不据这张表继续用确认结果挑另一套方案。额外羁绊交互已扣除关闭羁绊时同样换技能的收益；正的技能总收益不等于身份机制被增强。',
            '', '“全队身份适配”会按每名队友身份调整整队技能；其余两种只调整目标身份。四维、等级、阶位及技能原生属性均保持。需施法装备应结合实际出手率检查，填充角色的属性/开局机制仍持续生效。',
            '', '逐格结果与发动率、可重复技能占比、条件占比见`../results/joint/supply_stage_evidence.csv`和`../results/joint/supply_confirmation_evidence.csv`。这些技能参数指生成技能的原始值，女仆长等例外仍按真实规则结算，实际出手记录另存。本阶段人数是一个被测小组合点，不是人数曲线寻优后的最终门槛。']
        (folder/f'{s*5:02d}_people.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    write_csv(out/'supply_stage_evidence.csv',evidence)
    atomic_json(out/'skill_supply_design_candidates.json',dict(
        basis='independent confirmation; tier/axis/stat/level unchanged; stage identity gear specific candidates',
        policies={'random':'原始抽样','repeatable':'目标身份：无限次、高概率、少门槛偏好；现有池前四分位',
                  'throughput':'目标身份：10回合吞吐代理；现有池前四分位',
                  'matched':'全队按各成员身份适配；现有池前四分位'},
        rows=evidence))


def allocation_evidence(out):
    data=json.loads((out/'allocation_confirmation.json').read_text(encoding='utf-8'))
    rows=[]
    for cell in data['rows']:
        j=cell['cell']['job'];result=cell['result']
        rows.append(dict(stage=j['stage']+1,capacity=(j['stage']+1)*5,bond=j['bond'],identity=CN[j['bond']],
                         genre=j['genre'],difficulty=j['difficulty'],equivalent=result['equivalent'],
                         owner_gain=result.get('owner_gain',0.),reference_wr=result.get('reference_wr'),
                         refined_wr=result.get('refined_wr'),bond_interaction=result.get('bond_interaction',0.),
                         executed_battles=result['executed_battles']))
    write_csv(out/'allocation_evidence.csv',rows)
    return data,rows


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=HERE/'results/joint')
    p.add_argument('--counters-only',action='store_true');args=p.parse_args();out=args.output
    counter=counters(out);by_counter={}
    for key in ('military','killer','sage','hunter'):
        rr=[r for r in counter if r['bond']==key]
        by_counter[key]={k:avg(r[k] for r in rr) for k in rr[0] if isinstance(rr[0][k],(int,float))}
        by_counter[key]['interval']=cluster_interval(rr,'interaction')
    atomic_json(out/'counter_summary.json',by_counter)
    counter_guide(counter,by_counter,out)
    if args.counters_only:
        print(json.dumps(by_counter,ensure_ascii=False,indent=2));return
    rows,equipment,variants=confirmation(out);stage_guides(rows,out);grouped={}
    for key in IDENTITIES:
        for gear in ('basic','four_top'):
            rr=[r for r in rows if r['bond']==key and r['gear']==gear]
            grouped[f'{key}:{gear}']=dict(supply=cluster_interval(rr,'supply_gain'),
                interaction=cluster_interval(rr,'supply_interaction'),
                selected_bond_gain=avg(r['selected_bond_gain'] for r in rr),
                uncast_cast_gear_fraction=(sum(r['uncast_cast_gear_fraction']*r['cast_gear_count'] for r in rr)/
                                          max(1,sum(r['cast_gear_count'] for r in rr))),
                selected_censored=avg(r['selected_censored'] for r in rr),
                positive_cells=sum(r['supply_gain']>0 for r in rr),negative_cells=sum(r['supply_gain']<0 for r in rr),cells=len(rr))
    completed={p:json.loads((out/(p+'.json')).read_text(encoding='utf-8')) for p in ('counters','screen','confirm')}
    validation=json.loads((out/'validation.json').read_text(encoding='utf-8'))
    assert validation['status']=='passed' and all(p in validation['phases'] for p in completed)
    totals={p:dict(cells=d['cells'],executed_battles=d['executed_battles']) for p,d in completed.items()}
    attribute=None
    if (out/'attribute_sensitivity.json').exists():
        attribute=json.loads((out/'attribute_sensitivity.json').read_text(encoding='utf-8'))
        assert validation['phases']['attribute']['executed_battles']==attribute['executed_battles']
        totals['attribute']={k:attribute[k] for k in ('cells','executed_battles')}
    allocation=allocation_rows=None
    if (out/'allocation_confirmation.json').exists():
        allocation,allocation_rows=allocation_evidence(out)
        assert validation['phases']['allocation']['executed_battles']==allocation['executed_battles']
        totals['allocation']={k:allocation[k] for k in ('cells','changed_cells','executed_battles')}
    atomic_json(out/'design_evidence.json',dict(signature=validation['signature'],phases=totals,counters=by_counter,supply=grouped,
        analysis_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        validation_sha256=hashlib.sha256((out/'validation.json').read_bytes()).hexdigest()))
    lines=['# 六阶段身份技能、装备与专门克制设计指南','',
        '2026-10-21汇总。沿用玩家会排阵的前提；所有变体开关分别搜索顺位，再盲测。新一轮使用独立技能库和人物抽样池，保持角色、等级、四维预算、技能阶位与原生属性一致。',
        '',f'本轮正式执行{sum(x["executed_battles"] for x in totals.values()):,}次对战；专门克制{totals["counters"]["cells"]}单元、技能筛选{totals["screen"]["cells"]}单元、独立确认{totals["confirm"]["cells"]}单元。每格反复ROLL与独立阵容数量分开记账，贤者5人阶段无真实人物供给。',
        '', '## 专门克制', '',
        '表中收益为各自搜索后的开启−关闭羁绊；交互为挑战收益−对照收益。它描述这批固定NPC，不是泛用强弱排名。', '',
        '| 身份 | 对照场收益 | 挑战场收益 | 克制交互 | 挑战胜率：关闭→开启 |',
        '| --- | --- | --- | --- | --- |']
    for key,r in by_counter.items():
        lines.append(f'| {CN[key]} | {r["control_practical_gain"]*100:+.2f}pp | {r["challenge_practical_gain"]*100:+.2f}pp | {r["interaction"]*100:+.2f}pp | {r["challenge_off_wr"]:.1%}→{r["challenge_on_wr"]:.1%} |')
    lines += ['', '军人场只开关敌方忍者；杀手场只开关恢复型女仆长候选，前两位保留攻击者，减疗记录为封顶前恢复请求削减。贤者场改变同阶同原生属性的负面技能供给；猎手场把等预算敌方坚韧占比由25%改为65%，同时其他属性下降，属于构筑场景测试。不能把后二者解释为孤立一个防御参数的偏导。',
        '', '## 技能投放', '',
        '“重复出手”和“吞吐”只偏置本次目标身份的技能；“全队身份适配”按每名成员身份偏置整队技能，不能把其全部收益归因给目标身份。全部候选仅从实际生成技能的同阶同原生属性池选取前四分位；角色四维保持固定。技能库选择在验证集完成，确认集保留随机基线。技能供给表沿用基准装备归属，后续归属变化的收益见装备节。',
        '', '| 身份 | 普通装备：供给收益 | 四顶级：供给收益 | 四顶级：额外羁绊交互 | 四顶级：需施法装备未出手比例 |',
        '| --- | --- | --- | --- | --- |']
    for key in IDENTITIES:
        b=grouped[f'{key}:basic'];t=grouped[f'{key}:four_top']
        lines.append(f'| {CN[key]} | {b["supply"]["mean"]*100:+.2f}pp | {t["supply"]["mean"]*100:+.2f}pp | {t["interaction"]["mean"]*100:+.2f}pp | {t["uncast_cast_gear_fraction"]:.1%} |')
    lines += ['', '“供给收益”含技能自身变强；“额外羁绊交互”扣除关闭羁绊时同样换技能的收益。先看两者，再决定是否针对某身份限制技能供给。未出手比例只计必须施法的顶级装备；实际施法也未必满足装备的子效果条件，不能当作完整装备激活率。',
        '', '以下为机制对应的投放原则，具体是否值得偏置，以本轮独立确认表为准；不是额外增加规则或直接修改生成器。重复出手候选优先无限次、高发动率、少门槛；吞吐候选使用10回合代理排序，只负责提出候选，最终收益仍由完整引擎计算。',
        '', '现有引擎的恢复技能完成恢复后仍继续结算基础直伤；技能的main_type为Heal不等于这次行动没有攻击。供给代理和装备归属都要以实际管线复核，不能按其他游戏的治疗动作理解。',
        '', '| 身份 | 技能与装备投放原则 |','| --- | --- |']
    for key in IDENTITIES:lines.append(f'| {CN[key]} | {SUPPLY_RULES[key]} |')
    lines += ['', '逐阶段建议：[5人](joint_stage_guides/05_people.md)、[10人](joint_stage_guides/10_people.md)、[15人](joint_stage_guides/15_people.md)、[20人](joint_stage_guides/20_people.md)、[25人](joint_stage_guides/25_people.md)、[30人](joint_stage_guides/30_people.md)。每份列出候选、人数、技能收益与额外羁绊交互；均值之外还应检查逐流派明细。',
        '', '![六阶段供给收益](results/joint/supply_stage_heatmap.png)', '', '## 装备与属性预算', '',
        '每人一件普通属性装备；顶级档仅将四件替换为机制装备，普通属性保持相同。机制、数值来自既有36格装备候选表；归属按预先声明的机制匹配启发式，随角色一起排阵。四件是准备上限档，不代表每个阶段必然收集齐；0→4的实测收益不能线性反推1/2/3件。未对装备归属、种类与数值求全局最优。',
        '', '| 实际动作与角色位置 | 机制适配原则 |', '| --- | --- |',
        '| 帮派成员替代普攻 | 优先普攻加成与属性/开局效果；原技能已不调用，施法直伤、破防、暴击、递增等装备不能依靠原技能触发。普攻装备归属优先考虑实际发动机会。 |',
        '| 女仆长 | 按替代后的技能匹配施法装备；不限次数使增加技能次数无效。本轮我方为攻击候选、恢复型仅用于反制NPC；正式效果确定后再匹配其子效果。 |',
        '| 女仆长保证施法的单羁绊队伍 | 正常队伍行动不再触发全员失败的普攻保底；普攻装备不能按普通构筑的机会估值。混合帮派等额外替代普攻需要另测。 |',
        '| 有限次数的实际输出者 | 直伤/破防/暴击等装备按合法释放次数定价；增加次数需要真的消耗到原上限，不能仅凭技能有限次就算作生效。 |',
        '| 稳定重复施法者 | 可测试施法递增和对应技能加成；同时检查是否挤掉其他更重要技能。 |',
        '| 实际未获得出手的成员 | 仍提供普通属性、装备者属性加成或开局护盾；需施法的机制不会因放在高阶角色身上就自动生效。 |',
        '', '| 人数 | 流派 | 每件基准点数 | 0.75～1.25扫描带 | 全队基准点数 | 四顶级以外：基准总点数 |',
        '| --- | --- | --- | --- | --- | --- |']
    import joint_research as lab
    equipment_reference=[]
    for s in range(6):
        for g in lab.GENRES:
            point=lab.study.COMMON[(s,g)];lines.append(f'| {(s+1)*5} | {g} | {point:.3f} | {point*.75:.3f}～{point*1.25:.3f} | {point*(s+1)*5:.3f} | {point*((s+1)*5-4):.3f} |')
            equipment_reference.append(dict(stage=s+1,capacity=(s+1)*5,genre=g,common_points=point,
                low_points=point*.75,high_points=point*1.25,non_top_items=(s+1)*5-4,
                allocation_primary=.67,allocation_secondary=.33,
                **{f'top_{i+1}':f'{kind}:{value}' for i,(_,kind,value) in enumerate(lab.study.LOADS[(s,g)])}))
    write_csv(out/'equipment_reference_matrix.csv',equipment_reference)
    lines += ['', '36格四件顶级机制与数值、普通装备主/副属性分配比例见`equipment_reference_matrix.csv`。它是本轮验证的配置矩阵；具体装备归属按技能/机制匹配后随角色排阵，不能直接把四件都视为由队首释放。']
    lines += ['', '工程师现在同时放大显式四维和owner_stats实际贡献；技能倍率、护盾等机制不计入属性放大。新模型与旧工程师装备表应分开引用。']
    if allocation:
        lines += ['', f'装备归属追加复核{allocation["cells"]}个输入：将恢复后的基础直伤纳入评分，以初始第一名女仆作为替代技能装备的候选拥有者，并区分已开启的帮派替代普攻与仅有帮派标签的成员；顺位搜索仍可另选女仆长。{allocation["changed_cells"]}格发生实际物理变化，新增{allocation["executed_battles"]:,}次执行；其余归属的基础属性、全队护盾和成员主动机制在本轮装备表下等价。双方各自重排，使用与原确认不同的种子。',
            '', '| 身份 | 流派 | 实际变化格数 | 改进归属−原归属 |', '| --- | --- | --- | --- |']
        for key in IDENTITIES:
            if not any(r['bond']==key and not r['equivalent'] for r in allocation_rows):continue
            for g in lab.GENRES:
                group=[r for r in allocation_rows if r['bond']==key and r['genre']==g and not r['equivalent']]
                if not group:continue
                lines.append(f'| {CN[key]} | {g} | {len(group)} | {100*avg(r["owner_gain"] for r in group):+.2f}pp |')
        lines += ['', '以上只汇总发生物理变化的格子；未变化格子的归属效应严格为0，不新增重复对战。女仆的变化不能作为全流派统一规则；帮派应按实际普通攻击机会另看。新候选只是一轮明确的归属改进，不代表穷举了所有装备交换。逐格数据`allocation_evidence.csv`，两种归属的完整顺位与对局存于`allocation_replicates/`。']
    else:
        lines += ['', '本轮装备归属仍是原始匹配启发式；恢复后基础直伤与女仆长替代技能的归属改进尚待独立复核。']
    if attribute:
        lines += ['', f'属性带追加{attribute["executed_battles"]:,}次执行，中心点复用确认集前32条、两端同种子新算；本表数字为每件装备的四维总点数，按原流派主/副属性比例分配。四顶级以外仅调整N−4件普通装备，顶级装备属性与机制保持；全基础属性组则调整全部N件的显式属性，owner_stats比例机制保持。',
            '', '| 身份 | 仅普通装备−25%：胜率变化 | 仅普通装备+25%：胜率变化 | 全基础属性+25%：胜率变化 |',
            '| --- | --- | --- | --- |']
        ar=attribute['rows']
        for key in IDENTITIES:
            simple=[r for r in ar if r['bond']==key and r['gear']=='four_top' and r['scope']=='non_top']
            full=[r for r in ar if r['bond']==key and r['gear']=='four_top' and r['scope']=='all_base']
            lines.append(f'| {CN[key]} | {100*avg(r["on_wr_0.75"]-r["on_wr_1.0"] for r in simple):+.2f}pp | {100*avg(r["on_wr_1.25"]-r["on_wr_1.0"] for r in simple):+.2f}pp | {100*avg(r["on_wr_1.25"]-r["on_wr_1.0"] for r in full):+.2f}pp |')
        lines += ['', '扫描带是当前可操作的调参起点：先用中点，按对应阶段/流派及身份的实际曲线向两侧调整。它不等于全局安全上下限；这里锁定技能与顺位，不能与重新优化后的强度混为一谈。每个端点只跑32条配对种子，细微变化需更多样本。逐格胜率、删失和偏导估计见`attribute_band_evidence.csv`；偏导单位为“每件被调整装备增加1个四维总点”，不是凭空增加所有角色基础属性。']
    else:
        lines += ['', '这是本轮测试的属性基准；表中两端仅为预定扫描带，尚未追加执行，不是安全上下限。']
    lines += [
        '', '## 复现与适用范围', '',
        '入口`run_joint_research.ps1`；源码`joint_research.py`、`joint_core.py`。完整性与重放`verify_joint.py`，分析`analyze_joint.py`。结果目录保留源文件哈希、选型来源、SQLite断点、每格完整成员/技能/装备/排列/种子/逐场指标；克制场额外保留各上下文首场逐回合遥测。',
        '', '5人穷举120种排列；更大人数有限多起点搜索，不证明总体全局最优。筛选的有限预算只负责提出候选；独立确认不再挑方案。每个阶段/身份/流派只有一套确认阵容，两档难度共用人物，置信区间按阶段×流派阵容格重抽样，不能代表全部玩家构筑。',
        '', '当前沿用候选系数与小组合人数，军人至少占人数上限一半，学生老师/剑士/教徒差阶需成立。女仆长攻击、恢复NPC、农民果实等效果沿用已声明研究候选；经济、混合羁绊、更多独立阵容及系数/人数收敛仍需后续验证。',
        '', '数据：`counter_evidence.csv`、`supply_confirmation_evidence.csv`、`equipment_confirmation_evidence.csv`、`joint_variant_evidence.csv`、`design_evidence.json`、`validation.json`。']
    (HERE/'JOINT_DESIGN_GUIDE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    plot_heatmap(rows,out)
    print(json.dumps(totals,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
