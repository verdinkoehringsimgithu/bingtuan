"""Verify normal-budget, single-owner mechanisms separately from concentration."""
from advanced_study import *
from refine_delivery import bank_initializer


def main():
    source=pd.read_csv(OUT/'mainc_mechanism_scan.csv');source=source[source.value>0].copy();source['distance']=(source.delta-.25).abs()
    chosen=source.sort_values(['distance','value']).groupby(['stage','genre']).head(1);csv('unique_normal_budget_candidates.csv',chosen[['stage','genre','kind','value']]);meta=[];jobs=[];scenes=pd.read_csv(OUT/'difficulty_candidates.csv')
    for row in chosen.itertuples():
        scene=scenes[(scenes.stage==row.stage)&(scenes.genre==row.genre)&(scenes.difficulty==4)].iloc[0]
        meta.append(dict(stage=row.stage,genre=row.genre,kind=row.kind,value=row.value));jobs.append(dict(stage=int(row.stage),genre=row.genre,opponent=scene.opponent,p=[float(scene[k]) for k in PARAMS],solo_kind=row.kind,solo_value=row.value,validation=True,pool_offset=20480,trials=1200,cluster_results=True,stream='unique-normal-budget-fresh'))
    if not (OUT/'unique_normal_budget_fresh_holdout.csv').exists():
        with cf.ProcessPoolExecutor(4,initializer=bank_initializer) as pool:results=list(pool.map(advanced_evaluate,jobs))
        csv('unique_normal_budget_fresh_holdout.csv',pd.concat([pd.DataFrame(meta),pd.DataFrame(results)],axis=1))
    final=pd.read_csv(OUT/'unique_normal_budget_fresh_holdout.csv');clusters=[]
    for row in final.to_dict('records'):
        for entry in json.loads(row['clusters']):clusters.append({**{k:row[k] for k in ('stage','genre','kind','value')},**entry})
    csv('unique_normal_budget_fresh_clusters.csv',pd.DataFrame(clusters));save_json(OUT/'unique_normal_budget_manifest.json',dict(fresh_executions=86400,normal_generator_personal_budget_preserved=True,extra_top_mechanisms=1,final_catalog_offset=384,selection_objective='closest measured overall gain to 25 percentage points; cluster conditional results are post-selection verification, not preassigned failure classes'))


if __name__=='__main__':main()
