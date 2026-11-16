"""Independent small-group supply experiments versus unrestricted rosters."""
import argparse
import concurrent.futures as cf
import hashlib
import json
from pathlib import Path

from run_bonds import atomic_json,average
from rosters import build,encounter,seed
from bond_core import simulate
from settings import HERE


def evaluate(job):
    s=job['stage'];g=job['genre'];h,p=encounter(s,'extremely_hard');wins=[]
    for j in range(job['trials']):
        pool=job['offset']+j
        m,it=build(s,g,pool,(),'front',job['bank'])
        e,ei=build(s,h,pool+100003,(),'front',job['bank'])
        r,*_=simulate(m,e,seed('supply-independent',s,g,pool),it,ei,p=p)
        wins.append(r['win'])
    return dict(stage=s,genre=g,reference_wr=average(wins),trials=job['trials'])


def main():
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=4);args=p.parse_args()
    out=HERE/'results';source=out/'skill_supply_confirmation.json'
    rows=json.loads(source.read_text(encoding='utf-8'))
    jobs={}
    for row in rows:
        job={k:row[k] for k in ('stage','genre','offset','bank','trials')}
        jobs[(job['stage'],job['genre'])]=job
    with cf.ProcessPoolExecutor(args.workers) as pool:reference=list(pool.map(evaluate,jobs.values()))
    refs={(r['stage'],r['genre']):r['reference_wr'] for r in reference}
    result=[]
    for row in rows:
        r=refs[(row['stage'],row['genre'])]
        result.append(dict(stage=row['stage'],bond=row['bond'],genre=row['genre'],count=row['count'],policy=row['policy'],
                           reference_wr=r,random_off=row['random_off'],random_on=row['random_on'],policy_on=row['policy_on'],
                           composition_delta=row['random_off']-r,small_group_total_delta=row['random_on']-r,
                           supply_and_order_total_delta=row['policy_on']-r,trials=row['trials']))
    atomic_json(out/'small_group_composition.json',result)
    atomic_json(out/'small_group_manifest.json',dict(reference_battle_executions=sum(j['trials'] for j in jobs.values()),
                 source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 reference_reused_across_identities=True))
    print(f"Small-group reference: {sum(j['trials'] for j in jobs.values())} battles",flush=True)


if __name__=='__main__':main()
