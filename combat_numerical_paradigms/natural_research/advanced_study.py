"""Owner equipment, cluster-conditional interventions and strategic holdouts."""
from run_natural import *
import ast
import natural_core as natural
from trajectory_features import enrich

EXTRA_VALUES={'skill_hit':(0.,.25,.5,.75,1.),'added_dot':(0.,.005,.01,.02,.04)}
ALL_VALUES={**MECHANIC_VALUES,**EXTRA_VALUES}
_select=core.select_skill


def extra_select(team,enemy,turn):
    selected=_select(team,enemy,turn)
    team.hit_floor=0.
    if selected is not None:
        item=team.items[team.selected_owner]
        if item.kind=='skill_hit':team.hit_floor=item.value
    return selected


class ExtraAdapter(natural.NaturalAdapter):
    def visit_If(self,node):
        original=ast.unparse(node.test)
        result=super().visit_If(node)
        if original=='random.random() < dodge_rate':
            result.test=ast.parse('random.random() < calc_initiative_stats(def_i, eff_i)[0]*(1-getattr(acting,"hit_floor",0.))').body[0].value
        return result


core.select_skill=extra_select;core.Adapter=ExtraAdapter
core.ACTION=core.action_function(True)
_action=core.ACTION


def extra_action(acting,defender,first,turn):
    _action(acting,defender,first,turn)
    pos=acting.selected_owner
    if pos is not None and acting.last_hit and acting.selected_original is not None:
        item=acting.items[pos]
        if item.kind=='added_dot' and item.value>0:
            amp=engine.calc_magic_amp_responsive(acting.get_effective_stats()[3])
            defender.max_bp_dots.append(dict(val=item.value*amp,turns=2,source=acting,owner=pos))


core.ACTION=extra_action


def redistribute(members,factor,target=None):
    if factor==1 and target is None:return members
    old=np.array([m.stats for m in members],dtype=float);total=old.sum(0)
    share=np.clip(old[0]*factor/np.maximum(total,1e-12),0.,.95) if target is None else np.full(4,float(target))
    values=old.copy();values[0]=total*share
    for k in range(4):
        remainder=total[k]-values[0,k]
        values[1:,k]=old[1:,k]*remainder/max(1e-12,old[1:,k].sum())
    assert np.allclose(values.sum(0),total,atol=1e-8)
    return tuple(Member(m.uid,m.role,tuple(v),m.bp,m.skill) for m,v in zip(members,values))


def advanced_evaluate(job):
    out=[];baseline=[];cluster_rows=[];raw_controls=[]
    model=joblib.load(OUT/f"stage_S{job['stage']+1}_models.joblib") if job.get('cluster_results') else None
    for j in range(job.get('trials',128)):
        unmodified=members({**job,'foreign':None},j)
        m=redistribute(members(job,j),job.get('share_factor',1.),job.get('owner_target_share'));enemy=members(job,j,True)
        it=list(items(m,job));pos=job.get('solo_position',0)
        if job.get('solo_kind'):
            old=it[pos];it[pos]=Item(job['solo_kind'],job['solo_value'],old.stats,old.bp,True)
        if job.get('solo_axis'):
            old=it[pos];v=list(old.stats);v[FIELDS.index(job['solo_axis'])]+=job['solo_points'];it[pos]=Item(old.kind,old.value,tuple(v),old.bp,old.top)
        enemy_it=equipment(enemy,job.get('opponent',GENRES[j%6]),job.get('enemy_points',0.),loadout=job.get('enemy_loadout',()))
        rs=seed(job.get('stream','advanced'),job['stage'],job['genre'],job.get('opponent'),j)
        p=job['p'][:6] if job.get('p') is not None else None
        base_job={**job,'kind':None,'loadout':[],'solo_kind':None,'solo_axis':None,'foreign':None,'share_factor':1.,'owner_target_share':None,**job.get('base',{})}
        bm=redistribute(members(base_job,j),base_job.get('share_factor',1.),base_job.get('owner_target_share'));bi=items(bm,base_job)
        before,feature,rounds,_=simulate(bm,enemy,rs,bi,enemy_items=enemy_it,p=p,telemetry=bool(model));baseline.append(before)
        if model:feature=enrich(feature,rounds)
        after,_,_,_=simulate(m,enemy,rs,tuple(it),enemy_items=enemy_it,p=p);out.append(after)
        original_total=sum(sum(x.stats) for x in unmodified)
        raw_controls.append(dict(owner_share=sum(m[0].stats)/original_total,total_error=sum(sum(x.stats) for x in m)-original_total))
        if model:
            label=int(model['km'].predict(model['pca'].transform(model['scaler'].transform([[feature[c] for c in model['features']]]))[:,:model['k']])[0])
            cluster_rows.append(dict(cluster=label,base_win=before['win'],win=after['win'],base_downside=before['downside'],downside=after['downside']))
    result=summarize(out);base=summarize(baseline);change=np.array([r['win']-b['win'] for r,b in zip(out,baseline)]);se=change.std(ddof=1)/math.sqrt(len(change))
    result.update(base_wr=base['wr'],base_turns=base['turns'],base_hp=base['hp'],base_downside=base['downside'],delta=change.mean(),delta_lo=change.mean()-1.96*se,delta_hi=change.mean()+1.96*se,
                  output_ratio=result['damage_per_round']/max(1e-12,base['damage_per_round']),loss_variance=np.var([r['downside'] for r in out]),base_loss_variance=np.var([r['downside'] for r in baseline]),
                  owner_share=np.mean([x['owner_share'] for x in raw_controls]),max_stat_total_error=max(abs(x['total_error']) for x in raw_controls))
    if cluster_rows:
        table=[]
        for label,group in pd.DataFrame(cluster_rows).groupby('cluster'):
            delta=group.win-group.base_win;err=delta.std(ddof=1)/math.sqrt(len(delta)) if len(delta)>1 else float('nan')
            table.append(dict(cluster=int(label),n=len(group),base_wr=group.base_win.mean(),wr=group.win.mean(),delta=delta.mean(),delta_lo=delta.mean()-1.96*err,delta_hi=delta.mean()+1.96*err))
        result['clusters']=json.dumps(table)
    return result


class AdvancedStudy(Study):
    def __init__(self,workers):
        super().__init__(workers)
        self.signature=hashlib.sha256((CALCULATION_SIGNATURE+Path(__file__).read_text(encoding='utf-8')).encode()).hexdigest()
        self.scenes=pd.read_csv(OUT/'difficulty_candidates.csv')

    def jobs(self,jobs):
        rows=[None]*len(jobs);pending=[]
        for index,job in enumerate(jobs):
            encoded=json.dumps(job,sort_keys=True,default=float,separators=(',',':'));key=hashlib.sha256((self.signature+encoded).encode()).hexdigest()
            prior=self.cache.execute('SELECT result,executions FROM cells WHERE key=?',(key,)).fetchone()
            if prior:rows[index]=json.loads(prior[0]);self.cached_executions+=prior[1]
            else:pending.append((index,key,encoded,job))
        for count,(entry,result) in enumerate(zip(pending,self.pool.map(advanced_evaluate,[x[3] for x in pending],chunksize=2)),1):
            index,key,encoded,job=entry;rows[index]=result;n=job.get('trials',128)*2
            self.cache.execute('INSERT OR REPLACE INTO cells VALUES (?,?,?,?)',(key,encoded,json.dumps(result,default=float),n));self.cache.commit();self.total+=n
            if count%200==0:self.log(f'{count}/{len(pending)} advanced cells saved')
        return rows

    def table(self,name,meta,jobs):
        path=OUT/name
        if path.exists():return pd.read_csv(path)
        frame=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.jobs(jobs))],axis=1);csv(name,frame);return frame

    def mainc(self):
        meta=[];jobs=[]
        for s in range(6):
            for g in GENRES:
                scene=self.scene(s,g,4)
                for kind,values in ALL_VALUES.items():
                    for value in values:
                        meta.append(dict(stage=s,genre=g,kind=kind,value=value));jobs.append(dict(**scene,solo_kind=kind,solo_value=value,trials=128,stream='mainc-screen'))
        self.table('mainc_mechanism_scan.csv',meta,jobs)
        meta=[];jobs=[]
        for s in range(6):
            for g in GENRES:
                for axis in FIELDS:
                    for ratio in (0.,.25,.5,1.,2.,4.,8.):
                        value=COMMON[(s,g)]*ratio;meta.append(dict(stage=s,genre=g,axis=axis,value=value));jobs.append(dict(**self.scene(s,g,4),solo_axis=axis,solo_points=value,trials=128,stream='mainc-stat'))
        data=self.table('mainc_stat_scan.csv',meta,jobs);rows=[]
        for (s,g,a),sub in data.groupby(['stage','genre','axis']):
            sub=sub.sort_values('value')
            for row,slope in zip(sub.to_dict('records'),np.gradient(sub.wr,sub.value)):
                rows.append(dict(stage=s,genre=g,axis=a,value=row['value'],partial=slope,wr=row['wr']))
        csv('mainc_stat_derivatives.csv',pd.DataFrame(rows))

    def unique(self):
        meta=[];jobs=[]
        for s in range(6):
            for g in GENRES:
                for kind in ('skill_damage','skill_pierce','skill_chance','extra_use','skill_heal','added_dot','owner_stats'):
                    value=ALL_VALUES[kind][-2]
                    for factor in (.5,1.,2.,4.,8.):
                        meta.append(dict(stage=s,genre=g,kind=kind,value=value,share_factor=factor))
                        jobs.append(dict(**self.scene(s,g,4),solo_kind=kind,solo_value=value,share_factor=factor,trials=96,stream='unique-training'))
        data=self.table('unique_share_scan.csv',meta,jobs)
        chosen=data.sort_values(['delta_lo','owner_share'],ascending=[False,True]).groupby(['stage','genre']).head(1)
        meta=[];jobs=[]
        for r in chosen.itertuples():
            for control in ('original','redistribution_only','mechanism_only','both'):
                changed=control in ('mechanism_only','both');factor=r.share_factor if control in ('redistribution_only','both') else 1.
                meta.append(dict(stage=r.stage,genre=r.genre,control=control,kind=r.kind,value=r.value,share_factor=factor))
                jobs.append(dict(**self.scene(r.stage,r.genre,4),solo_kind=r.kind if changed else None,solo_value=r.value,share_factor=factor,validation=True,pool_offset=2048,trials=600,cluster_results=True,stream='unique-test'))
        results=self.table('unique_controls_holdout.csv',meta,jobs);clusters=[]
        for r in results.to_dict('records'):
            entries=json.loads(r['clusters']) if isinstance(r.get('clusters'),str) else r.get('clusters',[])
            for entry in entries:clusters.append({**{k:r[k] for k in ('stage','genre','control','kind','value','share_factor')},**entry})
        # CSV string representation is Python literal when serialized from a list.
        if clusters:csv('unique_cluster_holdout.csv',pd.DataFrame(clusters))

    def equipment_curves(self):
        loads=pd.read_csv(OUT/'four_top_loadouts.csv');meta=[];jobs=[]
        loadmap={(r.stage,r.genre):json.loads(r.loadout) for r in loads.itertuples()}
        for r in loads.itertuples():
            load=json.loads(r.loadout)
            for strength in (0.,.25,.5,.75,1.):
                modified=[(p,k,(round(v*strength) if k in ('extra_use','cleanse') else v*strength)) for p,k,v in load]
                meta.append(dict(stage=r.stage,genre=r.genre,strength=strength));jobs.append(dict(**self.scene(r.stage,r.genre,4),loadout=modified,validation=True,pool_offset=2816,trials=800,stream='four-strength-test'))
        self.table('four_top_strength_holdout.csv',meta,jobs)
        meta=[];jobs=[]
        # Identical foe roster and gear budget across player flows for range comparisons.
        for s in range(6):
            for h in GENRES:
                scene=self.scene(s,h,4)
                for g in GENRES:
                    for mode in ('original','pierce','dot','specialized4'):
                        load=[] if mode=='original' else [(0,'skill_pierce',.35)] if mode=='pierce' else [(0,'added_dot',.02)] if mode=='dot' else loadmap[(s,g)]
                        meta.append(dict(stage=s,genre=g,opponent=h,mode=mode));jobs.append(dict(stage=s,genre=g,opponent=h,p=scene['p'],loadout=load,validation=True,pool_offset=3328,trials=512,stream='versatility-test'))
        self.table('crossflow_versatility.csv',meta,jobs)

    def paths(self):
        meta=[];jobs=[]
        for s in range(6):
            for g in GENRES:
                for h in GENRES:
                    scene=self.scene(s,g,4)
                    for ratio in (.55,.8,1.,1.3,1.8):
                        p=list(scene['p']);p[0]*=ratio;p[1]*=ratio
                        meta.append(dict(stage=s,genre=g,opponent=h,ratio=ratio));jobs.append(dict(stage=s,genre=g,opponent=h,p=p,trials=96,stream='path-scenarios'))
        scenarios=self.table('strategic_scenario_scan.csv',meta,jobs)
        meta=[];jobs=[]
        for (s,g),sub in scenarios.groupby(['stage','genre']):
            for path,target in (('expand',.65),('counter',.25),('break',.5)):
                pool=sub
                if path=='counter' and (sub.base_wr<=.30).any():pool=sub[sub.base_wr<=.30]
                if path=='break' and (sub.base_turns>=8).any():pool=sub[sub.base_turns>=8]
                row=pool.loc[(pool.base_wr-target).abs().idxmin()];p=list(self.scene(s,g,4)['p']);p[0]*=row.ratio;p[1]*=row.ratio
                scene=dict(stage=int(s),genre=g,opponent=row.opponent,p=p)
                for kind in ('skill_damage','skill_pierce','skill_chance','opening_shield','death_lock','cast_ramp','added_dot'):
                    value=ALL_VALUES[kind][-2];load=[(i,kind,value) for i in range(4)]
                    meta.append(dict(stage=s,genre=g,path=path,opponent=row.opponent,ratio=row.ratio,kind=kind,value=value,p=json.dumps(p)))
                    jobs.append(dict(**scene,loadout=load,trials=128,stream='path-loadout-selection'))
        selected=self.table('strategic_loadout_scan.csv',meta,jobs).sort_values('delta_lo',ascending=False).groupby(['stage','genre','path']).head(1)
        meta=[];jobs=[]
        for r in selected.itertuples():
            scene=dict(stage=int(r.stage),genre=r.genre,opponent=r.opponent,p=json.loads(r.p));load=[(i,r.kind,r.value) for i in range(4)]
            for response in ('none','shield','chance','dot'):
                enemy=[] if response=='none' else [(i,{'shield':'opening_shield','chance':'skill_chance','dot':'added_dot'}[response],{'shield':.2,'chance':.2,'dot':.02}[response]) for i in range(4)]
                meta.append(dict(stage=r.stage,genre=r.genre,path=r.path,kind=r.kind,value=r.value,response=response))
                jobs.append(dict(**scene,loadout=load,enemy_loadout=enemy,validation=True,pool_offset=4096,trials=800,stream=f'path-test-{r.path}'))
        self.table('strategic_paths_holdout.csv',meta,jobs)
        meta=[];jobs=[]
        for s in range(6):
            for g in GENRES:
                for h in GENRES:
                    if h==g:continue
                    for pos in (0,STAGES[s][0]-1):
                        meta.append(dict(stage=s,genre=g,foreign=h,position=pos));jobs.append(dict(**self.scene(s,g,4),foreign=h,foreign_position=pos,validation=True,pool_offset=5120,trials=600,stream='heterogeneous-test'))
        self.table('heterogeneous_holdout.csv',meta,jobs)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=8);parser.add_argument('--phase',choices=('mainc','unique','curves','paths','all'),default='all');args=parser.parse_args();study=AdvancedStudy(args.workers)
    for name,method in (('mainc',study.mainc),('unique',study.unique),('curves',study.equipment_curves),('paths',study.paths)):
        if args.phase in (name,'all'):study.log('advanced phase '+name);method()
    study.finish('advanced_manifest_'+args.phase+'.json')


if __name__=='__main__':main()
