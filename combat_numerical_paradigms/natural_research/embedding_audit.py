"""Fresh paired embedding checks: output, actual new effects and defense."""
from advanced_study import *
from refine_delivery import bank_initializer


def check(job):
    results=[];changes=[];novel=0;activated=0;dr_changes=[];weak_changes=[];heal_changes=[]
    for j in range(800):
        original=members({**job,'foreign':None},j);replaced=members(job,j);enemy=members(job,j,True);rs=seed('embedding-mechanism-fresh',job['stage'],job['genre'],j)
        before,bf,br,bo=simulate(original,enemy,rs,items(original,job),p=job['p'][:6],telemetry=True);after,af,ar,ao=simulate(replaced,enemy,rs,items(replaced,job),p=job['p'][:6],telemetry=True);results.append(after);changes.append((before,after))
        pos=job['foreign_position'];old_types={m.skill.sub_effect_name for m in original};new_type=replaced[pos].skill.sub_effect_name
        added=bool(new_type and new_type not in old_types);novel+=added
        # Actual effects require a successful hit; owned heal/damage metrics are observed, not promised by equip labels.
        used=ao[pos].get('casts',0)>0 and (ao[pos].get('damage',0)>0 or ao[pos].get('self_heal',0)>0);activated+=added and used
        x=Team(original,items(original,job));y=Team(replaced,items(replaced,job));dr_changes.append(engine.calc_resilience_dr(y.base_resilience)[1]-engine.calc_resilience_dr(x.base_resilience)[1]);weak_changes.append(enrich(af,ar)['e_weak_area']-enrich(bf,br)['e_weak_area']);heal_changes.append(af['p_self_heal_flux']-bf['p_self_heal_flux'])
    base=summarize([x[0] for x in changes]);final=summarize(results);difference=np.array([a['win']-b['win'] for b,a in changes]);err=difference.std(ddof=1)/math.sqrt(len(difference))
    return dict(**final,base_wr=base['wr'],delta=difference.mean(),delta_lo=difference.mean()-1.96*err,delta_hi=difference.mean()+1.96*err,output_ratio=final['damage_per_round']/base['damage_per_round'],novel_effect_available_rate=novel/800,novel_effect_activated_rate=activated/800,pct_dr_change_mean=np.mean(dr_changes),enemy_weak_area_change=np.mean(weak_changes),self_heal_flux_change=np.mean(heal_changes))


def main():
    if (OUT/'embedding_mechanism_fresh_holdout.csv').exists():return
    data=pd.read_csv(OUT/'heterogeneous_holdout.csv');chosen=[]
    for _,group in data.groupby(['stage','genre']):
        eligible=group[group.output_ratio>=.95];chosen.append((eligible if len(eligible) else group).sort_values('delta_lo',ascending=False).iloc[0].to_dict())
    scenes=pd.read_csv(OUT/'difficulty_candidates.csv');meta=[];jobs=[]
    for row in chosen:
        scene=scenes[(scenes.stage==row['stage'])&(scenes.genre==row['genre'])&(scenes.difficulty==4)].iloc[0];meta.append({k:row[k] for k in ('stage','genre','foreign','position')})
        jobs.append(dict(stage=int(row['stage']),genre=row['genre'],foreign=row['foreign'],foreign_position=int(row['position']),opponent=scene.opponent,p=[float(scene[k]) for k in PARAMS],validation=True,pool_offset=28672))
    with cf.ProcessPoolExecutor(4,initializer=bank_initializer) as pool:results=list(pool.map(check,jobs))
    csv('embedding_mechanism_fresh_holdout.csv',pd.concat([pd.DataFrame(meta),pd.DataFrame(results)],axis=1));save_json(OUT/'embedding_audit_manifest.json',dict(fresh_executions=57600,final_catalog_offset=384,interpretation='New effect availability and actual activation are separate. Changes in enemy output also reflect fight duration and offense, and are not automatically attributed to resistance.'))


if __name__=='__main__':main()
