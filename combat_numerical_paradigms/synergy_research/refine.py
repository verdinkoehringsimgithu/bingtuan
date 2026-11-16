"""Validation-only coefficient selection and fresh-roster final confirmation."""
import argparse
from collections import defaultdict
import math

from run_bonds import Runner,atomic_json,count_options,average
from settings import HERE,IDENTITIES
from rosters import GENRES


SPECIAL={
 'sailor':[{'sailor':x} for x in (.03,.06,.12,.24)],
 'engineer':[{'engineer_base':x,'engineer_cast':x*.14} for x in (.25,.5,1.,2.)],
 'scholar':[{'scholar':x} for x in (.3,.6,1.,1.5)],
 'gang':[{'gang':x} for x in (1.3,2.6,5.2,8.)],
 'sword':[{'sword':x,'sword_decay':.5} for x in (.2,.35,.5)],
 'ninja':[{'ninja_base':x,'ninja_cast':x*.2,'ninja_cap':.65} for x in (.04,.08,.12)],
 'rich':[{'rich_dr':x} for x in (.005,.0125,.025)],
 'worker':[{'worker':x} for x in (.1,.2,.35)],
 'hunter':[{'hunter':x} for x in (.15,.35,.65,.9)],
}


def calibration_jobs(trials):
    jobs=[]
    for s in range(6):
        for key in IDENTITIES:
            options=count_options(s,key)
            if not options:continue
            n=5*(s+1)
            valid=[x for x in options if x>=math.ceil(n/2)]
            count=min(valid) if valid else options[-1]
            configs=SPECIAL.get(key,[{'gain':x} for x in (.5,1.,2.)])
            for cfg in configs:
                for g in GENRES:
                    jobs.append(dict(stage=s,genre=g,bond=key,count=count,composition=((key,count),),enabled=(key,),
                                     config=cfg,trials=trials,bank='validation',pool_offset=80000,reference=True))
    return jobs


def select(rows):
    import json
    groups=defaultdict(list)
    for r in rows:groups[(r['stage'],r['bond'],json.dumps(r['config'],sort_keys=True))].append(r)
    candidates=defaultdict(list)
    for (s,key,cfg),rs in groups.items():
        gain=average([r['delta_wr'] for r in rs])
        spread=math.sqrt(average([(r['delta_wr']-gain)**2 for r in rs]))
        censor=average([r['new_censored'] for r in rs])
        # A soft operating budget, not a promised win-rate interval or failure label.
        # Publish results at 5/10/20pp targets so this design preference is visible.
        for target in (.05,.10,.20):
            loss=abs(gain-target)+.20*spread+2*censor
            candidates[(s,key,target)].append(dict(config=json.loads(cfg),calibration_delta=gain,
                                                  flow_sd=spread,censor=censor,loss=loss,count=rs[0]['count']))
    out=[]
    for (s,key,target),rs in candidates.items():
        best=min(rs,key=lambda r:(r['loss'],str(r['config'])))
        out.append(dict(stage=s,bond=key,soft_delta_reference=target,**best))
    return out


def confirmation_jobs(selected,trials):
    jobs=[]
    for row in selected:
        if row['soft_delta_reference']!=.1:continue
        s=row['stage'];key=row['bond'];options=count_options(s,key)
        for count in sorted(set((row['count'],options[-1]))):
            for d in ('hard','extremely_hard'):
                for placement in ('front','back'):
                    for g in GENRES:
                        jobs.append(dict(stage=s,genre=g,bond=key,count=count,composition=((key,count),),enabled=(key,),
                                         config=row['config'],trials=trials,bank='final',pool_offset=90000,
                                         difficulty=d,placement=placement,reference=True))
    return jobs


def main():
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=8)
    p.add_argument('--trials',type=int,default=24);p.add_argument('--confirm-trials',type=int,default=24)
    p.add_argument('--output',type=__import__('pathlib').Path,default=HERE/'results')
    args=p.parse_args();runner=Runner(args.output,args.workers)
    try:
        runner.run('calibration',calibration_jobs(args.trials))
        selected=select(runner.rows('calibration'))
        atomic_json(args.output/'selected_coefficients.json',selected)
        runner.run('confirmation',confirmation_jobs(selected,args.confirm_trials))
    finally:runner.close()


if __name__=='__main__':main()
