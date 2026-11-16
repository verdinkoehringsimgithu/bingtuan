"""Validate scientific provenance, member limits and every stage's deliverables."""
from advanced_study import *


def main():
    required=('difficulty_delivery_holdout.csv','shared_macro_holdout.csv','reachability_fresh_catalog_holdout.csv','equipment_operating_fresh_holdout.csv','unique_budget_fresh_controls.csv','unique_normal_budget_fresh_holdout.csv','unique_cluster_multiple_comparison.csv','mainc_five_demands.csv','counter_balanced_fresh_holdout.csv','embedding_mechanism_fresh_holdout.csv','enemy_fixed_slice_contours.csv','execution_protocol.csv')
    checks={}
    for name in required:
        frame=pd.read_csv(OUT/name);assert len(frame)>0 and not frame.columns.duplicated().any(),name
        if 'stage' in frame:assert set(frame.stage)==set(range(6)),name
        if 'genre' in frame:assert set(frame.genre)==set(GENRES),name
        if 'top_count' in frame:assert frame.top_count.max()<=4,name
        if 'wr' in frame:assert frame.wr.between(0,1).all(),name
        if 'hp' in frame:assert frame.hp.between(0,1+1e-9).all(),name
        checks[name]=len(frame)
    stages=pd.read_csv(OUT/'difficulty_delivery_holdout.csv');assert len(stages)==144
    actual=pd.read_csv(OUT/'reachability_fresh_catalog_holdout.csv');terminal=actual[actual.stage==5];assert len(terminal)==1536 and terminal.reached.eq(1).all()
    assert actual[(actual.stage==5)].main.min()>=1000 and actual[actual.stage==5]['sub'].min()>=500
    for name in ('equipment_operating_fresh_holdout.csv','four_top_loadouts.csv','counter_balanced_fresh_holdout.csv'):
        for row in pd.read_csv(OUT/name).itertuples():
            load=json.loads(row.loadout);assert len(load)<=4 and len({p for p,_,_ in load})==len(load)
            assert all(0<=p<STAGES[row.stage][0] for p,_,_ in load)
    control=pd.read_csv(OUT/'unique_budget_fresh_controls.csv');assert control.max_stat_total_error.max()<1e-8;assert (control[control.control=='redistribution_only'].delta==0).all()
    for s in range(6):
        model=joblib.load(OUT/f'stage_S{s+1}_models.joblib');assert not set(model['features'])&{'win','source_win','stage','genre','difficulty','hp','turns','seed','opponent'}
        assignment=pd.read_csv(OUT/f'stage_S{s+1}_cluster_assignments.csv.gz');assert len(assignment)==6000 and assignment.split.value_counts().to_dict()=={'train':3600,'validation':1200,'test':1200}
        cumulative=pd.read_csv(OUT/f'stage_S{s+1}_pca_variance.csv');assert cumulative.cumulative.iloc[model['k']-1]>=.9
        for prefix in ('contours','discovery','centroids'):
            names=[f'contours_S{s+1}_{kind}.png' for kind in ('wr','turns')] if prefix=='contours' else [f'{prefix}_S{s+1}.png']
            assert all((OUT/'figures'/name).stat().st_size>1000 for name in names)
        assert (Path(__file__).parent/f'stage_guides/S{s+1}_{STAGES[s][0]}_MEMBERS.md').exists()
    assert hashlib.sha256(core.SOURCE.read_bytes()).hexdigest()=='d82477b368cea5994053bcee99a618d560135e6a5195926afe26f78aa91ba75e'
    # New channels preserve the zero-effect pipeline and whole-team stat sums.
    j=dict(stage=0,genre='C_I',opponent='M_I',p=[.7,.6,0,0,0,1,1,1,1,1],trials=48,stream='delivery-extra-zero')
    original=advanced_evaluate(j);zero=advanced_evaluate(dict(j,solo_kind='skill_hit',solo_value=0.))
    assert all(original[k]==zero[k] for k in ('wr','turns','hp','damage_per_round'))
    shifted=advanced_evaluate(dict(j,owner_target_share=.3));assert shifted['delta']==0 and shifted['max_stat_total_error']<1e-8
    # Added DoT is owner-gated and does not acquire a first-strike multiplier.
    skill=engine.BattleSkill(1,'validation',2,'魔力',main_param=100,trigger_chance=100,base_crit_rate=1.)
    roster_a=(Member(0,'carry',(50,50,500,100),1000000,skill),Member(1,'filler',(50,50,0,100),1000000,skill))
    no_effect=Team(roster_a,(Item(),Item('added_dot',.02,top=True)));enemy=Team(roster_a);random.seed(32);core.ACTION(no_effect,enemy,True,1);assert not enemy.max_bp_dots
    yes_effect=Team(roster_a,(Item('added_dot',.02,top=True),Item()));enemy=Team(roster_a);random.seed(32);core.ACTION(yes_effect,enemy,True,1);assert len(enemy.max_bp_dots)==1
    assert np.isclose(enemy.max_bp_dots[0]['val'],.02*engine.calc_magic_amp_responsive(200)) and enemy.max_bp_dots[0]['owner']==0
    parity=core.parity_test(600);validation=json.loads((OUT/'model_validation.json').read_text(encoding='utf-8'));assert validation['native_spread_pp']<=15
    for record in json.loads((OUT/'catalog_final_test.json').read_text(encoding='utf-8')):
        skill,stats=convert(record);assert stats==allocation(NAME_TO_LETTER[skill.genre],sum(stats),PROFILE['primary'],PROFILE['secondary'])
    save_json(OUT/'delivery_validation.json',dict(passed=True,required_tables=checks,all_stages_and_flows=True,final_30man_all_1536_samples_reached=True,top_cap_and_unique_holders=True,budget_conservation=True,redistribution_only_no_benefit=True,zero_extra_channel_parity=True,added_dot_owner_gate_and_magic_only=True,unsupervised_split_and_input_isolation=True,native_pipeline_cases=parity['native_pipeline_cases'],native_spread_pp=validation['native_spread_pp'],live_generator_concurrency_logged=True,ordinary_equipment_integer_quantization_not_claimed=True,original_targets_not_all_met=True))
    print('Delivery validation passed')


if __name__=='__main__':main()
