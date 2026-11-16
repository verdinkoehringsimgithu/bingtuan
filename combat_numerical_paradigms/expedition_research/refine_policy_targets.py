"""Re-rank saved calibration candidates against the user's explicit horizons.

Only calibration response/particle horizons are read. No held-out journey
outcome, reach rate or loot result is consulted when selecting this revision.
"""
import hashlib
import json
from pathlib import Path

import measure_response as lab
from run_bonds import atomic_json

OUT=lab.OUT/'refined'


def score(row,stage=None):
    losses=[]
    for s in range(6):
        if stage is not None and s!=stage:continue
        for kind in ('dominant','clutch'):
            values=[r['horizon'] for r in row['rows'] if r['stage']==s and r['kind']==kind]
            if not values:continue
            if kind=='dominant':
                loss=sum(10*(h>30)+((h-24)/24)**2+(max(0,10-h)/10)**2 for h in values)/len(values)
            else:loss=sum(10*(h>3)+(max(0,h-3)/5)**2 for h in values)/len(values)
            losses.append(loss)
    return sum(losses)/len(losses)


def main():
    source=lab.OUT/'policy_search.json';data=json.loads(source.read_text(encoding='utf-8'))
    for path,digest in data['sources'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
    candidates=data['candidates'];best=min(candidates,key=score)
    stages={str(s):min(candidates,key=lambda r:score(r,s))['policy'] for s in range(6)}
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'low_margin').mkdir(exist_ok=True)
    for name in ('regions.json','low_margin/regions.json'):
        (OUT/name).write_bytes((lab.OUT/name).read_bytes())
    paths=[Path(__file__),source,lab.HERE/'confirm_refined.py']
    sources={**data['sources'],**{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
    selected=dict(global_policy=best['policy'],global_fit_score=score(best),stage_policies=stages,
        sources=sources,reference_counts=best['reference_counts'],selection_scope='saved calibration candidates only',
        objective='prioritize <=30 dominant / <=3 low-winning-margin; then prefer a moderate dominant cadence')
    atomic_json(OUT/'selected_policies.json',selected)
    atomic_json(OUT/'selection_evidence.json',dict(global_candidate=best,
        stage_candidates={str(s):min(candidates,key=lambda r:score(r,s)) for s in range(6)}))
    print('refined policy selection:',selected,flush=True)


if __name__=='__main__':main()
