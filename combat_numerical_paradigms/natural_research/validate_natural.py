"""Source parity, additional generator effects, passive budgets and native guard."""
from run_natural import *
import contextlib,io,ast

def run():
    before=json.loads((OUT/'catalog_before.json').read_text(encoding='utf-8'));after=json.loads((OUT/'catalog_current.json').read_text(encoding='utf-8'))
    fields=('turn_cond1','turn_cond2','self_bp_cond1','self_bp_cond2','enemy_bp_cond1','enemy_bp_cond2','trigger_chance','times_limit','effect_type','param','param2')
    assert len(before)==len(after)==3072
    assert all(all(a['csv'][f]==b['csv'][f] for f in fields) for a,b in zip(before,after))
    budgets=PROFILE['budgets'];p=PROFILE['primary'];q=PROFILE['secondary']
    for record in after:
        skill,stats=convert(record);assert budgets[skill.tier-1][0]<=sum(stats)<=budgets[skill.tier-1][1]
        assert stats==allocation(NAME_TO_LETTER[skill.genre],sum(stats),p,q)
    # Current-BP healing is distinct from max-BP healing and independent of magic.
    m=copy.deepcopy(roster(5,'C_I'));a=Team(m);a.current_bp=a.max_bp*.5;a.selected_original=engine.BattleSkill(1,'check',2,'坚韧','Heal',sub_effect_name='当前战力自愈');a.heal_channel='self_heal';assert a.heal(a.max_bp*.2)==a.max_bp*.1
    # A fixed DoT remains absolute after the target's BP is changed.
    for alpha in (1.,2.):
        s=engine.BattleSkill(1,'fixed-check',2,'魔力',main_param=1,trigger_chance=100,times_limit=1,base_crit_rate=1,sub_effect_name='固定流失',sub_param=5000,sub_duration=2)
        am=(Member(0,'carry',(100,100,100,100),1000000,s),);bs=engine.BattleSkill(1,'normal',1,'勇气',trigger_chance=0)
        bm=(Member(0,'filler',(100,100,100,100),1000000*alpha,bs),);ta=Team(am);tb=Team(bm);random.seed(1);core.ACTION(ta,tb,True,1)
        amount=tb.max_bp*tb.max_bp_dots[0]['val'];expected=5000*engine.calc_magic_amp_responsive(100);assert np.isclose(amount,expected)
    # Physical pressure follows the remaining BP after its direct hit and accepts resilience.
    s=engine.BattleSkill(1,'pressure-check',2,'勇气',trigger_chance=100,base_crit_rate=1,sub_effect_name='敌方当前压制',sub_param=.12)
    ta=Team((Member(0,'carry',(100,100,100,100),1000000,s),));tb=Team((Member(0,'filler',(100,100,100,100),1000000,bs),));random.seed(4);core.ACTION(ta,tb,True,1)
    direct=ta.metrics['physical']+ta.metrics['physical_crit'];expected=(1000000-direct)*.12*(1-engine.calc_resilience_dr(100)[1]);assert np.isclose(ta.metrics['current_pressure'],expected)
    jobs=[dict(stage=s,genre=GENRES[s],opponent=GENRES[(s+1)%6],p=[1.2,1.1,0,0,0,1,1,1,1,1],trials=24,validation=True,stream='natural-parallel-check') for s in range(6)]
    serial=[evaluate(j) for j in jobs]
    with cf.ProcessPoolExecutor(2) as pool:parallel=list(pool.map(evaluate,jobs))
    assert serial==parallel
    data=core.parity_test(600);data.update(stat_export_cases=3072,active_parameters_unchanged=True,source_stat_allocation_exact=True,current_bp_heal_passed=True,fixed_dot_absolute_passed=True,current_pressure_defense_passed=True,serial_parallel_equal=True)
    random.seed(20261012);buffer=io.StringIO()
    with contextlib.redirect_stdout(buffer):engine.run_full_stress_test(2500)
    (OUT/'native_37500_regression.txt').write_text(buffer.getvalue(),encoding='utf-8');rates=[float(re.findall(r'([\d.]+)%',line)[-1]) for line in buffer.getvalue().splitlines() if len(re.findall(r'([\d.]+)%',line))==7];assert len(rates)==6 and max(rates)-min(rates)<=15
    data['native_spread_pp']=max(rates)-min(rates);save_json(OUT/'model_validation.json',data);print(json.dumps(data,ensure_ascii=False),flush=True)

if __name__=='__main__':run()
