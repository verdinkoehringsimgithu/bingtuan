"""Timing and no-skill gap features, derived without win/loss thresholds."""
import numpy as np


def enrich(features,rounds):
    values=dict(features)
    for side in ('p','e'):
        gaps=[];length=0
        for row in rounds:
            if row[side+'_normal_casts']>0:length+=1
            elif row[side+'_skill_casts']>0:
                if length:gaps.append(length)
                length=0
        if length:gaps.append(length)
        values[side+'_no_skill_gap_mean']=float(np.mean(gaps)) if gaps else 0.
        values[side+'_no_skill_gap_max']=float(max(gaps,default=0))
        for size in range(1,9):values[f'{side}_no_skill_gap_{size}']=sum(x==size for x in gaps)/len(rounds)
        values[side+'_no_skill_gap_tail']=sum(x>8 for x in gaps)/len(rounds)
        for status in ('weak','stat_weak'):
            areas=[(r[side+'_'+status+'_start']+r[side+'_'+status+'_end'])/2 for r in rounds]
            values[side+'_'+status+'_area']=float(sum(areas))
            values[side+'_'+status+'_coverage_mean']=float(np.mean(areas))
        ini=[r[side+'_initiative_start'] for r in rounds]+[rounds[-1][side+'_initiative_end']]
        values[side+'_initiative_drift']=float(ini[-1]-ini[0]);values[side+'_initiative_std']=float(np.std(ini))
    return values
