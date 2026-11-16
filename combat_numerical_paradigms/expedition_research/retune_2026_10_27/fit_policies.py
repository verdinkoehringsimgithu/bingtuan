"""Propose stage wear policies from frozen mixed-bond response curves."""
import concurrent.futures as cf
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'continuation_2026_10_27'))
import study_closure as old
from audit_research import check_manifest
from run_bonds import atomic_json
import numpy as np

OUT=HERE/'results'
_MODELS=None


def load_models():
    global _MODELS
    if _MODELS is not None:return _MODELS
    data=json.loads((old.OUT/'summary.json').read_text(encoding='utf-8'))
    models=[]
    for cell in data['rows']:
        if cell['result']['baseline_wr']<.95:continue
        with gzip.open(old.OUT/'replicates'/(cell['key']+'.json.gz'),'rt',encoding='utf-8') as f:raw=json.load(f)
        ps=[];ex=[];counts=[]
        for x in old.GRID:
            rr=raw['prepared'][str(x)]['trials'];wins=[r for r in rr if r['win']]
            ps.append(len(wins)/len(rr));counts.append(len(wins))
            ex.append([r['damage_exposure'] for r in wins]+[1.]*(96-len(wins)))
        models.append(dict(stage=cell['job']['stage'],key=cell['key'],p=ps,ex=ex,count=counts))
    _MODELS=models;return models


def paths(models,policy,particles=96):
    # Vectorization across fixed reference configurations. Counterpart
    # policies share random draws; only calibration observations enter.
    grid=np.array(old.GRID);m=len(models);p_table=np.array([r['p'] for r in models])
    exposure=np.array([r['ex'] for r in models]);counts=np.array([r['count'] for r in models])
    rng=np.random.default_rng(202610271);wear=np.zeros((m,particles));weights=np.ones((m,particles))
    rows=[];ar=np.arange(m)[:,None]
    for node in range(1,31):
        hi=np.searchsorted(grid,wear,side='right').clip(1,len(grid)-1);lo=hi-1
        t=((wear-grid[lo])/(grid[hi]-grid[lo])).clip(0,1)
        low=p_table[ar,lo];high=p_table[ar,hi];prob=(1-t)*low+t*high
        mass=weights.sum(axis=1)
        q=np.divide((weights*prob).sum(axis=1),mass,out=np.zeros(m),where=mass>1e-100)
        rows.append(dict(battle=node,conditional_wr=q.copy(),survive_after=(weights*prob).mean(axis=1)))
        choose=rng.random((m,particles))<np.divide(t*high,prob,out=np.zeros_like(prob),where=prob>0)
        point=np.where(choose,hi,lo);pos=(rng.random((m,particles))*np.maximum(1,counts[ar,point])).astype(int).clip(0,95)
        pressure=exposure[ar,point,pos]
        trigger=rng.random((m,particles))<policy['p']
        wear+=np.where(trigger,-np.log1p(-(policy['l0']+policy['l1']*pressure)),0.)
        weights*=prob
    return rows


def evaluate(policy):
    models=load_models();rows=paths(models,policy)
    stages={}
    for s in range(6):
        indices=[i for i,r in enumerate(models) if r['stage']==s]
        reference=[]
        for i in indices:
            wr=models[i]['p'][0];control=wr**6;s6=rows[5]['survive_after'][i]
            retain=s6/control if control else 0
            half=next((r['battle'] for r in rows if r['conditional_wr'][i]<=.5),31)
            tail=rows[-1]['conditional_wr'][i]
            loss_risk=(max(0.,.9-retain)/.1)**2
            loss_tail=(max(0.,tail-.5)/.25)**2
            loss_early=(max(0.,12-half)/12)**2
            preference=.1*((min(half,31)-24)/24)**2
            reference.append(dict(key=models[i]['key'],retain6=float(retain),s6=float(s6),half=half,
                wr30=float(tail),loss_risk=loss_risk,loss_tail=loss_tail,loss_early=loss_early,preference=preference))
        stages[str(s)]=dict(cases=len(reference),score=sum(r['loss_risk']+r['loss_tail']+r['loss_early']+r['preference'] for r in reference)/len(reference),
            mean_retain6=sum(r['retain6'] for r in reference)/len(reference),
            mean_s6=sum(r['s6'] for r in reference)/len(reference),
            within30=sum(r['half']<=30 for r in reference)/len(reference),
            mean_wr30=sum(r['wr30'] for r in reference)/len(reference),references=reference)
    return dict(policy=policy,stages=stages)


def main():
    OUT.mkdir(parents=True,exist_ok=True);manifest=check_manifest(old.OUT/'manifest.json')
    paths=[Path(__file__),old.OUT/'summary.json',HERE/'PROTOCOL.md']
    body=dict(parent_signature=manifest['signature'],sources={**manifest['sources'],
        **{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}})
    signature=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()
    atomic_json(OUT/'fit_manifest.json',dict(signature=signature,**body))
    policies=[dict(p=p,l0=l0,l1=l1) for p,l0,l1 in itertools.product((.35,.5,.65),
        (.0025,.005,.01,.02,.04,.08),(.025,.05,.1,.2))]
    with cf.ProcessPoolExecutor(6) as pool:
        answers=[]
        for i,r in enumerate(pool.map(evaluate,policies,chunksize=1),1):
            answers.append(r)
            if i%12==0:print('fit',i,'/72',flush=True)
    selected={str(s):min(answers,key=lambda r:(r['stages'][str(s)]['score'],r['policy']['l0'],r['policy']['l1']))['policy'] for s in range(6)}
    atomic_json(OUT/'calibration.json',dict(signature=signature,candidates=answers))
    atomic_json(OUT/'selected.json',dict(signature=signature,stage_policies=selected,
        calibration_sha256=hashlib.sha256((OUT/'calibration.json').read_bytes()).hexdigest(),
        selection_scope='calibration only; no fresh confirmation used'))
    print(json.dumps(selected),flush=True)


if __name__=='__main__':main()
