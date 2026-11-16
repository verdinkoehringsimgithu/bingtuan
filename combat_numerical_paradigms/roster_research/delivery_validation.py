"""Operating equipment budgets, difficulty with standard gear, and strategic paths."""
from run_study import *
from equipment_study import MECHANIC_VALUES

def operating_configs(q):
    ranges=pd.read_csv(q/'common_stat_recommendations.csv');roles=pd.read_csv(q/'roster_recommendations.csv');out=[]
    for (s,g),sub in ranges.groupby(['stage','genre']):
        stats=sub[sub.axis!='bp'];best=stats.sort_values('max_measured_gain',ascending=False).iloc[0]
        low=float(best.recommended_lower) if pd.notna(best.recommended_lower) else 0.;upper=float(best.recommended_upper)
        value=math.sqrt(low*upper) if low>0 else upper/4
        role=roles[(roles.stage==s)&(roles.genre==g)].iloc[0]
        out.append(dict(stage=int(s),genre=g,points=value,axis=best.axis,carry=int(role.carry),backup=int(role.backup),order=role.order,lower=low,upper=upper))
    return out

def calibrate(job):
    p=list(job['p']);lo=.05;hi=4.;records=[];target=job['target'];base=dict(job);base.pop('target');base.pop('difficulty',None)
    for step in range(10):
        p[1]=(lo+hi)/2;r=evaluate(dict(base,p=p,trials=256,stream='operating-calibration'))
        records.append(dict(stage=job['stage'],genre=job['genre'],difficulty=job['difficulty'],beta=p[1],**r))
        if r['wr']>target:lo=p[1]
        else:hi=p[1]
    best=min(records,key=lambda r:abs(r['wr']-target));p[1]=best['beta'];return p,records

class Delivery(Study):
    def load(self):
        self.roster_choice=self.read('roster_recommendations.csv');self.scenarios=self.read('difficulty_candidates.csv');self.operating=operating_configs(self.out)
        self.csv('common_operating_points.csv',pd.DataFrame(self.operating))
    def calibrated(self):
        if (self.out/'equipped_difficulty_holdout.csv').exists():self.calibrated_scenes=self.read('equipped_difficulty_candidates.csv');return
        jobs=[];meta=[]
        for config in self.operating:
            for d,target in ((3,.7),(4,.5),(1,.99),(2,.93)):
                scene=self.scenario(config['stage'],config['genre'],d);meta.append(dict(**config,difficulty=d,opponent=scene['opponent']))
                jobs.append(dict(**scene,points=config['points'],axis=config['axis'],carry=config['carry'],backup=config['backup'],order=config['order'],difficulty=d,target=target))
        results=list(self.pool.map(calibrate,jobs,chunksize=1));self.total+=len(jobs)*2560
        records=[];trace=[]
        for m,(p,hist) in zip(meta,results):records.append(dict(**m,**dict(zip(MACRO_NAMES,p))));trace.extend(hist)
        self.calibrated_scenes=pd.DataFrame(records);self.csv('equipped_difficulty_candidates.csv',self.calibrated_scenes);self.csv('equipped_difficulty_calibration.csv',pd.DataFrame(trace))
        jobs=[self.job(row,stream=f"equipped-difficulty-holdout-{row['difficulty']}",trials=800) for row in records]
        self.csv('equipped_difficulty_holdout.csv',pd.concat([self.calibrated_scenes,pd.DataFrame(self.jobs(jobs))],axis=1))
    def job(self,row,**extra):
        return dict(stage=int(row['stage']),genre=row['genre'],opponent=row['opponent'],p=[float(row[k]) for k in MACRO_NAMES],
                    carry=int(row['carry']),backup=int(row['backup']),order=row['order'],points=float(row['points']),axis=row['axis'],**extra)
    def select_four(self):
        if (self.out/'operating_four_item_holdout.csv').exists():self.loadouts=self.read('operating_four_item_loadouts.csv');return
        recommendations=self.read('mechanic_recommendations.csv');meta=[];jobs=[]
        # Re-measure all mechanism families at the non-saturated operating point.
        for scene in self.calibrated_scenes[self.calibrated_scenes.difficulty==4].to_dict('records'):
            for kind,values in MECHANIC_VALUES.items():
                sub=recommendations[(recommendations.stage==scene['stage'])&(recommendations.genre==scene['genre'])&(recommendations.kind==kind)]
                positive=sub[sub.recommended_upper>0]
                value=float(positive.recommended_upper.median()) if len(positive) else values[2]
                for alloc in ('front','backup','filler'):
                    meta.append(dict(stage=scene['stage'],genre=scene['genre'],kind=kind,value=value,allocation=alloc))
                    jobs.append(self.job(scene,top_kind=kind,top_value=value,allocation=alloc,paired=True,base=dict(points=scene['points'],axis=scene['axis']),trials=256,stream='operating-mechanisms'))
        scan=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.jobs(jobs))],axis=1);self.csv('operating_mechanic_responses.csv',scan)
        selected=[];search=[]
        for scene in self.calibrated_scenes[self.calibrated_scenes.difficulty==4].to_dict('records'):
            s,g=int(scene['stage']),scene['genre'];sub=scan[(scan.stage==s)&(scan.genre==g)]
            best=sub.sort_values('delta_lo',ascending=False).groupby('kind').head(1).head(5);candidates=[(r.kind,float(r.value)) for r in best.itertuples()]
            loadout=[];used=set()
            for depth in range(4):
                meta=[];jobs=[]
                for pos in range(STAGES[s][0]):
                    if pos in used:continue
                    for kind,value in candidates:
                        proposed=loadout+[(pos,kind,value)];meta.append(dict(stage=s,genre=g,depth=depth+1,loadout=json.dumps(proposed),kind=kind,position=pos+1))
                        jobs.append(self.job(scene,loadout=proposed,trials=128,stream=f'operating-allocation-{depth}'))
                data=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.jobs(jobs))],axis=1);search.extend(data.to_dict('records'))
                row=data.sort_values(['wr_lo','damage_per_round'],ascending=False).iloc[0];loadout=json.loads(row.loadout);used={x[0] for x in loadout}
            selected.append(dict(stage=s,genre=g,points=scene['points'],axis=scene['axis'],carry=scene['carry'],backup=scene['backup'],order=scene['order'],loadout=json.dumps(loadout)))
            self.log(f'operating S{s+1} {g}: four owner-specific top items verified for holdout')
        self.loadouts=pd.DataFrame(selected);self.csv('operating_four_item_loadouts.csv',self.loadouts);self.csv('operating_allocation_training.csv',pd.DataFrame(search))
        meta=[];jobs=[]
        for load in selected:
            for d in (3,4):
                scene=self.calibrated_scenes[(self.calibrated_scenes.stage==load['stage'])&(self.calibrated_scenes.genre==load['genre'])&(self.calibrated_scenes.difficulty==d)].iloc[0].to_dict()
                meta.append(dict(**load,difficulty=d));jobs.append(self.job(scene,loadout=json.loads(load['loadout']),paired=True,base=dict(points=load['points'],axis=load['axis']),trials=1200,stream=f'operating-four-holdout-{d}'))
        self.csv('operating_four_item_holdout.csv',pd.concat([pd.DataFrame(meta),pd.DataFrame(self.jobs(jobs))],axis=1))
    def paths(self):
        if (self.out/'strategic_paths_by_stage.csv').exists():return
        calibration=[];meta=[]
        for scene in self.calibrated_scenes[self.calibrated_scenes.difficulty==3].to_dict('records'):
            for path,target in (('advantage',.65),('counter',.28),('stalemate',.5)):
                job=self.job(scene);job.update(target=target,difficulty=3)
                if path=='stalemate':job['p'][0]=max(1.5,job['p'][0])
                calibration.append(job);meta.append(dict(stage=scene['stage'],genre=scene['genre'],path=path,**{k:scene[k] for k in ('points','axis','carry','backup','order','opponent')}))
        results=list(self.pool.map(calibrate,calibration,chunksize=1));self.total+=len(calibration)*2560
        metadata=[];jobs=[]
        for m,(p,_) in zip(meta,results):
            load=self.loadouts[(self.loadouts.stage==m['stage'])&(self.loadouts.genre==m['genre'])].iloc[0]
            metadata.append(dict(**m,**dict(zip(MACRO_NAMES,p)),loadout=load.loadout))
            jobs.append(dict(stage=int(m['stage']),genre=m['genre'],opponent=m['opponent'],p=p,carry=int(m['carry']),backup=int(m['backup']),order=m['order'],points=m['points'],axis=m['axis'],
                             loadout=json.loads(load.loadout),paired=True,base=dict(points=m['points'],axis=m['axis']),trials=800,stream='strategic-path-independent'))
        self.csv('strategic_paths_by_stage.csv',pd.concat([pd.DataFrame(metadata),pd.DataFrame(self.jobs(jobs))],axis=1))
        # Counter-equipment respects the same four-item cap on the enemy side.
        meta=[];jobs=[]
        for record in metadata:
            if record['path']!='advantage':continue
            for kind,value in (('skill_damage',.3),('skill_chance',.1),('opening_shield',.1),('extra_use',1.)):
                enemy_load=[(j,kind,value) for j in range(min(4,STAGES[int(record['stage'])][0]))]
                meta.append(dict(stage=record['stage'],genre=record['genre'],enemy_kind=kind))
                jobs.append(self.job(record,loadout=json.loads(record['loadout']),enemy_loadout=enemy_load,trials=600,stream='enemy-four-equipment-response'))
        self.csv('enemy_counter_equipment_by_stage.csv',pd.concat([pd.DataFrame(meta),pd.DataFrame(self.jobs(jobs))],axis=1))
        meta=[];jobs=[]
        for scene in self.calibrated_scenes[self.calibrated_scenes.difficulty==3].to_dict('records'):
            n=STAGES[int(scene['stage'])][0]
            for foreign in GENRES:
                if foreign==scene['genre']:continue
                for pos in (0,n-1):
                    meta.append(dict(stage=scene['stage'],genre=scene['genre'],foreign=foreign,position=pos+1))
                    jobs.append(self.job(scene,foreign=foreign,foreign_position=pos,paired=True,base=dict(points=scene['points'],axis=scene['axis']),trials=480,stream='heterogeneous-owner-independent'))
        self.csv('heterogeneous_embedding_by_stage.csv',pd.concat([pd.DataFrame(meta),pd.DataFrame(self.jobs(jobs))],axis=1))
    def ledger(self):
        data=[]
        for config in self.loadouts.to_dict('records'):
            s=int(config['stage']);g=config['genre'];members=roster(s,g,int(config['carry']),int(config['backup']),0,config['order']);items=member_items(members,dict(config,loadout=json.loads(config['loadout'])))
            data.append(dict(stage=s+1,genre=g,member_count=len(members),top_count=sum(x.top for x in items),members=[dict(position=j+1,role=m.role,stats=m.stats,bp=m.bp,skill=dict(m.skill.__dict__),equipment=dict(item.__dict__)) for j,(m,item) in enumerate(zip(members,items))]))
        save_json(self.out/'operating_roster_equipment_configs.json',data)
    def finalize(self):
        save_json(self.out/'delivery_validation_manifest.json',dict(simulations=self.total,elapsed_seconds=time.time()-self.started));self.pool.shutdown()

def main():
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=8);p.add_argument('--output',default=str(Path(__file__).parent/'results'));args=p.parse_args()
    study=Delivery(args);study.load();study.log('calibrating six-stage difficulty against measured common operating budgets');study.calibrated();study.select_four();study.paths();study.ledger();study.finalize()

if __name__=='__main__':main()
