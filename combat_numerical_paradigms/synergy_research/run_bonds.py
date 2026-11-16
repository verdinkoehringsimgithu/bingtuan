"""Resumable, parallel six-stage identity study. All source inputs are hashed."""
import argparse
import concurrent.futures as cf
import csv
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import time

for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
from settings import HERE,ROOT,IDENTITIES,CN,DEFAULTS,SOURCES
from rosters import build,encounter,availability,GENRES,STAGES,seed,bank,natural
from bond_core import simulate


def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)


def signature():
    paths=SOURCES+[HERE/name for name in ('settings.py','rosters.py','bond_core.py','run_bonds.py')]
    paths += [ROOT/'combat_numerical_paradigms/natural_research/results'/name for name in (
        'catalog_current.json','catalog_before.json','catalog_holdout.json','catalog_old_validation_growth.json',
        'catalog_final_test.json','catalog_old_final_growth.json','selected_stat_profile.json')]
    paths += [ROOT/'combat_numerical_paradigms/progression_difficulty/character_statistics/distribution_2026-10-15.json']
    manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    return hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest(),manifest


def average(values):return sum(values)/len(values) if values else 0.


def fit_skills(members,stage,bank_name):
    """Selection bias within existing tier/axis pool; no invented skill numbers.

    Keep members' four-stat budgets fixed to isolate skill supply from stat gain.
    """
    import copy
    skills,_,_=bank(bank_name);out=[]
    for pos,m in enumerate(members):
        x=copy.copy(m);s=m.skill;letter=natural.NAME_TO_LETTER[s.genre]
        candidates=skills[(s.tier,letter)]
        name=m.identity
        def score(row):
            z=row[0];repeat=z.times_limit>=999
            gates=int(z.turn_cond1>0)+int(z.turn_cond2>0)+int(z.self_bp_cond2>0)+int(z.enemy_bp_cond2>0)
            p=z.trigger_chance/100.
            if name in ('工程师','忍者','农民','盗贼','富翁','学者'):
                return 2*repeat+p-gates
            if name=='侠女':return p-gates+.25*(0<z.times_limit<999)
            if name=='剑士':return repeat+p-gates
            if name=='贤者':return 2*(z.sub_effect_name in ('虚弱压制','四维削弱','最大流失','已损流失'))+p-.5*gates
            if name=='杀手':return repeat+p-gates+.25*z.base_crit_rate
            if name=='猎手':return z.main_param/300+p-gates
            if name=='老师':return z.main_param/300+p-gates
            return -abs(z.main_param-s.main_param)-abs(z.trigger_chance-s.trigger_chance)
        ranked=sorted(candidates,key=score,reverse=True)
        # Best quartile instead of repeating the single best generated skill.
        ranked=ranked[:max(1,len(ranked)//4)]
        r=ranked[seed('fit',m.person_id,pos)%len(ranked)][0]
        x.skill=copy.copy(r);x.skill.id=s.id
        out.append(x)
    return tuple(out)


def flatten(result,prefix):
    out={prefix+k:result[k] for k in ('win','censored','draw','turns','hp','enemy_hp','margin','normal_rate','damage','coins','teacher_xp_multiplier','heroine_layers','adventure_goals')}
    for k in ('skill_casts','attacks','normal_casts','sword_extras','max_chain','scholar_restored','engineer_casts','ninja_casts','absolute_dodges','force_hit',
              'fruit_planted','fruit_accelerated','fruit_harvest','fruit_wait','worker_procs','hunter_scheduled','hunter_true','killer_marks','killer_healing_prevented','thief_stolen','rich_saved','mage_same','mage_switch','heroine_first','maid_casts'):
        out[prefix+'m_'+k]=result['metrics'].get(k,0.)
    return out


def evaluate(job):
    stage=job['stage'];genre=job['genre'];phase=job['phase'];trials=job['trials']
    composition=tuple(tuple(x) for x in job.get('composition',()))
    enabled=tuple(job.get('enabled',()))
    bank_name=job.get('bank','training');placement=job.get('placement','front')
    config=job.get('config',{});enemy_enabled=tuple(job.get('enemy_enabled',()))
    records=[];traces=[]
    difficulty=job.get('difficulty','extremely_hard')
    h,p=encounter(stage,difficulty)
    if job.get('symmetric'):h=job.get('enemy_genre',genre);p=None
    for j in range(trials):
        pool=j+job.get('pool_offset',0)
        m,it=build(stage,genre,pool,composition,placement,bank_name,job.get('preparation','standard'))
        ec=tuple(tuple(x) for x in job.get('enemy_composition',()))
        e,ei=build(stage,h,pool+100003,ec,'front',bank_name)
        bs=seed('bond-addressed',stage,genre,h,phase,pool)
        candidate=m
        if job.get('skill_fit'):candidate=fit_skills(m,stage,bank_name)
        wants_trace=job.get('trace',False) and j<4
        base,*_=simulate(m,e,bs,it,ei,p=p)
        new,trace,a,b=simulate(candidate,e,bs,it,ei,p=p,enabled=enabled,config=config,
                              enemy_enabled=enemy_enabled,enemy_config=job.get('enemy_config'),telemetry=wants_trace)
        row=dict(trial=j,**flatten(base,'base_'),**flatten(new,'new_'))
        if job.get('reference'):
            ref,ri=build(stage,genre,pool,(),placement,bank_name,job.get('preparation','standard'))
            r,*_=simulate(ref,e,bs,ri,ei,p=p)
            row.update(flatten(r,'ref_'))
        if job.get('interaction'):
            left,*_=simulate(m,e,bs,it,ei,p=p,enabled=(enabled[0],),config=config)
            right,*_=simulate(m,e,bs,it,ei,p=p,enabled=(enabled[1],),config=config)
            row.update(flatten(left,'left_'));row.update(flatten(right,'right_'))
        if job.get('skill_fit'):
            unfit,*_=simulate(m,e,bs,it,ei,p=p,enabled=enabled,config=config)
            fit_no_bond,*_=simulate(candidate,e,bs,it,ei,p=p)
            row.update(flatten(unfit,'unfit_'));row.update(flatten(fit_no_bond,'fit_off_'))
        records.append(row)
        if wants_trace:
            traces.append(dict(trial=j,battle_seed=bs,stage=stage+1,genre=genre,enabled=enabled,config=config,
                               result=new,rounds=trace,
                               members=[dict(person_id=x.person_id,identity=x.identity,tier=x.skill.tier,
                                             level=x.level,stats=x.stats,skill=dict(vars(x.skill)),item=dict(vars(y))) for x,y in zip(candidate,it)]))
    directory=Path(job['output']);key=job['key']
    target=directory/'replicates'/f'{key}.json.gz';target.parent.mkdir(exist_ok=True,parents=True)
    tmp=target.with_suffix('.tmp')
    with gzip.open(tmp,'wt',encoding='utf-8') as f:json.dump(records,f,ensure_ascii=False)
    tmp.replace(target)
    if traces:
        target=directory/'telemetry'/f'{key}.json.gz';target.parent.mkdir(exist_ok=True,parents=True)
        tmp=target.with_suffix('.tmp')
        with gzip.open(tmp,'wt',encoding='utf-8') as f:json.dump(traces,f,ensure_ascii=False)
        tmp.replace(target)
    summary={k:average([r[k] for r in records]) for k in records[0] if k!='trial'}
    deltas=[r['new_win']-r['base_win'] for r in records]
    summary['delta_wr']=average(deltas)
    summary['delta_se']=math.sqrt(sum((v-summary['delta_wr'])**2 for v in deltas)/(trials-1)/trials) if trials>1 else 0.
    summary['reversals']=sum(r['new_win']>r['base_win'] for r in records)
    summary['regressions']=sum(r['new_win']<r['base_win'] for r in records)
    if job.get('reference'):
        summary['composition_delta']=summary['base_win']-summary['ref_win']
        summary['total_delta']=summary['new_win']-summary['ref_win']
    if job.get('interaction'):
        summary['interaction_delta']=summary['new_win']-summary['left_win']-summary['right_win']+summary['base_win']
    if job.get('skill_fit'):
        summary['fit_with_bond_delta']=summary['new_win']-summary['unfit_win']
        summary['fit_without_bond_delta']=summary['fit_off_win']-summary['base_win']
        summary['fit_interaction']=summary['fit_with_bond_delta']-summary['fit_without_bond_delta']
    summary['trace_battles']=len(traces)
    summary['executed_battles']=trials*(2+int(bool(job.get('reference')))+2*int(bool(job.get('interaction')))+2*int(bool(job.get('skill_fit'))))
    return summary


class Runner:
    def __init__(self,output,workers):
        self.output=Path(output);self.output.mkdir(parents=True,exist_ok=True)
        self.sig,self.inputs=signature()
        self.db=sqlite3.connect(self.output/'checkpoints.sqlite')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('CREATE TABLE IF NOT EXISTS cells (key TEXT PRIMARY KEY, phase TEXT, job TEXT, result TEXT, signature TEXT)');self.db.commit()
        atomic_json(self.output/'input_manifest.json',dict(signature=self.sig,sources=self.inputs,defaults=DEFAULTS))
        self.pool=cf.ProcessPoolExecutor(max_workers=workers)
    def run(self,phase,jobs):
        pending={};count=0
        for original in jobs:
            job=dict(original,phase=phase)
            encoded=json.dumps(job,sort_keys=True,ensure_ascii=False)
            key=hashlib.sha256((self.sig+encoded).encode()).hexdigest()[:24]
            prior=self.db.execute('SELECT key FROM cells WHERE key=?',(key,)).fetchone()
            if prior:continue
            task={**job,'key':key,'output':str(self.output)}
            pending[self.pool.submit(evaluate,task)]=(key,encoded)
        print(f'{phase}: {len(jobs)} cells, {len(pending)} missing',flush=True)
        started=time.perf_counter()
        for future in cf.as_completed(pending):
            key,encoded=pending[future]
            result=future.result()
            self.db.execute('INSERT OR REPLACE INTO cells VALUES (?,?,?,?,?)',(key,phase,encoded,json.dumps(result),self.sig));self.db.commit();count+=1
            if count%200==0 or count==len(pending):print(f'{phase}: saved {count}/{len(pending)}, {time.perf_counter()-started:.1f}s',flush=True)
        rows=self.rows(phase)
        atomic_json(self.output/(phase+'.json'),rows)
    def rows(self,phase):
        return [dict(key=key,**json.loads(job),**json.loads(result)) for key,job,result in self.db.execute('SELECT key,job,result FROM cells WHERE phase=? AND signature=?',(phase,self.sig))]
    def close(self):self.pool.shutdown();self.db.close()


def count_options(stage,key):
    n=STAGES[stage][0]
    available=next(x['available'] for x in availability() if x['stage']==stage+1 and x['bond']==key)
    if not available:return []
    counts={1,math.ceil(n/3),math.ceil(n*2/3),n}
    if key=='military':counts.update({max(1,math.ceil(n/2)-1),math.ceil(n/2)})
    return sorted({min(x,available,n) for x in counts})


def screen_jobs(trials):
    jobs=[]
    for s in range(6):
        for key in IDENTITIES:
            for count in count_options(s,key):
                for gain in (.5,1.,2.):
                    for g in GENRES:
                        jobs.append(dict(stage=s,genre=g,bond=key,count=count,composition=((key,count),),enabled=(key,),
                                         config={'gain':gain},trials=trials,reference=True))
    return jobs


def holdout_jobs(trials):
    jobs=[]
    for s in range(6):
        for key in IDENTITIES:
            options=count_options(s,key)
            if not options:continue
            for count in sorted(set((options[len(options)//2],options[-1]))):
                for d in ('hard','extremely_hard'):
                    for placement in ('front','back'):
                        for g in GENRES:
                            jobs.append(dict(stage=s,genre=g,bond=key,count=count,composition=((key,count),),enabled=(key,),
                                             difficulty=d,placement=placement,trials=trials,bank='final',pool_offset=10000,trace=True,reference=True))
    return jobs


def pair_jobs(trials):
    import itertools
    jobs=[]
    for s in range(6):
        n=STAGES[s][0];count=max(1,n//3)
        available={r['bond']:r['available'] for r in availability() if r['stage']==s+1}
        for left,right in itertools.combinations(IDENTITIES,2):
            a=min(count,available[left]);b=min(count,available[right])
            if not a or not b:continue
            for g in GENRES:
                jobs.append(dict(stage=s,genre=g,bond=left+'+'+right,composition=((left,a),(right,b)),enabled=(left,right),
                                 bank='validation',pool_offset=20000,trials=trials,interaction=True))
    return jobs


def robustness_jobs(trials):
    jobs=[]
    for s in range(6):
        for key in IDENTITIES:
            options=count_options(s,key)
            if not options:continue
            count=options[len(options)//2]
            for prep in ('underdeveloped','four_top'):
                for g in GENRES:
                    jobs.append(dict(stage=s,genre=g,bond=key,count=count,composition=((key,count),),enabled=(key,),bank='final',
                                     preparation=prep,pool_offset=30000,trials=trials))
            # Native identity-sensitive skill supply, preserving four-stat budget.
            for g in GENRES:
                jobs.append(dict(stage=s,genre=g,bond=key,count=count,composition=((key,count),),enabled=(key,),bank='final',
                                 skill_fit=True,pool_offset=40000,trials=trials))
    return jobs


def variants_jobs(trials):
    jobs=[]
    variants=[('maid',{'maid_kind':x}) for x in ('attack','heal','shield')]
    variants += [('farmer',{'farmer_kind':x}) for x in ('heal','shield','damage')]
    variants += [('sword',{'sword_decay':x}) for x in (.35,.5,.7)]
    variants += [('hunter',{'hunter_turns':x}) for x in (2,3,4)]
    for s in range(6):
        for key,cfg in variants:
            options=count_options(s,key)
            if not options:continue
            count=options[len(options)//2]
            for g in GENRES:
                jobs.append(dict(stage=s,genre=g,bond=key,count=count,composition=((key,count),),enabled=(key,),
                                 config=cfg,bank='validation',pool_offset=50000,trials=trials))
        for g in GENRES:
            for h in GENRES:
                jobs.append(dict(stage=s,genre=g,enemy_genre=h,bond='all',enabled=tuple(IDENTITIES),enemy_enabled=tuple(IDENTITIES),
                                 symmetric=True,bank='final',pool_offset=60000,trials=trials,trace=True))
        # Specific adversary channels which the ordinary NPC does not contain.
        n=STAGES[s][0];avail={r['bond']:r['available'] for r in availability() if r['stage']==s+1}
        for key,enemy_key in (('military','ninja'),('killer','maid'),('hunter','rich'),('sage','sage')):
            if not avail[key] or not avail[enemy_key]:continue
            c=min(n,avail[key]);ec=min(n,avail[enemy_key])
            for g in GENRES:
                jobs.append(dict(stage=s,genre=g,bond=key,count=c,composition=((key,c),),enabled=(key,),
                                 enemy_composition=((enemy_key,ec),),enemy_enabled=(enemy_key,),enemy_config={'maid_kind':'heal'},
                                 bank='final',pool_offset=70000,trials=trials,symmetric=True))
    return jobs


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phase',choices=('all','screen','holdout','pairs','robustness','variants'),default='all')
    p.add_argument('--workers',type=int,default=8);p.add_argument('--output',type=Path,default=HERE/'results')
    p.add_argument('--screen-trials',type=int,default=6);p.add_argument('--holdout-trials',type=int,default=24)
    p.add_argument('--pair-trials',type=int,default=4);p.add_argument('--robust-trials',type=int,default=16)
    args=p.parse_args();runner=Runner(args.output,args.workers)
    atomic_json(args.output/'availability.json',availability())
    try:
        for name,maker,count in (('screen',screen_jobs,args.screen_trials),('holdout',holdout_jobs,args.holdout_trials),
                                 ('pairs',pair_jobs,args.pair_trials),('robustness',robustness_jobs,args.robust_trials),
                                 ('variants',variants_jobs,args.robust_trials)):
            if args.phase in ('all',name):runner.run(name,maker(count))
    finally:runner.close()


if __name__=='__main__':main()
