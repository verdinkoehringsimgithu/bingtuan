"""Fit event policies to measured battle response; no held-out chain selection.

Weighted particles condition their next state on actually winning each fight.
Weights preserve survival probabilities, avoiding extinction of finite cohorts.
Interpolation is a fitting surrogate only; final journeys use native battles.
"""
import argparse
import concurrent.futures as cf
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np

import measure_response as lab
from run_bonds import atomic_json

_groups = None


def load_groups():
    global _groups
    if _groups is None:
        main=json.loads((lab.OUT/'curves.json').read_text(encoding='utf-8'))['rows']
        extra=lab.OUT/'low_margin/curves.json'
        if extra.exists():main+=json.loads(extra.read_text(encoding='utf-8'))['rows']
        _groups=main
    return _groups


def response(cell,profile):
    points=cell['result']['points'];pp=[];hp=[];exposure=[];counts=[]
    for x in lab.GRID:
        point=points[f'{profile}:{x}']
        if 'alias'in point:point=points[point['alias']]
        wins=[r for r in point['outcomes'] if r['win']]
        pp.append(point['metrics']['win']);counts.append(len(wins))
        hp.append([r['hp'] for r in wins]+[0.]*(32-len(wins)))
        exposure.append([r['damage_exposure'] for r in wins]+[1.]*(32-len(wins)))
    return dict(prob=np.array(pp),hp=np.array(hp),exposure=np.array(exposure),count=np.array(counts))


def sample(model,wear,rng):
    grid=np.array(lab.GRID);hi=np.searchsorted(grid,wear,side='right').clip(1,len(grid)-1);lo=hi-1
    t=((wear-grid[lo])/(grid[hi]-grid[lo])).clip(0,1)
    pl=model['prob'][lo];ph=model['prob'][hi];p=(1-t)*pl+t*ph
    choose_high=rng.random(len(wear)) < np.divide(t*ph,p,out=np.zeros_like(p),where=p>0)
    point=np.where(choose_high,hi,lo)
    pos=(rng.random(len(wear))*np.maximum(1,model['count'][point])).astype(int).clip(0,31)
    return p,model['hp'][point,pos],model['exposure'][point,pos]


def simulate_curve(cell,policy,particles=64):
    model=response(cell,policy['profile']);rng=np.random.default_rng(lab.seed('path-fit',cell['key']))
    wear=np.zeros(particles);weights=np.ones(particles);rows=[]
    for battle in range(1,31):
        p,hp,exposure=sample(model,wear,rng);mass=float(weights.sum())
        probability=float(np.dot(weights,p)/mass) if mass>1e-100 else None
        rows.append(dict(battle=battle,conditional_wr=probability,survive_before=mass/particles,
            survive_after=float(np.dot(weights,p)/particles),
            mean_bp_cap=float(np.dot(weights,np.exp(-lab.PROFILES[policy['profile']][0]*wear))/mass) if mass>1e-100 else None,
            out_of_grid_mass=float(weights[wear>lab.GRID[-1]].sum()/particles)))
        pressure=1-hp if policy['signal']=='end_hp' else exposure
        chance=np.minimum(1.,policy['p0']+policy['p_pressure']*pressure)
        severity=policy['loss0']+policy['loss_pressure']*pressure
        add=rng.random(particles)<chance
        wear+=np.where(add,-np.log1p(-severity),0.)
        weights*=p
    return rows


def horizon(rows):
    return next((r['battle'] for r in rows if r['conditional_wr'] is not None and r['conditional_wr']<=.5),31)


def baseline(cell):
    value=cell['result']['points']['bp_only:0']['metrics']
    return value['win'],value['winning_hp']


def evaluate(policy):
    rows=[]
    for cell in load_groups():
        wr,hp=baseline(cell)
        clutch=(wr>0 and hp is not None and hp<=.2)
        dominant=wr>=.95 and not clutch
        if not(dominant or clutch):continue
        trajectory=simulate_curve(cell,policy,64);h=horizon(trajectory)
        # Soft design references, not manufactured pass/failure labels.
        if dominant:loss=((h-24)/12)**2
        else:loss=(max(0,h-3)/5)**2
        rows.append(dict(stage=cell['job']['stage'],kind='dominant' if dominant else 'clutch',
                         horizon=h,loss=loss,baseline_wr=wr,baseline_winning_hp=hp))
    by_stage={}
    for s in range(6):
        kinds=[]
        for kind in ('dominant','clutch'):
            group=[r for r in rows if r['stage']==s and r['kind']==kind]
            if group:kinds.append(sum(r['loss'] for r in group)/len(group))
        by_stage[str(s)]=sum(kinds)/len(kinds) if kinds else 1e6
    return dict(policy=policy,score=sum(by_stage.values())/6,stage_scores=by_stage,
        reference_counts={k:sum(r['kind']==k for r in rows) for k in ('dominant','clutch')},rows=rows)


def candidates():
    return [dict(profile=profile,signal=signal,p0=p0,p_pressure=pp,loss0=l0,loss_pressure=lp)
        for profile,signal,p0,pp,l0,lp in itertools.product(lab.PROFILES,('end_hp','exposure'),
            (.25,.45,.65),(0.,.5),(.025,.05,.08),(.1,.2,.3))]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workers',type=int,default=6);args=p.parse_args()
    paths=[lab.OUT/'curves.json',Path(__file__)]
    extra=lab.OUT/'low_margin/curves.json'
    if extra.exists():paths.append(extra)
    manifest={str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in paths}
    with cf.ProcessPoolExecutor(args.workers) as pool:
        rows=list(pool.map(evaluate,candidates(),chunksize=1))
    best=min(rows,key=lambda r:r['score']);stages={str(s):min(rows,key=lambda r:r['stage_scores'][str(s)])['policy'] for s in range(6)}
    atomic_json(lab.OUT/'policy_search.json',dict(sources=manifest,candidates=rows))
    selected=dict(global_policy=best['policy'],global_fit_score=best['score'],stage_policies=stages,
                  reference_counts=best['reference_counts'],sources=manifest)
    atomic_json(lab.OUT/'selected_policies.json',selected)
    print('policy fitting complete:',len(rows),'candidates;',selected,flush=True)
    predictions=[]
    for cell in load_groups():
        for name,policy in (('global',selected['global_policy']),('stage',selected['stage_policies'][str(cell['job']['stage'])])):
            predictions.append(dict(cell=cell['key'],job=cell['job'],policy_name=name,policy=policy,
                baseline=baseline(cell),trajectory=simulate_curve(cell,policy,512)))
    atomic_json(lab.OUT/'predicted_paths.json',dict(sources=manifest,rows=predictions))


if __name__=='__main__':main()
