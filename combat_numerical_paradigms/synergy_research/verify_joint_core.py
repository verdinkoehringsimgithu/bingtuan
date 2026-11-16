"""Verify the equipment-base correction without changing frozen combat paths."""
import copy
from pathlib import Path

import bond_core as old
import joint_core as new
from rosters import build, GENRES, STAGES, natural
from run_bonds import atomic_json
from settings import HERE


def main():
    exact=0;opening=0;deferred=0
    for s in range(6):
        for g in GENRES:
            mm,items=build(s,g,230000,(('engineer',2),),'front','final')
            enemy,ei=build(s,g,330003,(),'front','final')
            owner=list(items);item=owner[0]
            owner[0]=natural.Item('owner_stats',.5,item.stats,item.bp,True);owner=tuple(owner)
            for gear,active in ((items,()),(items,('engineer',)),(owner,()),(owner,('sailor',))):
                a,*_=old.simulate(mm,enemy,101+s,gear,ei,enabled=active)
                b,*_=new.simulate(mm,enemy,101+s,gear,ei,enabled=active)
                assert a==b,(s,g,active);exact+=1
            world=old.World(31);base=new.Team(mm,owner,0,world)
            enhanced=new.Team(mm,owner,0,world,('engineer',))
            q=enhanced.q('工程师')
            actual=[sum(it.stats[k]+(m.stats[k]*it.value if it.kind=='owner_stats' else 0.) for m,it in zip(mm,owner)) for k in range(4)]
            for k,f in enumerate(old.ATTRS):
                assert abs(enhanced.gear_stats[k]-actual[k])<1e-10
                delta=getattr(enhanced,'cur_'+f)-getattr(base,'cur_'+f)
                assert abs(delta-actual[k]*.25*q)<1e-9;opening+=1
            previous=[getattr(enhanced,'cur_'+f) for f in old.ATTRS]
            enhanced.pending_engineer=.035*q
            assert previous==[getattr(enhanced,'cur_'+f) for f in old.ATTRS]
            enhanced.round_commit()
            for k,f in enumerate(old.ATTRS):
                assert abs(getattr(enhanced,'cur_'+f)-previous[k]-actual[k]*.035*q)<1e-9;deferred+=1
            assert enhanced.pending_engineer==0.
    result=dict(status='passed',exact_unchanged_path_battles=exact,opening_stat_checks=opening,deferred_stat_checks=deferred,
                scope='engineer counts actual equipment four-stat contributions; all other effects unchanged')
    atomic_json(HERE/'results/joint_core_validation.json',result)
    print(result)


if __name__=='__main__':main()
