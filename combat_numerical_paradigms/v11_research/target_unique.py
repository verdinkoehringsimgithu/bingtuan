"""Find the smallest tested contribution achieving a 20--30 point cluster lift."""
import concurrent.futures as cf
import json
from pathlib import Path
import numpy as np
import pandas as pd
from run_research import unique_worker, dump

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--output",default=str(Path(__file__).parent/"results"));p.add_argument("--workers",type=int,default=8);args=p.parse_args()
    q=Path(args.output);data=pd.read_csv(q/"telemetry_cluster_assignments.csv.gz",dtype={"seed":str});selection=pd.read_csv(q/"selected_parameters.csv").to_dict("records")
    summary=pd.read_csv(q/"unique_cluster_training_summary.csv")
    # Mechanism is chosen from training centroids/interventions, without holdout labels.
    eligible=summary[summary.delta.between(.2,.3)].copy()
    eligible["center_distance"]=abs(eligible.delta-.25)
    chosen=eligible.sort_values(["share","center_distance"]).groupby("cluster").head(1)
    lever_defs={"U_ATTACK":{"attack":4.},"U_PIERCE":{"pierce":3.},"U_R":{"resilience":.8},"U_M":{"magic":.8},"U_I":{"initiative":.8},"U_C":{"courage":.8},"U_FLOOR":{"death_lock":.3,"normal_comp":3.},"U_RAMP":{"ramp":2.},"U_SHIELD":{"overheal_shield":1.,"shield_cap":1.},"U_HIT":{"hit_floor":1.}}
    train=data.query("split=='train' and censored==0").sample(n=1200,random_state=20261012)
    validation=data.query("split=='holdout' and censored==0").sample(n=2400,random_state=20261013)
    cols=["stage","genre","difficulty","opponent","seed","win","cluster"]
    jobs=[]
    for r in chosen.itertuples():
        records=train[train.cluster==r.cluster][cols].to_dict("records")
        for mult in np.arange(0.,2.01,.25):jobs.append((records,r.lever,float(mult),lever_defs[r.lever],selection))
    frontier=[]
    with cf.ProcessPoolExecutor(max_workers=args.workers) as pool:
        for chunk in pool.map(unique_worker,jobs):frontier.extend(chunk)
        f=pd.DataFrame(frontier);f.to_csv(q/"unique_share_frontier_battles.csv.gz",index=False)
        a=f.groupby(["cluster","lever","share_multiplier"]).agg(n=("win","size"),base_wr=("base_win","mean"),wr=("win","mean"),mean_share=("share","mean")).reset_index();a["delta"]=a.wr-a.base_wr
        a.to_csv(q/"unique_share_frontier.csv",index=False)
        best=a[a.delta.between(.2,.3)].sort_values("share_multiplier").groupby("cluster").head(1)
        jobs=[]
        for r in best.itertuples():
            records=validation[validation.cluster==r.cluster][cols].to_dict("records")
            jobs.append((records,r.lever,float(r.share_multiplier),lever_defs[r.lever],selection))
        v=[]
        for chunk in pool.map(unique_worker,jobs):v.extend(chunk)
        v=pd.DataFrame(v);v.to_csv(q/"unique_targeted_holdout_battles.csv.gz",index=False)
    result=[]
    for keys,s in v.groupby(["cluster","lever","share_multiplier"]):
        diff=(s.win-s.base_win).to_numpy();se=diff.std(ddof=1)/np.sqrt(len(diff));delta=diff.mean()
        result.append(dict(cluster=keys[0],lever=keys[1],share_multiplier=keys[2],n=len(s),base_wr=s.base_win.mean(),wr=s.win.mean(),delta=delta,delta_lo=delta-1.96*se,delta_hi=delta+1.96*se,target_20_30=.2<=delta<=.3,interval_entirely_20_30=.2<=delta-1.96*se and delta+1.96*se<=.3))
    pd.DataFrame(result).to_csv(q/"unique_targeted_holdout.csv",index=False)
    stage=v.groupby(["stage","cluster","lever","share_multiplier"]).agg(n=("win","size"),share=("share","mean"),base_wr=("base_win","mean"),wr=("win","mean")).reset_index();stage["delta"]=stage.wr-stage.base_wr
    stage.to_csv(q/"unique_targeted_stage_ladder.csv",index=False)
    dump(q/"unique_targeted_manifest.json",dict(training=len(f),holdout=len(v),total=len(f)+len(v),focus_interpretation="aggregate mechanism exposure, not an identifiable actor stat allocation"))
    print(pd.DataFrame(result).to_string(index=False))

if __name__=="__main__":main()
