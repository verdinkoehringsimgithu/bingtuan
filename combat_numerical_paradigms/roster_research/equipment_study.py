"""All six stages: common-stat ranges and four-top-equipment allocation."""
from run_study import *
LEVELS=(0.,.025,.05,.10,.20,.40,.75,1.25,2.,4.)
MECHANIC_VALUES={
 'skill_damage':(0.,.15,.3,.6,1.),'skill_pierce':(0.,.1,.2,.35,.6),
 'skill_crit':(0.,.1,.2,.4,.6),'skill_heal':(0.,.25,.5,1.,2.),
 'skill_dot':(0.,.25,.5,1.,2.),'skill_chance':(0.,.05,.1,.2,.35),
 'extra_use':(0.,1.,2.,3.,5.),'cast_ramp':(0.,.1,.2,.4,.8),
 'chance_ramp':(0.,.025,.05,.1,.2),'overheal_shield':(0.,.25,.5,1.,2.),
 'opening_shield':(0.,.05,.10,.20,.40),'death_lock':(0.,.001,.005,.01,.03),
 'owner_stats':(0.,.25,.5,1.,2.),'normal_damage':(0.,.25,.5,1.,2.),
 'cleanse':(0.,1.,2.,3.,4.)}

def knee(frame):
    f=frame.groupby('value').agg(wr=('wr','mean'),delta=('delta','mean'),lo=('delta_lo','mean'),hi=('delta_hi','mean')).reset_index().sort_values('value')
    x=f.value.to_numpy();y=f.delta.to_numpy();positive=f[f.lo>0]
    lower=float(positive.value.iloc[0]) if len(positive) else None
    gain=max(0.,float(y.max()))
    if gain<=0:return lower,0.,f
    # Maximum normalized gain above the linear resource-spend reference.
    z=np.maximum.accumulate(y)/gain-(x-x[0])/max(1e-12,x[-1]-x[0])
    ix=int(np.argmax(z));upper=float(x[ix]);upper=max(upper,lower or 0.)
    return lower,upper,f

class EquipmentStudy(Study):
    def load(self):
        self.roster_choice=self.read('roster_recommendations.csv');self.scenarios=self.read('difficulty_candidates.csv')
    def common(self):
        if (self.out/'common_stat_recommendations.csv').exists():self.common_choice=self.read('common_stat_recommendations.csv');return
        meta=[];jobs=[]
        for s in range(6):
            n,bp,*_=STAGES[s]
            for g in GENRES:
                average=sum(stage_stats(s,g))/n
                for d in (3,4):
                    scene=self.scenario(s,g,d)
                    for axis in (*FIELDS,'theme','balanced','bp'):
                        for level in LEVELS:
                            value=level*(bp/n if axis=='bp' else average)
                            meta.append(dict(stage=s,genre=g,difficulty=d,axis=axis,level=level,value=value))
                            config=dict(bp_each=value) if axis=='bp' else dict(points=value,axis=axis)
                            jobs.append(dict(**scene,**self.recipe(s,g),**config,paired=True,base=dict(points=0.,bp_each=0.),trials=192,stream=f'common-response-{d}'))
        self.log('task 3, every stage: seven stat channels, independent BP, common equipment response curves')
        data=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.jobs(jobs))],axis=1);self.csv('common_stat_scan.csv',data)
        ranges=[]
        for (s,g,axis),sub in data.groupby(['stage','genre','axis']):
            lower,upper,curve=knee(sub)
            n=STAGES[s][0]
            ranges.append(dict(stage=s,genre=g,axis=axis,recommended_lower=lower,recommended_upper=upper,
                               whole_team_lower=(lower*n if lower is not None else 0.),whole_team_upper=upper*n,
                               max_measured_gain=sub.delta.max(),scanned_max=sub.value.max(),last_interval_gain=curve.delta.iloc[-1]-curve.delta.iloc[-2]))
        self.common_choice=pd.DataFrame(ranges);self.csv('common_stat_recommendations.csv',self.common_choice)
        derivatives=[]
        for (s,g,d,axis),sub in data.groupby(['stage','genre','difficulty','axis']):
            sub=sub.sort_values('value');x=sub.value.to_numpy();y=sub.wr.to_numpy();slope=np.gradient(y,x)
            for row,v in zip(sub.itertuples(),slope):derivatives.append(dict(stage=s,genre=g,difficulty=d,axis=axis,value=row.value,wr=row.wr,partial_wr_per_item_point=v,partial_wr_per_team_point=v/STAGES[s][0],delta=row.delta,delta_lo=row.delta_lo,delta_hi=row.delta_hi))
        self.csv('stat_partial_derivatives.csv',pd.DataFrame(derivatives))
        self.plot_curves(data,'common_stats')
    def common_config(self,s,g):
        sub=self.common_choice[(self.common_choice.stage==s)&(self.common_choice.genre==g)&(self.common_choice.axis!='bp')]
        r=sub.sort_values('max_measured_gain',ascending=False).iloc[0]
        return dict(points=float(r.recommended_upper),axis=r.axis)
    def mechanic(self):
        if (self.out/'mechanic_recommendations.csv').exists():self.mechanic_choice=self.read('mechanic_recommendations.csv');return
        meta=[];jobs=[]
        for s in range(6):
            for g in GENRES:
                common=self.common_config(s,g)
                for d in (3,4):
                    for kind,values in MECHANIC_VALUES.items():
                        for allocation in ('front','backup','filler'):
                            for value in values:
                                meta.append(dict(stage=s,genre=g,difficulty=d,kind=kind,allocation=allocation,value=value))
                                jobs.append(dict(**self.scenario(s,g,d),**self.recipe(s,g),**common,top_kind=kind,top_value=value,allocation=allocation,
                                                 paired=True,base=common,trials=96,stream=f'mechanic-response-{d}'))
        self.log('all six stages: holder-only skill mechanisms, all three allocation priorities, cap=4')
        data=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.jobs(jobs))],axis=1);self.csv('mechanic_response_scan.csv',data)
        recommendations=[]
        for (s,g,kind,allocation),sub in data.groupby(['stage','genre','kind','allocation']):
            lower,upper,curve=knee(sub)
            recommendations.append(dict(stage=s,genre=g,kind=kind,allocation=allocation,recommended_lower=lower,recommended_upper=upper,
                                        max_measured_gain=sub.delta.max(),normal_rate=sub.normal_rate.mean(),upper_effect=curve.loc[curve.value==upper,'delta'].iloc[0]))
        self.mechanic_choice=pd.DataFrame(recommendations);self.csv('mechanic_recommendations.csv',self.mechanic_choice)
        self.plot_curves(data,'mechanics')
    def plot_curves(self,data,prefix):
        for s in range(6):
            fig,axs=plt.subplots(2,3,figsize=(13,7),constrained_layout=True)
            for ax,g in zip(axs.flat,GENRES):
                sub=data[(data.stage==s)&(data.genre==g)&(data.difficulty==3)]
                key='axis' if prefix=='common_stats' else 'kind'
                # Plot the four largest measured response channels; full grids remain in CSV.
                chosen=sub.groupby(key).delta.max().nlargest(4).index
                for name in chosen:
                    cur=sub[sub[key]==name].groupby('value').wr.mean();ax.plot(cur.index,cur.values,marker='.',label=name)
                ax.set(title=g,xlabel='single equipment input',ylabel='WR');ax.legend(fontsize=6)
            fig.suptitle(f'S{s+1} measured {prefix} responses; explicit {STAGES[s][0]} members')
            fig.savefig(self.out/'figures'/f'{prefix}_S{s+1}.png',dpi=150);plt.close(fig)
    def allocate(self):
        if (self.out/'four_item_holdout.csv').exists():return
        selections=[];searchrows=[]
        for s in range(6):
            for g in GENRES:
                common=self.common_config(s,g);scene=self.scenario(s,g,4);recipe=self.recipe(s,g)
                pool=self.mechanic_choice[(self.mechanic_choice.stage==s)&(self.mechanic_choice.genre==g)&(self.mechanic_choice.recommended_upper>0)]
                choices=pool.sort_values('upper_effect',ascending=False).groupby('kind').head(1).head(5)
                candidates=[(r.kind,float(r.recommended_upper)) for r in choices.itertuples()]
                if not candidates:candidates=[('opening_shield',.05)]
                loadout=[];used=set();n=STAGES[s][0]
                for depth in range(4):
                    jobs=[];meta=[]
                    for pos in range(n):
                        if pos in used:continue
                        for kind,value in candidates:
                            proposed=loadout+[(pos,kind,value)]
                            meta.append(dict(stage=s,genre=g,depth=depth+1,position=pos+1,kind=kind,value=value,loadout=json.dumps(proposed)))
                            jobs.append(dict(**scene,**recipe,**common,loadout=proposed,trials=96,stream=f'allocation-training-{depth}'))
                    results=self.jobs(jobs);frame=pd.concat([pd.DataFrame(meta),pd.DataFrame(results)],axis=1);searchrows.extend(frame.to_dict('records'))
                    # Lower confidence score penalizes sampling wins in a many-candidate search.
                    selected=frame.sort_values(['wr_lo','damage_per_round'],ascending=False).iloc[0]
                    loadout=json.loads(selected.loadout);used={x[0] for x in loadout}
                selections.append(dict(stage=s,genre=g,**recipe,**common,loadout=json.dumps(loadout)))
                self.log(f'S{s+1} {g}: four-slot allocation selected')
        selection=pd.DataFrame(selections);self.csv('four_item_allocation_search.csv',pd.DataFrame(searchrows));self.csv('four_item_loadouts.csv',selection)
        jobs=[];meta=[]
        for r in selection.to_dict('records'):
            for d in (3,4):
                meta.append(dict(**r,difficulty=d))
                jobs.append(dict(**self.scenario(r['stage'],r['genre'],d),carry=r['carry'],backup=r['backup'],order=r['order'],points=r['points'],axis=r['axis'],loadout=json.loads(r['loadout']),
                                 paired=True,base=dict(points=r['points'],axis=r['axis']),trials=800,stream=f'four-item-independent-{d}'))
        hold=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.jobs(jobs))],axis=1);self.csv('four_item_holdout.csv',hold)
        # Scarcity curve uses the selected priority ordering and actual 0..4 items.
        jobs=[];meta=[]
        for r in selection.to_dict('records'):
            load=json.loads(r['loadout'])
            for k in range(5):
                meta.append(dict(stage=r['stage'],genre=r['genre'],items=k,points=r['points'],axis=r['axis']))
                jobs.append(dict(**self.scenario(r['stage'],r['genre'],3),**self.recipe(r['stage'],r['genre']),points=r['points'],axis=r['axis'],loadout=load[:k],trials=480,stream='scarcity-independent'))
        self.csv('top_item_scarcity_curve.csv',pd.concat([pd.DataFrame(meta),pd.DataFrame(self.jobs(jobs))],axis=1))
        # Full roster/one-equipment ledger is an executable design configuration.
        configs=[]
        for r in selection.to_dict('records'):
            members=roster(r['stage'],r['genre'],r['carry'],r['backup'],0,r['order']);items=member_items(members,dict(r,loadout=json.loads(r['loadout'])))
            configs.append(dict(stage=r['stage']+1,genre=r['genre'],member_count=len(members),top_count=sum(i.top for i in items),
                                members=[dict(position=j+1,role=m.role,member_id=m.uid,stats=m.stats,bp=m.bp,skill=dict(m.skill.__dict__),equipment=dict(i.__dict__)) for j,(m,i) in enumerate(zip(members,items))]))
        save_json(self.out/'stage_roster_equipment_configs.json',configs)
    def owner_summary(self):
        records=[]
        for path in self.out.glob('owners_*.jsonl.gz'):
            parts=path.name.split('_');stage=int(parts[1][1:])-1;g=parts[2]+'_'+parts[3];d=int(parts[4].split('.')[0][1:])
            with gzip.open(path,'rt',encoding='utf-8') as f:
                for line in f:
                    b=json.loads(line)
                    for m in b['members']:
                        records.append(dict(stage=stage,genre=g,difficulty=d,position=m['position'],role=m['role'],raw_chance=m['raw_chance'],casts=m.get('casts',0),reached=m.get('reached',0),expected_cast=m.get('expected_cast',0),
                                            exhausted=m.get('exhausted',0),self_gate=m.get('self_gate',0),expected_reached=m.get('expected_reached',0),stat_budget=sum(m['stats'])))
        df=pd.DataFrame(records);summary=df.groupby(['stage','genre','difficulty','position','role']).mean(numeric_only=True).reset_index();self.csv('owner_probability_decay.csv',summary)
    def finalize(self):
        save_json(self.out/'equipment_manifest.json',dict(simulations=self.total,elapsed_seconds=time.time()-self.started,stages=6,flows=6,top_cap=4))
        self.pool.shutdown()

def main():
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=8);p.add_argument('--output',default=str(Path(__file__).parent/'results'));p.add_argument('--phase',choices=('common','all'),default='all');args=p.parse_args()
    study=EquipmentStudy(args);study.load();study.common()
    if args.phase=='all':study.mechanic();study.allocate();study.owner_summary()
    study.finalize()

if __name__=='__main__':main()
