"""Per-stage discovery, unconstrained role-count check and owner-budget intervention."""
from run_study import *

def stage_models(directory):
    q=Path(directory);data=pd.read_csv(q/'telemetry_features.csv.gz',dtype={'seed':str})
    excluded={'battle_id','stage','genre','opponent','difficulty','seed','win','source_win','censored','draw','turns','hp','enemy_hp','damage','damage_per_round','normal_rate','carry_rate','backup_rate','filler_rate','top_count','stat_gain','bp_gain','margin','downside',*MACRO_NAMES}
    summaries=[]
    for s,sub in data.groupby('stage'):
        columns=[c for c in sub if c not in excluded and sub[c].std()>1e-12];X=sub[columns].to_numpy()
        train,test=train_test_split(np.arange(len(X)),test_size=.3,random_state=20261012+s)
        scaler=StandardScaler().fit(X[train]);Z=scaler.transform(X);pca=PCA().fit(Z[train]);ratios=pca.explained_variance_ratio_;k=np.searchsorted(np.cumsum(ratios),.9)+1
        pc=pca.transform(Z)[:,:k];models=[];scores=[]
        for n in range(2,9):
            model=KMeans(n_clusters=n,n_init=5,random_state=20261012).fit(pc[train]);sil=silhouette_score(pc[test],model.predict(pc[test]),sample_size=1000,random_state=20261012);models.append(model);scores.append(sil)
        km=models[np.argmax(scores)];labels=km.predict(pc);sub=sub.copy();sub['cluster']=labels;sub['split']='train';sub.iloc[test,sub.columns.get_loc('split')]='holdout'
        sub.to_csv(q/f'stage_S{s+1}_cluster_assignments.csv.gz',index=False)
        pd.DataFrame(dict(pc=np.arange(1,len(ratios)+1),variance=ratios,cumulative=np.cumsum(ratios))).to_csv(q/f'stage_S{s+1}_pca_variance.csv',index=False)
        sub[columns+['win','normal_rate','turns']].corr().to_csv(q/f'stage_S{s+1}_correlations.csv')
        centers=[];descriptions=[]
        for cl in range(km.n_clusters):
            ix=np.flatnonzero(labels==cl);z=Z[ix].mean(0);top=np.argsort(abs(z))[::-1][:5]
            centers.append(dict(cluster=cl,**dict(zip(columns,X[ix].mean(0)))))
            descriptions.append(dict(cluster=cl,n=len(ix),wr=sub.iloc[ix].win.mean(),label='; '.join(f'{columns[j]}={z[j]:+.3f}SD' for j in top)))
        pd.DataFrame(centers).to_csv(q/f'stage_S{s+1}_cluster_centroids.csv',index=False);pd.DataFrame(descriptions).to_csv(q/f'stage_S{s+1}_cluster_descriptions.csv',index=False)
        joblib.dump(dict(features=columns,scaler=scaler,pca=pca,km=km,k=int(k)),q/f'stage_S{s+1}_models.joblib')
        summaries.append(dict(stage=s,pca_k90=int(k),clusters=km.n_clusters,silhouette=max(scores),battles=len(sub),pc1_variance=ratios[0]))
    pd.DataFrame(summaries).to_csv(q/'per_stage_discovery_summary.csv',index=False)

def expanded_roles(study):
    if (study.out/'expanded_role_count_holdout.csv').exists():return
    meta=[];jobs=[]
    for s in range(6):
        n=STAGES[s][0]
        for g in GENRES:
            for c in sorted(set(min(n,x) for x in (1,2,3,4,6,8,n//2,n-2,n))):
                for b in sorted(set(min(n-c,x) for x in (0,2,4,8,12,n-c))):
                    for d in (3,4):
                        meta.append(dict(stage=s,genre=g,difficulty=d,carry=c,backup=b,filler=n-c-b))
                        jobs.append(dict(**study.scenario(s,g,d),carry=c,backup=b,trials=144,stream='expanded-roles'))
    df=pd.concat([pd.DataFrame(meta),pd.DataFrame(study.jobs(jobs))],axis=1);study.csv('expanded_role_count_scan.csv',df)
    grouped=df.groupby(['stage','genre','carry','backup','filler']).agg(wr=('wr','mean'),normal_rate=('normal_rate','mean'),damage=('damage_per_round','mean')).reset_index()
    grouped['score']=grouped.wr+.2*grouped.damage-.1*grouped.normal_rate
    chosen=grouped.sort_values('score',ascending=False).groupby(['stage','genre']).head(1)
    meta=[];jobs=[]
    for r in chosen.itertuples():
        base=study.recipe(r.stage,r.genre)
        for d in (3,4):
            meta.append(dict(stage=r.stage,genre=r.genre,difficulty=d,carry=r.carry,backup=r.backup,filler=r.filler))
            jobs.append(dict(**study.scenario(r.stage,r.genre,d),carry=r.carry,backup=r.backup,paired=True,base=base,trials=600,stream='expanded-role-independent'))
    study.csv('expanded_role_count_holdout.csv',pd.concat([pd.DataFrame(meta),pd.DataFrame(study.jobs(jobs))],axis=1))

def intervention_worker(job):
    q=Path(job['directory']);s=job['stage'];data=pd.read_csv(q/f'stage_S{s+1}_cluster_assignments.csv.gz',dtype={'seed':str})
    subset=data[data.split==job['split']];subset=subset[subset.censored==0]
    if job['split']=='train':subset=subset.sample(n=min(600,len(subset)),random_state=20261012)
    config=json.loads((q/'stage_roster_equipment_configs.json').read_text(encoding='utf-8'))
    recommended={r['genre']:r for r in config if r['stage']==s+1}
    choices=pd.read_csv(q/'roster_recommendations.csv');candidates=pd.read_csv(q/'difficulty_candidates.csv');records=[]
    for row in subset.itertuples():
        recipe=choices[(choices.stage==s)&(choices.genre==row.genre)].iloc[0];members=list(roster(s,row.genre,int(recipe.carry),int(recipe.backup),int(row.battle_id.rsplit('_',1)[-1])%8,recipe.order))
        # Personal concentration conserves all four team budgets exactly.
        factor=job['share_factor'];owner=0;old=members[owner];target=min(.8,factor/STAGES[s][0]);totals=np.sum([m.stats for m in members],axis=0)
        totals=np.array([sum(m.stats[k] for m in members) for k in range(4)])
        desired=totals*target;other=totals-np.array(old.stats);scale=(totals-desired)/other
        for pos,m in enumerate(members):
            members[pos]=Member(m.uid,m.role,tuple(desired if pos==owner else np.array(m.stats)*scale),m.bp,m.skill)
        last=members[-1];corrected=list(last.stats)
        for k in range(4):corrected[k]+=totals[k]-sum(m.stats[k] for m in members)
        members[-1]=Member(last.uid,last.role,tuple(corrected),last.bp,last.skill)
        members=tuple(members);items=[Item() for _ in members]
        assert all(getattr(Team(members),'base_'+f)==round(totals[k],10) for k,f in enumerate(FIELDS))
        # The lever belongs to the unique character; attribution is never spread by 1/N.
        items[owner]=Item(job['kind'],job['value'],top=True)
        enemy=roster(s,row.opponent,2,4,(int(row.battle_id.rsplit('_',1)[-1])+3)%8)
        p=[getattr(row,k) for k in MACRO_NAMES]
        result,_,_,_=simulate(members,enemy,int(row.seed),tuple(items),p=p)
        records.append(dict(stage=s,genre=row.genre,cluster=row.cluster,kind=job['kind'],value=job['value'],share_factor=factor,share=target,base_win=row.win,win=result['win'],censored=result['censored']))
    return records

def unique_interventions(study):
    if (study.out/'unique_stage_cluster_holdout.csv').exists():return
    meta=[];jobs=[]
    levers=(('skill_damage',.6),('skill_chance',.25),('extra_use',2.),('owner_stats',1.),('opening_shield',.2),('death_lock',.01))
    for s in range(6):
        for kind,value in levers:
            for share in (.5,1.,2.,4.):jobs.append(dict(directory=str(study.out),stage=s,kind=kind,value=value,share_factor=share,split='train'))
    records=[]
    for chunk in study.pool.map(intervention_worker,jobs,chunksize=1):records.extend(chunk)
    train=pd.DataFrame(records);study.csv('unique_owner_training.csv.gz',train)
    agg=train.groupby(['stage','cluster','kind','value','share_factor']).agg(n=('win','size'),base_wr=('base_win','mean'),wr=('win','mean'),share=('share','mean')).reset_index();agg['delta']=agg.wr-agg.base_wr
    # Select cost-smallest observed 20--30 point lift when available; otherwise best lever and magnitude remain visible.
    picks=[]
    for keys,sub in agg.groupby(['stage','cluster']):
        target=sub[sub.delta.between(.2,.3)]
        chosen=target.sort_values(['share_factor','delta']).iloc[0] if len(target) else sub.sort_values(['delta','share_factor'],ascending=[False,True]).iloc[0]
        picks.append(chosen.to_dict())
    study.csv('unique_owner_training_summary.csv',agg);jobs=[]
    for r in picks:jobs.append(dict(directory=str(study.out),stage=int(r['stage']),kind=r['kind'],value=r['value'],share_factor=r['share_factor'],split='holdout',cluster=int(r['cluster'])))
    rows=[]
    for chunk,j in zip(study.pool.map(intervention_worker,jobs,chunksize=1),jobs):rows.extend(x for x in chunk if x['cluster']==j['cluster'])
    data=pd.DataFrame(rows);study.csv('unique_owner_holdout_battles.csv.gz',data);summary=[]
    for keys,sub in data.groupby(['stage','cluster','kind','value','share_factor']):
        d=(sub.win-sub.base_win).to_numpy();se=d.std(ddof=1)/math.sqrt(len(d))
        summary.append(dict(stage=keys[0],cluster=keys[1],kind=keys[2],value=keys[3],share_factor=keys[4],share=sub.share.mean(),n=len(sub),base_wr=sub.base_win.mean(),wr=sub.win.mean(),delta=d.mean(),delta_lo=d.mean()-1.96*se,delta_hi=d.mean()+1.96*se))
    study.csv('unique_stage_cluster_holdout.csv',pd.DataFrame(summary));study.total+=len(train)+len(data)

def decay_curves(study):
    if (study.out/'skill_decay_by_round.csv').exists():return
    points=[];burnout=[]
    for path in study.out.glob('rounds_*.jsonl.gz'):
        with gzip.open(path,'rt',encoding='utf-8') as f:
            for line in f:
                battle=json.loads(line);s=battle['stage'];g=battle['genre'];d=battle['difficulty'];empty=None
                for row in battle['rounds']:
                    if row['p_finite_left_start']==0 and empty is None:empty=row['turn']
                    points.append(dict(stage=s,genre=g,difficulty=d,turn=row['turn'],normal_probability=row['p_expected_normal'],carry_cast=row['p_carry_casts'],backup_cast=row['p_backup_casts'],filler_cast=row['p_filler_casts'],finite_remaining=row['p_finite_left_start'],damage=sum(row['p_'+c] for c in CHANNELS)))
                burnout.append(dict(stage=s,genre=g,difficulty=d,finite_exhausted_turn=empty,turns=len(battle['rounds'])))
    df=pd.DataFrame(points);summary=df.groupby(['stage','genre','difficulty','turn']).agg(at_risk=('damage','size'),normal_probability=('normal_probability','mean'),carry_cast=('carry_cast','mean'),backup_cast=('backup_cast','mean'),filler_cast=('filler_cast','mean'),finite_remaining=('finite_remaining','mean'),damage=('damage','mean')).reset_index();study.csv('skill_decay_by_round.csv',summary)
    study.csv('finite_skill_exhaustion_battles.csv.gz',pd.DataFrame(burnout))
    for s in range(6):
        fig,axs=plt.subplots(2,3,figsize=(13,7),constrained_layout=True)
        for ax,g in zip(axs.flat,GENRES):
            sub=summary[(summary.stage==s)&(summary.genre==g)&(summary.difficulty==3)]
            for col in ('carry_cast','backup_cast','filler_cast','normal_probability'):ax.plot(sub.turn,sub[col],label=col)
            ax.set(title=g,xlabel='round; surviving battles only',ylabel='activation frequency');ax.legend(fontsize=6)
        fig.savefig(study.out/'figures'/f'skill_queue_decay_S{s+1}.png',dpi=150);plt.close(fig)

def main():
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=8);p.add_argument('--output',default=str(Path(__file__).parent/'results'));args=p.parse_args()
    study=Study(args);study.roster_choice=study.read('roster_recommendations.csv');study.scenarios=study.read('difficulty_candidates.csv')
    if not (study.out/'per_stage_discovery_summary.csv').exists():stage_models(study.out)
    study.log('per-stage PCA and clustering complete; expanding role counts independent of four-item cap')
    expanded_roles(study);study.log('task 2: per-stage owned-character intervention and conserved personal budgets')
    unique_interventions(study);decay_curves(study)
    save_json(study.out/'extensions_manifest.json',dict(simulations=study.total,elapsed_seconds=time.time()-study.started));study.pool.shutdown()

if __name__=='__main__':main()
