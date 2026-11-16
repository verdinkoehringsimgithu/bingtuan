"""Opening-bond numerical parity, not a new balance study.

Use the existing joint research Team as the opening-stat oracle, then run the
unchanged native action pipeline with shared sequential RNG tapes.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OLD=HERE.parent/'expedition_runtime_2026_10_27'
sys.path.insert(0,str(OLD))
import generate_limited_parity as g
sys.path.insert(0,str(ROOT/'combat_numerical_paradigms/synergy_research'))
import joint_core as oracle
from settings import DEFAULTS

CONFIGS=None
FACTORS=(1.,)*5
TEAMS=[]


class OpeningTeam(g.core.Team):
    def __init__(self,*args,**kwargs):
        self.factors=(1.,)*5
        self.minimum=1.
        self.opening_stats=None
        super().__init__(*args,**kwargs)
        side=0 if self.name=='player' else 1
        rules=CONFIGS[side]
        enabled=tuple(key for key in ('sailor','merchant') if rules.get(key))
        cfg=dict(count_k=rules['countK'],gain=rules['gain'],sailor=rules['sailorCoefficient'],merchant=rules['merchantCoefficient'])
        reference=oracle.Team(self.members,self.items,side,oracle.frozen.World(0),enabled,cfg)
        self.opening_stats=tuple(getattr(reference,'cur_'+axis) for axis in g.core.FIELDS)
        # Treat the oracle's opening result as this battle's initial budget. In
        # particular, native macro() must not revert the enemy's sailor initiative.
        for axis,value in zip(g.core.FIELDS,self.opening_stats):
            setattr(self,'cur_'+axis,value)
            setattr(self,'base_'+axis,value)
        if side==0:
            self.factors=FACTORS
            self.max_bp*=FACTORS[0]
            self.current_bp=self.max_bp
        TEAMS.append(self)

    def reset(self):
        super().reset()
        if self.opening_stats is not None:
            for axis,value in zip(g.core.FIELDS,self.opening_stats):setattr(self,'cur_'+axis,value)

    def get_effective_stats(self):
        return tuple(value*factor for value,factor in zip(super().get_effective_stats(),self.factors[1:]))

    def add(self,key,value):
        super().add(key,value)
        if key=='damage_received':self.minimum=min(self.minimum,max(0.,self.current_bp)/self.max_bp)


g.namespace['Team']=OpeningTeam


def rules(sailor=False,merchant=False,gain=1.):
    return dict(sailor=sailor,merchant=merchant,countK=DEFAULTS['count_k'],gain=gain,
                sailorCoefficient=DEFAULTS['sailor'],merchantCoefficient=DEFAULTS['merchant'])


def pack(roster):
    members,items=g.unpack(roster)
    for member,source in zip(members,roster):member.identity=source['traits']['identity']
    return members,items


def main():
    global CONFIGS,FACTORS
    source=HERE.parent/'runtime_parity_cases.json'
    fixtures=json.loads(source.read_text(encoding='utf-8-sig'))
    profiles=((rules(True),rules(),(1.,)*5),(rules(merchant=True),rules(),(1.,)*5),
              (rules(True,True),rules(merchant=True),(1.,)*5),
              (rules(True,True,.5),rules(True,True),(.6,.7,.8,.5,.9)))
    results=[]
    for index,fixture in enumerate(fixtures):
        fixture=copy.deepcopy(fixture)
        for side in ('left','right'):
            for pos,member in enumerate(fixture[side]):
                # Controlled mechanism fixtures; original stats/skills/equipment are untouched.
                member['traits']=dict(personId=f'parity:{side}:{pos}',identity=('水手','行商','学生','老师')[pos%4])
        left,left_items=pack(fixture['left']);right,right_items=pack(fixture['right'])
        for profile,(left_rules,right_rules,FACTORS) in enumerate(profiles):
            CONFIGS=(left_rules,right_rules);TEAMS.clear()
            result,*_=g.simulate(left,right,280000+index*10+profile,left_items,right_items,
                                p=fixture.get('macro'),max_turns=fixture['rounds'])
            a,b=TEAMS
            results.append(dict(name=fixture['name']+':opening-'+str(profile),left=fixture['left'],right=fixture['right'],
                limits=dict(zip(('bp','courage','resilience','initiative','magic'),FACTORS)),leftRules=left_rules,rightRules=right_rules,
                macro=fixture.get('macro'),rounds=fixture['rounds'],random=g.tape.values,
                hp=result['hp'],enemy_hp=result['enemy_hp'],turns=result['turns'],win=result['win'],censored=result['censored'],draw=result['draw'],
                left_received=a.metrics['damage_received'],right_received=b.metrics['damage_received'],left_min=a.minimum,right_min=b.minimum,
                left_stats=a.get_effective_stats(),right_stats=b.get_effective_stats(),
                left_uses=[a.usage.get(i,0) for i in range(len(left))],right_uses=[b.usage.get(i,0) for i in range(len(right))]))
    (HERE/'opening_cases.json').write_text(json.dumps(results,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    sources=[source,Path(__file__),Path(g.__file__),Path(oracle.__file__),Path(oracle.frozen.__file__),
             ROOT/'combat_numerical_paradigms/synergy_research/settings.py',Path(g.core.__file__),Path(g.natural_core.__file__),g.core.SOURCE]
    (HERE/'parity_sources.json').write_text(json.dumps(dict(cases=len(results),profiles=profiles,
        oracle='Existing joint_core.Team constructor, only sailor/merchant enabled',
        sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}),indent=2),encoding='utf-8')
    print(f'{len(results)} opening-bond native fixtures generated')


if __name__=='__main__':main()
