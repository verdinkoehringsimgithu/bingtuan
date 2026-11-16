"""Explicit conversion from missing-cap restoration to log-wear removal."""
import math


def restore_missing_caps(state,result_id,fractions):
    if len(fractions)!=5 or any(not math.isfinite(x) or not 0<=x<=1 for x in fractions):
        raise ValueError('Missing-cap restoration requires five finite fractions in [0,1]')
    removals=[]
    for wear,u in zip(state.wear,fractions):
        old=math.exp(-wear);new=old+u*(1-old)
        removals.append(0. if wear==0 else min(1.,max(0.,1+math.log(new)/wear)))
    state.supply(result_id,removals)
    return dict(mode='restore_missing_cap',fractions=list(fractions),result_factors=list(state.factors))
