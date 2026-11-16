"""Behavioural verification before running any effect search."""
import copy
import json
import random
import time
from pathlib import Path
from rosters import build, natural, seed, availability, GENRES
from bond_core import simulate, Team, World, select, attack, make_action, deal, post_attack


def fixture(names, chance=100, limit=999, main=100):
    members=[]
    for pos,name in enumerate(names):
        s=natural.engine.BattleSkill(pos+1,'fixture',4,'勇气',main_param=main,trigger_chance=chance,times_limit=limit)
        m=natural.Member(pos,'carry',(50.,50.,50.,50.),200000./len(names),s)
        m.identity=name;m.level=20;m.person_id=str(pos);members.append(m)
    return tuple(members),tuple(natural.Item() for _ in members)


def run():
    checks=[]
    def check(name,condition):
        if not condition:raise AssertionError(name)
        checks.append(name)
    start=time.perf_counter()
    # Exact legacy RNG parity isolates the extension from the old model.
    for j in range(120):
        stage=j%6;g=GENRES[j%6];h=GENRES[(j//6)%6]
        m,it=build(stage,g,j,(),bank_name='training',preparation='four_top' if j%3==0 else 'standard')
        e,ei=build(stage,h,j+100003,(),bank_name='training')
        bs=seed('bond-parity',j)
        old,*_=natural.simulate(m,e,bs,it,ei)
        new,*_=simulate(m,e,bs,it,ei,legacy=True)
        for key in ('win','censored','draw','turns','hp','enemy_hp','normal_rate'):
            check(f'parity_{j}_{key}',abs(old[key]-new[key])<1e-9)
    for stage in range(6):
        m,it=build(stage,'M_R',3,(('maid',2),))
        back,bit=build(stage,'M_R',3,(('maid',2),),'back')
        check(f'order_preserves_people_skills_equipment_{stage}',
              sorted((x.person_id,x.skill.id,x.skill.main_param,x.level,y.kind,y.stats) for x,y in zip(m,it))==
              sorted((x.person_id,x.skill.id,x.skill.main_param,x.level,y.kind,y.stats) for x,y in zip(back,bit)))
    m,it=fixture(['女仆','剑士','剑士'],chance=0,limit=1)
    for x in m:x.skill.turn_cond1=99;x.skill.turn_cond2=1;x.skill.self_bp_cond2=1;x.skill.enemy_bp_cond2=1
    e,ei=fixture(['军人'])
    r,rows,a,b=simulate(m,e,100,it,ei,enabled=('maid',),telemetry=True,max_turns=8)
    check('maid_ignores_gates_chance_limit',a.casts[0]==r['turns'] and a.casts[0]>1)
    check('maid_blocks_later_positions',a.casts[1:]==[0,0])
    m,it=fixture(['剑士','剑士','剑士'],limit=2,main=1)
    r,rows,a,b=simulate(m,e,101,it,ei,enabled=('sword',),config={'sword':100.,'sword_decay':1.},telemetry=True,max_turns=1)
    check('sword_three_extras_four_total',a.metrics['sword_extras']==3 and sum(a.casts)==4)
    check('sword_consumes_actual_uses',sum(a.usage.values())==4 and all(v<=2 for v in a.usage.values()))
    m,it=fixture(['工程师','忍者']);w=World(1);a=Team(m,it,0,w,('engineer','ninja'));b=Team(e,ei,1,w)
    original=a.get_effective_stats();post_attack(a,b,0,True,True);post_attack(a,b,1,True,True)
    check('growth_deferred_entire_round',a.get_effective_stats()==original and a.ninja_growth==0 and a.pending_ninja>0)
    a.round_commit();check('growth_commits_next_round',a.ninja_growth>0)
    m,it=fixture(['帮派']);m[0].skill.sub_effect_name='最大流失';m[0].skill.sub_param=.5
    r,_,a,b=simulate(m,e,5,it,ei,enabled=('gang',),max_turns=1)
    check('gang_no_original_skill_or_usage',not a.usage and a.casts==[0] and not b.max_bp_dots and a.metrics['gang_attacks']==1)
    m,it=fixture(['农民','农民']);w=World(1);a=Team(m,it,0,w,('farmer',));b=Team(e,ei,1,w);a.turn=1
    post_attack(a,b,0,False,False);check('shared_fruit_plant_five_rounds',a.fruit_ready==6)
    post_attack(a,b,1,False,False);check('shared_fruit_accelerates_same_fruit',a.fruit_ready==5 and a.metrics['fruit_planted']==1)
    a.turn=6;post_attack(a,b,0,False,False);check('shared_fruit_single_harvest',a.fruit_ready is None and a.metrics['fruit_harvest']==1)
    m,it=fixture(['行商']);m[0].stats=(10,100,50,25);w=World(1);a=Team(m,it,0,w,('merchant',));b=Team(e,ei,1,w)
    opening=a.cur_courage;a.turn=2;a.round_commit();check('merchant_opening_once',a.cur_courage==opening and opening>10)
    m,it=fixture(['盗贼']);w=World(1);a=Team(m,it,0,w,('thief',));b=Team(e,ei,1,w)
    before=[x+y for x,y in zip(a.get_effective_stats(),b.get_effective_stats())]
    post_attack(a,b,0,False,False)
    check('thief_conserves_four_stats',all(abs(x-y-z)<1e-9 for x,y,z in zip(before,a.get_effective_stats(),b.get_effective_stats())))
    fresh=Team(e,ei,1,w);check('thief_does_not_persist',fresh.get_effective_stats()==(50,50,50,50))
    m,it=fixture(['社畜']);a=Team(m,it,0,w,('worker',));b=Team(e,ei,1,w)
    deal(b,a,1e7,'fixture');check('worker_survives_first_lethal',a.current_bp>0 and a.worker_used)
    deal(b,a,1e7,'fixture');check('worker_only_once',a.current_bp==0 and a.metrics['worker_procs']==1)
    m,it=fixture(['杀手']);a=Team(m,it,0,w,('killer',));b=Team(e,ei,1,w);a.turn=b.turn=1
    post_attack(a,b,0,True,True);check('killer_sets_next_skill_mark',b.next_heal_penalty>0)
    select(b,a,1);check('killer_consumed_by_next_skill',b.next_heal_penalty==0 and b.recovery_factor<1)
    select(b,a,1);check('killer_does_not_affect_following_skill',b.recovery_factor==1)
    m,it=fixture(['军人']);e,ei=fixture(['忍者']);a=Team(m,it,0,w,('military',),{'military_hit':100.});b=Team(e,ei,1,w,('ninja',),{'ninja_base':100.,'ninja_cap':1.})
    a.turn=b.turn=1;w.actor=a;attack(a,b,True,1,make_action(w))
    check('forced_hit_overrides_absolute_dodge',a.last_hit and b.metrics['absolute_dodges']==0)
    m,it=fixture(['女仆']);it=(natural.Item('skill_crit',.4,top=True),)
    a=Team(m,it,0,w,('maid',));b=Team(e,ei,1,w);a.turn=b.turn=1
    skill=select(a,b,1)
    check('maid_replacement_preserves_owner_equipment',skill.base_crit_rate==.4 and a.overflow_convert==1.)
    m,it=fixture(['军人']);a=Team(m,it,0,w,('worker',))
    deal(b,a,1e7,'fixture');check('missing_identity_cannot_activate_bond',a.is_dead() and not a.worker_used)
    # Full telemetry must be serializable, including generated integer stats.
    m,it=build(5,'M_R',81,(('engineer',5),));e,ei=build(5,'C_R',91,())
    r,trace,a,b=simulate(m,e,5,it,ei,enabled=('engineer',),telemetry=True)
    json.dumps(dict(result=r,trace=trace,members=[dict(stats=x.stats,skill=vars(x.skill)) for x in m]))
    check('full_telemetry_serializable',True)
    # No-op enabled mechanisms must exactly match no mechanisms under keyed RNG.
    for j in range(12):
        m,it=build(j%6,'C_R',j,(('hunter',2),));e,ei=build(j%6,'M_R',j+1000,())
        x,*_=simulate(m,e,j,it,ei)
        y,*_=simulate(m,e,j,it,ei,enabled=('hunter',),config={'gain':0})
        check('zero_gain_'+str(j),x==y)
    return dict(passed=True,checks=len(checks),seconds=time.perf_counter()-start,names=checks)


if __name__=='__main__':
    result=run();path=Path(__file__).parent/'results';path.mkdir(exist_ok=True)
    (path/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='names'},ensure_ascii=False))
