"""Level growth and reusable stage / NPC type / difficulty operating bands."""
import os,sys
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'natural_research'))
from run_natural import *
import natural_core as natural

OUT=HERE/'results';OUT.mkdir(exist_ok=True)
SOURCE_OUT=HERE.parent/'natural_research/results'
LEVEL_BANDS=((1,7),(5,12),(10,17),(15,22),(20,27),(25,30))
PREPARATIONS=('underdeveloped','standard','different_order','strong_collection','four_top')
TARGETS={'hard':(.70,.80),'very_hard':(.55,.70),'extremely_hard':(.45,.55)}
OLD={};NEW={};PATHS={};ACTIVE_BANK=None
LOADS={(int(r.stage),r.genre):json.loads(r.loadout) for r in pd.read_csv(SOURCE_OUT/'equipment_operating_candidates.csv').itertuples()}


def write(name,frame):
    target=OUT/name;temporary=target.with_name(target.name+'.tmp');frame.to_csv(temporary,index=False,encoding='utf-8-sig');temporary.replace(target)


def grow_path(start,end,power=1.):
    start=np.array(start,dtype=int);end=np.array(end,dtype=int);assert np.all(end>=start)
    current=start.copy();rows=[tuple(current)]
    for level in range(2,31):
        fraction=((level-1)/29)**power;desired=start+(end-start)*fraction;total=round(sum(start)+(sum(end)-sum(start))*fraction)
        for _ in range(total-int(current.sum())):current[int(np.argmax(desired-current))]+=1
        rows.append(tuple(current))
    assert rows[-1]==tuple(end) and all(all(b>=a for a,b in zip(x,y)) for x,y in zip(rows,rows[1:]))
    return tuple(rows)


def set_bank(bank):
    global ACTIVE_BANK,OLD,NEW
    if ACTIVE_BANK==bank:return
    suffix={'training':'catalog_current.json','validation':'catalog_holdout.json','final':'catalog_final_test.json'}[bank]
    old_suffix={'training':'catalog_before.json','validation':'catalog_old_validation_growth.json','final':'catalog_old_final_growth.json'}[bank]
    records=json.loads((SOURCE_OUT/suffix).read_text(encoding='utf-8'));old_records=json.loads((SOURCE_OUT/old_suffix).read_text(encoding='utf-8'))
    OLD={(int(r['tier']),NAME_TO_LETTER[r['genre']],int(r['sample'])):tuple(int(r['csv'][k]) for k in ('dodge','defense','speed','authority')) for r in old_records}
    NEW={};natural.SKILLS.clear();natural.HOLDOUT_SKILLS.clear()
    for record in records:
        skill,stats=convert(record);letter=NAME_TO_LETTER[skill.genre];NEW[(skill.tier,letter,record['sample'])]=stats
        natural.SKILLS.setdefault((skill.tier,letter),[]).append((skill,stats,record['sample']))
    natural.HOLDOUT_SKILLS.update(natural.SKILLS);natural.roster.cache_clear();PATHS.clear();ACTIVE_BANK=bank


def player(s,g,pool,preparation='standard',power=1.,level_shift=0):
    n=STAGES[s][0];lower,upper=LEVEL_BANDS[s];base_prep='standard' if preparation in ('different_order','four_top') else preparation
    carry=1 if base_prep=='underdeveloped' else min(n,max(2,n//2)) if base_prep=='strong_collection' else 2
    backup=min(4,n-carry)
    source=natural.roster(s,g,pool,carry=carry,backup=backup,profile='upper' if base_prep=='strong_collection' else 'mixed')
    grown=[];levels=[];rng=random.Random(seed('growth-levels',s,g,pool,base_prep))
    for pos,m in enumerate(source):
        skill=m.skill;letter=NAME_TO_LETTER[skill.genre];sample=m.uid
        if base_prep=='underdeveloped' and skill.tier>1:
            role=m.role;skill,_,sample=natural.choice(rng,skill.tier-1,letter,role);skill=copy.copy(skill);skill.id=pos+1
        key=(skill.tier,letter,sample);path_key=(*key,power)
        if path_key not in PATHS:PATHS[path_key]=grow_path(OLD[key],NEW[key],power)
        if base_prep=='underdeveloped':lo,hi=lower,(lower+upper)//2
        elif base_prep=='strong_collection':lo,hi=(lower+upper+1)//2,upper
        else:lo,hi=lower,upper
        level=int(np.clip(rng.randint(lo,hi)+level_shift,1,30));levels.append(level)
        grown.append(Member(m.uid,m.role,PATHS[path_key][level-1],m.bp,skill))
    if preparation=='different_order':random.Random(seed('alternative-order',s,g,pool)).shuffle(grown)
    points=COMMON[(s,g)]*(.75 if base_prep=='underdeveloped' else 1.25 if base_prep=='strong_collection' else 1.)
    load=LOADS[(s,g)] if preparation=='four_top' else []
    return tuple(grown),equipment(tuple(grown),g,points,loadout=load),levels


def evaluate_growth(job):
    set_bank(job.get('bank','training'));s=job['stage'];g=job['genre'];h=job['enemy_genre'];results=[];stats=[];levels=[]
    for j in range(job.get('trials',32)):
        pool=j+job.get('pool_offset',0);m,it,lv=player(s,g,pool,job.get('preparation','standard'),job.get('power',1.),job.get('level_shift',0));e,_,_=player(s,h,pool+100003,'standard',job.get('power',1.))
        balance=job.get('npc_balance',0.)
        if balance:
            e=tuple(Member(x.uid,x.role,tuple(v*(1-balance)+sum(x.stats)/4*balance for v in x.stats),x.bp,x.skill) for x in e)
        rho=job.get('rho',1.);p=[job['alpha']*rho,job['beta']*rho,0.,0.,0.,1.]
        result,_,_,_=simulate(m,e,seed(job.get('stream','growth-grid'),s,g,h,j),it,p=p);results.append(result)
        team=Team(m,it);stats.append([getattr(team,'base_'+f) for f in FIELDS]);levels.extend(lv)
    answer=summarize(results);answer.update(level_mean=np.mean(levels),**dict(zip(FIELDS,np.mean(stats,axis=0))));return answer


class GrowthStudy:
    def __init__(self,workers):
        self.pool=cf.ProcessPoolExecutor(workers);self.db=sqlite3.connect(OUT/'checkpoints.sqlite');self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('CREATE TABLE IF NOT EXISTS cells (key TEXT PRIMARY KEY, job TEXT, result TEXT)');self.db.commit()
        self.signature=hashlib.sha256(Path(__file__).read_bytes()+core.SOURCE.read_bytes()).hexdigest()
    def jobs(self,jobs):
        answers=[None]*len(jobs);missing=[]
        for i,job in enumerate(jobs):
            encoded=json.dumps(job,sort_keys=True,default=float);key=hashlib.sha256((self.signature+encoded).encode()).hexdigest();prior=self.db.execute('SELECT result FROM cells WHERE key=?',(key,)).fetchone()
            if prior:answers[i]=json.loads(prior[0])
            else:missing.append((i,key,encoded,job))
        for count,(entry,result) in enumerate(zip(missing,self.pool.map(evaluate_growth,[x[3] for x in missing],chunksize=2)),1):
            i,key,encoded,job=entry;answers[i]=result;self.db.execute('INSERT OR REPLACE INTO cells VALUES (?,?,?)',(key,encoded,json.dumps(result,default=float)));self.db.commit()
            if count%300==0:print(time.strftime('%H:%M:%S'),f'{count}/{len(missing)} cells saved',flush=True)
        return answers
    def table(self,name,meta,jobs):
        path=OUT/name
        if path.exists():return pd.read_csv(path)
        frame=pd.concat([pd.DataFrame(meta),pd.DataFrame(self.jobs(jobs))],axis=1);write(name,frame);return frame
    def screen(self):
        meta=[];jobs=[]
        for s in range(6):
            for h in GENRES:
                for alpha in (.25,.4,.6,.85,1.1,1.5,2.1):
                    for beta in (.12,.22,.35,.5,.7,1.,1.4):
                        for g in GENRES:
                            meta.append(dict(stage=s,enemy_genre=h,genre=g,alpha=alpha,beta=beta));jobs.append(dict(stage=s,enemy_genre=h,genre=g,alpha=alpha,beta=beta,trials=16))
        data=self.table('enemy_screen.csv',meta,jobs);aggregate=data.groupby(['stage','enemy_genre','alpha','beta']).agg(wr=('wr','mean'),flow_spread=('wr',lambda x:x.max()-x.min())).reset_index();selected=[]
        for (s,h),sub in aggregate.groupby(['stage','enemy_genre']):
            for difficulty,(lo,hi) in TARGETS.items():
                scores=abs(sub.wr-(lo+hi)/2)+.1*sub.flow_spread;row=sub.loc[scores.idxmin()].to_dict();selected.append(dict(**row,difficulty=difficulty))
        write('screen_anchors.csv',pd.DataFrame(selected));return selected
    def refine(self,anchors):
        meta=[];jobs=[]
        for row in anchors:
            for a in (.85,1.,1.15):
                for b in (.85,1.,1.15):
                    for g in GENRES:
                        alpha=row['alpha']*a;beta=row['beta']*b;meta.append(dict(stage=row['stage'],enemy_genre=row['enemy_genre'],difficulty=row['difficulty'],genre=g,alpha=alpha,beta=beta));jobs.append(dict(stage=int(row['stage']),enemy_genre=row['enemy_genre'],genre=g,alpha=alpha,beta=beta,bank='validation',pool_offset=512,trials=32,stream='growth-refine'))
        data=self.table('enemy_validation_refine.csv',meta,jobs);aggregate=data.groupby(['stage','enemy_genre','difficulty','alpha','beta']).agg(wr=('wr','mean'),flow_spread=('wr',lambda x:x.max()-x.min())).reset_index();selected=[]
        for (s,h,d),sub in aggregate.groupby(['stage','enemy_genre','difficulty']):
            lo,hi=TARGETS[d];scores=abs(sub.wr-(lo+hi)/2)+.1*sub.flow_spread;selected.append(sub.loc[scores.idxmin()].to_dict())
        write('refined_anchors.csv',pd.DataFrame(selected));return selected
    def bands(self,anchors):
        meta=[];jobs=[]
        for row in anchors:
            for rho in (.75,.85,.925,1.,1.075,1.15,1.25):
                for g in GENRES:
                    meta.append(dict(stage=row['stage'],enemy_genre=row['enemy_genre'],difficulty=row['difficulty'],genre=g,rho=rho,alpha=row['alpha'],beta=row['beta']));jobs.append(dict(stage=int(row['stage']),enemy_genre=row['enemy_genre'],genre=g,alpha=row['alpha'],beta=row['beta'],rho=rho,bank='validation',pool_offset=1024,trials=64,stream='growth-band'))
        data=self.table('difficulty_band_validation.csv',meta,jobs);aggregate=data.groupby(['stage','enemy_genre','difficulty','alpha','beta','rho']).agg(wr=('wr','mean'),flow_min=('wr','min'),flow_max=('wr','max')).reset_index();selected=[]
        for (s,h,d),sub in aggregate.groupby(['stage','enemy_genre','difficulty']):
            lo,hi=TARGETS[d];accepted=sub[sub.wr.between(lo,hi)];accepted=accepted if len(accepted) else sub.iloc[[int(np.argmin(abs(sub.wr-(lo+hi)/2)))]]
            anchor=accepted.iloc[int(np.argmin(abs(accepted.wr-(lo+hi)/2)))];selected.append(dict(stage=s,enemy_genre=h,difficulty=d,alpha=anchor.alpha,beta=anchor.beta,rho_lower=accepted.rho.min(),rho_center=anchor.rho,rho_upper=accepted.rho.max(),validation_in_band=bool(sub.wr.between(lo,hi).any())))
        write('difficulty_intervals.csv',pd.DataFrame(selected));return selected
    def final(self,intervals):
        meta=[];jobs=[]
        for row in intervals:
            for point in ('lower','center','upper'):
                for preparation in PREPARATIONS:
                    for g in GENRES:
                        rho=row['rho_'+point];meta.append(dict(stage=row['stage'],enemy_genre=row['enemy_genre'],difficulty=row['difficulty'],point=point,preparation=preparation,genre=g,rho=rho,alpha=row['alpha'],beta=row['beta']));jobs.append(dict(stage=int(row['stage']),enemy_genre=row['enemy_genre'],genre=g,alpha=row['alpha'],beta=row['beta'],rho=rho,preparation=preparation,bank='final',pool_offset=4096,trials=128,stream='growth-final'))
        self.table('difficulty_final_holdout.csv',meta,jobs)
        meta=[];jobs=[]
        for row in intervals:
            for power in (.8,1.,1.25):
                for shift in (-3,0,3):
                    for g in GENRES:
                        meta.append(dict(stage=row['stage'],enemy_genre=row['enemy_genre'],difficulty=row['difficulty'],genre=g,power=power,level_shift=shift));jobs.append(dict(stage=int(row['stage']),enemy_genre=row['enemy_genre'],genre=g,alpha=row['alpha'],beta=row['beta'],rho=row['rho_center'],power=power,level_shift=shift,bank='final',pool_offset=8192,trials=32,stream='growth-robustness'))
        self.table('growth_curve_sensitivity.csv',meta,jobs)
    def close(self):self.pool.shutdown();self.db.close()


def growth_export():
    set_bank('training');rows=[];checks=0
    for key,old in OLD.items():
        for power in (.8,1.,1.25):
            path=grow_path(old,NEW[key],power);checks+=1
            for level,stats in enumerate(path,1):rows.append(dict(tier=key[0],genre=key[1],sample=key[2],power=power,level=level,budget=sum(stats),**dict(zip(FIELDS,stats))))
    frame=pd.DataFrame(rows);target=OUT/'individual_growth_samples.csv.gz';frame.to_csv(target,index=False,compression='gzip')
    summary=frame.groupby(['tier','power','level']).budget.agg(['min','mean','max']).reset_index();write('growth_budget_table.csv',summary)
    save_json(OUT/'growth_validation.json',dict(paths_checked=checks,old_level1_and_new_level30_exact=True,all_four_stats_monotonic=True,budget_preserved_after_integer_allocation=True,level_range=[1,30],default_power=1.,stage_level_bands=LEVEL_BANDS))


def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=8);parser.add_argument('--output',type=Path,default=OUT);args=parser.parse_args();OUT=args.output.resolve();OUT.mkdir(parents=True,exist_ok=True);growth_export();study=GrowthStudy(args.workers)
    anchors=study.screen();anchors=study.refine(anchors);intervals=study.bands(anchors);study.final(intervals);study.close()
    save_json(OUT/'settings.json',dict(stage_level_bands=LEVEL_BANDS,preparations=PREPARATIONS,difficulty_targets=TARGETS,npc_has_no_equipment=True,canonical_stage_bp_unchanged=True,level_only_changes_four_stats=True,skills_not_scaled_with_level=True,stage_count=6,source='frozen real skill generator exports',status='all_experiments_complete'))


if __name__=='__main__':main()
