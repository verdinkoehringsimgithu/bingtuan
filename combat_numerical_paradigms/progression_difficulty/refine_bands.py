"""Resolve narrow operating bands, then confirm reusable NPC selections."""
import study
from study import *


def confirmation(job):
    if study.ACTIVE_BANK!='confirmation':
        records=json.loads((SOURCE_OUT/'catalog_growth_confirmation.json').read_text(encoding='utf-8'));old=json.loads((SOURCE_OUT/'catalog_old_growth_confirmation.json').read_text(encoding='utf-8'))
        study.OLD={(int(r['tier']),NAME_TO_LETTER[r['genre']],int(r['sample'])):tuple(int(r['csv'][k]) for k in ('dodge','defense','speed','authority')) for r in old};study.NEW={};natural.SKILLS.clear();natural.HOLDOUT_SKILLS.clear()
        for row in records:
            skill,stats=convert(row);letter=NAME_TO_LETTER[skill.genre];study.NEW[(skill.tier,letter,row['sample'])]=stats;natural.SKILLS.setdefault((skill.tier,letter),[]).append((skill,stats,row['sample']))
        natural.HOLDOUT_SKILLS.update(natural.SKILLS);natural.roster.cache_clear();study.PATHS.clear();study.ACTIVE_BANK='confirmation'
    return evaluate_growth({**job,'bank':'confirmation'})


def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=OUT);args=parser.parse_args();OUT=args.output.resolve();study.OUT=OUT
    study_runner=GrowthStudy(8);coarse=pd.read_csv(OUT/'difficulty_intervals.csv');meta=[];jobs=[]
    for r in coarse.itertuples():
        for offset in np.linspace(-.10,.10,21):
            rho=float(r.rho_center+offset)
            for g in GENRES:
                meta.append(dict(stage=r.stage,enemy_genre=r.enemy_genre,difficulty=r.difficulty,genre=g,rho=rho,alpha=r.alpha,beta=r.beta));jobs.append(dict(stage=int(r.stage),enemy_genre=r.enemy_genre,genre=g,alpha=r.alpha,beta=r.beta,rho=rho,bank='validation',pool_offset=16384,trials=64,stream='growth-fine-bands'))
    data=study_runner.table('fine_band_validation.csv',meta,jobs);aggregate=data.groupby(['stage','enemy_genre','difficulty','alpha','beta','rho']).agg(wr=('wr','mean'),flow_min=('wr','min'),flow_max=('wr','max')).reset_index();intervals=[]
    for (s,h,d),sub in aggregate.groupby(['stage','enemy_genre','difficulty']):
        lo,hi=TARGETS[d];accepted=sub[sub.wr.between(lo,hi)];met=len(accepted)>0
        if not met:accepted=sub.iloc[[int(np.argmin(abs(sub.wr-(lo+hi)/2)))]]
        anchor=accepted.iloc[int(np.argmin(abs(accepted.wr-(lo+hi)/2)))];ordered=sub.sort_values('rho').reset_index(drop=True);ix=int(np.argmin(abs(ordered.rho-anchor.rho)));left=right=ix
        # Keep a contiguous measured interval; do not assume an untested Cartesian product.
        while left>0 and lo<=ordered.wr.iloc[left-1]<=hi:left-=1
        while right<len(ordered)-1 and lo<=ordered.wr.iloc[right+1]<=hi:right+=1
        intervals.append(dict(stage=s,enemy_genre=h,difficulty=d,alpha=anchor.alpha,beta=anchor.beta,rho_lower=ordered.rho.iloc[left],rho_center=anchor.rho,rho_upper=ordered.rho.iloc[right],validation_in_band=met))
    write('fine_difficulty_intervals.csv',pd.DataFrame(intervals));meta=[];jobs=[]
    for row in intervals:
        for point in ('lower','center','upper'):
            for preparation in PREPARATIONS:
                if point!='center' and preparation!='standard':continue
                for g in GENRES:
                    rho=row['rho_'+point];meta.append(dict(stage=row['stage'],enemy_genre=row['enemy_genre'],difficulty=row['difficulty'],point=point,preparation=preparation,genre=g,rho=rho,alpha=row['alpha'],beta=row['beta']));jobs.append(dict(stage=int(row['stage']),enemy_genre=row['enemy_genre'],genre=g,alpha=row['alpha'],beta=row['beta'],rho=rho,preparation=preparation,bank='final',pool_offset=20480,trials=64,stream='growth-fine-final'))
    final=study_runner.table('fine_difficulty_holdout.csv',meta,jobs);study_runner.close()
    centers=final[(final.point=='center')&(final.preparation=='standard')];means=centers.groupby(['stage','difficulty','enemy_genre']).agg(wr=('wr','mean'),flow_spread=('wr',lambda x:x.max()-x.min()),censor=('censor','mean')).reset_index();recommendations=[]
    for (s,d),sub in means.groupby(['stage','difficulty']):
        lo,hi=TARGETS[d];score=abs(sub.wr-(lo+hi)/2)+.25*sub.flow_spread+sub.censor;r=sub.loc[score.idxmin()]
        candidates=pd.DataFrame(intervals);recommendations.append(candidates[(candidates.stage==s)&(candidates.difficulty==d)&(candidates.enemy_genre==r.enemy_genre)].iloc[0].to_dict())
    recommendation=pd.DataFrame(recommendations);write('recommended_templates.csv',recommendation)
    meta=[];jobs=[]
    for row in recommendations:
        for point in ('lower','center','upper'):
            for preparation in PREPARATIONS:
                for g in GENRES:
                    rho=row['rho_'+point];meta.append(dict(stage=row['stage'],enemy_genre=row['enemy_genre'],difficulty=row['difficulty'],point=point,preparation=preparation,genre=g,rho=rho,alpha=row['alpha'],beta=row['beta']));jobs.append(dict(stage=int(row['stage']),enemy_genre=row['enemy_genre'],genre=g,alpha=row['alpha'],beta=row['beta'],rho=rho,preparation=preparation,pool_offset=24576,trials=128,stream='growth-template-confirmation'))
    if not (OUT/'recommended_confirmation.csv').exists():
        with cf.ProcessPoolExecutor(8) as pool:results=list(pool.map(confirmation,jobs,chunksize=2))
        write('recommended_confirmation.csv',pd.concat([pd.DataFrame(meta),pd.DataFrame(results)],axis=1))


if __name__=='__main__':main()
