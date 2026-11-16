"""Test budget-conserving NPC stat blends for reduced player-flow disparity."""
import study
from study import *
from refine_bands import confirmation


def main():
    runner=GrowthStudy(8);anchors=pd.read_csv(OUT/'fine_difficulty_intervals.csv');meta=[];jobs=[]
    for r in anchors.itertuples():
        for balance in (0.,.5,1.):
            for ratio in (.7,.85,1.,1.15,1.3):
                rho=r.rho_center*ratio
                for g in GENRES:
                    meta.append(dict(stage=r.stage,difficulty=r.difficulty,enemy_genre=r.enemy_genre,genre=g,alpha=r.alpha,beta=r.beta,rho=rho,npc_balance=balance));jobs.append(dict(stage=int(r.stage),enemy_genre=r.enemy_genre,genre=g,alpha=r.alpha,beta=r.beta,rho=rho,npc_balance=balance,bank='validation',pool_offset=32768,trials=32,stream='npc-balance-screen'))
    scan=runner.table('balanced_npc_scan.csv',meta,jobs);aggregate=scan.groupby(['stage','difficulty','enemy_genre','alpha','beta','rho','npc_balance']).agg(wr=('wr','mean'),spread=('wr',lambda x:x.max()-x.min()),censor=('censor','mean')).reset_index();picks=[]
    for (s,d),sub in aggregate.groupby(['stage','difficulty']):
        lo,hi=TARGETS[d];score=abs(sub.wr-(lo+hi)/2)+.35*sub.spread+2*sub.censor;picks.append(sub.loc[score.idxmin()].to_dict())
    meta=[];jobs=[]
    for row in picks:
        for offset in np.linspace(-.08,.08,17):
            rho=row['rho']+offset
            for g in GENRES:
                meta.append(dict(stage=row['stage'],difficulty=row['difficulty'],enemy_genre=row['enemy_genre'],genre=g,alpha=row['alpha'],beta=row['beta'],rho=rho,npc_balance=row['npc_balance']));jobs.append(dict(stage=int(row['stage']),enemy_genre=row['enemy_genre'],genre=g,alpha=row['alpha'],beta=row['beta'],rho=rho,npc_balance=row['npc_balance'],bank='validation',pool_offset=34816,trials=64,stream='npc-balanced-band'))
    fine=runner.table('balanced_npc_bands.csv',meta,jobs);aggregate=fine.groupby(['stage','difficulty','enemy_genre','alpha','beta','rho','npc_balance']).agg(wr=('wr','mean'),spread=('wr',lambda x:x.max()-x.min()),censor=('censor','mean')).reset_index();selected=[]
    for (s,d),sub in aggregate.groupby(['stage','difficulty']):
        lo,hi=TARGETS[d];valid=sub[sub.wr.between(lo,hi)];candidate=valid if len(valid) else sub;score=abs(candidate.wr-(lo+hi)/2)+.15*candidate.spread+2*candidate.censor;r=candidate.loc[score.idxmin()];row=r.to_dict();ordered=sub.sort_values('rho').reset_index(drop=True);i=int(np.argmin(abs(ordered.rho-r.rho)));left=right=i
        while left>0 and lo<=ordered.wr.iloc[left-1]<=hi:left-=1
        while right<len(ordered)-1 and lo<=ordered.wr.iloc[right+1]<=hi:right+=1
        row.update(rho_lower=ordered.rho.iloc[left],rho_center=r.rho,rho_upper=ordered.rho.iloc[right]);selected.append(row)
    write('balanced_recommended_templates.csv',pd.DataFrame(selected));runner.close();meta=[];jobs=[]
    for row in selected:
        for point in ('lower','center','upper'):
            for preparation in PREPARATIONS:
                for g in GENRES:
                    meta.append(dict(stage=row['stage'],difficulty=row['difficulty'],enemy_genre=row['enemy_genre'],genre=g,point=point,preparation=preparation,rho=row['rho_'+point],npc_balance=row['npc_balance'],alpha=row['alpha'],beta=row['beta']));jobs.append(dict(stage=int(row['stage']),enemy_genre=row['enemy_genre'],genre=g,preparation=preparation,alpha=row['alpha'],beta=row['beta'],rho=row['rho_'+point],npc_balance=row['npc_balance'],pool_offset=36864,trials=128,stream='npc-balanced-confirmation'))
    if not (OUT/'balanced_recommended_confirmation.csv').exists():
        with cf.ProcessPoolExecutor(8) as pool:results=list(pool.map(confirmation,jobs,chunksize=2))
        write('balanced_recommended_confirmation.csv',pd.concat([pd.DataFrame(meta),pd.DataFrame(results)],axis=1))


if __name__=='__main__':main()
