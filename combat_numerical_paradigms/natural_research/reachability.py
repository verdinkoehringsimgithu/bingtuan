"""Measured source-record reachability and global tier-budget optimisation."""
import os
for v in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[v]='1'
from natural_core import *
import argparse,time
import pandas as pd
from scipy.optimize import differential_evolution
sys.path.insert(0,str(ROOT/'combat_numerical_paradigms/roster_research'))
from run_study import save_json
OUT=Path(__file__).parent/'results'

def common_points(stage,g):
    frame=pd.read_csv(ROOT/'combat_numerical_paradigms/roster_research/results/common_operating_points.csv')
    return float(frame[(frame.stage==stage)&(frame.genre==g)].iloc[0].points)
POINTS={(s,g):common_points(s,g) for s in range(6) for g in GENRES}

def source_audit():
    OUT.mkdir(parents=True,exist_ok=True);records=[]
    for row in CATALOG:
        skill,values=convert(row);assert sum(values) in range(OLD_BUDGETS[skill.tier-1][0],OLD_BUDGETS[skill.tier-1][1]+1)
        assert skill.sub_effect_name in ('','总战力恢复','当前战力自愈','虚弱压制','四维削弱','敌方已损斩杀','自身已损反噬','敌方当前压制','最大流失','已损流失','固定流失','战力吸收')
        records.append(dict(tier=skill.tier,genre=skill.genre,total=sum(values),**dict(zip(FIELDS,values))))
    pd.DataFrame(records).groupby(['tier','genre']).agg(['min','mean','max']).to_csv(OUT/'source_stat_distribution.csv')
    save_json(OUT/'source_chain_audit.json',dict(generator='SkillGenerator.cs GetStatBudget/AllocateStats -> CsvData dodge/defense/speed/authority',
        integration='Unity strategy builds fresh budgets independently; direct CSV stat import is not present in inspected paths',
        stat_growth='inspected UpgradeToMaxLevel changes BP only multiplicatively; its rank35 adds personal C/R/I/M=(5,5,5,2), recorded separately',
        growth_note='rank35 is a specific source execution path, not an invented four-stat multiplier; primary study uses generator plus equipment, rank variant reported separately',
        bp_ruler='canonical stage BP, equally owned by N members; four-stat totals naturally summed without normalization',
        extended_effects='current-BP heal; current-BP physical pressure after direct hit; fixed DoT uses magic/defense/output rules with original owner',
        catalog_records=len(CATALOG),generator_sha256=hashlib.sha256((ROOT/'SkillGenerator.cs').read_bytes()).hexdigest(),native=core.parity_test(600)))

def scan(budgets=None,primary=.6,secondary=.2,stream='source',pools=128):
    rows=[]
    for s in range(6):
        n=STAGES[s][0]
        for g in GENRES:
            for profile in ('mixed','upper'):
                for pool in range(pools):
                    m=roster(s,g,pool,profile,budgets=budgets,primary=primary,secondary=secondary);raw=np.sum([x.stats for x in m],axis=0)
                    for stock in range(5):
                        # Personal-stat top channel upper-budget scenario. Active mechanisms carry no extra static points.
                        load=[(j,'owner_stats',1.) for j in range(stock)]
                        it=equipment(m,g,POINTS[(s,g)],'theme',loadout=load);team=Team(m,it)
                        total=np.array([getattr(team,'base_'+f) for f in FIELDS]);target=stage_stats(s,g)
                        rows.append(dict(stage=s,genre=g,profile=profile,pool=pool,stock=stock,points=POINTS[(s,g)],
                            main=total[LETTER[g[0]]],sub=total[LETTER[g[2]]],raw_main=raw[LETTER[g[0]]],raw_sub=raw[LETTER[g[2]]],
                            target_main=target[LETTER[g[0]]],target_sub=target[LETTER[g[2]]],main_gap=max(0,target[LETTER[g[0]]]-total[LETTER[g[0]]]),sub_gap=max(0,target[LETTER[g[2]]]-total[LETTER[g[2]]]),
                            reached=int(total[LETTER[g[0]]]>=target[LETTER[g[0]]] and total[LETTER[g[2]]]>=target[LETTER[g[2]]]),raw_total=raw.sum(),item_total=sum(sum(x.stats) for x in it),owner_bonus_total=total.sum()-raw.sum()-sum(sum(x.stats) for x in it),
                            **dict(zip(FIELDS,total))))
    frame=pd.DataFrame(rows);frame.to_csv(OUT/f'{stream}_reachability.csv.gz',index=False)
    summary=frame.groupby(['stage','genre','profile','stock']).agg(n=('reached','size'),reached=('reached','mean'),main_mean=('main','mean'),main_min=('main','min'),main_max=('main','max'),sub_mean=('sub','mean'),sub_min=('sub','min'),sub_max=('sub','max'),raw_total=('raw_total','mean'),item_total=('item_total','mean'),owner_bonus_total=('owner_bonus_total','mean'),main_gap=('main_gap','mean'),sub_gap=('sub_gap','mean')).reset_index()
    summary.to_csv(OUT/f'{stream}_reachability_summary.csv',index=False,encoding='utf-8-sig')
    if budgets is None and stream=='source':
        variant=[]
        for s in range(6):
            for g in GENRES:
                for pool in range(128):
                    m=roster(s,g,pool,rank=True);it=equipment(m,g,POINTS[(s,g)],'theme');t=Team(m,it)
                    variant.append(dict(stage=s,genre=g,pool=pool,main=getattr(t,'base_'+FIELDS[LETTER[g[0]]]),sub=getattr(t,'base_'+FIELDS[LETTER[g[2]]])))
        pd.DataFrame(variant).groupby(['stage','genre']).agg(['min','mean','max']).to_csv(OUT/'source_rank35_reachability.csv')
    return frame,summary

def parameterize(x):
    means=np.sort(x[:6]);ranges=tuple((max(0,round(v*.9)),max(1,round(v*1.1))) for v in means)
    p=float(x[6]);q=min(float(x[7]),1-p)
    return ranges,p,q

def optimize():
    # Fixed generated members and budgets; only global tier allocation is changed.
    desc=[];groups=[];item_stats=[];target=[]
    for s in range(6):
        for g in GENRES:
            for pool in range(32):
                index=len(groups);m=roster(s,g,pool);groups.append((s,g,pool));target.append(stage_stats(s,g));v=[0.]*4;v[LETTER[g[0]]]=POINTS[(s,g)]*STAGES[s][0]*.67;v[LETTER[g[2]]]=POINTS[(s,g)]*STAGES[s][0]*.33;item_stats.append(v)
                for pos,member in enumerate(m):
                    letter=NAME_TO_LETTER[member.skill.genre]
                    u=random.Random(seed('natural-stat-budget',s,g,pool,pos,member.skill.tier,member.uid)).random()
                    desc.append((index,member.skill.tier-1,LETTER[letter],LETTER[SECONDARY[letter]],u))
    a=np.array(desc);grp=a[:,0].astype(int);tiers=a[:,1].astype(int);pr=a[:,2].astype(int);se=a[:,3].astype(int);u=a[:,4];ix=np.arange(len(a));letters={v:k for k,v in LETTER.items()};other=np.array([[LETTER[k] for k in OTHER_ORDER[letters[p]]] for p in pr])
    items=np.array(item_stats);targets=np.array(target);main_ix=np.array([LETTER[g[0]] for _,g,_ in groups]);sub_ix=np.array([LETTER[g[2]] for _,g,_ in groups]);gx=np.arange(len(groups))
    def response(x):
        ranges,p,q=parameterize(x);low=np.array([z[0] for z in ranges]);width=np.array([z[1]-z[0]+1 for z in ranges]);tot=low[tiers]+np.floor(u*width[tiers]);vals=np.zeros((len(a),4));vals[ix,pr]=np.rint(tot*p);vals[ix,se]=np.rint(tot*q);vals[ix,other[:,0]]=np.rint(tot*(1-p-q)/2);vals[ix,other[:,1]]=tot-vals.sum(1)
        agg=np.array([np.bincount(grp,weights=vals[:,k],minlength=len(groups)) for k in range(4)]).T+items
        ratios=np.c_[agg[gx,main_ix]/targets[gx,main_ix],agg[gx,sub_ix]/targets[gx,sub_ix]]
        deficit=np.maximum(0,1-ratios)
        # Goals define the measured gap; these weights define the explicit resource/coverage tradeoff, not failure labels.
        loss=100*deficit.mean()+200*deficit.max()+np.maximum(0,ratios-1).mean()+.15*(agg.sum(1)/targets.sum(1)).mean()
        return loss,ratios,agg
    bounds=[(0,180)]*6+[(.6,.95),(.0,.25)]
    fit=differential_evolution(lambda x:response(x)[0],bounds,seed=20261012,popsize=10,maxiter=55,tol=.002,polish=False,workers=1)
    ranges,p,q=parameterize(fit.x);loss,ratios,agg=response(fit.x)
    config=dict(budgets=ranges,primary=p,secondary=q,objective=loss,optimizer_evaluations=fit.nfev,training_roster_groups=len(groups),
        objective_formula='100*mean(relative_deficit)+200*max(relative_deficit)+mean(relative_surplus)+0.15*mean(total_stat/target_total)',
        equipment_points=[dict(stage=s,genre=g,points=POINTS[(s,g)],axis='theme',primary_fraction=.67) for s in range(6) for g in GENRES])
    save_json(OUT/'selected_stat_profile.json',config)
    rows=[]
    for j,(s,g,pool) in enumerate(groups):rows.append(dict(stage=s,genre=g,pool=pool,main_ratio=ratios[j,0],sub_ratio=ratios[j,1],**dict(zip(FIELDS,agg[j]))))
    pd.DataFrame(rows).to_csv(OUT/'stat_optimization_training.csv',index=False)
    scan(ranges,p,q,'candidate',128)
    return config

def patch_generator(config):
    source=ROOT/'SkillGenerator.cs';before=source.read_text(encoding='utf-8-sig');snapshot=OUT.parent/'source_snapshots';snapshot.mkdir(exist_ok=True)
    (snapshot/'SkillGenerator_before.cs').write_text(before,encoding='utf-8')
    pairs=', '.join('{ '+str(lo)+', '+str(hi)+' }' for lo,hi in config['budgets'])
    code='''        private static readonly int[,] StatBudgetRanges = new int[,] { PAIRS };
        private const double StatPrimaryWeight = PRIMARY;
        private const double StatSecondaryWeight = SECONDARY;

        private static int GetStatBudget(int tier)
        {
            int index = Math.Max(0, Math.Min(5, tier - 1));
            return _rand.Next(StatBudgetRanges[index, 0], StatBudgetRanges[index, 1] + 1);
        }

        private static string GetStatBudgetDesc(int tier)
        {
            int index = Math.Max(0, Math.Min(5, tier - 1));
            return string.Format("{0} ~ {1} 点", StatBudgetRanges[index, 0], StatBudgetRanges[index, 1]);
        }

'''.replace('PAIRS',pairs).replace('PRIMARY',format(config['primary'],'.12g')).replace('SECONDARY',format(config['secondary'],'.12g'))
    start=before.index('        private static int GetStatBudget(int tier)');end=before.index('        private static void AllocateStats(',start)
    changed=before[:start]+code+before[end:]
    start=changed.index('        private static void AllocateStats(');end=changed.index('        private static int GetSynergyBudget(',start)
    method=changed[start:end].replace('total * 0.60','total * StatPrimaryWeight').replace('total * 0.20','total * StatSecondaryWeight').replace('total * 0.10','total * (1.0 - StatPrimaryWeight - StatSecondaryWeight) / 2.0')
    changed=changed[:start]+method+changed[end:];source.write_text(changed,encoding='utf-8-sig')
    save_json(OUT/'generator_patch_audit.json',dict(before_sha256=hashlib.sha256(before.encode('utf-8')).hexdigest(),after_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),changed='global tier stat budgets, stat weights and displayed budget descriptions; active skill parameters/conditions/counts unchanged'))

def main():
    p=argparse.ArgumentParser();p.add_argument('--patch',action='store_true');args=p.parse_args();source_audit();scan();config=optimize();print(json.dumps(config,ensure_ascii=False,indent=2),flush=True)
    if args.patch:patch_generator(config)

if __name__=='__main__':main()
