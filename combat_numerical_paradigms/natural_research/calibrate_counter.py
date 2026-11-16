"""Dose-response for the counter path, preserving the measured hostile scenario."""
from advanced_study import *
from refine_delivery import bank_initializer


def main():
    study=AdvancedStudy(4);data=pd.read_csv(OUT/'strategic_loadout_scan.csv');best=data[data.path=='counter'].sort_values('delta_lo',ascending=False).groupby(['stage','genre']).head(1);meta=[];jobs=[]
    for r in best.itertuples():
        for strength in (0.,.1,.2,.3,.4,.5,.6,.8,1.):
            load=[(j,r.kind,r.value*strength) for j in range(4)];meta.append(dict(stage=r.stage,genre=r.genre,strength=strength,kind=r.kind,value=r.value,p=r.p,opponent=r.opponent,loadout=json.dumps(load)))
            jobs.append(dict(stage=int(r.stage),genre=r.genre,opponent=r.opponent,p=json.loads(r.p),loadout=load,validation=True,pool_offset=24576,trials=256,stream='counter-dose-validation'))
    validation=study.table('counter_dose_validation.csv',meta,jobs);validation['target_distance']=(validation.wr-.5).abs();selected=validation.sort_values(['target_distance','strength']).groupby(['stage','genre']).head(1);study.finish('counter_dose_validation_manifest.json')
    if not (OUT/'counter_balanced_fresh_holdout.csv').exists():
        jobs=[dict(stage=int(r.stage),genre=r.genre,opponent=r.opponent,p=json.loads(r.p),loadout=json.loads(r.loadout),validation=True,pool_offset=26624,trials=1200,stream='counter-balanced-fresh') for r in selected.itertuples()]
        with cf.ProcessPoolExecutor(4,initializer=bank_initializer) as pool:results=list(pool.map(advanced_evaluate,jobs))
        csv('counter_balanced_fresh_holdout.csv',pd.concat([selected[['stage','genre','opponent','strength','kind','value','loadout']].reset_index(drop=True),pd.DataFrame(results)],axis=1))
    save_json(OUT/'counter_calibration_manifest.json',dict(validation_executions=165888,fresh_executions=86400,final_catalog_offset=384,goal='45..55 percent WR, baseline at most30 percent; recorded results determine acceptance'))


if __name__=='__main__':main()
