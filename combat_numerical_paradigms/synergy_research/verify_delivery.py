"""Validate only completed current-signature results, with no invented totals."""
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3

import pandas as pd
import numpy as np

from settings import HERE,ROOT,IDENTITIES
from run_bonds import screen_jobs,holdout_jobs,pair_jobs,robustness_jobs,variants_jobs
from refine import calibration_jobs,confirmation_jobs


def main():
    out=HERE/'results';manifest=json.loads((out/'input_manifest.json').read_text(encoding='utf-8'))
    checks=0
    def require(ok,message):
        nonlocal checks
        if not ok:raise AssertionError(message)
        checks+=1
    for name,digest in manifest['sources'].items():require(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,'Input changed: '+name)
    selected=json.loads((out/'selected_coefficients.json').read_text(encoding='utf-8'))
    expected=dict(screen=len(screen_jobs(6)),holdout=len(holdout_jobs(24)),pairs=len(pair_jobs(4)),
                  robustness=len(robustness_jobs(16)),variants=len(variants_jobs(16)),
                  calibration=len(calibration_jobs(24)),confirmation=len(confirmation_jobs(selected,24)))
    db=sqlite3.connect(out/'checkpoints.sqlite');totals={};trace_count=0
    for phase,count in expected.items():
        rows=db.execute('SELECT key,job,result FROM cells WHERE phase=? AND signature=?',(phase,manifest['signature'])).fetchall()
        require(len(rows)==count,f'Incomplete {phase}: {len(rows)}/{count}')
        totals[phase]=0
        for key,job,result in rows:
            j=json.loads(job);r=json.loads(result)
            require(all(np.isfinite(v) for v in r.values() if isinstance(v,(int,float))),f'Nonfinite {key}')
            require(0<=r['base_win']<=1 and 0<=r['new_win']<=1,f'Invalid wins {key}')
            require(r['new_m_max_chain']<=3,f'Extra chain exceeds cap {key}')
            require(r['new_m_hunter_true']<=r['new_m_hunter_scheduled']+1e-6,f'Hunter damage exceeds scheduled amount {key}')
            path=out/'replicates'/(key+'.json.gz')
            require(path.exists(),f'Missing raw trial file {key}')
            # Every raw pair is retained; check contents on a reproducible sample.
            if int(key[:4],16)%37==0:
                with gzip.open(path,'rt',encoding='utf-8') as f:replicates=json.load(f)
                require(len(replicates)==j['trials'],f'Raw row count mismatch {key}')
                require(abs(np.mean([x['new_win']-x['base_win'] for x in replicates])-r['delta_wr'])<1e-12,f'Raw delta mismatch {key}')
            if r['trace_battles']:
                path=out/'telemetry'/(key+'.json.gz');require(path.exists(),f'Missing temporal file {key}')
            trace_count+=r['trace_battles'];totals[phase]+=r['executed_battles']
    require(trace_count>=10000,'Insufficient temporal battles')
    frame=pd.read_csv(out/'confirmation_by_stage_identity.csv')
    require(len(frame)==137,'Expected 23 identities × six stages minus unavailable S1 sage')
    require(set(frame.bond)==set(IDENTITIES),'Missing identity specification')
    require(set(frame.stage)==set(range(6)),'Missing stage')
    pca=pd.read_csv(out/'pca_summary.csv');require(len(pca)==6,'Missing PCA stage')
    require(int(pca.battles.sum())==sum(json.loads(x[0])['trace_battles'] for x in db.execute('SELECT result FROM cells WHERE phase=? AND signature=?',('holdout',manifest['signature']))),'PCA battle count mismatch')
    for stage in range(1,7):require((HERE/'stage_guides'/f'S{stage}_{stage*5}_MEMBERS.md').exists(),'Missing stage guide')
    supply=json.loads((out/'skill_supply_execution_summary.json').read_text(encoding='utf-8'))
    require(supply['combat_signature']==manifest['signature'],'Skill study uses a different numerical model')
    supply_frame=pd.read_csv(out/'identity_only_skill_supply.csv')
    require(len(supply_frame)==137,'Missing isolated skill supply stage/identity')
    small=json.loads((out/'small_group_manifest.json').read_text(encoding='utf-8'))
    require(small['source_sha256']==hashlib.sha256((out/'skill_supply_confirmation.json').read_bytes()).hexdigest(),'Small-group reference mismatch')
    for name in ('stage_effect_heatmap.png','count_response.png','skill_supply_response.png','recommended_design.json',
                 'pca_variance.csv','pca_loadings.csv','cluster_centroids.csv','feature_outcome_correlation.csv'):
        require((out/name).exists(),'Missing artifact '+name)
    verification=json.loads((out/'verification.json').read_text(encoding='utf-8'))
    require(verification['passed'] and verification['checks']>=880,'Behaviour verification incomplete')
    answer=dict(passed=True,checks=checks,behaviour_checks=verification['checks'],phase_battle_executions=totals,
                skill_supply_battle_executions=supply['battle_executions'],
                small_group_reference_battle_executions=small['reference_battle_executions'],
                total_research_battle_executions=sum(totals.values())+supply['battle_executions']+small['reference_battle_executions'],
                temporal_battles=trace_count,input_signature=manifest['signature'])
    (out/'delivery_validation.json').write_text(json.dumps(answer,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(answer,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
