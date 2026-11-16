"""Calibrate strategic baselines, measure downside risk, and verify new channels."""
import concurrent.futures as cf
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from run_research import batch_worker, paired_worker, summary_table, response_worker, dump
from research_core import *

def calibrate(row):
    p=json.loads(row["p"]);target={"advantage":.65,"counter":.28,"stalemate":.50}[row["path"]]
    lo,hi=.3,2.5;screen=[]
    for step in range(11):
        beta=(lo+hi)/2;p[1]=beta
        result=batch_worker((5,row["genre"],p,1800,f"calibration-common-{row['path']}",None,row["genre"],None))
        screen.append(dict(genre=row["genre"],path=row["path"],step=step,beta=beta,**result))
        if result["wr"]>target:lo=beta
        else:hi=beta
    best=min(screen,key=lambda x:abs(x["wr"]-target));p[1]=best["beta"]
    return dict(row,p=json.dumps(p)),screen

def floor_worker(g):
    out=[];n=1500
    mechanisms={"baseline":{},"death_lock":{"death_lock":.3},"hit_floor":{"hit_floor":1.},
                "normal_comp":{"normal_comp":3.},"shield":{"overheal_shield":1.,"shield_cap":1.}}
    for name,cfg in mechanisms.items():
        records=[]
        for j in range(n):
            a,b=assemble(5,g),assemble(5,GENRES[j%6])
            result,_,_=run(a,b,stable_seed("floor-downside",g,j),None,cfg)
            result["margin"]=result["hp"]-result["enemy_hp"]
            records.append(result)
        x=pd.DataFrame(records);margin=x.margin.to_numpy();negative=np.minimum(margin,0.)
        summary=summary_table(records)
        summary.update(genre=g,mechanism=name,margin_variance=np.var(margin,ddof=1),downside_semivariance=np.mean(negative**2),
                       margin_q10=np.quantile(margin,.1),negative_margin_mean=negative.mean())
        out.append(summary)
    return out

def heterogeneous_worker(job):
    g,foreign=job;n=720;out=[]
    for label in ("base","embedded"):
        rows=[]
        for j in range(n):
            a,b=assemble(5,g),assemble(5,GENRES[j%6]);share=1/30
            if label=="embedded":
                f=assemble(5,foreign)
                for field in ("courage","resilience","initiative","magic"):
                    setattr(a,"base_"+field,(1-share)*getattr(a,"base_"+field)+share*getattr(f,"base_"+field))
                for s in a.skills:s.trigger_chance*=1-share
                for k,s in enumerate(f.skills):s.id+=100+k;s.trigger_chance*=share;a.skills.append(s)
            summary,features,_=run(a,b,stable_seed("hetero-channel",g,foreign,j),None,telemetry=True)
            summary.update({c:a.metrics[c]/a.max_bp for c in ("self_heal","lifesteal","max_dot","lost_dot","backlash","execute","pure_true","penetration_credit")})
            summary["player_weak_area"]=features["p_weak_area"];summary["enemy_weak_area"]=features["e_weak_area"]
            summary["player_stat_area"]=features["p_stat_area"];summary["enemy_stat_area"]=features["e_stat_area"]
            rows.append(summary)
        result=summary_table(rows)
        result.update(genre=g,foreign=foreign,version=label)
        for c in ("self_heal","lifesteal","max_dot","lost_dot","backlash","execute","pure_true","penetration_credit","player_weak_area","enemy_weak_area","player_stat_area","enemy_stat_area"):
            result[c]=np.mean([r[c] for r in rows])
        out.append(result)
    return out

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--output",default=str(Path(__file__).parent/"results"));p.add_argument("--workers",type=int,default=8);args=p.parse_args()
    directory=Path(args.output);counts={}
    with cf.ProcessPoolExecutor(max_workers=args.workers) as pool:
        print("Calibrating strategic baselines on independent screening samples",flush=True)
        original=pd.read_csv(directory/"strategic_paths_holdout.csv")
        calibrated=[];screen=[]
        for r,s in pool.map(calibrate,original[["genre","path","p","config","lever"]].to_dict("records")):
            calibrated.append(r);screen.extend(s)
        pd.DataFrame(screen).to_csv(directory/"strategic_baseline_calibration.csv",index=False)
        # Re-select intervention on the calibrated conditions, then final holdout.
        candidates={"P_ATTACK":{"attack":6.,"pierce":3.,"magic":.5},"P_FLOOR":{"death_lock":.5,"hit_floor":1.,"normal_comp":4.},
                    "P_RAMP2":{"ramp":2.,"resilience":.5},"P_RAMP6":{"ramp":6.,"resilience":.5},
                    "P_TRUE":{"pierce":6.,"magic":1.},"P_EXTREME":{"attack":12.,"pierce":6.,"ramp":6.}}
        meta=[];jobs=[]
        for r in calibrated:
            for name,cfg in candidates.items():
                meta.append(dict(genre=r["genre"],path=r["path"],p=r["p"],lever=name,config=json.dumps(cfg)))
                jobs.append((5,r["genre"],json.loads(r["p"]),480,"calibrated-path-training",cfg,r["genre"],None))
        train=pd.concat([pd.DataFrame(meta),pd.DataFrame(list(pool.map(paired_worker,jobs)))],axis=1)
        train["selection"]=np.where(train.path=="counter",-np.abs(train.wr-.5),train.wr)
        train.to_csv(directory/"strategic_calibrated_training.csv",index=False)
        selected=train.sort_values("selection",ascending=False).groupby(["genre","path"]).head(1)
        meta=[];jobs=[]
        for r in selected.itertuples():
            meta.append(dict(genre=r.genre,path=r.path,p=r.p,lever=r.lever,config=r.config))
            jobs.append((5,r.genre,json.loads(r.p),1500,"calibrated-path-holdout",json.loads(r.config),r.genre,None))
        df=pd.concat([pd.DataFrame(meta),pd.DataFrame(list(pool.map(paired_worker,jobs)))],axis=1)
        # Explicit criterion at 65%: baseline confidence interval must contain .65.
        # Recompute baseline CI from n and proportion rather than an invented tolerance.
        from run_research import wilson
        cis=[wilson(round(r.base_wr*r.n),r.n) for r in df.itertuples()]
        df["base_wr_lo"]=[c[0] for c in cis];df["base_wr_hi"]=[c[1] for c in cis]
        df["target_pass"]=[((r.base_wr_lo<=.65<=r.base_wr_hi and r.wr>=.92 and 1-r.wr<.05) if r.path=="advantage" else
                           (r.base_wr<=.30 and .45<=r.wr<=.55) if r.path=="counter" else
                           (r.base_turns>=8 and r.base_wr_lo<=.5<=r.base_wr_hi and r.delta>=.30)) and
                           r.censor_rate==0 and r.base_censor_rate==0 and r.draw_rate==0 and r.base_draw_rate==0 for r in df.itertuples()]
        df.to_csv(directory/"strategic_calibrated_holdout.csv",index=False)
        print("Testing enemy equipment responses, downside risk and foreign channels",flush=True)
        meta=[];jobs=[]
        for r in df.query("path=='advantage'").itertuples():
            for name,cfg in candidates.items():
                meta.append(dict(genre=r.genre,enemy_response=name))
                jobs.append((r.genre,json.loads(r.p),json.loads(r.config),cfg,900,"calibrated-enemy-response"))
        response=pd.concat([pd.DataFrame(meta),pd.DataFrame(list(pool.map(response_worker,jobs)))],axis=1)
        response.to_csv(directory/"calibrated_enemy_counter_response.csv",index=False)
        floor=[]
        for chunk in pool.map(floor_worker,GENRES):floor.extend(chunk)
        pd.DataFrame(floor).to_csv(directory/"floor_downside_risk.csv",index=False)
        heter=[]
        for chunk in pool.map(heterogeneous_worker,[(g,h) for g in GENRES for h in GENRES if g!=h]):heter.extend(chunk)
        heter=pd.DataFrame(heter);heter.to_csv(directory/"heterogeneous_observed_channels.csv",index=False)
        paired=[]
        for (g,h),sub in heter.groupby(["genre","foreign"]):
            base=sub.query("version=='base'").iloc[0];new=sub.query("version=='embedded'").iloc[0]
            healing_new=(base.self_heal+base.lifesteal==0) and new.self_heal+new.lifesteal>0
            suppression_new=(base.enemy_weak_area==0 and new.enemy_weak_area>0) or (base.enemy_stat_area==0 and new.enemy_stat_area>0)
            paired.append(dict(genre=g,foreign=h,base_wr=base.wr,wr=new.wr,output_ratio=new.damage_per_round/base.damage_per_round,
                               new_healing_observed=healing_new,new_suppression_observed=suppression_new,
                               combined_target_pass=new.damage_per_round/base.damage_per_round>=.95 and (healing_new or suppression_new)))
        pd.DataFrame(paired).to_csv(directory/"heterogeneous_joint_validation.csv",index=False)
    counts=dict(calibration=18*11*1800,strategy_training=108*480*2,strategy_holdout=18*1500*2,
                enemy_responses=36*900,floor=6*5*1500,heterogeneous_observed=30*720*2)
    dump(directory/"extended_manifest.json",dict(counts=counts,total=sum(counts.values()),seed_scheme="stable_seed with independent named streams",actor_focus=1/30))
    print("Extended validation complete",flush=True)

if __name__=="__main__":main()
