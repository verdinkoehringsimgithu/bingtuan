"""Six stages x six flows: enemy delivery, telemetry/unique, all-member equipment.

Every saved experiment owns explicit N-member rosters and at most four top items.
Numeric recommendations are computed from response curves and fresh holdouts.
"""
from __future__ import annotations
import os
for v in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[v]='1'
import argparse
import concurrent.futures as cf
import gzip
import itertools
import json
import math
import time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import qmc
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler,PolynomialFeatures
from sklearn.linear_model import Ridge
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from roster_core import *

def save_json(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=lambda x:x.item() if hasattr(x,'item') else str(x)),encoding='utf-8')
def ci(w,n):
    z=1.959964;p=w/n;d=1+z*z/n;c=(p+z*z/2/n)/d;r=z*math.sqrt(p*(1-p)/n+z*z/4/n/n)/d;return c-r,c+r
def summarize(records):
    x=pd.DataFrame(records);n=len(x);lo,hi=ci(x.win.sum(),n)
    return dict(n=n,wr=x.win.mean(),wr_lo=lo,wr_hi=hi,censor=x.censored.mean(),draw=x.draw.mean(),turns=x.turns.mean(),hp=x.hp.mean(),
                normal_rate=x.normal_rate.mean(),carry_rate=x.carry_rate.mean(),backup_rate=x.backup_rate.mean(),filler_rate=x.filler_rate.mean(),
                damage_per_round=x.damage_per_round.mean(),downside=x.downside.mean(),top_count=x.top_count.max(),stat_gain=x.stat_gain.mean(),bp_gain=x.bp_gain.mean())
def positions(members,mode,count=4):
    priority={'front':['carry','backup','filler'],'backup':['backup','carry','filler'],'filler':['filler','backup','carry']}[mode]
    return sorted(range(len(members)),key=lambda j:(priority.index(members[j].role),j))[:min(count,len(members))]
def member_items(members,job):
    items=list(equipment(members,job['genre'],job.get('points',0.),job.get('axis','theme'),job.get('bp_each',0.)))
    if job.get('top_kind'):
        for pos in positions(members,job.get('allocation','front'),job.get('top_count',4)):
            old=items[pos];items[pos]=Item(job['top_kind'],job.get('top_value',0.),old.stats,old.bp,True)
    for entry in job.get('loadout',[]):
        pos,kind,value=entry;old=items[pos];items[pos]=Item(kind,value,old.stats,old.bp,True)
    return tuple(items)
def modify_roster(members,job):
    if not job.get('foreign'):return members
    index=job.get('foreign_position',0);foreign=roster(job['stage'],job['foreign'],job.get('carry',2),job.get('backup',4),job.get('pool',0))
    out=list(members);old=out[index];new=foreign[min(index,len(foreign)-1)]
    total=sum(old.stats);scale=total/sum(new.stats);s=copy.copy(new.skill);s.id=old.skill.id
    out[index]=Member(old.uid,old.role,tuple(v*scale for v in new.stats),old.bp,s);return tuple(out)
def evaluate(job):
    results=[];baseline=[]
    for j in range(job.get('trials',96)):
        pool=j%8;stage=job['stage'];g=job['genre'];h=job.get('opponent',GENRES[j%6])
        members=roster(stage,g,job.get('carry',2),job.get('backup',4),pool,job.get('order','default'))
        enemy=roster(stage,h,job.get('enemy_carry',2),job.get('enemy_backup',4),(j+3)%8)
        enemy_items=member_items(enemy,dict(genre=h,points=job.get('enemy_points',0.),axis=job.get('enemy_axis','theme'),loadout=job.get('enemy_loadout',[]))) if job.get('enemy_loadout') else None
        items=member_items(members,job);p=job.get('p');rs=seed(job.get('stream','screen'),stage,g,h,j)
        if job.get('paired'):
            basejob=job.get('base',{})
            basemembers=roster(stage,g,basejob.get('carry',job.get('carry',2)),basejob.get('backup',job.get('backup',4)),pool,basejob.get('order',job.get('order','default')))
            baseitems=member_items(basemembers,dict(job,top_kind=None,loadout=[],**basejob))
            old,_,_,_=simulate(basemembers,enemy,rs,baseitems,enemy_items=enemy_items,p=p);baseline.append(old)
        members=modify_roster(members,dict(job,pool=pool))
        new,_,_,_=simulate(members,enemy,rs,items,enemy_items=enemy_items,p=p);results.append(new)
    summary=summarize(results)
    if baseline:
        base=summarize(baseline);d=np.array([b['win']-a['win'] for a,b in zip(baseline,results)]);se=d.std(ddof=1)/math.sqrt(len(d))
        summary.update(base_wr=base['wr'],base_turns=base['turns'],base_normal=base['normal_rate'],delta=d.mean(),delta_lo=d.mean()-1.96*se,delta_hi=d.mean()+1.96*se,
                       output_ratio=summary['damage_per_round']/base['damage_per_round'] if base['damage_per_round'] else 0.,base_censor=base['censor'])
    return summary

class Study:
    def __init__(self,args):
        self.args=args;self.out=Path(args.output).resolve();self.out.mkdir(parents=True,exist_ok=True);(self.out/'figures').mkdir(exist_ok=True)
        self.pool=cf.ProcessPoolExecutor(max_workers=args.workers);self.total=0;self.started=time.time()
        save_json(self.out/'settings.json',vars(args))
    def log(self,text):print(time.strftime('%H:%M:%S'),text,flush=True)
    def csv(self,name,data):
        # Macro self-healing delta and paired win-rate delta are different units.
        if list(data.columns).count('delta')>1:
            cols=list(data.columns);cols[cols.index('delta')]='macro_delta';data=data.copy();data.columns=cols
        assert not data.columns.duplicated().any(),name
        data.to_csv(self.out/name,index=False,encoding='utf-8-sig')
    def jobs(self,jobs):
        out=[]
        for i,r in enumerate(self.pool.map(evaluate,jobs,chunksize=2)):
            out.append(r)
            if (i+1)%300==0:self.log(f'{i+1}/{len(jobs)} experiment cells complete')
        self.total+=sum(j.get('trials',96)*(2 if j.get('paired') else 1) for j in jobs)
        return out
    def read(self,name):return pd.read_csv(self.out/name)
    def scenario(self,s,g,d=3):
        r=self.scenarios[(self.scenarios.stage==s)&(self.scenarios.genre==g)&(self.scenarios.difficulty==d)].iloc[0]
        return dict(stage=s,genre=g,opponent=r.opponent,p=[float(r[k]) for k in MACRO_NAMES])

    def audit(self):
        data=parity_test(600)
        data.update(research_rule='Spec 01: defender initiative evasion and effective resilience for DoT',top_limit=4,equipment_per_member=1,
                    selection='independent rolls in member order; first success ends selection',counts='per member skill instance',normal_owner='uniform random member, current BattleTroop.SelectSkill',
                    roster_source='native portfolios + current skill generator + stage budgets; explicit reproducible benchmark members')
        save_json(self.out/'rules_audit.json',data)

    def rosters(self):
        if (self.out/'roster_recommendations.csv').exists():self.roster_choice=self.read('roster_recommendations.csv');return
        meta=[];jobs=[]
        for s in range(6):
            n=STAGES[s][0]
            for g in GENRES:
                for c in (1,2,4):
                    if c>=n:continue
                    for b in sorted(set(min(n-c,x) for x in (0,2,4,6,8,12))):
                        for order in ('default','backup_first'):
                            meta.append(dict(stage=s,genre=g,carry=c,backup=b,order=order))
                            jobs.append(dict(stage=s,genre=g,carry=c,backup=b,order=order,trials=96,stream='roster-training',p=[1.3,1.1,0,0,0,1]))
        self.log('all six stages: role counts and ordering scan')
        df=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.jobs(jobs))],axis=1);self.csv('roster_count_order_scan.csv',df)
        # Select survival/output and coverage, retaining tradeoff table instead of imposing a guaranteed skill threshold.
        df['score']=df.wr+.2*df.damage_per_round-.1*df.normal_rate-.5*df.censor
        chosen=df.sort_values(['score','backup'],ascending=[False,True]).groupby(['stage','genre']).head(1)
        self.roster_choice=chosen[['stage','genre','carry','backup','order','wr','normal_rate']].sort_values(['stage','genre']);self.csv('roster_recommendations.csv',self.roster_choice)

    def recipe(self,s,g):
        r=self.roster_choice[(self.roster_choice.stage==s)&(self.roster_choice.genre==g)].iloc[0]
        return dict(carry=int(r.carry),backup=int(r.backup),order=r.order)

    def enemies(self):
        if (self.out/'difficulty_holdout.csv').exists():self.scenarios=self.read('difficulty_candidates.csv');return
        unit=qmc.Sobol(6,scramble=True,seed=20261012).random_base2(6)
        vectors=qmc.scale(unit,BOUNDS[:,0],BOUNDS[:,1]).tolist()
        vectors += [[a,b,0,0,t,1] for a in (.3,.6,1.,1.5,2.) for b in (.3,.7,1.1,1.7) for t in (0.,)]
        meta=[];jobs=[]
        for s in range(6):
            for g in GENRES:
                for h in GENRES:
                    for k,p in enumerate(vectors):
                        meta.append(dict(stage=s,genre=g,opponent=h,point=k,**dict(zip(MACRO_NAMES,p))))
                        jobs.append(dict(stage=s,genre=g,opponent=h,p=p,**self.recipe(s,g),trials=12,stream='enemy-global'))
        self.log('task 1: complete-stage, per-flow difficulty landscape')
        scan=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.jobs(jobs))],axis=1);self.csv('enemy_global_scan.csv',scan)
        candidates=[];calibration=[]
        for s in range(6):
            for g in GENRES:
                sub=scan[(scan.stage==s)&(scan.genre==g)]
                for d,target,time_ref in ((3,.70,8.),(4,.50,14.),(1,.99,2.),(2,.93,5.)):
                    score=(sub.wr-target).abs()+.03*(sub.turns-time_ref).abs()+2*sub.censor
                    row=sub.loc[score.idxmin()];p=[row[k] for k in MACRO_NAMES]
                    # Data-driven local refinement changes all six channels, preserving stage and enemy profile.
                    u=qmc.Sobol(6,scramble=True,seed=seed(s,g,d)%2**32).random_base2(3)
                    local=[p]+[np.clip(np.array(p)+(v-.5)*.16*(BOUNDS[:,1]-BOUNDS[:,0]),BOUNDS[:,0],BOUNDS[:,1]).tolist() for v in u]
                    for idx,v in enumerate(local):
                        calibration.append(dict(stage=s,genre=g,opponent=row.opponent,difficulty=d,point=idx,**dict(zip(MACRO_NAMES,v))))
        jobs=[dict(stage=r['stage'],genre=r['genre'],opponent=r['opponent'],p=[r[k] for k in MACRO_NAMES],**self.recipe(r['stage'],r['genre']),trials=96,stream=f"difficulty-local-{r['difficulty']}") for r in calibration]
        local=pd.concat([pd.DataFrame(calibration),pd.DataFrame(self.jobs(jobs))],axis=1);self.csv('enemy_local_scan.csv',local)
        for (s,g,d),sub in local.groupby(['stage','genre','difficulty']):
            target,time_ref={1:(.99,2),2:(.93,5),3:(.70,8),4:(.50,14)}[d]
            score=(sub.wr-target).abs()+.03*(sub.turns-time_ref).abs()+2*sub.censor
            r=sub.loc[score.idxmin()];candidates.append(dict(stage=s,genre=g,difficulty=d,opponent=r.opponent,**{k:r[k] for k in MACRO_NAMES}))
        self.scenarios=pd.DataFrame(candidates);self.csv('difficulty_candidates.csv',self.scenarios)
        jobs=[dict(stage=r.stage,genre=r.genre,opponent=r.opponent,p=[getattr(r,k) for k in MACRO_NAMES],**self.recipe(r.stage,r.genre),trials=600,stream=f'difficulty-holdout-{r.difficulty}') for r in self.scenarios.itertuples()]
        self.csv('difficulty_holdout.csv',pd.concat([self.scenarios,pd.DataFrame(self.jobs(jobs))],axis=1))
        coefficients=[]
        for g,sub in self.scenarios.groupby('genre'):
            X=np.c_[sub.stage/5,(sub.difficulty-1)/3];poly=PolynomialFeatures(2);Z=poly.fit_transform(X)
            y=sub[list(MACRO_NAMES)].to_numpy();u=np.clip((y-BOUNDS[:,0])/(BOUNDS[:,1]-BOUNDS[:,0]),.001,.999)
            fit=Ridge(alpha=.05,fit_intercept=False).fit(Z,np.log(u/(1-u)))
            coefficients.append(dict(genre=g,basis=poly.get_feature_names_out(['stage','difficulty']).tolist(),coefficients=fit.coef_.tolist()))
        save_json(self.out/'continuous_delivery_by_flow.json',dict(formula='L+(U-L)*sigmoid(dot(w,[1,s,d,s^2,s*d,d^2]))',coefficients=coefficients,parameter_order=MACRO_NAMES,bounds=BOUNDS.tolist(),enemy_profiles='discrete opponent codes remain in difficulty_candidates.csv'))

    def telemetry(self):
        if (self.out/'telemetry_features.csv.gz').exists():self.tele=self.read('telemetry_features.csv.gz');return
        jobs=[]
        for s in range(6):
            for g in GENRES:
                for d in (3,4):
                    jobs.append(dict(**self.scenario(s,g,d),**self.recipe(s,g),difficulty=d,trials=400,output=str(self.out),stream='telemetry-'+str(d)))
        self.log('task 2: 28,800 complete-roster battles, ownership and every-round probability telemetry')
        records=[]
        for result in self.pool.map(telemetry_job,jobs,chunksize=1):records.extend(result)
        self.tele=pd.DataFrame(records);self.csv('telemetry_features.csv.gz',self.tele);self.total+=len(records)

    def discovery(self):
        if (self.out/'cluster_descriptions.csv').exists():return
        excluded={'battle_id','stage','genre','opponent','difficulty','seed','win','source_win','censored','draw','turns','hp','enemy_hp','damage','damage_per_round','normal_rate','carry_rate','backup_rate','filler_rate','top_count','stat_gain','bp_gain','margin','downside',*MACRO_NAMES}
        cols=[c for c in self.tele if c not in excluded and self.tele[c].std()>1e-12]
        X=self.tele[cols].to_numpy();train,test=train_test_split(np.arange(len(X)),test_size=.3,random_state=20261012)
        scale=StandardScaler().fit(X[train]);Z=scale.transform(X);pca=PCA().fit(Z[train]);ratio=pca.explained_variance_ratio_;k=np.searchsorted(np.cumsum(ratio),.90)+1
        PC=pca.transform(Z)[:,:k];models=[];scores=[]
        for n in range(2,11):
            km=KMeans(n_clusters=n,n_init=5,random_state=20261012).fit(PC[train]);sil=silhouette_score(PC[test],km.predict(PC[test]),sample_size=1200,random_state=20261012)
            scores.append(dict(k=n,silhouette=sil));models.append(km)
        km=models[np.argmax([x['silhouette'] for x in scores])];labels=km.predict(PC)
        self.tele['cluster']=labels;self.tele['split']='train';self.tele.loc[test,'split']='holdout';self.csv('telemetry_cluster_assignments.csv.gz',self.tele)
        joblib.dump(dict(scaler=scale,pca=pca,km=km,features=cols,k=int(k)),self.out/'discovery_models.joblib')
        self.csv('pca_variance.csv',pd.DataFrame(dict(pc=np.arange(1,len(ratio)+1),variance=ratio,cumulative=np.cumsum(ratio))))
        pd.DataFrame(pca.components_.T,index=cols).to_csv(self.out/'pca_loadings.csv');self.csv('cluster_model_selection.csv',pd.DataFrame(scores))
        self.tele[cols+['win','turns','normal_rate']].corr().to_csv(self.out/'feature_correlations.csv')
        contribution=(pca.components_[:k]**2*ratio[:k,None]).sum(0);rank=pd.DataFrame(dict(feature=cols,contribution=contribution)).sort_values('contribution',ascending=False);self.csv('feature_variance_ranking.csv',rank)
        descriptions=[];centroids=[]
        for cl in range(km.n_clusters):
            ix=np.flatnonzero(labels==cl);mean=Z[ix].mean(0);top=np.argsort(abs(mean))[::-1][:5]
            descriptions.append(dict(cluster=cl,n=len(ix),wr=self.tele.iloc[ix].win.mean(),label='; '.join(f'{cols[j]}={mean[j]:+.3f}SD' for j in top)))
            centroids.append(dict(cluster=cl,**dict(zip(cols,X[ix].mean(0)))))
        self.csv('cluster_centroids.csv',pd.DataFrame(centroids));self.csv('cluster_descriptions.csv',pd.DataFrame(descriptions))
        # Stratified centroid summaries keep all six stages visible even with global PCA.
        self.csv('stage_cluster_distribution.csv',self.tele.groupby(['stage','genre','cluster']).agg(n=('win','size'),wr=('win','mean'),normal=('normal_rate','mean')).reset_index())
        fig,axs=plt.subplots(1,2,figsize=(12,4),constrained_layout=True);axs[0].bar(np.arange(1,len(ratio)+1),ratio);axs[1].plot(np.arange(1,len(ratio)+1),np.cumsum(ratio));axs[1].axhline(.9,ls='--',color='grey')
        for ax in axs:ax.set_xlabel('PC')
        fig.savefig(self.out/'figures/pca_variance.png',dpi=150);plt.close(fig)
        topcols=rank.feature.head(24).tolist()+['win','normal_rate'];corr=self.tele[topcols].corr();fig,ax=plt.subplots(figsize=(12,10),constrained_layout=True);im=ax.imshow(corr,vmin=-1,vmax=1,cmap='coolwarm');ax.set_xticks(range(len(topcols)),topcols,rotation=90,fontsize=7);ax.set_yticks(range(len(topcols)),topcols,fontsize=7);fig.colorbar(im,ax=ax);fig.savefig(self.out/'figures/correlation_matrix.png',dpi=150);plt.close(fig)
        self.log(f'ownership trajectories: {k} PCs explain 90%; KMeans K={km.n_clusters}')

    def finish(self):
        save_json(self.out/('manifest.json' if self.total or not (self.out/'manifest.json').exists() else 'cached_foundation_manifest.json'),dict(args=vars(self.args),simulations_current_run=self.total,elapsed_seconds=time.time()-self.started,
                  source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),stage_count=6,flow_count=6,top_equipment_limit=4))
        self.pool.shutdown()

def telemetry_job(job):
    records=[];out=Path(job['output']);s=job['stage'];g=job['genre'];d=job['difficulty']
    with gzip.open(out/f'rounds_S{s+1}_{g}_D{d}.jsonl.gz','wt',encoding='utf-8') as raw, gzip.open(out/f'owners_S{s+1}_{g}_D{d}.jsonl.gz','wt',encoding='utf-8') as ownerfile:
        for j in range(job['trials']):
            members=roster(s,g,job['carry'],job['backup'],j%8,job['order']);enemy=roster(s,job['opponent'],2,4,(j+3)%8)
            rs=seed(job['stream'],s,g,j);r,f,rows,owners=simulate(members,enemy,rs,p=job['p'],telemetry=True)
            bid=f'S{s+1}_{g}_D{d}_{j}';context=dict(battle_id=bid,stage=s,genre=g,opponent=job['opponent'],difficulty=d,seed=str(rs),**dict(zip(MACRO_NAMES,job['p'])))
            records.append(dict(**context,**r,**f));raw.write(json.dumps(dict(**context,result=r,rounds=rows),ensure_ascii=False)+'\n');ownerfile.write(json.dumps(dict(battle_id=bid,members=owners),ensure_ascii=False)+'\n')
    return records

def main():
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=8);p.add_argument('--output',default=str(Path(__file__).parent/'results'));p.add_argument('--phase',choices=('foundation','all'),default='all');args=p.parse_args()
    study=Study(args);study.audit();study.rosters();study.enemies();study.telemetry();study.discovery();study.finish()
    if args.phase=='all':
        import subprocess,sys
        for script in ('equipment_study.py','stage_extensions.py','delivery_validation.py','final_checks.py','build_report.py'):
            subprocess.run([sys.executable,str(Path(__file__).parent/script),'--workers',str(args.workers),'--output',args.output],check=True)

if __name__=='__main__':main()
