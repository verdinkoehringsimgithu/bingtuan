"""Military/ninja parity against the existing research action implementation.

Only adapt stage capacity, preserve opening initiative under macro, and install
the same sequential tape protocol as production. Frozen research files stay unchanged.
"""
import copy
import hashlib
import inspect
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/'expedition_runtime_2026_10_27'))
import generate_limited_parity as g
sys.path.insert(0,str(ROOT/'combat_numerical_paradigms/synergy_research'))
import joint_core as joint
import bond_core as native
from settings import DEFAULTS

native.random=g.tape
select_namespace=dict(vars(native))
select_source=inspect.getsource(native.select).replace("ratio=team.counts['军人']/len(team.members)","ratio=team.counts['军人']/team.member_capacity")
exec(compile(select_source,'<stage-capacity-selection>','exec'),select_namespace)
native.select=select_namespace['select']
FACTORS=(1.,)*5
CAPACITY=5
TRACE=[]
TEAMS=[]


class Team(joint.Team):
    def __init__(self,*args,**kwargs):
        self.member_capacity=CAPACITY
        self.factors=(1.,)*5
        self.minimum=1.
        self._absolute=False
        super().__init__(*args,**kwargs)
        # Opening effects become this battle's initial budget; macro must retain them.
        for axis in g.core.FIELDS:setattr(self,'base_'+axis,getattr(self,'cur_'+axis))
        if self.side==0:
            self.factors=FACTORS;self.max_bp*=FACTORS[0];self.current_bp=self.max_bp
        TEAMS.append(self)

    def get_effective_stats(self):
        return tuple(value*factor for value,factor in zip(super().get_effective_stats(),self.factors[1:]))

    def add(self,key,value):
        super().add(key,value)
        if key=='damage_received':self.minimum=min(self.minimum,max(0.,self.current_bp)/self.max_bp)


old_absolute=native.absolute_miss
def absolute(a,b):
    result=old_absolute(a,b);a._absolute=result;return result
native.absolute_miss=absolute
old_make=native.make_action
def make_action(world):
    action=old_make(world)
    def run(a,b,first,turn):
        a._absolute=False;a._critical_before=a.metrics['crit_hits'];action(a,b,first,turn)
    return run
native.make_action=make_action
old_post=native.post_attack
def post(a,b,owner,skill,hit):
    old_post(a,b,owner,skill,hit)
    TRACE.append(dict(round=a.turn,side=a.side,owner=owner,normal=not skill,critical=a.metrics['crit_hits']>a._critical_before,
        missed=not hit,forcedHit=a.force_hit,absoluteEvaded=a._absolute,index=len(g.tape.values)))
native.post_attack=post
namespace=dict(vars(native),Team=Team)
exec(compile(inspect.getsource(native.simulate),'<evasion-parity-battle>','exec'),namespace)
simulate=namespace['simulate']


def evasion(military=False,ninja=False,gain=1):
    return dict(military=military,ninja=ninja,gain=gain,countK=DEFAULTS['count_k'],militaryHit=DEFAULTS['military_hit'],
                ninjaBase=DEFAULTS['ninja_base'],ninjaCast=DEFAULTS['ninja_cast'],ninjaCap=DEFAULTS['ninja_cap'])


def cfg(evasion):
    return dict(gain=evasion['gain'],count_k=evasion['countK'],military_hit=evasion['militaryHit'],
                ninja_base=evasion['ninjaBase'],ninja_cast=evasion['ninjaCast'],ninja_cap=evasion['ninjaCap'])


def pack(roster):
    members,items=g.unpack(roster)
    for member,row in zip(members,roster):member.identity=row['traits']['identity']
    return members,items


def summary(team):
    return dict(forcedHits=int(team.metrics['force_hit']),absoluteDodges=int(team.metrics['absolute_dodges']),
                ninjaSkillCasts=int(team.metrics['ninja_casts']),ninjaGrowth=team.ninja_growth,pendingNinja=team.pending_ninja)


def main():
    global CAPACITY,FACTORS
    source=HERE.parent/'runtime_parity_cases.json'
    fixtures=json.loads(source.read_text(encoding='utf-8-sig'))
    cases=[]
    for index,base in enumerate(fixtures):
        for profile in range(5):
            fixture=copy.deepcopy(base);CAPACITY=len(fixture['left']);FACTORS=(.6,.7,.8,.5,.9) if profile==4 else (1.,)*5
            left_rules=evasion(military=profile!=1,ninja=profile>=2)
            right_rules=evasion(military=profile==2,ninja=True)
            if profile==3:fixture['left']=fixture['left'][:max(1,(CAPACITY-1)//2)]
            for side in ('left','right'):
                for pos,row in enumerate(fixture[side]):
                    if profile<=1 or profile==3:identity='军人' if side=='left' else '忍者'
                    elif profile==2:identity=('军人','军人','军人','忍者','忍者')[pos%5]
                    else:identity=('军人','军人','军人','军人','忍者','水手','行商')[pos%7]
                    row['traits']=dict(personId=f'parity:{side}:{pos}',identity=identity)
            left,li=pack(fixture['left']);right,ri=pack(fixture['right'])
            enabled=['military'] if left_rules['military'] else []
            if left_rules['ninja']:enabled.append('ninja')
            enemy_enabled=['ninja']
            if right_rules['military']:enemy_enabled.append('military')
            opening=dict(sailor=profile==4,merchant=profile==4,countK=4,gain=1,sailorCoefficient=.006,merchantCoefficient=.30)
            if profile==4:enabled+=['sailor','merchant'];enemy_enabled+=['sailor','merchant']
            TRACE.clear();TEAMS.clear()
            result,*_=simulate(left,right,288000+index*10+profile,li,ri,p=fixture.get('macro'),enabled=enabled,enemy_enabled=enemy_enabled,
                               config=cfg(left_rules),enemy_config=cfg(right_rules),max_turns=fixture['rounds'],legacy=True)
            a,b=TEAMS
            cases.append(dict(name=fixture['name']+':evasion-'+str(profile),capacity=CAPACITY,
                left=fixture['left'],right=fixture['right'],leftEvasion=left_rules,rightEvasion=right_rules,leftOpening=opening,rightOpening=opening,
                limits=dict(zip(('bp','courage','resilience','initiative','magic'),FACTORS)),macro=fixture.get('macro'),rounds=fixture['rounds'],
                random=g.tape.values,actions=list(TRACE),hp=result['hp'],enemy_hp=result['enemy_hp'],turns=result['turns'],win=result['win'],
                censored=result['censored'],draw=result['draw'],left_received=a.metrics['damage_received'],right_received=b.metrics['damage_received'],
                left_min=a.minimum,right_min=b.minimum,left_stats=a.get_effective_stats(),right_stats=b.get_effective_stats(),
                left_uses=[a.usage.get(i,0) for i in range(len(left))],right_uses=[b.usage.get(i,0) for i in range(len(right))],
                left_summary=summary(a),right_summary=summary(b)))
    (HERE/'evasion_cases.json').write_text(json.dumps(cases,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    sources=[source,Path(__file__),Path(g.__file__),Path(joint.__file__),Path(native.__file__),Path(g.core.__file__),Path(g.natural_core.__file__),g.core.SOURCE,
             ROOT/'combat_numerical_paradigms/synergy_research/settings.py']
    (HERE/'parity_sources.json').write_text(json.dumps(dict(cases=len(cases),profiles=5,
        sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        adaptations=['military denominator uses stage capacity','opening initiative survives macro','shared sequential RNG tape']),indent=2),encoding='utf-8')
    print(f'{len(cases)} native military/ninja fixtures generated')


if __name__=='__main__':main()
