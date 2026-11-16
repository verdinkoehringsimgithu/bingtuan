"""Derive reviewable numeric tables from measured results, without simulations."""
from run_natural import *
from collections import defaultdict
from scipy.stats import norm


def main():
    tuned=pd.read_csv(OUT/'tuned_reachability.csv.gz');standard=tuned[(tuned.profile=='mixed')&(tuned.stock==0)]
    four=standard.groupby(['stage','genre'])[[*FIELDS,'raw_total','item_total']].mean().reset_index();csv('player_four_stat_baseline.csv',four)
    enemy_values=[]
    for scene in pd.read_csv(OUT/'difficulty_delivery_candidates.csv').itertuples():
        aggregates=[]
        for j in range(128):
            pack=roster(scene.stage,scene.opponent,j+8192+7,validation=True);v=np.sum([m.stats for m in pack],axis=0)*np.array([getattr(scene,k) for k in ('scale_c','scale_r','scale_i','scale_m')]);v[2]=max(0,v[2]+scene.theta);aggregates.append(v)
        mean=np.array(aggregates).mean(0);enemy_values.append(dict(stage=scene.stage,genre=scene.genre,difficulty=scene.difficulty,opponent=scene.opponent,max_bp=STAGES[scene.stage][1]*scene.alpha,full_bp_base_hit=.135*STAGES[scene.stage][1]*scene.beta,regen_per_round=STAGES[scene.stage][1]*scene.alpha*scene.delta,**dict(zip(FIELDS,mean))))
    csv('enemy_absolute_delivery.csv',pd.DataFrame(enemy_values))
    fresh=pd.read_csv(OUT/'reachability_fresh_catalog_holdout.csv');coverage=[]
    for (s,g),sub in fresh.groupby(['stage','genre']):
        n=STAGES[s][0];main,secondary=STAGES[s][2:4]
        required=np.maximum.reduce([np.zeros(len(sub)),(main-sub.raw_main)/(.67*n),(secondary-sub.raw_sub)/(.33*n)])
        coverage.append(dict(stage=s,genre=g,measured_equipment_points=COMMON[(s,g)],coverage_points_median=np.median(required),coverage_points_p95=np.quantile(required,.95),coverage_points_max=required.max(),coverage_integer_points=math.ceil(required.max()),raw_main_mean=sub.raw_main.mean(),raw_sub_mean=sub.raw_sub.mean(),equipped_main_mean=sub.main.mean(),equipped_sub_mean=sub['sub'].mean(),reached=sub.reached.mean()))
    csv('ordinary_coverage_bounds.csv',pd.DataFrame(coverage))
    stats=defaultdict(lambda:defaultdict(float))
    for s in range(6):
        for g in GENRES:
            for d in (3,4):
                with gzip.open(OUT/f'owners_S{s+1}_{g}_D{d}.jsonl.gz','rt',encoding='utf-8') as source:
                    for line in source:
                        record=json.loads(line)
                        for owner in record['members']:
                            row=stats[(s,g,owner['role'])];row['observations']+=1;row['casts']+=owner.get('casts',0);row['expected_cast']+=owner.get('expected_cast',0);row['eligible_rounds']+=owner.get('eligible_rounds',0);row['expected_reached']+=owner.get('expected_reached',0);row['damage']+=owner.get('damage',0);row['total_stats']+=sum(owner['stats'])
    records=[]
    for (s,g,role),value in stats.items():
        observations=value['observations'];records.append(dict(stage=s,genre=g,role=role,n_owners=int(observations),casts_per_battle_owner=value['casts']/observations,expected_casts_per_owner=value['expected_cast']/observations,eligible_checks_per_owner=value['eligible_rounds']/observations,reach_checks_per_owner=value['expected_reached']/observations,damage_per_owner=value['damage']/observations,personal_raw_stat_mean=value['total_stats']/observations))
    csv('equipment_owner_exposure.csv',pd.DataFrame(records))
    m=pd.read_csv(OUT/'mainc_mechanism_scan.csv');r=[]
    for (s,g,k),sub in m.groupby(['stage','genre','kind']):
        sub=sub.sort_values('value');positive=sub[(sub.value>0)&(sub.delta_lo>0)];slopes=np.gradient(sub.wr,sub.value);i=int(np.argmax(slopes));idx=min(max(1,i),len(sub)-1)
        r.append(dict(stage=s,genre=g,kind=k,positive_lower=positive.value.min() if len(positive) else np.nan,scanned_max=sub.value.max(),max_measured_gain=sub.delta.max(),largest_slope=slopes[i],transition_lower=sub.value.iloc[idx-1],transition_upper=sub.value.iloc[idx],variance_floor_ratio_min=(sub.loss_variance/np.maximum(sub.base_loss_variance,1e-12)).min()))
    csv('mainc_five_demands.csv',pd.DataFrame(r))
    cross=pd.read_csv(OUT/'crossflow_versatility.csv');rows=[]
    for (s,h,mode),sub in cross.groupby(['stage','opponent','mode']):rows.append(dict(stage=s,opponent=h,mode=mode,wr_min=sub.wr.min(),wr_max=sub.wr.max(),spread_pp=100*(sub.wr.max()-sub.wr.min()),mean_wr=sub.wr.mean()))
    csv('versatility_spread.csv',pd.DataFrame(rows))
    rows=[]
    for (s,g,mode),sub in cross.groupby(['stage','genre','mode']):rows.append(dict(stage=s,genre=g,mode=mode,best_wr=sub.wr.max(),worst_wr=sub.wr.min(),spread_pp=100*(sub.wr.max()-sub.wr.min())))
    csv('specialization_boundaries.csv',pd.DataFrame(rows))
    path=pd.read_csv(OUT/'strategic_paths_holdout.csv');scenarios=pd.read_csv(OUT/'strategic_loadout_scan.csv');chosen=scenarios.sort_values('delta_lo',ascending=False).groupby(['stage','genre','path']).head(1)
    path=path.merge(chosen[['stage','genre','path','base_wr','base_turns']].rename(columns={'base_wr':'selection_base_wr','base_turns':'selection_base_turns'}),on=['stage','genre','path'])
    path['eligible_trigger']=np.where(path.path=='expand',abs(path.selection_base_wr-.65)<=.05,np.where(path.path=='counter',path.selection_base_wr<=.30,(path.selection_base_turns>=8)&(abs(path.selection_base_wr-.5)<=.1)))
    path['meets_requested_result']=np.where(path.path=='expand',(path.wr>=.92)&((1-path.wr)<.05),np.where(path.path=='counter',path.wr.between(.45,.55),path.delta>=.30))
    path['significant_gain']=path.delta_lo>0;csv('strategic_path_acceptance.csv',path)
    clusters=pd.read_csv(OUT/'unique_normal_budget_fresh_clusters.csv');se=(clusters.delta_hi-clusters.delta_lo)/(2*1.96);z=np.divide(clusters.delta,np.maximum(se,1e-12));p=2*norm.sf(abs(z));order=np.argsort(p);q=np.empty(len(p));q[order]=np.minimum(1,np.minimum.accumulate((p[order]*len(p)/np.arange(1,len(p)+1))[::-1])[::-1]);clusters['p_two_sided_normal']=p;clusters['bh_q']=q;csv('unique_cluster_multiple_comparison.csv',clusters)
    save_json(OUT/'evidence_status.json',dict(excluded_from_final_evidence=['candidate_reachability.csv.gz','candidate_reachability_summary.csv','stat_optimization_training.csv'],reason='Written before exact C# allocation residual-order mirror fix; final reachability uses real source exports and unseen catalog.',actual_source_export='catalog_current.json and catalog_final_test.json',generator_status='feasible selected global budget profile, not a proven global optimum',curve_interpretation='Finite differences and observed response knees; transition brackets do not prove mathematical phase transitions; scanned maximum is not an enforced attribute cap',cluster_interpretation='Retrospective complete-trajectory clusters, low silhouette in several stages; not intrinsically separated failure classes',skill_decay_audit='Canonical source has BP-weighted base damage, finite-use exhaustion, eligibility gates, debuff duration countdown and late-owner activation attenuation. No additional per-cast multiplier decay formula was found; no such rule was invented.'))


if __name__=='__main__':main()
