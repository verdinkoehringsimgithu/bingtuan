"""Calibrate four-item operating points, then test on an unseen skill bank."""
from advanced_study import *
from refine_delivery import bank_initializer


def scaled_loadout(loadout,strength,n):
    # Passive opening shields have identical value at any owner position.
    active=[(p,k,v*strength) for p,k,v in loadout if k!='opening_shield'];used={p for p,_,_ in active}
    empty=[p for p in range(n-1,-1,-1) if p not in used];passive=[]
    for p,k,v in loadout:
        if k=='opening_shield':passive.append((empty.pop(0),k,v*strength))
    return active+passive


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=4);args=parser.parse_args();study=AdvancedStudy(args.workers);loads=pd.read_csv(OUT/'four_top_loadouts.csv');meta=[];jobs=[]
    for r in loads.itertuples():
        load=json.loads(r.loadout)
        for strength in (.1,.15,.2,.25,.3,.35,.4,.45,.5,.6):
            config=scaled_loadout(load,strength,STAGES[r.stage][0]);meta.append(dict(stage=r.stage,genre=r.genre,strength=strength,loadout=json.dumps(config)))
            jobs.append(dict(**study.scene(r.stage,r.genre,4),loadout=config,validation=True,pool_offset=14336,trials=256,stream='equipment-strength-validation'))
    validation=study.table('equipment_operating_validation.csv',meta,jobs);validation['target_distance']=(validation.wr-.825).abs()
    chosen=validation.sort_values(['target_distance','strength']).groupby(['stage','genre']).head(1);csv('equipment_operating_candidates.csv',chosen[['stage','genre','strength','loadout']])
    study.finish('equipment_calibration_validation_manifest.json')
    if not (OUT/'equipment_operating_fresh_holdout.csv').exists():
        jobs=[dict(stage=int(r.stage),genre=r.genre,opponent=study.scene(r.stage,r.genre,4)['opponent'],p=study.scene(r.stage,r.genre,4)['p'],loadout=json.loads(r.loadout),validation=True,pool_offset=16384,trials=1500,stream='equipment-operating-fresh') for r in chosen.itertuples()]
        with cf.ProcessPoolExecutor(args.workers,initializer=bank_initializer) as pool:results=list(pool.map(advanced_evaluate,jobs))
        csv('equipment_operating_fresh_holdout.csv',pd.concat([chosen[['stage','genre','strength','loadout']].reset_index(drop=True),pd.DataFrame(results)],axis=1))
    save_json(OUT/'equipment_calibration_manifest.json',dict(validation_executions=len(validation)*256*2,fresh_holdout_executions=108000,target_wr=.825,target_is_selection_objective_not_guarantee=True,final_catalog_offset=384,passive_opening_shields_assigned_to_unused_back_positions=True))


if __name__=='__main__':main()
