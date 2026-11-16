"""Conservation/parity checks, conditional response surfaces and audit ledger."""
from run_study import *

def checks(q):
    audit=parity_test(600);cases=0
    for s in range(6):
        for g in GENRES:
            for c,b in ((1,2),(2,4),(STAGES[s][0],0)):
                m=roster(s,g,c,b);t=Team(m)
                assert len(m)==STAGES[s][0]
                assert [getattr(t,'base_'+f) for f in FIELDS]==stage_stats(s,g)
                assert t.max_bp==STAGES[s][1];cases+=1
    # Exact independent first-success probabilities, with no assumed coverage sum.
    m=list(roster(5,'C_I',4,0))[:4]
    for j,x in enumerate(m):
        x=copy.deepcopy(x);x.skill.trigger_chance=30;x.skill.turn_cond1=0;x.skill.turn_cond2=0;x.skill.self_bp_cond2=0;x.skill.enemy_bp_cond2=0;x.skill.times_limit=1;m[j]=x
    t=Team(tuple(m));e=Team(tuple(m));t.trace=True;random.seed(14);select_skill(t,e,1)
    assert np.allclose([x[4] for x in t.probabilities],[.3*.7**j for j in range(4)])
    assert np.isclose(t.metrics['expected_normal'],.7**4)
    # Counts belong to the owner, and an activation spends a use before hitting.
    t=Team(tuple(m));t.members[0].skill.trigger_chance=100
    select_skill(t,e,1);assert t.usage[t.members[0].skill.id]==1
    assert eligibility(t,e,t.members[0].skill,1,2)[1]=='exhausted'
    gear=list(equipment(tuple(m),'C_I'));gear[0]=Item('extra_use',2,top=True);t=Team(tuple(m),tuple(gear))
    for turn in range(1,4):select_skill(t,e,turn)
    assert t.usage[t.members[0].skill.id]==3
    assert eligibility(t,e,t.members[0].skill,3,4)[1]=='exhausted'
    t.members[0].skill.self_bp_cond2=50
    assert eligibility(t,e,t.members[0].skill,99,1)[1]=='self_gate'
    # Passive personal attributes count in full even for the last member.
    m=roster(5,'M_R');plain=Team(m);it=list(equipment(m,'M_R'));it[-1]=Item('owner_stats',1,top=True);boost=Team(m,tuple(it))
    for k,f in enumerate(FIELDS):assert np.isclose(getattr(boost,'base_'+f)-getattr(plain,'base_'+f),m[-1].stats[k])
    configs=json.loads((q/'operating_roster_equipment_configs.json').read_text(encoding='utf-8'))
    for x in configs:
        assert len(x['members'])==STAGES[x['stage']-1][0]
        assert x['top_count']<=4
        assert sum(m['equipment']['top'] for m in x['members'])==x['top_count']
    # Replay one complete independent telemetry battle per stage/flow/difficulty.
    choice=pd.read_csv(q/'roster_recommendations.csv');rounds=0;battles=0;owner_members=0;replays=0
    for path in sorted(q.glob('rounds_*.jsonl.gz')):
        with gzip.open(path,'rt',encoding='utf-8') as f:
            for j,line in enumerate(f):
                x=json.loads(line);r=x['result'];rows=x['rounds'];rounds+=len(rows);battles+=1
                assert len(rows)==r['turns']
                for row in rows:
                    for side in ('p','e'):
                        assert np.isfinite(row[side+'_bp_end'])
                if j==0:
                    s=x['stage'];g=x['genre'];ch=choice[(choice.stage==s)&(choice.genre==g)].iloc[0]
                    a=roster(s,g,int(ch.carry),int(ch.backup),0,ch.order);b=roster(s,x['opponent'],2,4,3)
                    fresh,_,_,_=simulate(a,b,int(x['seed']),p=[x[k] for k in MACRO_NAMES])
                    assert fresh['win']==r['win'] and fresh['turns']==r['turns'],x['battle_id']
                    assert np.isclose(fresh['hp'],r['hp'],atol=1e-9),x['battle_id'];replays+=1
    for path in q.glob('owners_*.jsonl.gz'):
        with gzip.open(path,'rt',encoding='utf-8') as f:
            for line in f:owner_members+=len(json.loads(line)['members'])
    assert battles==28800 and owner_members==504000
    sample_jobs=[dict(stage=s,genre=GENRES[s],opponent=GENRES[(s+1)%6],p=[1.2,1.1,0.,0.,0.,1.],trials=24,stream='process-reproducibility') for s in range(6)]
    serial=[evaluate(x) for x in sample_jobs]
    with cf.ProcessPoolExecutor(max_workers=2) as pool:parallel=list(pool.map(evaluate,sample_jobs))
    assert serial==parallel
    audit.update(stage_budget_cases=cases,telemetry_battles=battles,rounds=rounds,owner_records=owner_members,replayed_strata=replays,serial_parallel_identical=True,
                 independent_probability_test=True,owner_use_limit_test=True,condition_gate_test=True,passive_attribute_test=True,one_item_four_top_test=True)
    save_json(q/'final_model_checks.json',audit)
    # Regression calls the unmodified source function, records its printed matrix.
    if not (q/'native_37500_regression.txt').exists():
        import contextlib,io
        random.seed(20261012);buf=io.StringIO()
        with contextlib.redirect_stdout(buf):engine.run_full_stress_test(2500)
        (q/'native_37500_regression.txt').write_text(buf.getvalue(),encoding='utf-8')
    import re
    text=(q/'native_37500_regression.txt').read_text(encoding='utf-8');rates=[float(re.findall(r'([\d.]+)%',line)[-1]) for line in text.splitlines() if len(re.findall(r'([\d.]+)%',line))==7]
    assert len(rates)==6 and max(rates)-min(rates)<=15.
    audit['native_overall_spread_percentage_points']=max(rates)-min(rates);save_json(q/'final_model_checks.json',audit)
    return audit

def surfaces(study):
    path=study.out/'conditional_alpha_beta_surfaces.csv'
    if not path.exists():
        scenes=study.read('equipped_difficulty_candidates.csv');meta=[];jobs=[]
        for r in scenes[scenes.difficulty==3].to_dict('records'):
            alphas=np.linspace(max(.3,r['alpha']*.65),min(3.5,r['alpha']*1.35),7)
            betas=np.linspace(max(.05,r['beta']*.65),min(4.,r['beta']*1.35),7)
            for a in alphas:
                for b in betas:
                    p=[r[k] for k in MACRO_NAMES];p[0]=a;p[1]=b
                    meta.append(dict(stage=r['stage'],genre=r['genre'],opponent=r['opponent'],**dict(zip(MACRO_NAMES,p))))
                    jobs.append(dict(stage=int(r['stage']),genre=r['genre'],opponent=r['opponent'],p=p,carry=int(r['carry']),backup=int(r['backup']),order=r['order'],points=r['points'],axis=r['axis'],trials=96,stream='conditional-surface'))
        study.csv(path.name,pd.concat([pd.DataFrame(meta),pd.DataFrame(study.jobs(jobs))],axis=1))
    df=study.read(path.name)
    for s in range(6):
        for metric in ('wr','turns'):
            fig,axs=plt.subplots(2,3,figsize=(13,8),constrained_layout=True)
            for ax,g in zip(axs.flat,GENRES):
                sub=df[(df.stage==s)&(df.genre==g)];tab=sub.pivot(index='alpha',columns='beta',values=metric)
                mesh=ax.contourf(tab.columns,tab.index,tab.to_numpy(),levels=np.linspace(0,1,11) if metric=='wr' else 10,cmap='viridis');fig.colorbar(mesh,ax=ax)
                ax.set(title=g,xlabel='beta: attack flux',ylabel='alpha: BP multiplier')
            fig.suptitle(f'S{s+1} / {STAGES[s][0]} members: {metric}; other channels fixed at D3\n96 trials per node; contours interpolate measured nodes')
            fig.savefig(study.out/'figures'/f'conditional_{metric}_S{s+1}.png',dpi=140);plt.close(fig)

def paths_and_dimensions(q):
    df=pd.read_csv(q/'strategic_paths_by_stage.csv')
    if 'delta.1' in df:
        df=df.rename(columns={'delta':'macro_delta','delta.1':'delta'})
        df.to_csv(q/'strategic_paths_by_stage.csv',index=False,encoding='utf-8-sig')
    enemy_response=pd.read_csv(q/'enemy_counter_equipment_by_stage.csv').groupby(['stage','genre']).wr.min()
    df['enemy_four_item_worst_wr']=[enemy_response.loc[(r.stage,r.genre)] for r in df.itertuples()]
    df['enemy_reversal_probability']=1-df.wr
    df['reference_met']=((df.path=='advantage')&(df.base_wr.between(.60,.70))&(df.wr>=.92)&(df.enemy_reversal_probability<.05))|((df.path=='counter')&(df.base_wr<=.30)&df.wr.between(.45,.55))|((df.path=='stalemate')&(df.base_turns>=8)&(df.delta>=.30))
    # These are final requested design targets, never cluster labels.
    df.to_csv(q/'strategic_path_reference_checks.csv',index=False,encoding='utf-8-sig')
    hetero=pd.read_csv(q/'heterogeneous_embedding_by_stage.csv');hetero['output_preserved']=hetero.output_ratio>=.95
    hetero.to_csv(q/'heterogeneous_reference_checks.csv',index=False,encoding='utf-8-sig')
    # Five dimensions: observed extrema/slopes and downside, with no failure thresholds.
    raw=pd.read_csv(q/'mechanic_response_scan.csv');rows=[]
    for keys,sub in raw.groupby(['stage','genre','kind','allocation']):
        avg=sub.groupby('value').agg(wr=('wr','mean'),delta=('delta','mean'),downside=('downside','mean'),spread=('wr','std')).sort_index()
        vals=avg.index.to_numpy();slopes=np.diff(avg.wr)/np.diff(vals);imax=int(np.argmax(abs(slopes))) if len(slopes) else 0
        rows.append(dict(stage=keys[0],genre=keys[1],kind=keys[2],allocation=keys[3],observed_min_wr=sub.wr.min(),observed_max_wr=sub.wr.max(),best_gain=sub.delta.max(),worst_gain=sub.delta.min(),
                         largest_response_slope=slopes[imax] if len(slopes) else 0,transition_low=vals[imax],transition_high=vals[min(imax+1,len(vals)-1)],minimum_downside=sub.downside.min(),maximum_downside=sub.downside.max()))
    pd.DataFrame(rows).to_csv(q/'five_dimension_mechanism_evidence.csv',index=False,encoding='utf-8-sig')

def heterogeneous_channels(job):
    samples=[]
    for j in range(320):
        s=job['stage'];m=roster(s,job['genre'],job['carry'],job['backup'],j%8,job['order']);e=roster(s,job['opponent'],2,4,(j+3)%8)
        it=member_items(m,job);rs=seed('heterogeneous-channel-independent',s,job['genre'],j)
        base,bf,_,_=simulate(m,e,rs,it,p=job['p'],telemetry=True)
        new,nf,_,_=simulate(modify_roster(m,dict(job,pool=j%8)),e,rs,it,p=job['p'],telemetry=True)
        samples.append(dict(base_win=base['win'],win=new['win'],base_output=base['damage_per_round'],output=new['damage_per_round'],**{'change_'+k:nf[k]-bf[k] for k in nf if k.endswith('_flux') or 'weak_mean' in k}))
    d=pd.DataFrame(samples);out=d.mean().to_dict();out['delta']=out['win']-out['base_win'];out['output_ratio']=out['output']/out['base_output'];out['n']=len(d)
    return out

def hetero_evidence(study):
    if (study.out/'heterogeneous_channel_holdout.csv').exists():return
    raw=study.read('heterogeneous_embedding_by_stage.csv');scenes=study.read('equipped_difficulty_candidates.csv');jobs=[];meta=[]
    for (s,g),sub in raw.groupby(['stage','genre']):
        eligible=sub[sub.output_ratio>=.95];pick=(eligible if len(eligible) else sub).sort_values('delta',ascending=False).iloc[0]
        r=scenes[(scenes.stage==s)&(scenes.genre==g)&(scenes.difficulty==3)].iloc[0]
        meta.append(dict(stage=s,genre=g,foreign=pick.foreign,position=int(pick.position)))
        jobs.append(dict(stage=int(s),genre=g,opponent=r.opponent,carry=int(r.carry),backup=int(r.backup),order=r.order,points=r.points,axis=r.axis,p=[r[k] for k in MACRO_NAMES],foreign=pick.foreign,foreign_position=int(pick.position)-1))
    study.csv('heterogeneous_channel_holdout.csv',pd.concat([pd.DataFrame(meta),pd.DataFrame(study.pool.map(heterogeneous_channels,jobs,chunksize=1))],axis=1));study.total+=len(jobs)*640

def continuous_tables(q):
    rows=pd.read_csv(q/'equipped_difficulty_candidates.csv').to_dict('records')
    save_json(q/'continuous_equipped_delivery.json',dict(formula='f_g(x,y)=sum_(s,d) h_s(x) h_d(y) p_(g,s,d); h_k(z)=max(0,1-abs(z-k))',
        x='member_count/5-1 in [0,5]',y='difficulty-1 in [0,3]',parameters=list(MACRO_NAMES),nodes=rows,
        validation='exact nodes reproduce held-out calibrated encounters; between-node interpolation is a design tool, not an independently validated stage',
        opponent='discrete code in each node; categorical skill profiles are not interpolated',beta_scan_extension=[.05,4.]))

def regular_top_budget(study):
    if (study.out/'regular_four_item_holdout.csv').exists():return
    loads=study.read('operating_four_item_loadouts.csv');scenes=study.read('equipped_difficulty_candidates.csv');meta=[];jobs=[]
    def make(r,scale,trials,stream):
        scene=scenes[(scenes.stage==r['stage'])&(scenes.genre==r['genre'])&(scenes.difficulty==4)].iloc[0]
        load=[(int(pos),kind,(int(float(value)*scale) if kind in ('extra_use','cleanse') else float(value)*scale)) for pos,kind,value in json.loads(r['loadout'])]
        return dict(stage=int(r['stage']),genre=r['genre'],opponent=scene.opponent,p=[scene[k] for k in MACRO_NAMES],carry=int(r['carry']),backup=int(r['backup']),order=r['order'],points=r['points'],axis=r['axis'],loadout=load,paired=True,base=dict(points=r['points'],axis=r['axis']),trials=trials,stream=stream)
    for r in loads.to_dict('records'):
        for scale in (0.,.25,.5,.75,1.):
            job=make(r,scale,800,'four-top-strength-training');meta.append({**r,'strength_scale':scale,'loadout':json.dumps(job['loadout'])});jobs.append(job)
    df=pd.concat([pd.DataFrame(meta),pd.DataFrame(study.jobs(jobs))],axis=1);study.csv('four_item_strength_curves.csv',df)
    chosen=[];jobs=[]
    for _,sub in df.groupby(['stage','genre']):
        r=sub.iloc[(sub.wr-.825).abs().argmin()].to_dict()
        # Values in the row are already scaled; do not scale the selected loadout twice.
        chosen.append({k:r[k] for k in ('stage','genre','points','axis','carry','backup','order','loadout','strength_scale')});jobs.append(make(r,1.,1200,'regular-four-top-independent'))
    study.csv('regular_four_item_loadouts.csv',pd.DataFrame(chosen));study.csv('regular_four_item_holdout.csv',pd.concat([pd.DataFrame(chosen),pd.DataFrame(study.jobs(jobs))],axis=1))
    cfg=json.loads((study.out/'operating_roster_equipment_configs.json').read_text(encoding='utf-8'))
    for r in cfg:
        match=next(x for x in chosen if x['stage']==r['stage']-1 and x['genre']==r['genre']);bypos={int(p):(k,v) for p,k,v in json.loads(match['loadout'])}
        for member in r['members']:
            pos=member['position']-1
            if pos in bypos:member['equipment']['kind'],member['equipment']['value']=bypos[pos]
        r['strength_scale']=match['strength_scale']
    save_json(study.out/'regular_roster_equipment_configs.json',cfg)

def versatility_matrix(study):
    if (study.out/'versatility_all_flow_matrix.csv').exists():return
    loads=study.read('regular_four_item_loadouts.csv');meta=[];jobs=[]
    for r in loads.to_dict('records'):
        for h in GENRES:
            meta.append(dict(stage=r['stage'],genre=r['genre'],opponent=h))
            jobs.append(dict(stage=int(r['stage']),genre=r['genre'],opponent=h,p=[1.3,1.1,0.,0.,0.,1.],carry=int(r['carry']),backup=int(r['backup']),order=r['order'],points=r['points'],axis=r['axis'],loadout=json.loads(r['loadout']),paired=True,base=dict(points=r['points'],axis=r['axis']),trials=240,stream='cross-flow-versatility-independent'))
    df=pd.concat([pd.DataFrame(meta),pd.DataFrame(study.jobs(jobs))],axis=1);study.csv('versatility_all_flow_matrix.csv',df)
    rows=[]
    for (s,g),sub in df.groupby(['stage','genre']):rows.append(dict(stage=s,genre=g,base_mean=sub.base_wr.mean(),base_min=sub.base_wr.min(),base_max=sub.base_wr.max(),base_range=sub.base_wr.max()-sub.base_wr.min(),equipped_mean=sub.wr.mean(),equipped_min=sub.wr.min(),equipped_max=sub.wr.max(),equipped_range=sub.wr.max()-sub.wr.min(),range_change=(sub.wr.max()-sub.wr.min())-(sub.base_wr.max()-sub.base_wr.min())))
    study.csv('versatility_flow_ranges.csv',pd.DataFrame(rows))

def main():
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=8);p.add_argument('--output',default=str(Path(__file__).parent/'results'));args=p.parse_args()
    study=Study(args);study.log('checking ownership, conserved budgets, native parity and telemetry replay');checks(study.out)
    study.log('measuring conditional alpha/beta surfaces for all six stages and flows');surfaces(study);paths_and_dimensions(study.out)
    hetero_evidence(study);continuous_tables(study.out);regular_top_budget(study);versatility_matrix(study)
    save_json(study.out/'final_checks_manifest.json',dict(simulations=study.total,elapsed_seconds=time.time()-study.started));study.pool.shutdown()

if __name__=='__main__':main()
