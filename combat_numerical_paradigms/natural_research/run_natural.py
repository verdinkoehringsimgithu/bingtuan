"""Three tasks for six stages, using actual C# generator records and natural stats."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
from natural_core import *
import argparse,time,gzip,sqlite3,concurrent.futures as cf
import pandas as pd
from scipy.stats import qmc
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import joblib
from run_study import summarize,save_json
from equipment_study import MECHANIC_VALUES,knee
OUT=Path(__file__).parent/'results'
PARAMS=('alpha','beta','gamma','delta','theta','mu','scale_c','scale_r','scale_i','scale_m')
BOUNDS=np.array(((.06,3.5),(.015,2.5),(0,.8),(0,.5),(-200,500),(.6,2.),(.1,1.6),(.1,1.6),(.1,1.6),(.1,1.6)))
PROFILE=json.loads((OUT/'selected_stat_profile.json').read_text(encoding='utf-8'))
COMMON={(r['stage'],r['genre']):r['points'] for r in PROFILE['equipment_points']}

def csv(name,frame):
    cols=list(frame.columns)
    if cols.count('delta')>1:cols[cols.index('delta')]='macro_delta';frame=frame.copy();frame.columns=cols
    assert not frame.columns.duplicated().any(),name
    target=OUT/name;temporary=target.with_name(target.name+'.tmp')
    frame.to_csv(temporary,index=False,encoding='utf-8-sig',compression='gzip' if name.endswith('.gz') else None)
    temporary.replace(target)

def calculation_signature():
    paths=[Path(__file__),Path(__file__).with_name('natural_core.py'),core.SOURCE,
           ROOT/'combat_numerical_paradigms/roster_research/roster_core.py',
           OUT/'catalog_current.json',OUT/'catalog_holdout.json',OUT/'selected_stat_profile.json']
    h=hashlib.sha256()
    for path in paths:h.update(path.read_bytes())
    return h.hexdigest()

CALCULATION_SIGNATURE=calculation_signature()

def members(job,j,enemy=False):
    s=job['stage'];g=job.get('opponent',GENRES[j%6]) if enemy else job['genre'];valid=job.get('validation',False)
    r=roster(s,g,(j+7 if enemy else j)+job.get('pool_offset',0),carry=job.get('enemy_carry',2) if enemy else job.get('carry',2),backup=job.get('enemy_backup',4) if enemy else job.get('backup',4),
             mix=job.get('enemy_mix',.7) if enemy else job.get('mix',.7),order='default' if enemy else job.get('order','default'),validation=valid)
    if enemy and job.get('p'):
        scale=job['p'][6:10];r=tuple(Member(m.uid,m.role,tuple(v*x for v,x in zip(m.stats,scale)),m.bp,m.skill) for m in r)
    if not enemy and job.get('foreign'):
        pos=job.get('foreign_position',0);alt=roster(s,job['foreign'],j+job.get('pool_offset',0),validation=valid)[pos];original=r[pos]
        # Reassign a fixed personal total across four channels; BP and ordering remain owned.
        total=sum(original.stats);v=np.array(alt.stats)*total/sum(alt.stats);skill=copy.copy(alt.skill);skill.id=original.skill.id
        rr=list(r);rr[pos]=Member(original.uid,original.role,tuple(v),original.bp,skill);r=tuple(rr)
    return r

def items(m,job):
    pts=job.get('points',COMMON[(job['stage'],job['genre'])]);load=job.get('loadout',[])
    if job.get('kind'):
        priority={'front':('carry','backup','filler'),'backup':('backup','carry','filler'),'filler':('filler','backup','carry')}[job.get('allocation','front')]
        pos=sorted(range(len(m)),key=lambda j:(priority.index(m[j].role),j))[:min(4,job.get('stock',4))];load=[(j,job['kind'],job['value']) for j in pos]
    return equipment(m,job['genre'],pts,job.get('axis','theme'),job.get('item_mix',.67),load)

def evaluate(job):
    out=[];base=[]
    for j in range(job.get('trials',128)):
        m=members(job,j);e=members(job,j,True);it=items(m,job);rs=seed(job.get('stream','natural-screen'),job['stage'],job['genre'],job.get('opponent'),j)
        p=job.get('p');p=p[:6] if p is not None else None
        if job.get('paired'):
            bj={**job,**job.get('base',{}),'kind':None,'loadout':[]};bm=members(bj,j);bi=items(bm,bj);r,_,_,_=simulate(bm,e,rs,bi,p=p);base.append(r)
        r,_,_,_=simulate(m,e,rs,it,p=p);out.append(r)
    result=summarize(out)
    if base:
        b=summarize(base);d=np.array([r['win']-s['win'] for r,s in zip(out,base)]);se=d.std(ddof=1)/math.sqrt(len(d))
        result.update(base_wr=b['wr'],base_hp=b['hp'],base_turns=b['turns'],delta=d.mean(),delta_lo=d.mean()-1.96*se,delta_hi=d.mean()+1.96*se,output_ratio=result['damage_per_round']/b['damage_per_round'],base_downside=b['downside'])
    return result

def objective(r,d):
    dist=lambda x,lo,hi:max(lo-x,0,x-hi)
    if d==1:return 40*max(0,.99-r['wr'])+.25*dist(r['turns'],1,3)+6*max(0,.85-r['hp'])+5*r['censor']
    target,turn_lo,turn_hi,hp_lo,hp_hi={2:(.925,4,6,.60,.75),3:(.75,7,10,.30,.50),4:(.50,12,18,.05,.20)}[d]
    return 8*abs(r['wr']-target)+.15*dist(r['turns'],turn_lo,turn_hi)+4*dist(r['hp'],hp_lo,hp_hi)+5*r['censor']

def refine(job):
    d=job['difficulty'];x=np.array(job['p']);base={k:v for k,v in job.items() if k!='difficulty'};trace=[]
    # A deterministic coordinate search; all ten axes remain available.
    for cycle in range(3):
        candidates=[x.copy()]
        for k in (0,1,5,6,7,8,9):
            for ratio in (.75,1.25):
                p=x.copy();p[k]=np.clip(p[k]*ratio,*BOUNDS[k]);candidates.append(p)
        for k,step in ((2,.05),(3,.015),(4,35)):
            for sign in (-1,1):
                p=x.copy();p[k]=np.clip(p[k]+sign*step,*BOUNDS[k]);candidates.append(p)
        rows=[]
        for p in candidates:
            r=evaluate({**base,'p':p.tolist(),'trials':128,'stream':f'natural-joint-local-{d}'});score=objective(r,d)
            rows.append((score,p,r));trace.append(dict(stage=job['stage'],genre=job['genre'],difficulty=d,opponent=job['opponent'],cycle=cycle,score=score,**dict(zip(PARAMS,p)),**r))
        _,x,_=min(rows,key=lambda z:z[0])
    best=min(trace,key=lambda r:r['score']);return best,trace

def telemetry_job(job):
    s,g,d=job['stage'],job['genre'],job['difficulty'];records=[]
    prefix=f'S{s+1}_{g}_D{d}';done=OUT/f'telemetry_checkpoint_{prefix}.json'
    signature=hashlib.sha256((CALCULATION_SIGNATURE+json.dumps(job,sort_keys=True)).encode()).hexdigest()
    if done.exists():
        prior=json.loads(done.read_text(encoding='utf-8'))
        if prior['signature']==signature:return prior['records']
    rounds_path=OUT/f'rounds_{prefix}.jsonl.gz';owners_path=OUT/f'owners_{prefix}.jsonl.gz'
    rounds_tmp=rounds_path.with_name(rounds_path.name+'.tmp');owners_tmp=owners_path.with_name(owners_path.name+'.tmp')
    with gzip.open(rounds_tmp,'wt',encoding='utf-8') as f,gzip.open(owners_tmp,'wt',encoding='utf-8') as of:
        for j in range(500):
            m=members(job,j);e=members(job,j,True);it=items(m,job);rs=seed('natural-telemetry',s,g,d,j)
            r,features,rounds,owners=simulate(m,e,rs,it,p=job['p'][:6],telemetry=True)
            context=dict(battle_id=f'S{s+1}_{g}_D{d}_{j}',stage=s,genre=g,opponent=job['opponent'],difficulty=d,seed=str(rs),**dict(zip(PARAMS,job['p'])))
            records.append(dict(**context,**r,**features));f.write(json.dumps(dict(**context,result=r,rounds=rounds),ensure_ascii=False)+'\n');of.write(json.dumps(dict(battle_id=context['battle_id'],members=owners),ensure_ascii=False)+'\n')
    rounds_tmp.replace(rounds_path);owners_tmp.replace(owners_path)
    temporary=done.with_suffix('.json.tmp');temporary.write_text(json.dumps(dict(signature=signature,records=records)),encoding='utf-8');temporary.replace(done)
    return records

class Study:
    def __init__(self,workers):
        self.pool=cf.ProcessPoolExecutor(workers);self.total=0;self.cached_executions=0;self.started=time.time()
        self.cache=sqlite3.connect(OUT/'calculation_checkpoints.sqlite');self.cache.execute('PRAGMA journal_mode=WAL')
        self.cache.execute('CREATE TABLE IF NOT EXISTS cells (key TEXT PRIMARY KEY, job TEXT NOT NULL, result TEXT NOT NULL, executions INTEGER NOT NULL)');self.cache.commit()
    def log(self,msg):print(time.strftime('%H:%M:%S'),msg,flush=True)
    def jobs(self,jobs):
        rows=[None]*len(jobs);missing=[];keys=[];indices=[]
        for index,job in enumerate(jobs):
            encoded=json.dumps(job,sort_keys=True,default=lambda x:float(x),separators=(',',':'))
            key=hashlib.sha256((CALCULATION_SIGNATURE+encoded).encode()).hexdigest();saved=self.cache.execute('SELECT result,executions FROM cells WHERE key=?',(key,)).fetchone()
            if saved:rows[index]=json.loads(saved[0]);self.cached_executions+=saved[1]
            else:missing.append(job);keys.append((key,encoded));indices.append(index)
        for completed,(index,key,job,r) in enumerate(zip(indices,keys,missing,self.pool.map(evaluate,missing,chunksize=2)),1):
            count=job.get('trials',128)*(2 if job.get('paired') else 1);rows[index]=r
            self.cache.execute('INSERT OR REPLACE INTO cells VALUES (?,?,?,?)',(key[0],key[1],json.dumps(r,default=lambda x:float(x)),count));self.cache.commit();self.total+=count
            if completed%300==0:self.log(f'{completed}/{len(missing)} new cells saved; {len(jobs)-len(missing)} reused')
        return rows
    def scene(self,s,g,d):
        r=self.scenes[(self.scenes.stage==s)&(self.scenes.genre==g)&(self.scenes.difficulty==d)].iloc[0]
        return dict(stage=int(s),genre=g,opponent=r.opponent,p=[float(r[k]) for k in PARAMS])
    def difficulty(self):
        if (OUT/'difficulty_holdout.csv').exists():self.scenes=pd.read_csv(OUT/'difficulty_candidates.csv');return
        u=qmc.Sobol(10,scramble=True,seed=20261012).random_base2(6);vectors=qmc.scale(u,BOUNDS[:,0],BOUNDS[:,1]).tolist()
        # Include interpretable low-threat anchors and broad original macro space.
        vectors += [[a,b,0,0,0,1,1,1,1,1] for a in (.06,.10,.15,.25,.4,.6,.8,1.2,1.8,2.5) for b in (.04,.12,.3,.6,1.0,1.5)]
        u=qmc.Sobol(10,scramble=True,seed=20261013).random_base2(5)
        low=np.array((.08,.03,0,0,-100,.7,.25,.25,.25,.25));high=np.array((1.5,1.7,.12,.04,150,1.25,1.5,1.5,1.5,1.5));vectors+=qmc.scale(u,low,high).tolist()
        meta=[];jobs=[]
        for s in range(6):
            for g in GENRES:
                for h in GENRES:
                    for k,p in enumerate(vectors):
                        meta.append(dict(stage=s,genre=g,opponent=h,point=k,**dict(zip(PARAMS,p))));jobs.append(dict(stage=s,genre=g,opponent=h,p=p,trials=12,stream='natural-enemy-global'))
        self.log('ten-axis enemy search, natural six-stage rosters')
        df=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.jobs(jobs))],axis=1);csv('enemy_global_scan.csv',df)
        picks=[];jobs=[]
        for (s,g),sub in df.groupby(['stage','genre']):
            for d in (1,2,3,4):
                scores=sub.apply(lambda r:objective(r,d),axis=1);r=sub.loc[scores.idxmin()]
                jobs.append(dict(stage=int(s),genre=g,opponent=r.opponent,p=[r[k] for k in PARAMS],difficulty=d))
        traces=[]
        for best,trace in self.pool.map(refine,jobs,chunksize=1):picks.append(best);traces.extend(trace)
        self.total+=len(traces)*128;csv('enemy_joint_refinement.csv',pd.DataFrame(traces));self.scenes=pd.DataFrame(picks)[['stage','genre','difficulty','opponent',*PARAMS]];csv('difficulty_candidates.csv',self.scenes)
        jobs=[]
        for r in self.scenes.to_dict('records'):
            d=r['difficulty'];jobs.append(dict(stage=int(r['stage']),genre=r['genre'],opponent=r['opponent'],p=[r[k] for k in PARAMS],trials={1:5000,2:2500,3:1500,4:1500}[d],validation=True,pool_offset=512,stream=f'natural-difficulty-final-{d}'))
        csv('difficulty_holdout.csv',pd.concat([self.scenes,pd.DataFrame(self.jobs(jobs))],axis=1))
    def role_scan(self):
        if (OUT/'role_count_holdout.csv').exists():return
        meta=[];jobs=[]
        for s in range(6):
            n=STAGES[s][0]
            for g in GENRES:
                for c in sorted(set(min(n,x) for x in (1,2,4,8,n//2,n))):
                    for b in sorted(set(min(n-c,x) for x in (0,2,4,8))):
                        for order in ('default','backup_first'):
                            meta.append(dict(stage=s,genre=g,carry=c,backup=b,order=order));jobs.append(dict(**self.scene(s,g,4),carry=c,backup=b,order=order,trials=96,stream='natural-role-training'))
        df=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.jobs(jobs))],axis=1);csv('role_count_order_scan.csv',df)
        chosen=df.sort_values(['wr','downside'],ascending=[False,True]).groupby(['stage','genre']).head(1);meta=[];jobs=[]
        for r in chosen.itertuples():
            meta.append(dict(stage=r.stage,genre=r.genre,carry=r.carry,backup=r.backup,order=r.order));jobs.append(dict(**self.scene(r.stage,r.genre,4),carry=r.carry,backup=r.backup,order=r.order,validation=True,pool_offset=768,paired=True,base=dict(carry=2,backup=4,order='default'),trials=800,stream='natural-role-final'))
        csv('role_count_holdout.csv',pd.concat([pd.DataFrame(meta),pd.DataFrame(self.jobs(jobs))],axis=1))
    def equipment(self):
        if not (OUT/'common_stat_scan.csv').exists():
            meta=[];jobs=[]
            for s in range(6):
                for g in GENRES:
                    for d in (3,4):
                        for axis in (*FIELDS,'theme','balanced'):
                            for ratio in (0.,.25,.5,1.,2.,4.,8.):
                                value=COMMON[(s,g)]*ratio;meta.append(dict(stage=s,genre=g,difficulty=d,axis=axis,value=value));jobs.append(dict(**self.scene(s,g,d),axis=axis,points=value,paired=True,base=dict(points=0.),trials=128,stream='natural-common-stat'))
            df=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.jobs(jobs))],axis=1);csv('common_stat_scan.csv',df)
            recommendations=[];slopes=[]
            for (s,g,a),sub in df.groupby(['stage','genre','axis']):
                lo,hi,curve=knee(sub);recommendations.append(dict(stage=s,genre=g,axis=a,lower=lo,upper=hi))
            for (s,g,d,a),sub in df.groupby(['stage','genre','difficulty','axis']):
                sub=sub.sort_values('value');derivative=np.gradient(sub.wr,sub.value)
                for r,v in zip(sub.itertuples(),derivative):slopes.append(dict(stage=s,genre=g,difficulty=d,axis=a,value=r.value,wr=r.wr,partial_per_item=v,partial_per_team=v/STAGES[s][0]))
            csv('common_stat_ranges.csv',pd.DataFrame(recommendations));csv('stat_partial_derivatives.csv',pd.DataFrame(slopes))
        if (OUT/'four_top_holdout.csv').exists() and (OUT/'four_top_scarcity.csv').exists():return
        meta=[];jobs=[]
        for s in range(6):
            for g in GENRES:
                for kind,values in MECHANIC_VALUES.items():
                    for allocation in ('front','backup','filler'):
                        for value in values:
                            meta.append(dict(stage=s,genre=g,kind=kind,allocation=allocation,value=value));jobs.append(dict(**self.scene(s,g,4),kind=kind,allocation=allocation,value=value,trials=96,paired=True,stream='natural-mechanism'))
        if (OUT/'mechanism_response_scan.csv').exists():scan=pd.read_csv(OUT/'mechanism_response_scan.csv')
        else:scan=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.jobs(jobs))],axis=1);csv('mechanism_response_scan.csv',scan)
        selected=[];search=[]
        for s in range(6):
            for g in GENRES:
                sub=scan[(scan.stage==s)&(scan.genre==g)].sort_values('delta_lo',ascending=False).groupby('kind').head(1).head(5);candidates=[(r.kind,r.value) for r in sub.itertuples()];load=[]
                for depth in range(4):
                    meta=[];jobs=[];used={x[0] for x in load}
                    for pos in range(STAGES[s][0]):
                        if pos in used:continue
                        for kind,value in candidates:
                            proposed=load+[(pos,kind,value)];meta.append(dict(stage=s,genre=g,depth=depth+1,loadout=json.dumps(proposed)));jobs.append(dict(**self.scene(s,g,4),loadout=proposed,trials=96,stream=f'natural-four-allocation-{depth}'))
                    frame=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.jobs(jobs))],axis=1);search.extend(frame.to_dict('records'));r=frame.sort_values(['wr_lo','damage_per_round'],ascending=False).iloc[0];load=json.loads(r.loadout)
                selected.append(dict(stage=s,genre=g,loadout=json.dumps(load)))
                self.log(f'S{s+1} {g} top allocation selected')
        csv('four_top_search.csv',pd.DataFrame(search));loads=pd.DataFrame(selected);csv('four_top_loadouts.csv',loads)
        meta=[];jobs=[]
        for r in selected:
            for d in (3,4):
                meta.append(dict(**r,difficulty=d));jobs.append(dict(**self.scene(r['stage'],r['genre'],d),loadout=json.loads(r['loadout']),validation=True,pool_offset=1024,paired=True,trials=1000,stream=f'natural-four-final-{d}'))
        csv('four_top_holdout.csv',pd.concat([pd.DataFrame(meta),pd.DataFrame(self.jobs(jobs))],axis=1))
        meta=[];jobs=[]
        for r in selected:
            for stock in range(5):
                meta.append(dict(stage=r['stage'],genre=r['genre'],stock=stock));jobs.append(dict(**self.scene(r['stage'],r['genre'],4),loadout=json.loads(r['loadout'])[:stock],validation=True,paired=True,trials=320,stream='natural-stock'))
        csv('four_top_scarcity.csv',pd.concat([pd.DataFrame(meta),pd.DataFrame(self.jobs(jobs))],axis=1))
    def telemetry(self):
        if (OUT/'telemetry_features.csv.gz').exists():return
        jobs=[dict(**self.scene(s,g,d),difficulty=d,validation=True,pool_offset=1536) for s in range(6) for g in GENRES for d in (3,4)];records=[]
        for result in self.pool.map(telemetry_job,jobs,chunksize=1):records.extend(result)
        csv('telemetry_features.csv.gz',pd.DataFrame(records));self.total+=len(records)
    def discovery(self):
        if (OUT/'per_stage_discovery.csv').exists():return
        data=pd.read_csv(OUT/'telemetry_features.csv.gz',dtype={'seed':str});excluded={'battle_id','stage','genre','opponent','difficulty','seed','win','source_win','censored','draw','turns','hp','enemy_hp','damage','damage_per_round','normal_rate','carry_rate','backup_rate','filler_rate','top_count','stat_gain','bp_gain','margin','downside',*PARAMS};summaries=[]
        for s,sub in data.groupby('stage'):
            sub=sub.reset_index(drop=True);columns=[c for c in sub if c not in excluded and sub[c].std()>1e-12];X=sub[columns].to_numpy();rng=np.random.default_rng(20261012+s);idx=rng.permutation(len(X));train,val,test=idx[:3600],idx[3600:4800],idx[4800:]
            scaler=StandardScaler().fit(X[train]);Z=scaler.transform(X);pca=PCA().fit(Z[train]);k=int(np.searchsorted(np.cumsum(pca.explained_variance_ratio_),.9)+1);pc=pca.transform(Z)[:,:k];scores=[];models=[]
            for clusters in range(2,9):
                km=KMeans(clusters,n_init=5,random_state=20261012).fit(pc[train]);scores.append(silhouette_score(pc[val],km.predict(pc[val]),sample_size=800,random_state=20261012));models.append(km)
            km=models[int(np.argmax(scores))];sub['cluster']=km.predict(pc);sub['split']='train';sub.loc[val,'split']='validation';sub.loc[test,'split']='test';csv(f'stage_S{s+1}_cluster_assignments.csv.gz',sub)
            pd.DataFrame(pca.components_.T,index=columns).to_csv(OUT/f'stage_S{s+1}_pca_loadings.csv');csv(f'stage_S{s+1}_pca_variance.csv',pd.DataFrame(dict(pc=np.arange(1,len(pca.explained_variance_ratio_)+1),variance=pca.explained_variance_ratio_,cumulative=np.cumsum(pca.explained_variance_ratio_))))
            sub[columns+['win']].corr().to_csv(OUT/f'stage_S{s+1}_correlations.csv');centers=[]
            for cl,group in sub.groupby('cluster'):
                ix=group.index;z=Z[ix].mean(0);highest=np.argsort(abs(z))[::-1][:5];centers.append(dict(cluster=cl,n=len(group),wr=group.win.mean(),label='; '.join(f'{columns[j]}={z[j]:+.3f}SD' for j in highest),**dict(zip(columns,X[ix].mean(0)))))
            csv(f'stage_S{s+1}_cluster_centroids.csv',pd.DataFrame(centers));joblib.dump(dict(features=columns,scaler=scaler,pca=pca,km=km,k=k),OUT/f'stage_S{s+1}_models.joblib');summaries.append(dict(stage=s,n=len(sub),pca_k90=k,clusters=km.n_clusters,validation_silhouette=max(scores),test_silhouette=silhouette_score(pc[test],km.predict(pc[test]),sample_size=800,random_state=20261012)))
        csv('per_stage_discovery.csv',pd.DataFrame(summaries))
    def finish(self,name='experiment_manifest.json'):
        target=OUT/name
        if target.exists():
            history=OUT/'run_history';history.mkdir(exist_ok=True);target=history/(Path(name).stem+'_'+str(time.time_ns())+'.json')
        save_json(target,dict(recorded_executions=self.total,reused_cached_executions=self.cached_executions,calculation_signature=CALCULATION_SIGNATURE,elapsed_seconds=time.time()-self.started,generator_sha256=hashlib.sha256((ROOT/'SkillGenerator.cs').read_bytes()).hexdigest(),research_generator_sha256=hashlib.sha256((Path(__file__).parent/'source_snapshots/SkillGenerator_checkpoint.cs').read_bytes()).hexdigest(),native_sha256=hashlib.sha256(core.SOURCE.read_bytes()).hexdigest(),stages=6,flows=6,top_cap=4));self.cache.close();self.pool.shutdown()

def main():
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=8);p.add_argument('--phase',choices=('foundation','all'),default='all');args=p.parse_args();s=Study(args.workers);s.difficulty()
    if args.phase=='all':s.role_scan();s.equipment();s.telemetry();s.discovery()
    s.finish('foundation_manifest.json' if args.phase=='foundation' else 'continuation_manifest.json')

if __name__=='__main__':main()
