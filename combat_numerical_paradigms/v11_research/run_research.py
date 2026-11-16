"""Reproducible V11 research: scan -> holdout -> telemetry -> discovery -> interventions.

Run with --workers N. Each stage resumes from immutable phase files; use a new
--output directory when changing settings. Parallel workers use independent seeds.
No victory/failure taxonomy is assigned before clustering.
"""
from __future__ import annotations
import os
for var in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"):
    os.environ[var] = "1"
import argparse
import concurrent.futures as cf
import gzip
import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import qmc
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.linear_model import Ridge
from sklearn.metrics import silhouette_score, mean_absolute_error, r2_score
from sklearn.mixture import GaussianMixture
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from research_core import *

TARGETS = {1:((.99,1.),(1.,3.),(.85,1.)), 2:((.90,.95),(4.,6.),(.60,.75)),
           3:((.70,.80),(7.,10.),(.30,.50)), 4:((.45,.55),(12.,18.),(.05,.20))}
SLOTS = {
    "core": {"K0":{}, "K1":{"pierce":2.}, "K2":{"ramp":2.}, "K3":{"overheal_shield":1.,"shield_cap":1.}},
    "attribute": {"A0":{},"A1":{"attack":3.},"A2":{"magic":.5},"A3":{"resilience":.5}},
    "strategy": {"S0":{},"S1":{"death_lock":.3},"S2":{"hit_floor":1.,"normal_comp":3.},"S3":{"crit":3.,"overflow_true":1.}}
}

def dump(path, data):
    Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2,default=lambda x:x.item() if hasattr(x,"item") else str(x)),encoding="utf-8")

def interval_distance(value, bounds):
    return max(bounds[0]-value, 0., value-bounds[1])

def wilson(wins, n):
    if not n: return (0.,1.)
    p = wins/n; z=1.959963984540054
    den=1+z*z/n; c=(p+z*z/(2*n))/den
    r=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return c-r,c+r

def summary_table(results):
    df=pd.DataFrame(results)
    n=len(df); lo,hi=wilson(int(df.win.sum()),n)
    return dict(n=n,wr=df.win.mean(),wr_lo=lo,wr_hi=hi,decisive_wr=df.decisive_win.mean(),
                censor_rate=df.censored.mean(),draw_rate=df.draw.mean(),turns=df.turns.mean(),
                hp=df.hp.mean(),winner_hp=df.loc[df.win==1,"hp"].mean() if df.win.sum() else 0.,
                turns_sd=df.turns.std(),hp_sd=df.hp.std(),loss_hp_variance=df.loc[df.win==0,"hp"].var() if (df.win==0).sum()>1 else 0.,
                hp_q10=df.hp.quantile(.1),damage_output=df.damage_output.mean(),
                damage_per_round=(df.damage_output/df.turns).mean())

def batch_worker(job):
    stage,genre,p,n,seed_group,config,enemy_genre,extra=job
    out=[]
    for j in range(n):
        opp=enemy_genre or GENRES[j%6]
        player,enemy=assemble(stage,genre),assemble(stage,opp)
        if extra and "hetero" in extra:
            foreign=assemble(stage,extra["hetero"]); share=extra["share"]
            for field in ("courage","resilience","initiative","magic"):
                setattr(player,"base_"+field,(1-share)*getattr(player,"base_"+field)+share*getattr(foreign,"base_"+field))
            for s in player.skills: s.trigger_chance*=1-share
            for k,s in enumerate(foreign.skills):
                s.id+=100+k
                s.trigger_chance*=share
                player.skills.append(s)
        res,_,_=run(player,enemy,stable_seed(seed_group,stage,genre,j),p,config)
        out.append(res)
    return summary_table(out)

def paired_worker(job):
    stage,genre,p,n,seed_group,config,enemy_genre,extra=job
    old=[];new=[]
    for j in range(n):
        opp=enemy_genre or GENRES[j%6]
        seed=stable_seed(seed_group,stage,genre,j)
        a,_,_=run(assemble(stage,genre),assemble(stage,opp),seed,p)
        b,_,_=run(assemble(stage,genre),assemble(stage,opp),seed,p,config)
        old.append(a);new.append(b)
    result=summary_table(new); base=summary_table(old)
    diff=np.array([b["win"]-a["win"] for a,b in zip(old,new)])
    delta=diff.mean(); se=diff.std(ddof=1)/math.sqrt(n)
    result.update(base_wr=base["wr"],base_turns=base["turns"],base_output=base["damage_per_round"],
                  base_censor_rate=base["censor_rate"],base_draw_rate=base["draw_rate"],
                  delta=delta,delta_lo=delta-1.96*se,delta_hi=delta+1.96*se,
                  rescue=np.mean([(a["win"]==0 and b["win"]==1) for a,b in zip(old,new)]),
                  spoil=np.mean([(a["win"]==1 and b["win"]==0) for a,b in zip(old,new)]),
                  output_ratio=result["damage_per_round"]/base["damage_per_round"] if base["damage_per_round"] else 0.)
    return result

class Study:
    def __init__(self,args):
        self.args=args
        self.out=Path(args.output).resolve(); self.out.mkdir(parents=True,exist_ok=True)
        (self.out/"figures").mkdir(exist_ok=True)
        self.pool=cf.ProcessPoolExecutor(max_workers=args.workers)
        self.started=time.time(); self.counts={}
        settings={k:v for k,v in vars(args).items() if k not in ("workers","output","stop_after")}
        settings["canonical_sha256"]=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        config_path=self.out/"settings.json"
        if config_path.exists() and json.loads(config_path.read_text(encoding="utf-8"))!=settings:
            self.pool.shutdown()
            raise ValueError("Settings or canonical source changed; use a new --output directory.")
        dump(config_path,settings)
    def log(self,msg): print(time.strftime("%H:%M:%S"),msg,flush=True)
    def execute(self,jobs,worker=batch_worker):
        results=[]
        for i,r in enumerate(self.pool.map(worker,jobs,chunksize=2)):
            results.append(r)
            if (i+1)%200==0: self.log(f"completed {i+1}/{len(jobs)} experiment cells")
        self.counts[worker.__name__]=self.counts.get(worker.__name__,0)+sum(j[3] for j in jobs)*(2 if worker is paired_worker else 1)
        return results
    def csv(self,name,df): df.to_csv(self.out/name,index=False,encoding="utf-8-sig")
    def checkpoint(self,name): return self.out/name

    def audit(self):
        report=parity(1200)
        report["magic_examples"]={str(m):engine.calc_magic_amp_responsive(m) for m in (50,100,280,500,1000)}
        report["conflicts"]=[
            "Action dodge reads attacker initiative, not defender initiative; preserved in all native tests.",
            "DoT uses current resilience, not debuff-reduced effective resilience; preserved.",
            "True damage uses threshold .85 and coefficient .20; AGENT.md describes threshold 1.0 and .18.",
            "At magic 280, live amplifier is 1.89; the mathematical document example says 2.04.",
            "Heal action discards crit/preempt in its accompanying direct hit; preserved.",
            "The native 40-round cap awards victory by BP ratio, with first-side tie advantage.",
            "Early-stage full skill portfolios and single-character entities are not defined by the source."
        ]
        dump(self.out/"audit.json",report)
        self.log("exact canonical parity passed")

    def score(self,df,d):
        target=TARGETS[d]; errs=[]
        for r in df.itertuples():
            errs.append(sum((interval_distance(v,b)/scale)**2 for v,b,scale in zip((r.wr,r.turns,r.hp),target,(.05,2.,.1)))+100*r.censor_rate)
        return float(np.mean(errs)+max(errs))

    def scan(self):
        path=self.checkpoint("selected_parameters.csv")
        if path.exists() and all(self.checkpoint(n).exists() for n in ("difficulty_holdout.csv","continuous_function_holdout.csv")):
            self.selected=pd.read_csv(path); self.log("loaded completed scan"); return
        # Low-discrepancy coverage and exact boundary points have no preset outcome labels.
        unit=qmc.Sobol(6,scramble=True,seed=self.args.seed).random_base2(self.args.scan_power)
        points=qmc.scale(unit,BOUNDS[:,0],BOUNDS[:,1]).tolist()
        import itertools
        points += list(itertools.product(*BOUNDS.tolist()))
        points += [[.3,.3,0,0,-200,.8],[1,1,0,0,0,1]]
        meta=[];jobs=[]
        for s in range(6):
            for k,p in enumerate(points):
                for g in GENRES:
                    meta.append(dict(stage=s+1,genre=g,point=k,phase="global",**dict(zip(PARAMS,p))))
                    jobs.append((s,g,p,self.args.screen_trials,"scan-global",None,None,None))
        self.log(f"global scan: {len(points)} parameter vectors x 6 stages x 6 flows")
        results=self.execute(jobs)
        data=pd.concat([pd.DataFrame(meta),pd.DataFrame(results)],axis=1)
        self.csv("scan_global.csv",data)
        local_meta=[];local_jobs=[];initial={}
        for s in range(1,7):
            sdf=data[data.stage==s]
            for d in range(1,5):
                ranked=sorted(((self.score(f,d),k) for k,f in sdf.groupby("point")))
                initial[s,d]=ranked[0]
                centers=[sdf[sdf.point==k].iloc[0][list(PARAMS)].to_numpy(float) for _,k in ranked[:3]]
                candidates=[]
                for cidx,c in enumerate(centers):
                    u=qmc.Sobol(6,scramble=True,seed=stable_seed(s,d,cidx)%2**32).random_base2(3)
                    for v in u:
                        candidates.append(np.clip(c+(v-.5)*.30*(BOUNDS[:,1]-BOUNDS[:,0]),BOUNDS[:,0],BOUNDS[:,1]))
                    candidates.append(c)
                for k,p in enumerate(candidates):
                    for g in GENRES:
                        local_meta.append(dict(stage=s, difficulty=d,genre=g,point=k,phase="local",**dict(zip(PARAMS,p))))
                        local_jobs.append((s-1,g,p,self.args.local_trials,f"scan-local-{s}-{d}",None,None,None))
        self.log("refining shared configurations with independent random streams")
        local=pd.concat([pd.DataFrame(local_meta),pd.DataFrame(self.execute(local_jobs))],axis=1)
        self.csv("scan_local.csv",local)
        chosen=[];hold_meta=[];hold_jobs=[]
        for (s,d),sdf in local.groupby(["stage","difficulty"]):
            score,k=min((self.score(f,int(d)),k) for k,f in sdf.groupby("point"))
            p=sdf[sdf.point==k].iloc[0][list(PARAMS)].to_numpy(float)
            chosen.append(dict(stage=int(s),difficulty=int(d),screen_score=score,**dict(zip(PARAMS,p))))
            for g in GENRES:
                hold_meta.append(dict(stage=s,difficulty=d,genre=g,**dict(zip(PARAMS,p))))
                hold_jobs.append((int(s)-1,g,p,self.args.holdout_trials,f"holdout-{d}",None,None,None))
        self.selected=pd.DataFrame(chosen);self.csv("selected_parameters.csv",self.selected)
        hold=pd.concat([pd.DataFrame(hold_meta),pd.DataFrame(self.execute(hold_jobs))],axis=1)
        for key in ("point_pass","interval_pass"):
            vals=[]
            for r in hold.itertuples():
                b=TARGETS[r.difficulty]
                if key=="point_pass": ok=all(interval_distance(v,t)==0 for v,t in zip((r.wr,r.turns,r.hp),b))
                else: ok=r.wr_lo>=b[0][0] and r.wr_hi<=b[0][1] and interval_distance(r.turns,b[1])==0 and interval_distance(r.hp,b[2])==0
                vals.append(bool(ok and r.censor_rate==0 and r.draw_rate==0))
            hold[key]=vals
        self.csv("difficulty_holdout.csv",hold)
        self.fit_deployment_function()

    def fit_deployment_function(self):
        X=np.c_[(self.selected.stage.to_numpy()-1)/5,(self.selected.difficulty.to_numpy()-1)/3]
        poly=PolynomialFeatures(2,include_bias=True); Z=poly.fit_transform(X)
        y=self.selected[list(PARAMS)].to_numpy(float)
        u=np.clip((y-BOUNDS[:,0])/(BOUNDS[:,1]-BOUNDS[:,0]),.001,.999)
        model=Ridge(alpha=.05,fit_intercept=False).fit(Z,np.log(u/(1-u)))
        pred=BOUNDS[:,0]+(BOUNDS[:,1]-BOUNDS[:,0])/(1+np.exp(-model.predict(Z)))
        function=dict(formula="p_j(s,d)=L_j+(U_j-L_j)*sigmoid(sum_k coef[j,k]*phi_k)",
                      variables="s=(stage-1)/5; d=(difficulty-1)/3",basis=poly.get_feature_names_out(["s","d"]).tolist(),
                      coefficients=model.coef_.tolist(),parameter_order=PARAMS,bounds=BOUNDS.tolist(),
                      purpose="Smooth empirical proposal; feasibility must be checked independently.")
        dump(self.out/"continuous_deployment_function.json",function)
        meta=[];jobs=[]
        for r,p in zip(self.selected.itertuples(),pred):
            for g in GENRES:
                meta.append(dict(stage=r.stage,difficulty=r.difficulty,genre=g,**dict(zip(PARAMS,p))))
                jobs.append((r.stage-1,g,p,self.args.function_trials,f"function-check-{r.difficulty}",None,None,None))
        df=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.execute(jobs))],axis=1)
        df["point_pass"]=[all(interval_distance(v,t)==0 for v,t in zip((r.wr,r.turns,r.hp),TARGETS[r.difficulty])) and r.censor_rate==0 for r in df.itertuples()]
        self.csv("continuous_function_holdout.csv",df)

    def contours(self):
        if self.checkpoint("contour_slices.csv").exists() and all((self.out/"figures"/f"contour_S{s}_{m}.png").exists() for s in range(1,7) for m in ("wr","turns")): return
        meta=[];jobs=[]
        for s in range(1,7):
            p0=self.selected.query("stage==@s and difficulty==3").iloc[0][list(PARAMS)].to_numpy(float)
            for a in np.linspace(.3,3.5,self.args.contour_grid):
                for b in np.linspace(.3,2.5,self.args.contour_grid):
                    p=p0.copy();p[:2]=a,b
                    for g in GENRES:
                        meta.append(dict(stage=s,genre=g,**dict(zip(PARAMS,p))))
                        jobs.append((s-1,g,p,self.args.screen_trials,"contour",None,None,None))
        df=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.execute(jobs))],axis=1)
        self.csv("contour_slices.csv",df)
        for s in range(1,7):
            for metric in ("wr","turns"):
                fig,axs=plt.subplots(2,3,figsize=(13,7),constrained_layout=True)
                for ax,g in zip(axs.flat,GENRES):
                    pivot=df.query("stage==@s and genre==@g").pivot(index="beta",columns="alpha",values=metric)
                    img=ax.contourf(pivot.columns,pivot.index,pivot.values,levels=12,cmap="viridis")
                    ax.set(title=g,xlabel="alpha (HP)",ylabel="beta (base strike)")
                    fig.colorbar(img,ax=ax)
                fig.suptitle(f"S{s}: measured {metric}; other parameters fixed at shared D3 candidate")
                fig.savefig(self.out/"figures"/f"contour_S{s}_{metric}.png",dpi=150);plt.close(fig)

    def telemetry(self):
        path=self.checkpoint("telemetry_features.csv.gz")
        if path.exists(): self.tele=pd.read_csv(path);return
        jobs=[];meta=[]
        strata=[(s,g,d) for s in range(1,7) for g in GENRES for d in (3,4)]
        each,remainder=divmod(self.args.telemetry_battles,len(strata))
        for idx,(s,g,d) in enumerate(strata):
            p=self.selected.query("stage==@s and difficulty==@d").iloc[0][list(PARAMS)].to_numpy(float)
            jobs.append((s-1,g,p,each+(idx<remainder),f"telemetry-D{d}",None,None,dict(difficulty=d,out=str(self.out))))
        self.log(f"collecting {self.args.telemetry_battles} full trajectories in 72 strata")
        chunks=list(self.pool.map(telemetry_worker,jobs,chunksize=1))
        self.tele=pd.concat([pd.DataFrame(chunk) for chunk in chunks],ignore_index=True)
        self.csv("telemetry_features.csv.gz",self.tele)
        self.counts["telemetry"]=len(self.tele)
        self.log("full per-round telemetry saved")

    def discover(self):
        if self.checkpoint("discovery_models.joblib").exists() and self.checkpoint("telemetry_cluster_assignments.csv.gz").exists():
            self.models=joblib.load(self.out/"discovery_models.joblib")
            self.tele=pd.read_csv(self.out/"telemetry_cluster_assignments.csv.gz");return
        context={"battle_id","stage","genre","difficulty","opponent","seed","win","decisive_win","censored","draw","turns","hp","enemy_hp","damage_output","p_gap_distribution","e_gap_distribution"}
        features=[c for c in self.tele.columns if c not in context and c not in PARAMS]
        # Remove constants; label and cohort context never enter scaling/PCA/KMeans.
        features=[c for c in features if self.tele[c].std()>1e-12]
        X=self.tele[features].to_numpy(float)
        train,test=train_test_split(np.arange(len(X)),test_size=.3,random_state=self.args.seed)
        scaler=StandardScaler().fit(X[train]); Z=scaler.transform(X)
        pca=PCA(svd_solver="full").fit(Z[train]);cum=np.cumsum(pca.explained_variance_ratio_)
        k=int(np.searchsorted(cum,.90)+1); PCs=pca.transform(Z)[:,:k]
        candidates=[];kms=[]
        for n in range(2,11):
            km=KMeans(n_clusters=n,n_init=5,random_state=self.args.seed,max_iter=150).fit(PCs[train])
            sil=silhouette_score(PCs[test],km.predict(PCs[test]),sample_size=min(1600,len(test)),random_state=self.args.seed)
            gm=GaussianMixture(n_components=n,covariance_type="diag",random_state=self.args.seed,max_iter=150).fit(PCs[train])
            candidates.append(dict(k=n,silhouette_holdout=sil,gmm_bic_train=gm.bic(PCs[train]),gmm_loglik_holdout=gm.score(PCs[test]),gmm_converged=gm.converged_))
            kms.append(km)
        best=int(np.argmax([r["silhouette_holdout"] for r in candidates]));km=kms[best]
        labels=km.predict(PCs);self.tele["cluster"]=labels;self.tele["split"]="train";self.tele.loc[test,"split"]="holdout"
        self.models=dict(scaler=scaler,pca=pca,km=km,features=features,pca_k=k)
        joblib.dump(self.models,self.out/"discovery_models.joblib")
        self.csv("cluster_model_selection.csv",pd.DataFrame(candidates))
        self.csv("pca_variance.csv",pd.DataFrame(dict(pc=np.arange(1,len(cum)+1),variance=pca.explained_variance_ratio_,cumulative=cum)))
        loadings=pd.DataFrame(pca.components_.T,index=features,columns=[f"PC{i+1}" for i in range(len(cum))]);loadings.reset_index(names="feature").to_csv(self.out/"pca_loadings.csv",index=False)
        corr=self.tele[features+["win","turns","hp","censored"]].corr();corr.to_csv(self.out/"feature_correlations.csv")
        # Physical feature contribution to retained explained standardized variance.
        contribution=(pca.components_[:k]**2*pca.explained_variance_ratio_[:k,None]).sum(axis=0)
        ranking=pd.DataFrame(dict(feature=features,explained_variance_contribution=contribution,win_correlation=corr.loc[features,"win"].to_numpy())).sort_values("explained_variance_contribution",ascending=False)
        self.csv("physical_feature_variance_ranking.csv",ranking)
        centroids=[];zrows=[];descriptions=[]
        for cl in range(km.n_clusters):
            ix=np.flatnonzero(labels==cl);tr=np.intersect1d(ix,train);te=np.intersect1d(ix,test)
            mean=X[tr].mean(axis=0);zmean=Z[tr].mean(axis=0)
            centroids.append(dict(cluster=cl,**dict(zip(features,mean))))
            zrows.append(dict(cluster=cl,**dict(zip(features,zmean))))
            order=np.argsort(np.abs(zmean))[::-1][:6]
            name=" / ".join(f"{features[j]}{'↑' if zmean[j]>0 else '↓'}" for j in order[:3])
            descriptions.append(dict(cluster=cl,label=name,n_train=len(tr),n_holdout=len(te),wr_train=self.tele.iloc[tr].win.mean(),
                                     wr_holdout=self.tele.iloc[te].win.mean(),censor_holdout=self.tele.iloc[te].censored.mean(),
                                     top_deviations="; ".join(f"{features[j]}={zmean[j]:+.3f} SD" for j in order)))
        self.csv("cluster_centroids.csv",pd.DataFrame(centroids));self.csv("cluster_centroids_standardized.csv",pd.DataFrame(zrows))
        self.csv("cluster_descriptions.csv",pd.DataFrame(descriptions))
        self.csv("telemetry_cluster_assignments.csv.gz",self.tele)
        self.fig_discovery(corr,ranking,pca,PCs,labels,zrows)
        self.log(f"PCA retains {k} components for 90% variance; empirical KMeans K={km.n_clusters}")

    def fig_discovery(self,corr,ranking,pca,pcs,labels,zrows):
        top=ranking.feature.head(28).tolist()+["win","turns","hp","censored"]
        fig,ax=plt.subplots(figsize=(13,11),constrained_layout=True)
        im=ax.imshow(corr.loc[top,top],vmin=-1,vmax=1,cmap="coolwarm")
        ax.set_xticks(range(len(top)),top,rotation=90,fontsize=7);ax.set_yticks(range(len(top)),top,fontsize=7)
        fig.colorbar(im,ax=ax);ax.set_title("Top variance features: correlation (full matrix in CSV)")
        fig.savefig(self.out/"figures"/"correlation_matrix.png",dpi=160);plt.close(fig)
        fig,axs=plt.subplots(1,2,figsize=(12,4),constrained_layout=True)
        ratios=pca.explained_variance_ratio_;axs[0].bar(np.arange(1,len(ratios)+1),ratios);axs[0].set(xlabel="PC",ylabel="explained variance")
        axs[1].plot(np.arange(1,len(ratios)+1),np.cumsum(ratios));axs[1].axhline(.9,color="grey",ls="--");axs[1].set(xlabel="PC",ylabel="cumulative variance")
        fig.savefig(self.out/"figures"/"pca_variance.png",dpi=160);plt.close(fig)
        fig,ax=plt.subplots(figsize=(9,6),constrained_layout=True)
        take=np.arange(0,len(pcs),max(1,len(pcs)//7000));im=ax.scatter(pcs[take,0],pcs[take,1],c=labels[take],s=5,alpha=.35,cmap="tab10")
        ax.set(xlabel="PC1",ylabel="PC2",title="Unsupervised trajectories; outcome excluded from clustering")
        fig.colorbar(im,ax=ax,label="cluster");fig.savefig(self.out/"figures"/"cluster_distribution.png",dpi=160);plt.close(fig)
        top=ranking.feature.head(20).tolist();df=pd.DataFrame(zrows).set_index("cluster")
        fig,ax=plt.subplots(figsize=(12,4),constrained_layout=True);im=ax.imshow(df[top],cmap="coolwarm",aspect="auto")
        ax.set_xticks(range(len(top)),top,rotation=70,ha="right",fontsize=8);ax.set_yticks(range(len(df)),[f"F{i:02}" for i in df.index]);fig.colorbar(im,ax=ax,label="centroid SD")
        fig.savefig(self.out/"figures"/"cluster_centroids.png",dpi=160);plt.close(fig)

    def sensitivities(self):
        if all(self.checkpoint(n).exists() for n in ("equipment_sensitivity.csv","specialization_summary.csv","spike_activation_thresholds.csv")): return
        axes={"attack":[0,1,2,3,4,6,8],"courage":[0,.1,.2,.3,.5,.7,1],"resilience":[0,.1,.2,.3,.5,.7,1],
              "initiative":[0,.1,.2,.3,.5,.7,1],"magic":[0,.1,.2,.3,.5,.7,1],"pierce":[0,.5,1,2,3,4,6],
              "death_lock":[0,.1,.2,.3,.5,.7,1],"hit_floor":[0,.2,.4,.6,.8,1],"normal_comp":[0,1,2,3,4,6,8],
              "crit":[0,5,10,15,20,25,30,35,40],"overheal_shield":[0,.25,.5,.75,1],"ramp":[0,.5,1,2,3,4,6]}
        meta=[];jobs=[]
        for g in GENRES:
            p=self.selected.query("stage==6 and difficulty==4").iloc[0][list(PARAMS)].to_numpy(float)
            for axis,values in axes.items():
                for value in values:
                    cfg={axis:value}
                    if axis=="crit":cfg["overflow_true"]=1.
                    meta.append(dict(stage=6,genre=g,axis=axis,value=value,focus=1/30,config=json.dumps(cfg)))
                    jobs.append((5,g,p,self.args.equipment_trials,"sensitivity",cfg,None,None))
        df=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.execute(jobs,paired_worker))],axis=1)
        derivatives=[]
        for (g,axis),sdf in df.groupby(["genre","axis"]):
            sdf=sdf.sort_values("value");x=sdf.value.to_numpy();y=sdf.wr.to_numpy()
            slope=np.gradient(y,x)
            for r,der in zip(sdf.itertuples(),slope):
                # Per actor input and per aggregate input have different units.
                derivatives.append(dict(genre=g,axis=axis,value=r.value,wr=r.wr,partial_wr_actor=der,partial_wr_aggregate=der/r.focus,
                                        delta=r.delta,delta_lo=r.delta_lo,delta_hi=r.delta_hi))
        self.csv("equipment_sensitivity.csv",df);self.csv("winrate_partial_derivatives.csv",pd.DataFrame(derivatives))
        fig,axs=plt.subplots(2,3,figsize=(13,7),constrained_layout=True)
        for ax,g in zip(axs.flat,GENRES):
            for axis in ("attack","pierce","ramp"):
                s=df.query("genre==@g and axis==@axis");ax.plot(s.value,s.wr,marker=".",label=axis)
            ax.set(title=g,xlabel="actor lever",ylabel="win rate");ax.legend(fontsize=8)
        fig.savefig(self.out/"figures"/"equipment_response_curves.png",dpi=160);plt.close(fig)
        # Equal-total-stat extreme compositions and collapse against every native opponent.
        meta=[];jobs=[]
        for g in GENRES:
            for field in range(4):
                for share in (0.,.1,.2,.4,.6,.8,1.):
                    allocation=[0.]*4;allocation[field]=1.
                    cfg=dict(allocation=allocation,share=share)
                    for h in GENRES:
                        meta.append(dict(genre=g,opponent=h,attribute=("courage","resilience","initiative","magic")[field],share=share))
                        jobs.append((5,g,None,self.args.specialization_trials,"specialization",cfg,h,None))
        sdf=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.execute(jobs))],axis=1)
        self.csv("specialization_boundaries.csv",sdf)
        spec=sdf.groupby(["genre","attribute","share"]).agg(wr_min=("wr","min"),wr_max=("wr","max"),wr_mean=("wr","mean")).reset_index()
        spec["wr_range"]=spec.wr_max-spec.wr_min;self.csv("specialization_summary.csv",spec)
        # Native threshold calculations identify spike activation, independently of outcome labels.
        thresholds=[]
        for g in GENRES:
            t=assemble(5,g);m=engine.calc_magic_amp_responsive(t.base_magic);cr,_=engine.calc_courage_stats(t.base_courage)
            for sk in t.skills:
                esc=sk.base_crit_rate*(1+(m-1)*.45)
                crit_actor_needed=max(0.,(1-cr)/(1+(m-1)*.45)-sk.base_crit_rate)*30
                pierce_actor_needed=max(0.,.85/m-sk.ignore_def_ratio)*30
                thresholds.append(dict(genre=g,skill_id=sk.id,magic_amp=m,crit_total=cr+esc,crit_actor_activation=crit_actor_needed,
                                       pierce_actor_activation=pierce_actor_needed,has_heal=sk.main_type=="Heal" or sk.sub_effect_name=="战力吸收"))
        self.csv("spike_activation_thresholds.csv",pd.DataFrame(thresholds))

    def slots(self):
        if all(self.checkpoint(n).exists() for n in ("equipment_matrix_holdout.csv","versatility_ranges.csv")):return
        import itertools
        catalog=[]
        for core,attr,strategy in itertools.product(SLOTS["core"],SLOTS["attribute"],SLOTS["strategy"]):
            cfg={**SLOTS["core"][core],**SLOTS["attribute"][attr],**SLOTS["strategy"][strategy]}
            catalog.append((f"{core}/{attr}/{strategy}",cfg))
        dump(self.out/"three_slot_catalog.json",SLOTS)
        meta=[];jobs=[]
        for g in GENRES:
            p=self.selected.query("stage==6 and difficulty==4").iloc[0][list(PARAMS)].to_numpy(float)
            for name,cfg in catalog:
                meta.append(dict(genre=g,slots=name,config=json.dumps(cfg)))
                jobs.append((5,g,p,self.args.slot_trials,"slot-training",cfg,None,None))
        df=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.execute(jobs))],axis=1);self.csv("three_slot_search.csv",df)
        chosen=df.sort_values("wr",ascending=False).groupby("genre").head(1)
        meta=[];jobs=[]
        for r in chosen.itertuples():
            cfg=json.loads(r.config);g=r.genre;p=self.selected.query("stage==6 and difficulty==4").iloc[0][list(PARAMS)].to_numpy(float)
            meta.append(dict(genre=g,slots=r.slots,config=r.config,focus=1/30))
            jobs.append((5,g,p,self.args.holdout_trials,"slot-independent-holdout",cfg,None,None))
        hold=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.execute(jobs,paired_worker))],axis=1)
        hold["d4_specialization_target"]=hold.wr.between(.80,.85)&(hold.censor_rate==0)
        self.csv("equipment_matrix_holdout.csv",hold)
        # Versatility is tested on all matchups, not only the training opponent mixture.
        meta=[];jobs=[]
        for r in hold.itertuples():
            for h in GENRES:
                meta.append(dict(genre=r.genre,opponent=h,slots=r.slots))
                jobs.append((5,r.genre,None,self.args.equipment_trials,"versatility-holdout",json.loads(r.config),h,None))
        v=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.execute(jobs,paired_worker))],axis=1);self.csv("versatility_matchups.csv",v)
        self.csv("versatility_ranges.csv",v.groupby("genre").agg(base_min=("base_wr","min"),base_max=("base_wr","max"),equipped_min=("wr","min"),equipped_max=("wr","max")).reset_index())

    def unique(self):
        if self.checkpoint("unique_cluster_holdout.csv").exists():return
        levers={"U_ATTACK":{"attack":4.},"U_PIERCE":{"pierce":3.},"U_R":{"resilience":.8},
                "U_M":{"magic":.8},"U_I":{"initiative":.8},"U_C":{"courage":.8},
                "U_FLOOR":{"death_lock":.3,"normal_comp":3.},"U_RAMP":{"ramp":2.},
                "U_SHIELD":{"overheal_shield":1.,"shield_cap":1.},"U_HIT":{"hit_floor":1.}}
        # Stage ladders are tested at three contribution shares, rather than assumed optimal.
        configs=[]
        for mult in (1,2,4):
            for name,cfg in levers.items(): configs.append((name,mult,cfg))
        training=self.tele.query("split=='train' and censored==0").sample(n=min(self.args.unique_train,len(self.tele.query("split=='train' and censored==0"))),random_state=self.args.seed)
        jobs=[]
        records=training[["stage","genre","difficulty","opponent","seed","win","cluster"]].to_dict("records")
        # CSV stores 64-bit seeds as strings; do not route them through a float.
        for name,mult,cfg in configs:jobs.append((records,name,mult,cfg,self.selected.to_dict("records")))
        self.log("testing cluster-specific rescue mechanisms and contribution shares")
        results=[]
        for chunk in self.pool.map(unique_worker,jobs,chunksize=1):results.extend(chunk)
        train=pd.DataFrame(results);self.csv("unique_cluster_training.csv",train)
        agg=train.groupby(["cluster","lever","share_multiplier"]).agg(n=("win","size"),base_wr=("base_win","mean"),wr=("win","mean"),share=("share","mean")).reset_index()
        agg["delta"]=agg.wr-agg.base_wr;self.csv("unique_cluster_training_summary.csv",agg)
        chosen=agg.sort_values(["delta","share_multiplier"],ascending=[False,True]).groupby("cluster").head(1)
        val=self.tele.query("split=='holdout' and censored==0").sample(n=min(self.args.unique_holdout,len(self.tele.query("split=='holdout' and censored==0"))),random_state=self.args.seed+1)
        jobs=[]
        for r in chosen.itertuples():
            records=val.query("cluster==@r.cluster")[["stage","genre","difficulty","opponent","seed","win","cluster"]].to_dict("records")
            jobs.append((records,r.lever,int(r.share_multiplier),levers[r.lever],self.selected.to_dict("records")))
        output=[]
        for chunk in self.pool.map(unique_worker,jobs,chunksize=1):output.extend(chunk)
        v=pd.DataFrame(output);self.csv("unique_cluster_holdout_battles.csv.gz",v)
        rows=[]
        for cl,sub in v.groupby("cluster"):
            diff=(sub.win-sub.base_win).to_numpy();delta=diff.mean();se=diff.std(ddof=1)/math.sqrt(len(diff)) if len(diff)>1 else 1
            rows.append(dict(cluster=cl,lever=sub.lever.iloc[0],share_multiplier=sub.share_multiplier.iloc[0],n=len(sub),
                             base_wr=sub.base_win.mean(),wr=sub.win.mean(),delta=delta,delta_lo=delta-1.96*se,delta_hi=delta+1.96*se,
                             rescue_of_losses=((sub.win==1)&(sub.base_win==0)).sum()/max(1,(sub.base_win==0).sum()),
                             target_20_30_point=.20<=delta<=.30,confirmed_at_least_20=delta-1.96*se>=.20))
        self.csv("unique_cluster_holdout.csv",pd.DataFrame(rows))
        self.csv("unique_stage_share_ladder.csv",pd.DataFrame([dict(stage=s+1,roster=n,share_multiplier=mult,budget_share=min(.4,mult/n)) for s,(n,*_) in enumerate(STAGES) for mult in (1,2,4)]))

    def strategies(self):
        if all(self.checkpoint(n).exists() for n in ("strategic_paths_holdout.csv","heterogeneous_new_channels.csv")):return
        # Matchup selection uses measured baselines. Targets are fitting criteria only.
        meta=[];jobs=[]
        for g in GENRES:
            for a in (1.,1.5,2.):
                for b in np.linspace(.3,2.5,17):
                    p=[a,b,0,0,0,1]
                    meta.append(dict(genre=g,alpha=a,beta=b))
                    jobs.append((5,g,p,self.args.screen_trials*2,"path-screen",None,g,None))
        screen=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.execute(jobs))],axis=1);self.csv("strategic_baseline_search.csv",screen)
        paths=[]
        for g,sdf in screen.groupby("genre"):
            for name,target in (("advantage",.65),("counter",.28),("stalemate",.5)):
                cand=sdf if name=="stalemate" else sdf.query("alpha==1")
                loss=np.abs(cand.wr-target)
                if name=="stalemate":loss+=np.maximum(0.,8-cand.turns)/8
                r=cand.loc[loss.idxmin()];paths.append(dict(genre=g,path=name,p=[r.alpha,r.beta,0,0,0,1]))
        candidates={"P_ATTACK":{"attack":6.,"pierce":3.,"magic":.5},
                    "P_FLOOR":{"death_lock":.5,"hit_floor":1.,"normal_comp":4.},
                    "P_RAMP2":{"ramp":2.,"resilience":.5},"P_RAMP6":{"ramp":6.,"resilience":.5},
                    "P_TRUE":{"pierce":6.,"magic":1.},"P_EXTREME":{"attack":12.,"pierce":6.,"ramp":6.}}
        meta=[];jobs=[]
        for path in paths:
            for name,cfg in candidates.items():
                meta.append(dict(genre=path["genre"],path=path["path"],p=json.dumps(path["p"]),lever=name,config=json.dumps(cfg)))
                jobs.append((5,path["genre"],path["p"],self.args.equipment_trials,"path-training",cfg,path["genre"],None))
        train=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.execute(jobs,paired_worker))],axis=1);self.csv("strategic_path_training.csv",train)
        train["selection"]=np.where(train.path=="counter",-np.abs(train.wr-.5),train.wr)
        chosen=train.sort_values("selection",ascending=False).groupby(["genre","path"]).head(1)
        meta=[];jobs=[]
        for r in chosen.itertuples():
            meta.append(dict(genre=r.genre,path=r.path,lever=r.lever,p=r.p,config=r.config))
            jobs.append((5,r.genre,json.loads(r.p),self.args.holdout_trials,"path-independent-holdout",json.loads(r.config),r.genre,None))
        hold=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.execute(jobs,paired_worker))],axis=1)
        hold["target_pass"]=[(abs(r.base_wr-.65)<=.05 and r.wr>=.92 and 1-r.wr<.05) if r.path=="advantage" else
                             (r.base_wr<=.30 and .45<=r.wr<=.55) if r.path=="counter" else
                             (r.base_turns>=8 and .45<=r.base_wr<=.55 and r.delta>=.30) for r in hold.itertuples()]
        self.csv("strategic_paths_holdout.csv",hold)
        # Enemy equipment responses: this is an actual adaptive counter-test.
        jobs=[];meta=[]
        for r in hold.query("path=='advantage'").itertuples():
            for name,cfg in candidates.items():
                meta.append(dict(genre=r.genre,enemy_response=name))
                jobs.append((r.genre,json.loads(r.p),json.loads(r.config),cfg,self.args.equipment_trials,"enemy-response"))
        response=pd.concat([pd.DataFrame(meta),pd.DataFrame(list(self.pool.map(response_worker,jobs)))],axis=1)
        self.csv("enemy_counter_response.csv",response)
        # Fourth path: fixed-budget heterogeneity, all foreign codes and opponents.
        meta=[];jobs=[]
        for g in GENRES:
            for foreign in GENRES:
                if foreign==g:continue
                for h in GENRES:
                    meta.append(dict(genre=g,foreign=foreign,opponent=h,share=1/30))
                    jobs.append((5,g,None,self.args.equipment_trials,"hetero",None,h,dict(hetero=foreign,share=1/30)))
        base_jobs=[(j[0],j[1],j[2],j[3],j[4],None,j[6],None) for j in jobs]
        base=self.execute(base_jobs);hetero=self.execute(jobs)
        df=pd.concat([pd.DataFrame(meta),pd.DataFrame(hetero)],axis=1)
        df["base_wr"]=[b["wr"] for b in base];df["base_output"]=[b["damage_per_round"] for b in base]
        df["output_ratio"]=df.damage_per_round/df.base_output
        df["output_loss_at_most_5pct"]=df.output_ratio>=.95
        self.csv("heterogeneous_embedding.csv",df)
        # Mechanical channel novelty from native source, alongside observed output.
        nov=[]
        for g in GENRES:
            own={s.sub_effect_name for s in assemble(5,g).skills}
            for h in GENRES:
                if g!=h:nov.append(dict(genre=g,foreign=h,new_channels=";".join(sorted({s.sub_effect_name for s in assemble(5,h).skills}-own-{""}))))
        self.csv("heterogeneous_new_channels.csv",pd.DataFrame(nov))

    def finalize(self):
        manifest=dict(seed=self.args.seed,args=vars(self.args),elapsed_seconds=time.time()-self.started,
                      simulation_counts_current_invocation=self.counts,python=sys.version,platform=platform.platform(),
                      source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                      truth_sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [SOURCE,ROOT/"combat_numerical_paradigms/01_COMBAT_CORE_MATHEMATICAL_MODEL.md",ROOT/"combat_numerical_paradigms/02_PROGRESSION_STAGES_AND_BUDGETS.md"]},
                      definitions=dict(win="canonical winner, including ratio adjudication at cap",decisive_win="player survives and enemy dies",hp="all-game player terminal HP, losses included",winner_hp="conditional on canonical win",censored="both sides alive at native round cap",stage_projection="S1-S5 are declared uniform tier projections; S6 exact preset",single_actor="aggregate focus approximation only"))
        import importlib.metadata
        manifest["dependencies"]={p:importlib.metadata.version(p) for p in ["numpy","pandas","scipy","scikit-learn","matplotlib"]}
        # Count persisted evidence, including custom workers, so resuming preserves
        # the completed study count instead of reporting only this invocation.
        counts={}
        for name,mult in (("scan_global",1),("scan_local",1),("difficulty_holdout",1),("continuous_function_holdout",1),
                          ("contour_slices",1),("equipment_sensitivity",2),("specialization_boundaries",1),
                          ("three_slot_search",1),("equipment_matrix_holdout",2),("versatility_matchups",2),
                          ("strategic_baseline_search",1),("strategic_path_training",2),("strategic_paths_holdout",2),
                          ("enemy_counter_response",1),("heterogeneous_embedding",2)):
            path=self.out/(name+".csv")
            if path.exists():counts[name]=int(pd.read_csv(path).n.sum())*mult
        for name,file in (("telemetry","telemetry_features.csv.gz"),("unique_training","unique_cluster_training.csv"),("unique_holdout","unique_cluster_holdout_battles.csv.gz")):
            if (self.out/file).exists():counts[name]=len(pd.read_csv(self.out/file))
        manifest["persisted_simulation_counts"]=counts
        manifest["persisted_simulation_total"]=sum(counts.values())
        dump(self.out/"manifest.json",manifest)
        self.pool.shutdown()

def telemetry_worker(job):
    stage,g,p,n,seed_group,cfg,opp,extra=job
    records=[];rawpath=Path(extra["out"])/f"rounds_S{stage+1}_{g}_D{extra['difficulty']}.jsonl.gz"
    with gzip.open(rawpath,"wt",encoding="utf-8") as f:
        for j in range(n):
            h=GENRES[j%6];seed=stable_seed(seed_group,stage,g,j)
            summary,features,rows=run(assemble(stage,g),assemble(stage,h),seed,p,telemetry=True)
            battle_id=f"S{stage+1}_{g}_D{extra['difficulty']}_{j}"
            context=dict(battle_id=battle_id,stage=stage+1,genre=g,difficulty=extra["difficulty"],opponent=h,seed=str(seed),**dict(zip(PARAMS,p)))
            records.append(dict(**context,**summary,**features))
            f.write(json.dumps(dict(**context,summary=summary,rounds=rows),ensure_ascii=False)+"\n")
    return records

def unique_worker(job):
    records,name,mult,cfg,selected=job
    lookup={(r["stage"],r["difficulty"]):[r[k] for k in PARAMS] for r in selected};out=[]
    for r in records:
        stage=r["stage"]-1;share=min(.4,mult/STAGES[stage][0]);config=dict(cfg,focus=share)
        summary,_,_=run(assemble(stage,r["genre"]),assemble(stage,r["opponent"]),int(r["seed"]),lookup[r["stage"],r["difficulty"]],config)
        out.append(dict(stage=stage+1,genre=r["genre"],difficulty=r["difficulty"],cluster=r["cluster"],lever=name,share_multiplier=mult,share=share,base_win=r["win"],win=summary["win"],censored=summary["censored"]))
    return out

def response_worker(job):
    g,p,pc,ec,n,sg=job;out=[]
    # Equip the enemy after macro application; run reset would discard this, so
    # compose interventions through a wrapper around apply_macro for this worker.
    original=run.__globals__["apply_macro"]
    def with_equipment(enemy,parameters):original(enemy,parameters);equip(enemy,ec)
    run.__globals__["apply_macro"]=with_equipment
    try:
        for j in range(n):
            res,_,_=run(assemble(5,g),assemble(5,g),stable_seed(sg,g,j),p,pc)
            out.append(res)
    finally:run.__globals__["apply_macro"]=original
    result=summary_table(out);result["enemy_flip_probability"]=1-result["wr"]
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",default=str(Path(__file__).parent/"results"))
    p.add_argument("--seed",type=int,default=20261012);p.add_argument("--workers",type=int,default=min(8,max(1,(os.cpu_count() or 2)-1)))
    p.add_argument("--scan-power",type=int,default=8);p.add_argument("--screen-trials",type=int,default=24)
    p.add_argument("--local-trials",type=int,default=96);p.add_argument("--holdout-trials",type=int,default=600)
    p.add_argument("--function-trials",type=int,default=240);p.add_argument("--contour-grid",type=int,default=9)
    p.add_argument("--telemetry-battles",type=int,default=24000);p.add_argument("--equipment-trials",type=int,default=240)
    p.add_argument("--slot-trials",type=int,default=120);p.add_argument("--specialization-trials",type=int,default=120)
    p.add_argument("--unique-train",type=int,default=1200);p.add_argument("--unique-holdout",type=int,default=2400)
    p.add_argument("--stop-after",choices=["scan","telemetry","all"],default="all")
    args=p.parse_args()
    if args.telemetry_battles<10000:raise ValueError("Full study requires at least 10,000 telemetry battles")
    study=Study(args);study.audit();study.scan()
    if args.stop_after=="scan":study.finalize();return
    study.contours();study.telemetry();study.discover()
    if args.stop_after=="telemetry":study.finalize();return
    study.sensitivities();study.slots();study.unique();study.strategies();study.finalize()
    study.log("all phases finished; evidence tables and figures saved")

if __name__=="__main__":main()
