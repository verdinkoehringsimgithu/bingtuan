"""Expand saved telemetry and refit unsupervised models with isolated splits."""
from run_natural import *
from trajectory_features import enrich
import shutil


def main():
    if (OUT/'trajectory_enrichment_manifest.json').exists():return
    backup=OUT/'discovery_before_trajectory_enrichment';backup.mkdir(exist_ok=True)
    for path in [OUT/'per_stage_discovery.csv',OUT/'telemetry_features.csv.gz',*OUT.glob('stage_S*')]:
        if path.is_file() and not (backup/path.name).exists():shutil.copy2(path,backup/path.name)
    frame=pd.read_csv(OUT/'telemetry_features.csv.gz',dtype={'seed':str});extra=[];round_count=0;owner_count=0
    for s in range(6):
        for g in GENRES:
            for d in (3,4):
                with gzip.open(OUT/f'rounds_S{s+1}_{g}_D{d}.jsonl.gz','rt',encoding='utf-8') as stream:
                    for line in stream:
                        record=json.loads(line);round_count+=len(record['rounds']);extra.append(dict(battle_id=record['battle_id'],**enrich({},record['rounds'])))
                with gzip.open(OUT/f'owners_S{s+1}_{g}_D{d}.jsonl.gz','rt',encoding='utf-8') as stream:
                    for line in stream:owner_count+=len(json.loads(line)['members'])
    frame=frame.merge(pd.DataFrame(extra),on='battle_id',validate='one_to_one');csv('telemetry_features.csv.gz',frame)
    excluded={'battle_id','stage','genre','opponent','difficulty','seed','win','source_win','censored','draw','turns','hp','enemy_hp','damage','damage_per_round','normal_rate','carry_rate','backup_rate','filler_rate','top_count','stat_gain','bp_gain','margin','downside',*PARAMS};summaries=[]
    for s,sub in frame.groupby('stage'):
        sub=sub.reset_index(drop=True);columns=[c for c in sub if c not in excluded and sub[c].std()>1e-12];X=sub[columns].to_numpy();idx=np.random.default_rng(20261012+s).permutation(len(X));train,val,test=idx[:3600],idx[3600:4800],idx[4800:]
        scaler=StandardScaler().fit(X[train]);Z=scaler.transform(X);pca=PCA().fit(Z[train]);k=int(np.searchsorted(np.cumsum(pca.explained_variance_ratio_),.9)+1);pc=pca.transform(Z)[:,:k];scores=[];models=[]
        for clusters in range(2,9):
            km=KMeans(clusters,n_init=5,random_state=20261012).fit(pc[train]);scores.append(silhouette_score(pc[val],km.predict(pc[val]),sample_size=800,random_state=20261012));models.append(km)
        km=models[int(np.argmax(scores))];sub['cluster']=km.predict(pc);sub['split']='train';sub.loc[val,'split']='validation';sub.loc[test,'split']='test';csv(f'stage_S{s+1}_cluster_assignments.csv.gz',sub)
        pd.DataFrame(pca.components_.T,index=columns).to_csv(OUT/f'stage_S{s+1}_pca_loadings.csv');csv(f'stage_S{s+1}_pca_variance.csv',pd.DataFrame(dict(pc=np.arange(1,len(pca.explained_variance_ratio_)+1),variance=pca.explained_variance_ratio_,cumulative=np.cumsum(pca.explained_variance_ratio_))))
        sub[columns+['win']].corr().to_csv(OUT/f'stage_S{s+1}_correlations.csv');centers=[]
        for cl,group in sub.groupby('cluster'):
            z=Z[group.index].mean(0);largest=np.argsort(abs(z))[::-1][:6];centers.append(dict(cluster=cl,n=len(group),wr=group.win.mean(),label='; '.join(f'{columns[i]}={z[i]:+.3f}SD' for i in largest),**dict(zip(columns,X[group.index].mean(0)))))
        csv(f'stage_S{s+1}_cluster_centroids.csv',pd.DataFrame(centers));joblib.dump(dict(features=columns,scaler=scaler,pca=pca,km=km,k=k),OUT/f'stage_S{s+1}_models.joblib')
        summaries.append(dict(stage=s,n=len(sub),features=len(columns),pca_k90=k,clusters=km.n_clusters,validation_silhouette=max(scores),test_silhouette=silhouette_score(pc[test],km.predict(pc[test]),sample_size=800,random_state=20261012)));print('enriched discovery',s+1,flush=True)
    csv('per_stage_discovery.csv',pd.DataFrame(summaries));save_json(OUT/'trajectory_enrichment_manifest.json',dict(battles=len(frame),rounds=round_count,player_owners=owner_count,train_per_stage=3600,validation_per_stage=1200,test_per_stage=1200,outcome_excluded_from_inputs=True))


if __name__=='__main__':main()
