"""Build a short designer-facing guide from measured stage candidates."""
import json
import pandas as pd
from settings import HERE,IDENTITIES,CN,DEFAULTS
from analyze import mdtable


def value(key,cfg):
    c={**DEFAULTS,**cfg};g=c.get('gain',1.)
    pct=lambda name:f"{c[name]*g*100:g}"
    if key=='academy':return pct('teacher_damage')+'%/学生等级'
    if key=='military':return '系数'+pct('military_hit')+'%'
    if key=='mage':return pct('mage_pct')+'%q／'+pct('mage_damage')+'%q'
    if key=='cult':return pct('cult')+'%/低阶教徒'
    if key=='fighter':return pct('fighter')+'%q/回合'
    if key=='hunter':return pct('hunter')+'%q转化'
    if key=='heroine':return pct('heroine')+'%q/首次接力'
    if key=='maid':return '倍率1＋'+f"{c['maid_power']*g:g}q"
    if key=='lady':return pct('lady')+'%q'
    if key=='scholar':return pct('scholar')+'%q恢复概率'
    if key=='sage':return '+'+pct('sage_out')+'%q／−'+pct('sage_in')+'%q'
    if key=='engineer':return '+'+pct('engineer_base')+'%q／每技能+'+pct('engineer_cast')+'%q'
    if key=='sword':return pct('sword')+'%q；逐次×'+str(c['sword_decay'])
    if key=='ninja':return pct('ninja_base')+'%q／每技能+'+pct('ninja_cast')+'个百分点q'
    if key=='adventurer':return pct('adventurer')+'%q/目标'
    if key=='sailor':return '均人预算×'+f"{c['sailor']*g:g}q/身份/维"
    if key=='gang':return '普攻倍率1＋'+f"{c['gang']*g:g}q"
    if key=='merchant':return '最高维×'+pct('merchant')+'%q'
    if key=='farmer':return pct('farmer_value')+'%q最大BP/收获'
    if key=='thief':return pct('thief')+'%q/攻击'
    if key=='rich':return pct('rich_dr')+'%/本场G'
    if key=='worker':return pct('worker')+'%q最大BP'
    if key=='killer':return pct('killer')+'%q恢复压制'


def main():
    out=HERE/'results';selected=json.loads((out/'selected_coefficients.json').read_text(encoding='utf-8'))
    selected={(r['stage'],r['bond']):r for r in selected if r['soft_delta_reference']==.1}
    rows=[]
    for key in IDENTITIES:
        row={'羁绊':CN[key]}
        for s in range(6):row[f'{5*(s+1)}人']=value(key,selected[(s,key)]['config']) if (s,key) in selected else '当前无角色'
        rows.append(row)
    validation=json.loads((out/'delivery_validation.json').read_text(encoding='utf-8'))
    raw=pd.read_csv(out/'identity_only_skill_supply.csv')
    supply=raw.groupby('identity').agg(平均额外收益pp=('delta',lambda x:100*x.mean()),下界=('ci_low','min'),上界=('ci_high','max')).reset_index()
    lines=[
        '# 身份羁绊投放指南：供设计者使用','',
        '> 2026-10-20顺位复核更新：23项已按现有人物供给补齐六阶段复核，见[最优顺位设计指南](OPTIMAL_ORDER_DESIGN_GUIDE.md)。本页保留预设顺位的历史数据与候选系数，读取数值时请同时参考新测结果及适用范围。','',
        f"已完成 {validation['total_research_battle_executions']:,} 次研究对战执行、{validation['temporal_battles']:,} 场时序遥测和 {validation['behaviour_checks']} 项机制检查。详细证据、适用范围与候选结算见[完整规范](DESIGN_SPECIFICATION.md)。",'',
        '## 先采用的设计规范','',
        '1. 机制按用户23项确认稿；数值按阶段分别读取。军人最低人数为3／5／8／10／13／15，对应5／10／15／20／25／30人上限。',
        '2. 人数增长暂用q(n)=n/(n+4)。人数系数递增，整队净收益另计换人代价；没有额外3/6/9解锁门槛。这是测试过的候选曲线。',
        '3. 正常行动只选一次技能；剑士最多追加3次、总计4次完整技能，每次消耗真实次数，追加概率逐次衰减。',
        '4. 女仆长取首位女仆，100%、无限次、无回合/血线门槛、不可封印。位置由玩家安排；具体技能效果仍是候选。',
        '5. 工程师和忍者的成长到双方整个回合结束后生效；行商开局一次；农民共用一颗果实；盗贼与富翁只记录本场变化。',
        '6. 每人一件装备、顶级装备最多四件；技能投放适配不能偷偷增加个人四维预算。','',
        '## 六阶段数值起点','',
        '下表中q都使用该身份上阵人数计算，不能直接把表中系数当最终加成。阶段参数来自验证集选择，已用独立技能库确认；不是23项已经全部完成平衡的宣告。',
        '军人不使用q：占比r低于50%无效，否则概率=min(100%，表中系数×[0.25+0.75×(2r−1)])。表中150%是计算系数，不能当作150%的最终概率。',
        '同一羁绊跨阶段参数不同，暂不强求一条统一成长函数。','',mdtable(pd.DataFrame(rows)),'',
        '这些是各阶段独立校准的强度候选，不是玩家进阶时直接切换的成长表。正式投放选择统一系数或平滑成长时，还需避免既有羁绊因进阶反向变弱；本轮没有把这张独立标尺当作该成长已经验证。',
        '最终概率和恢复压制均截到0～100%，贤者强化仍遵守原生负面效果的幅度上限。',
        '30人例子：10名剑士q=10/14，有合格追加对象时首次追加约14.29%，之后约7.14%、3.57%，最多3次追加；10名忍者初始绝对闪避约2.86%，每次忍者技能从下回合起再增加约0.57个百分点。',
        '工程师表中的比例是显式装备四维额外贡献，不能拿它直接乘技能倍率；当前实验未把owner_stats等其他装备机制一概放大。',
        '老师经验速度独立于战斗平衡：6%／12%／24%每老师是扫描候选，本轮没有经验成本和任务收益数据，不能用战斗校准系数证明哪个培养速度最合适。','',
        '## 结合角色分布的编队规范','',
        '低阶集中的身份尤其需要保留主C、回转成员和少量支持的空间。不要只看开启羁绊后胜率增加，就认为替换大量高阶角色仍然值得。',
        '完整规范同时给出同阵容机制收益、凑身份的换人代价与最终净收益；小组合另测约三分之一人数。尚未获得净收益的配置不作为成熟流派投放结论。',
        '贤者在5人阶段参考阶级上限内无人；忍者六阶段可用人数分别为3／9／12／16／17／17。所有采样人物去重，没有为填满队伍复制稀缺角色。','',
        '## 身份技能投放可以怎样设计','',
        '保留四种原生技能类型和既有阶位预算，在同阶同类型内调整抽样倾向，再与顺位一起验证。优先采用现有生成器已经能生成的合法技能组合。','',
        '- **侠女**：提高早期可用、有限次技能的供给机会，让不同人先后完成首次出手；保底技能仍需保留。',
        '- **工程师、农民、富翁、盗贼**：比较可重复、少门槛技能与持续有效输出技能，避免只按发动率排序而损失太多单次效果。',
        '- **剑士**：提供可以接受追加释放的次数资源；追加对象的普通发动概率不用再次判定。',
        '- **女仆、帮派**：重点设计专用替代攻击与顺位，不能继续按原随机技能的完整效果估值。',
        '- **贤者、杀手**：保证存在可利用负面强化或恢复压制的技能场景，再评估系数。',
        '- **忍者、学者**：本轮偏可重复等投放方案在独立样本中没有稳定改善，不建议直接全面改成高发动技能。学者应先验证次数消耗和恢复机会确实存在。',
        '- **行商、社畜、水手、淑女**：被动价值不要求本人高频出手，优先保证其所在队伍的主C与回转。',
        '单身份研究的六阶段均值：女仆的顺位方案额外+19.33个百分点，帮派+17.19，农民+13.95；这些主要说明顺位与技能机会的重要性，不是羁绊自身增加了同样多的强度。各阶段的具体策略与配对区间见独立供给表。','',
        '## 当前不宜直接定稿的部分','',
        '- 女仆长纯直伤候选在10／20／25人阶段出现负收益；保留其确定发动规则，具体效果继续在已测攻击／恢复／护盾候选之间设计。',
        '- 学者的普通配置收益仍偏弱，单纯提高恢复概率不能保证产生可用机会；不能直接宣称强度已经解决。',
        '- 帮派原技能损失、猎手延后伤害、农民成熟等待均有真实代价。人数与系数必须一起看，不用一个全局增伤数覆盖所有阶段。',
        '- 富翁金币目前用G计研究单位，正式金币兑换、失败或退出的结算及重复刷取经济尚未标定。',
        '- 女仆长、果实、冒险目标的具体效果，以及拜火教跨身份强化范围等，仍需区分用户原始机制与本轮具体候选。','',
        '## 文件入口','',
        '- [完整设计规范](DESIGN_SPECIFICATION.md)：结算、候选公式、阶段结果、交互、PCA和技能供给。',
        '- [5人](stage_guides/S1_5_MEMBERS.md)／[10人](stage_guides/S2_10_MEMBERS.md)／[15人](stage_guides/S3_15_MEMBERS.md)／[20人](stage_guides/S4_20_MEMBERS.md)／[25人](stage_guides/S5_25_MEMBERS.md)／[30人](stage_guides/S6_30_MEMBERS.md)：逐身份数值与独立确认。',
        '- [机器可读候选](results/recommended_design.json)、[小组合净收益](results/small_group_net_gain.csv)、[技能投放独立确认](results/identity_only_skill_supply.csv)。',
        '- [一键复现](run_all.ps1)：可断点续跑的本地并发研究入口。','',
        '本轮完成的是研究规范与候选数值；Unity正式战斗系统、人物技能生成规则和奖励钱包尚未接入这些羁绊。',
    ]
    (HERE/'DESIGN_GUIDE.md').write_text('\n'.join(lines),encoding='utf-8')
    print('Designer guide written',flush=True)


if __name__=='__main__':main()
