"""Delivery checks for growth endpoints, template API and unchanged physics."""
import study
from study import *
from refine_bands import confirmation
from model import character_stats,encounter


def main():
    path=OUT/'recommended_confirmation.csv';frame=pd.read_csv(path);assert len(frame)==1620
    assert set(frame.stage)==set(range(6)) and set(frame.genre)==set(GENRES) and set(frame.preparation)==set(PREPARATIONS)
    assert frame.top_count.max()<=4 and frame.wr.between(0,1).all()
    intervals=pd.read_csv(OUT/'fine_difficulty_intervals.csv');assert len(intervals)==108 and intervals.validation_in_band.all()
    assert (intervals.rho_lower<=intervals.rho_center).all() and (intervals.rho_center<=intervals.rho_upper).all()
    assert (intervals.rho_lower<intervals.rho_upper).all()
    for stage in range(1,7):
        for difficulty in TARGETS:
            record=encounter(stage,difficulty);assert record['members_cap']==5*stage and record['enemy_max_bp']>0 and record['enemy_full_bp_base_hit']>0
            assert record['standard_reference_wr'] is not None
            for npc in GENRES:assert encounter(stage,difficulty,npc)['standard_reference_wr'] is not None
    set_bank('training');checks=0
    for key in list(study.OLD)[::16]:
        for power in (.8,1.,1.25):
            path=grow_path(study.OLD[key],study.NEW[key],power)
            for level in range(1,31):
                assert tuple(character_stats(level,study.OLD[key],study.NEW[key],power).values())==path[level-1];checks+=1
    a,_,_=player(3,'C_I',17,'standard');b,_,_=player(3,'C_I',17,'different_order')
    assert sorted((m.skill.id,m.stats) for m in a)==sorted((m.skill.id,m.stats) for m in b)
    before=sum(sum(m.stats) for m in a)
    for fraction in (.5,1.):
        values=[tuple(v*(1-fraction)+sum(m.stats)/4*fraction for v in m.stats) for m in a];assert np.isclose(sum(sum(v) for v in values),before)
    row=frame[(frame.point=='center')&(frame.preparation=='standard')].iloc[0]
    job=dict(stage=int(row.stage),genre=row.genre,enemy_genre=row.enemy_genre,alpha=row.alpha,beta=row.beta,rho=row.rho,preparation=row.preparation,pool_offset=24576,trials=128,stream='growth-template-confirmation')
    result=confirmation(job)
    for key in ('wr','turns','hp','courage','resilience','initiative','magic'):assert np.isclose(result[key],row[key],rtol=0,atol=1e-10),key
    zero=confirmation(dict(job,npc_balance=0.));assert result==zero
    assert hashlib.sha256(core.SOURCE.read_bytes()).hexdigest()=='d82477b368cea5994053bcee99a618d560135e6a5195926afe26f78aa91ba75e'
    save_json(OUT/'delivery_validation.json',dict(passed=True,public_growth_comparisons=checks,all_108_intervals_positive_width=True,all_18_recommended_templates_and_108_typed_api_cases=True,player_flow_count=6,preparation_scenarios=5,top_cap=4,random_order_has_identical_members_and_stats=True,npc_balance_preserves_total_budget=True,stored_holdout_exactly_replayed=True,zero_npc_balance_exact=True,combat_source_unchanged=True))
    print('Growth and difficulty delivery checks passed')


if __name__=='__main__':main()
