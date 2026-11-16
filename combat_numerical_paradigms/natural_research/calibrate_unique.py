"""Single-owner share and amplification response; four fixed-budget controls."""
from advanced_study import *
from refine_delivery import bank_initializer


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=4);args=parser.parse_args();study=AdvancedStudy(args.workers);meta=[];jobs=[]
    for s in range(6):
        for g in GENRES:
            for share in (.05,.1,.15,.2,.25,.3,.4,.5):
                for value in (.25,.5,1.,2.):
                    meta.append(dict(stage=s,genre=g,share=share,value=value));jobs.append(dict(**study.scene(s,g,4),owner_target_share=share,solo_kind='owner_stats',solo_value=value,trials=128,stream='unique-budget-training'))
    data=study.table('unique_budget_response.csv',meta,jobs);data['target_distance']=(data.delta-.25).abs()
    # The target is a gain objective. Cost is share times multiplier; budgets stay conserved before the item.
    data['team_bonus_fraction']=data.share*data.value
    selected=data.sort_values(['target_distance','team_bonus_fraction','share']).groupby(['stage','genre']).head(1);csv('unique_budget_candidates.csv',selected[['stage','genre','share','value']]);study.finish('unique_budget_training_manifest.json')
    if not (OUT/'unique_budget_fresh_controls.csv').exists():
        meta=[];jobs=[]
        for r in selected.itertuples():
            for control in ('original','redistribution_only','mechanism_only','both'):
                share=r.share if control in ('redistribution_only','both') else None;enabled=control in ('mechanism_only','both')
                meta.append(dict(stage=r.stage,genre=r.genre,control=control,share=r.share,value=r.value))
                jobs.append(dict(**study.scene(r.stage,r.genre,4),owner_target_share=share,solo_kind='owner_stats' if enabled else None,solo_value=r.value,validation=True,pool_offset=18432,trials=800,cluster_results=True,stream='unique-budget-fresh'))
        with cf.ProcessPoolExecutor(args.workers,initializer=bank_initializer) as pool:results=list(pool.map(advanced_evaluate,jobs))
        final=pd.concat([pd.DataFrame(meta),pd.DataFrame(results)],axis=1);csv('unique_budget_fresh_controls.csv',final)
    final=pd.read_csv(OUT/'unique_budget_fresh_controls.csv');clusters=[]
    for row in final.to_dict('records'):
        for entry in json.loads(row['clusters']):clusters.append({**{k:row[k] for k in ('stage','genre','control','share','value')},**entry})
    csv('unique_budget_fresh_clusters.csv',pd.DataFrame(clusters))
    save_json(OUT/'unique_budget_manifest.json',dict(training_executions=294912,fresh_holdout_executions=230400,budget_conserved_before_item=True,final_catalog_offset=384,mechanism='owner_stats multiplies only holder personal stats; whole-team budget grows by share*value via that item',interpretation='Role budget concentration alone has no benefit in team-sum physics. This is a calibrated holder-dependent mechanism recipe, not a new character implemented in the game.'))


if __name__=='__main__':main()
