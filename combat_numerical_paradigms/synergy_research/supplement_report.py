"""Append isolated identity skill supply findings and selection limits."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from settings import HERE,CN
from analyze import mdtable,aggregate

NAMES={
 'random':'保留随机供给', 'repeatable':'偏可重复、少门槛', 'throughput':'偏持续有效输出',
 'frontloaded':'偏前期释放', 'support_order':'只调整技能顺位',
 'repeatable_order':'可重复倾向＋顺位', 'throughput_order':'持续输出倾向＋顺位',
}


def main():
    out=HERE/'results';rows=json.loads((out/'skill_supply_confirmation.json').read_text(encoding='utf-8'))
    validation=json.loads((out/'skill_supply_validation.json').read_text(encoding='utf-8'))
    result=[]
    for (s,key),rs in pd.DataFrame(rows).groupby(['stage','bond']):
        n=int(rs.trials.sum());delta=float(np.average(rs.win_delta,weights=rs.trials))
        second=sum((r.delta_se**2*(r.trials-1)+r.win_delta**2)*r.trials for r in rs.itertuples())/n
        se=np.sqrt(max(0,second-delta*delta)/max(1,n-1))
        result.append(dict(stage=s+1,bond=key,identity=CN[key],n=n,delta=delta,ci_low=delta-1.96*se,ci_high=delta+1.96*se,
                           generic_delta=float(np.average(rs.policy_off-rs.random_off,weights=rs.trials)),
                           interaction=float(np.average(rs.interaction,weights=rs.trials)),
                           policies='；'.join(NAMES[x] for x in sorted(set(rs.policy))),
                           mean_scholar_restored=float(rs.scholar_restored.mean()),
                           mean_growth_casts=float(rs.growth_casts.mean()),mean_fruit_harvest=float(rs.fruit_harvest.mean())))
    frame=pd.DataFrame(result);frame.to_csv(out/'identity_only_skill_supply.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(rows).to_csv(out/'identity_only_skill_supply_by_flow.csv',index=False,encoding='utf-8-sig')
    policies=pd.DataFrame(validation).groupby(['stage','bond','policy']).win_delta.mean().reset_index()
    policies.to_csv(out/'skill_policy_validation.csv',index=False,encoding='utf-8-sig')
    table=frame[['stage','identity','policies','delta','ci_low','ci_high','generic_delta','interaction']].copy()
    for c in ('delta','ci_low','ci_high','generic_delta','interaction'):table[c]*=100
    table.columns=['阶段','身份','验证选择的候选','额外收益pp','区间下限pp','区间上限pp','无羁绊供给收益pp','交互pp']
    total_battles=sum(j['trials']*(2+2*sum(x!='random' for x in j['policies'])) for j in {json.dumps({k:r[k] for k in ('stage','genre','bond','count','config','policies','bank','offset','trials')},sort_keys=True):r for r in validation+rows}.values())
    # Summaries are expanded one row per policy. Deduplicate job-level execution.
    manifest=json.loads((out/'skill_supply_manifest.json').read_text(encoding='utf-8'))
    meta=dict(battle_executions=total_battles,validation_cells=len(validation)//7,confirmation_cells=len(rows),
              combat_signature=manifest['combat_signature'],skill_signature=manifest['signature'])
    (out/'skill_supply_execution_summary.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    confirmation=json.loads((out/'confirmation.json').read_text(encoding='utf-8'))
    counts=aggregate(confirmation,['stage','bond','count','placement'])
    counts['stage']+=1
    counts.to_csv(out/'composition_cost_and_order.csv',index=False,encoding='utf-8-sig')
    best=counts.loc[counts.groupby(['stage','bond']).total_delta.idxmax()]
    best.to_csv(out/'observed_composition_candidates.csv',index=False,encoding='utf-8-sig')
    small=json.loads((out/'small_group_composition.json').read_text(encoding='utf-8'))
    small_meta=json.loads((out/'small_group_manifest.json').read_text(encoding='utf-8'))
    small_frame=pd.DataFrame(small).groupby(['stage','bond','count']).agg(
        凑人代价=('composition_delta','mean'),仅羁绊净收益=('small_group_total_delta','mean'),
        技能供给与顺位联合净收益=('supply_and_order_total_delta','mean')).reset_index()
    small_frame['stage']+=1;small_frame['bond']=small_frame.bond.map(CN)
    small_frame.to_csv(out/'small_group_net_gain.csv',index=False,encoding='utf-8-sig')
    small_display=small_frame.copy()
    for c in ('凑人代价','仅羁绊净收益','技能供给与顺位联合净收益'):small_display[c]*=100
    small_display=small_display.rename(columns={'stage':'阶段','bond':'身份','count':'上阵人数'})
    chunk=[
        '\n## 补充：仅改变目标身份的技能供给与顺位\n',
        f'追加 {total_battles:,} 次对战执行。每阶段、每身份比较7种方案（含保留随机供给），只替换目标身份的技能，固定角色四维、装备及其他身份技能。验证选候选后，在独立技能库与新阵容种子上确认。',
        '技能候选仍来自原生成器同阶位、同原生类型，未任意提高发动率、倍率或次数。顺位方案保留技能条件和剩余次数。',
        '前一节的全队适配试验是诊断性对照，会同时调整其他角色；本节才用于单身份供给建议。重复发动倾向不能一概推广，未明显改善的阶段保留原随机供给。',
        '本补充采用约三分之一人数，军人低于50%时羁绊无效，因此军人在本补充中的收益仅表示供给/顺位的普通收益；军人羁绊本身读取前面达到门槛的确认与对忍者测试。',
        '表中区间是当前六类队伍样本的配对抽样区间，不代表已验证所有混合阵容。候选在独立确认中退步的记录照实保留，不用测试集再次挑赢家。\n',
        mdtable(table),
        '\n## 机制收益与换人代价的使用规则\n',
        '只开关羁绊得到的正收益，不保证换人成立后的总收益为正。低阶人物集中的女仆、农民、帮派、行商、社畜等尤其需要同时查看composition_delta与total_delta。',
        '人数越多不自动等于越值得上阵：每增加一个支持位，都可能替换掉更高阶技能和四维贡献。优先保留核心与必要的技能回转，再比较支持人数。',
        'observed_composition_candidates.csv列出本次已测人数/前后顺位中较好的结果，仅供探索，未把事后选择当作独立确认的最优阵容。',
        '本轮沿用旧难度模型的宏观参数，但NPC成员也改按真实人物阶级抽样，因此旧指南中的胜率不直接继承；本轮实际基线胜率已重新记录。',
        f"\n小组合另补 {small_meta['reference_battle_executions']:,} 场不限制身份的对照，同阶段/队伍类型参照跨身份复用，不重复计执行量。以下为各阶段约三分之一身份成员的净收益（百分点），原始CSV保留小数比例。",'',
        mdtable(small_display),
    ]
    path=HERE/'DESIGN_SPECIFICATION.md';path.write_text(path.read_text(encoding='utf-8')+'\n'.join(chunk),encoding='utf-8')
    for stage in range(1,7):
        path=HERE/'stage_guides'/f'S{stage}_{stage*5}_MEMBERS.md'
        sub=table[table['阶段']==stage]
        path.write_text(path.read_text(encoding='utf-8')+'\n## 单身份技能供给的独立确认\n\n'+mdtable(sub)+'\n\n## 小组合的净收益（百分点）\n\n'+mdtable(small_display[small_display['阶段']==stage])+'\n',encoding='utf-8')
    print(json.dumps(meta),flush=True)


if __name__=='__main__':main()
