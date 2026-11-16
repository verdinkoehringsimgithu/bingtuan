"""Produce a practical growth and stage-difficulty design model from measurements."""
from study import *
import study as simulation
from model import character_stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

LABELS={'hard':'难','very_hard':'很难','extremely_hard':'非常难'}
PREP_LABELS={'underdeveloped':'培养与收集不足','standard':'常规参考','different_order':'不同顺位','strong_collection':'较高收集与培养','four_top':'常规阵容＋四件顶级装备'}


def table(frame,columns=None):
    frame=frame if columns is None else frame[columns]
    def cell(value):return f'{value:.3f}' if isinstance(value,(float,np.floating)) else str(value).replace('|','/')
    return '| '+' | '.join(map(str,frame.columns))+' |\n| '+' | '.join(['---']*len(frame.columns))+' |\n'+'\n'.join('| '+' | '.join(cell(v) for v in row)+' |' for row in frame.itertuples(index=False,name=None))


def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=OUT);args=parser.parse_args();OUT=args.output.resolve();simulation.OUT=OUT
    final=pd.read_csv(OUT/'recommended_confirmation.csv');fine=pd.read_csv(OUT/'fine_difficulty_intervals.csv');recommended=pd.read_csv(OUT/'recommended_templates.csv');means=final.groupby(['stage','difficulty','point','preparation']).agg(wr=('wr','mean'),wr_min=('wr','min'),wr_max=('wr','max'),turns=('turns','mean'),hp=('hp','mean'),censor=('censor','mean')).reset_index();write('recommended_profile_ranges.csv',means)
    reference=final[(final.preparation=='standard')&(final.point=='center')].groupby(['stage','difficulty']).agg(wr=('wr','mean'),wr_min=('wr','min'),wr_max=('wr','max'),turns=('turns','mean'),hp=('hp','mean'),censor=('censor','mean')).reset_index();write('standard_reference_summary.csv',reference)
    confirmation_new=json.loads((SOURCE_OUT/'catalog_growth_confirmation.json').read_text(encoding='utf-8'));confirmation_old=json.loads((SOURCE_OUT/'catalog_old_growth_confirmation.json').read_text(encoding='utf-8'))
    simulation.OLD={(int(r['tier']),NAME_TO_LETTER[r['genre']],int(r['sample'])):tuple(int(r['csv'][k]) for k in ('dodge','defense','speed','authority')) for r in confirmation_old};simulation.NEW={};natural.SKILLS.clear();natural.HOLDOUT_SKILLS.clear()
    for row in confirmation_new:
        skill,stats=convert(row);letter=NAME_TO_LETTER[skill.genre];simulation.NEW[(skill.tier,letter,row['sample'])]=stats;natural.SKILLS.setdefault((skill.tier,letter),[]).append((skill,stats,row['sample']))
    natural.HOLDOUT_SKILLS.update(natural.SKILLS);natural.roster.cache_clear();simulation.PATHS.clear();simulation.ACTIVE_BANK='confirmation';npc_stats={};npc_rows=[]
    for s in range(6):
        for h in GENRES:
            values=[];levels=[]
            for j in range(128):
                m,_,lv=player(s,h,j+100003+24576);values.append(np.sum([x.stats for x in m],axis=0));levels.extend(lv)
            array=np.array(values);mean=dict(zip(FIELDS,array.mean(0)));npc_stats[(s,h)]=mean;npc_rows.append(dict(stage=s,enemy_genre=h,level_mean=np.mean(levels),**mean))
    write('npc_reference_four_stats.csv',pd.DataFrame(npc_rows))
    all_test=pd.read_csv(OUT/'fine_difficulty_holdout.csv');typed=all_test[(all_test.point=='center')&(all_test.preparation=='standard')].groupby(['stage','difficulty','enemy_genre']).wr.agg(['mean','min','max']).reset_index();policies=[]
    for r in fine.to_dict('records'):
        measured=typed[(typed.stage==r['stage'])&(typed.difficulty==r['difficulty'])&(typed.enemy_genre==r['enemy_genre'])].iloc[0]
        policies.append(dict(**r,enemy_mean_four_stats=npc_stats[(r['stage'],r['enemy_genre'])],measured_reference_wr=measured['mean'],measured_flow_range=[measured['min'],measured['max']],measurement_catalog_offset=384))
    selected=[]
    for row in recommended.to_dict('records'):
        measured=reference[(reference.stage==row['stage'])&(reference.difficulty==row['difficulty'])].iloc[0];selected.append(dict(**row,enemy_mean_four_stats=npc_stats[(row['stage'],row['enemy_genre'])],confirmed_standard_wr=measured.wr,confirmed_flow_range=[measured.wr_min,measured.wr_max]))
    model=dict(growth_formula='B(L)=B1+(B30-B1)*((L-1)/29)^p; interpolate each four-stat endpoint and allocate integer increments by largest remaining deficit.',default_growth_power=1.,difficulty_targets=TARGETS,
               stages=[dict(stage=s,members=STAGES[s][0],bp=STAGES[s][1],skill_tier_cap=STAGES[s][-1],level_band=LEVEL_BANDS[s]) for s in range(6)],recommended=selected,all_archetypes=policies,
               applicability='Reference level bands are editable design assumptions, not a discovered player distribution. BP stays at canonical stage ruler, no invented level-BP growth. Mean four stats describe sampled NPC rosters; skill order/chance/limits remain part of the template.',strength='rho scales both enemy BP and attack flux; do not independently combine BP and hit maxima/minima. Enemy never adapts to actual player roster.')
    save_json(OUT/'encounter_model.json',model)
    growth=pd.read_csv(OUT/'growth_budget_table.csv');sample=growth[(growth.power==1)&growth.level.isin((1,5,10,15,20,25,30))].pivot(index='tier',columns='level',values='mean').reset_index();write('recommended_level_budget.csv',sample)
    curve=pd.read_csv(OUT/'growth_curve_sensitivity.csv');curve_summary=curve.groupby(['power','level_shift']).wr.mean().reset_index();write('growth_robustness_summary.csv',curve_summary)
    figures=OUT/'figures';figures.mkdir(exist_ok=True);fig,axes=plt.subplots(1,2,figsize=(12,5),constrained_layout=True)
    for tier in range(1,7):
        x=growth[(growth.tier==tier)&(growth.power==1)];axes[0].plot(x.level,x['mean'],label=f'T{tier}')
    axes[0].set(xlabel='Character level',ylabel='Mean total four-stat budget',title='Old level 1 -> measured level 30');axes[0].legend()
    for prep in PREPARATIONS:
        x=means[(means.point=='center')&(means.preparation==prep)].groupby('stage').wr.mean();axes[1].plot(5*(x.index+1),x,marker='o',label=prep)
    axes[1].set(xlabel='Stage member cap',ylabel='WR across three difficulties / six flows',title='Fixed enemies; preparation changes outcomes');axes[1].legend(fontsize=7);fig.savefig(figures/'growth_and_preparation.png',dpi=150);plt.close(fig)
    total=0
    for name in ('enemy_screen.csv','enemy_validation_refine.csv','difficulty_band_validation.csv','difficulty_final_holdout.csv','growth_curve_sensitivity.csv','fine_band_validation.csv','fine_difficulty_holdout.csv','recommended_confirmation.csv'):
        total+=int(pd.read_csv(OUT/name).n.sum())
    balanced=pd.read_csv(OUT/'balanced_recommended_confirmation.csv');base_spread=final[(final.point=='center')&(final.preparation=='standard')].groupby(['stage','difficulty']).wr.agg(lambda x:x.max()-x.min());balanced_spread=balanced[(balanced.point=='center')&(balanced.preparation=='standard')].groupby(['stage','difficulty']).wr.agg(lambda x:x.max()-x.min())
    balance_comparison=pd.DataFrame({'original_spread':base_spread,'balanced_spread':balanced_spread}).reset_index();write('npc_balance_generality_comparison.csv',balance_comparison)
    for name in ('balanced_npc_scan.csv','balanced_npc_bands.csv','balanced_recommended_confirmation.csv'):total+=int(pd.read_csv(OUT/name).n.sum())
    recipe=recommended.copy();recipe['人数']=5*(recipe.stage+1);recipe['难度']=recipe.difficulty.map(LABELS);recipe=recipe.merge(reference,on=['stage','difficulty']);recipe['敌方BP下限']=[STAGES[s][1]*a*r for s,a,r in zip(recipe.stage,recipe.alpha,recipe.rho_lower)];recipe['敌方BP上限']=[STAGES[s][1]*a*r for s,a,r in zip(recipe.stage,recipe.alpha,recipe.rho_upper)];recipe['满血打击下限']=[.135*STAGES[s][1]*b*r for s,b,r in zip(recipe.stage,recipe.beta,recipe.rho_lower)];recipe['满血打击上限']=[.135*STAGES[s][1]*b*r for s,b,r in zip(recipe.stage,recipe.beta,recipe.rho_upper)];write('designer_delivery_table.csv',recipe)
    contents=['# 角色等级成长与阶段难度投放指南（2026-10-13）','目标是提供可调、可复用的阶段标尺，保持玩家收集与编成带来的优势。角色成长与敌人难度分别标定；敌人不根据实际玩家阵容动态追平。',
    '## 可以采用的默认规则','1. 1级保留旧技能生成器的真实四维；30级使用已测的新预算。默认p=1线性成长，按个人起点/终点分别插值四维。\n2. 阶段决定人数上限和技能供给上限，再指定该阶段参考等级分布。玩家四维由各成员自然求和，不预设总属性。\n3. 设计者输入阶段、难度，默认采用经多流派比较后推荐的NPC技能类型；需要固定剧情NPC类型时，用该类型专属区间。\n4. 在一组固定攻防比例上，rho共同缩放敌方BP与打击力；上下限是联动端点，不是可随意组合的独立属性盒子。',
    '## 1—30级成长公式','B(L)=B1+(B30−B1)×((L−1)/29)^p。推荐先用p=1；0.8和1.25也有敏感度测试。每维用同样的端点插值，预算向偶数舍入；整数点按剩余目标缺口分配，保证不丢总预算、不降低已有属性，1级和30级精确匹配源码。',table(sample),
    '表为真实生成器各阶位预算均值；具体角色保留自己的随机起点/终点。T2—T5满级预算接近，稀有技能的机制差异仍存在；等级不自动提高技能倍率、发动率或次数。不同属性的战斗响应非线性，不要求每一级的胜率线性增加。model.py提供无第三方依赖的character_stats函数。',
    '## 阶段参考：不是对玩家状态的断言',table(pd.DataFrame([dict(阶段=f'S{s+1}',人数上限=STAGES[s][0],参考等级下限=lo,参考等级上限=hi,技能阶位上限=STAGES[s][-1],BP标尺=STAGES[s][1]) for s,(lo,hi) in enumerate(LEVEL_BANDS)])),
    '参考等级范围是本轮探索采用的初始进度方案，可根据游戏节奏调整；不是从真实玩家数据发现的规律。等级仅改变四维，BP保留阶段标尺。若游戏以后加入等级BP成长，也应作为独立预算通道重新标定，不能把本结果当作该成长已测试。',
    '五类准备程度都是输入条件，不是事先贴的胜负标签：培养不足使用较低角色阶位、等级区间下半段、75%普通装备属性；常规配置满编、主C2及最多4名保底；不同顺位使用相同成员与属性再打乱顺位；高收集使用阶段上限技能、较高等级、125%普通装备属性；四件顶级装备使用与常规相同角色/等级，加先前校准的四件配置。高阶技能也可能因条件与限次使回转变差，高收集不被预先强定为必胜。',
    '## 阶段＋难度的默认投放',table(recipe,['人数','难度','enemy_genre','rho_lower','rho_center','rho_upper','敌方BP下限','敌方BP上限','满血打击下限','满血打击上限','wr','wr_min','wr_max','turns']),
    '难/很难/非常难的常规参考胜率目标分别为70%—80%、55%—70%、45%—55%；它们是设计目标，不是败因分类。表中wr是六流派等权均值，wr_min/wr_max是流派均值范围，不能将群体均值解释成每个流派必然达到。没有强行约束回合或终局血量，实际指标一并输出。',
    'alpha定义敌方BP相对阶段标尺，beta定义满血基础打击通量。实际敌方BP=阶段BP×alpha×rho；满血基础打击力=0.135×阶段BP×beta×rho；战中仍按0.09MaxBP+0.045CurBP衰减，攻击补偿因子为beta/alpha。四维采用NPC模板的阶段等级成长和自然技能供给，均值在npc_reference_four_stats.csv；技能顺位、概率、门槛与限次不省略。',
    '不同技能类型共108组区间在fine_difficulty_intervals.csv。默认类型按常规胜率误差、六流派胜率跨度与截尾率综合筛选，再用偏移640的全新技能库确认。敌人固定，不读取真实玩家的阵容来反向调参。',
    '## 不同培养程度的实测范围',table(means[means.point=='center'].assign(难度=lambda x:x.difficulty.map(LABELS),准备程度=lambda x:x.preparation.map(PREP_LABELS)),['stage','难度','准备程度','wr','wr_min','wr_max','turns','censor']),
    '阶段stage从0起，对应S1—S6。上下端点的所有配置见recommended_profile_ranges.csv。某些极端收集/顺位样本的胜率显著偏离常规目标，是玩家状态造成的实际差异，保留这种差异，不强行抹平。',
    '## 泛用性与适用范围',table(curve_summary),
    '曲率和±3等级敏感度使用初始锚点做开放压力测试，不保证变更进度后仍落在相同难度带；大型进度改动应重标定。人数上限是阶段容量，不直接等于已拥有角色的强度。本轮双方均满编，未声称已覆盖缺员队伍、单敌人单技能或完整生产卡池经济。',
    '当前区间只联动BP和基础打击力，NPC技能类型与阶段四维分布作为模板保留。它是可使用的第一版标尺，未把四维、恢复、吸收等所有轴捏成一条万能公式。后续可按实际支线手感调节攻防比例，再走相同验证流程。',
    '## 复现、审计与证据',f'本轮协议覆盖{total:,}次仿真执行。训练/验证技能库偏移0/128；完整压力测试偏移384；推荐类型筛选后使用偏移640新库确认。角色成长用各自匹配的旧/新C#导出，不手造等级端点。逐参数SQLite落盘，完成CSV原子替换。',
    '所有未结束对局保留censor，wr表示已确认胜利比例，真实最终胜率可能在[wr,wr+censor]，不按血量强判胜负。成长单调性、端点、属性预算与校准数据校验见validation.json。旧满级研究保留，本轮成长条件下应采用新难度表。',
    '使用model.py：character_stats(等级,旧四维,满级四维,power=1)；encounter(阶段1—6,难度中文或代号,archetype=None,position="center")。默认返回推荐模板及对应人数上限、等级参考、敌方BP/打击力、NPC四维均值与常规胜率。JSON可以被游戏工具读取，本轮只新增研究模型，没有改Unity运行时。',
    '![成长与培养程度](results/figures/growth_and_preparation.png)']
    contents.insert(-2,f'### 额外泛用性试验：敌方四维均衡\n\n保持每个敌人成员的四维总预算不变，测试原分配、50%均衡、全均衡，并重新标定强度。独立确认后，六流派平均胜率跨度从{base_spread.mean()*100:.1f}降至{balanced_spread.mean()*100:.1f}个百分点，整体改善很小。因此默认指南继续使用原分配模板，保留均衡试验数据作为属性分配的适用边界；不能承诺简单均分就消除技能及成长阈值导致的差异。')
    contents.append('本轮只标定等级成长、阶段难度与五类准备程度压力；普通装备数值仍沿用上一轮的阶段参考，未新增装备等级规则。其他角色补强与装备五维机制仍以旧满级研究条件为依据，不能自动视为全等级均已重新验证。')
    (HERE/'DESIGN_GUIDE.md').write_text('\n\n'.join(contents)+'\n',encoding='utf-8');save_json(OUT/'experiment_manifest.json',dict(protocol_executions=total,stages=6,difficulties=3,npc_archetypes=6,preparation_scenarios=5,default_growth_power=1.,confirmation_catalog_offset=640))
    # Public pure-Python implementation must match the tested NumPy implementation.
    set_bank('training')
    for key in list(simulation.OLD)[::16]:
        for power in (.8,1.,1.25):
            path=grow_path(simulation.OLD[key],simulation.NEW[key],power)
            for level in range(1,31):assert tuple(character_stats(level,simulation.OLD[key],simulation.NEW[key],power).values())==path[level-1]
    assert set(final.stage)==set(range(6)) and set(final.genre)==set(GENRES);assert final.top_count.max()<=4
    save_json(OUT/'validation.json',dict(passed=True,public_growth_matches_simulation=True,endpoints_and_monotonicity=True,stage_count=6,player_flow_count=6,top_cap=4,recommendations_confirmed_on_new_catalog=True,reference_level_bands_are_assumptions=True))


if __name__=='__main__':main()
