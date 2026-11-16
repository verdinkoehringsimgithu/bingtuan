"""D2 validation refinement, fresh generator test bank and analytic policies."""
from run_natural import *
import natural_core as natural


def bank_initializer():
    natural.HOLDOUT_SKILLS.clear()
    for row in json.loads((OUT/'catalog_final_test.json').read_text(encoding='utf-8')):
        skill,stats=natural.convert(row);natural.HOLDOUT_SKILLS.setdefault((skill.tier,natural.NAME_TO_LETTER[skill.genre]),[]).append((skill,stats,row['sample']))
    natural.roster.cache_clear()


def d2_refine(job):
    start=list(job['p']);trace=[];best=None
    for cycle in range(3):
        candidates=[start.copy()]
        for index in (0,1,5):
            for ratio in (.9,1.1):
                p=start.copy();p[index]=float(np.clip(p[index]*ratio,*BOUNDS[index]));candidates.append(p)
        for index,step in ((2,.025),(3,.008),(4,20)):
            for sign in (-1,1):
                p=start.copy();p[index]=float(np.clip(p[index]+sign*step,*BOUNDS[index]));candidates.append(p)
        rows=[]
        for p in candidates:
            result=evaluate(dict(job,p=p,trials=256,validation=True,pool_offset=6144,stream='d2-validation-refine'))
            score=objective(result,2);row=dict(stage=job['stage'],genre=job['genre'],opponent=job['opponent'],difficulty=2,cycle=cycle,score=score,**dict(zip(PARAMS,p)),**result);rows.append(row);trace.append(row)
        best=min(rows,key=lambda x:x['score']);start=[best[k] for k in PARAMS]
    return best,trace


def test_config(job):
    s,g=job['stage'],job['genre'];rows=[]
    for j in range(256):
        m=roster(s,g,j+8192,validation=True);it=equipment(m,g,COMMON[(s,g)]);team=Team(m,it);raw=np.array([m.stats for m in m]).sum(0);total=np.array([getattr(team,'base_'+f) for f in FIELDS]);target=stage_stats(s,g)
        rows.append(dict(stage=s,genre=g,pool=j+8192,main=total[LETTER[g[0]]],sub=total[LETTER[g[2]]],raw_main=raw[LETTER[g[0]]],raw_sub=raw[LETTER[g[2]]],reached=int(total[LETTER[g[0]]]>=target[LETTER[g[0]]] and total[LETTER[g[2]]]>=target[LETTER[g[2]]])))
    return rows


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=4);args=parser.parse_args()
    scenes=pd.read_csv(OUT/'difficulty_candidates.csv');picks=[];traces=[]
    if not (OUT/'d2_validation_refinement.csv').exists():
        jobs=[dict(stage=int(r.stage),genre=r.genre,opponent=r.opponent,p=[getattr(r,k) for k in PARAMS]) for r in scenes[scenes.difficulty==2].itertuples()]
        with cf.ProcessPoolExecutor(args.workers) as pool:
            for best,trace in pool.map(d2_refine,jobs):
                picks.append(best);traces.extend(trace)
                csv('d2_validation_progress.csv',pd.DataFrame(picks));csv('d2_validation_trace_progress.csv',pd.DataFrame(traces));print('D2 refined',best['stage']+1,best['genre'],flush=True)
        csv('d2_validation_refinement.csv',pd.DataFrame(traces));csv('d2_validation_candidates.csv',pd.DataFrame(picks))
    picks=pd.read_csv(OUT/'d2_validation_candidates.csv')
    for r in picks.itertuples():
        mask=(scenes.stage==r.stage)&(scenes.genre==r.genre)&(scenes.difficulty==2)
        scenes.loc[mask,list(PARAMS)]=[getattr(r,k) for k in PARAMS]
    csv('difficulty_delivery_candidates.csv',scenes)
    if not (OUT/'d2_fresh_catalog_holdout.csv').exists():
        jobs=[dict(stage=int(r.stage),genre=r.genre,opponent=r.opponent,p=[getattr(r,k) for k in PARAMS],validation=True,pool_offset=8192,trials=2500,stream='d2-fresh-final') for r in scenes[scenes.difficulty==2].itertuples()]
        with cf.ProcessPoolExecutor(args.workers,initializer=bank_initializer) as pool:
            results=list(pool.map(evaluate,jobs));reached=[]
            for rows in pool.map(test_config,[dict(stage=s,genre=g) for s in range(6) for g in GENRES]):reached.extend(rows)
        csv('d2_fresh_catalog_holdout.csv',pd.concat([scenes[scenes.difficulty==2].reset_index(drop=True),pd.DataFrame(results)],axis=1));csv('reachability_fresh_catalog_holdout.csv',pd.DataFrame(reached))
    original=pd.read_csv(OUT/'difficulty_holdout.csv');final=pd.concat([original[original.difficulty!=2],pd.read_csv(OUT/'d2_fresh_catalog_holdout.csv')],ignore_index=True).sort_values(['stage','genre','difficulty']);csv('difficulty_delivery_holdout.csv',final)
    shared=[];jobs=[]
    for (s,d),group in scenes.groupby(['stage','difficulty']):
        p=group[list(PARAMS)].median().tolist()
        for r in group.itertuples():
            shared.append(dict(stage=s,genre=r.genre,difficulty=d,opponent=r.opponent,**dict(zip(PARAMS,p))));jobs.append(dict(stage=int(s),genre=r.genre,opponent=r.opponent,p=p,validation=True,pool_offset=9216,trials=512,stream=f'shared-macro-{d}'))
    if not (OUT/'shared_macro_holdout.csv').exists():
        with cf.ProcessPoolExecutor(args.workers,initializer=bank_initializer) as pool:results=list(pool.map(evaluate,jobs))
        csv('shared_macro_holdout.csv',pd.concat([pd.DataFrame(shared),pd.DataFrame(results)],axis=1))
    policy=dict(formula='For N between measured stages: interpolate log(alpha),log(beta),log(mu),log(scale_C/R/I/M) linearly in N; gamma/delta/theta linearly in N. Enemy BP=alpha*stage_BP; full-BP base hit=0.135*beta*stage_BP; enemy stats=sum(member source stats)*scale. Do not extrapolate beyond 5..30 members.',
                opponent_selection='Flow-specific opponent codes remain discrete. Shared median macro policy is separately tested and is not assumed to satisfy all experience goals.',
                interpolation_status='Measured six knots; unmeasured intermediate N has no empirical guarantee.',knots=scenes.to_dict('records'))
    save_json(OUT/'enemy_delivery_policy.json',policy)
    save_json(OUT/'refinement_manifest.json',dict(validation_executions=len(pd.read_csv(OUT/'d2_validation_refinement.csv'))*256,fresh_d2_executions=90000,shared_macro_executions=73728,reachability_samples=9216,final_catalog_offset=384,independent_final_bank=True))


if __name__=='__main__':main()
