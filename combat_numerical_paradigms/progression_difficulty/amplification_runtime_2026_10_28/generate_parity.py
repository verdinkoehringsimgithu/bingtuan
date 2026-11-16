"""Five existing amplification mechanisms over the verified support oracle."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('support_oracle',HERE.parent/'support_runtime_2026_10_28/generate_parity.py')
sup=importlib.util.module_from_spec(spec);sys.modules[spec.name]=sup;spec.loader.exec_module(sup)
ev=sup.ev;native=sup.native


def fighter_factor(team):
    base=native.natural.Team.get_dmg_output_factor(team)
    return team.get_dmg_output_factor()/base if base else 1.


old_make=native.make_action
def make_action(world):
    action=old_make(world)
    def run(a,b,first,turn):
        a._heroine_before=a.metrics['heroine_first'];action(a,b,first,turn)
    return run
native.make_action=make_action
old_post=native.attack.__globals__['post_attack']
def post(a,b,owner,skill,hit):
    old_post(a,b,owner,skill,hit)
    gear=a.items[owner];baseline=1.
    if skill and gear.kind=='skill_damage':baseline=1+gear.value
    elif skill and gear.kind=='cast_ramp':baseline=1+gear.value*(a.casts[owner]-1)
    elif not skill and gear.kind=='normal_damage':baseline=1+gear.value
    sup.TRACE[-1].update(heroineFirst=a.metrics['heroine_first']>a._heroine_before,
        bondDirectMultiplier=a.direct_factor/baseline,bondOutputMultiplier=fighter_factor(a))
native.attack.__globals__['post_attack']=post
namespace=dict(sup.namespace,make_action=make_action,attack=native.attack)
exec(compile(sup.tree,'<amplification-oracle>','exec'),namespace)
simulate=namespace['simulate']


def rules(profile,gain):
    keys=('academy','cult','fighter','heroine','lady')
    d=dict(zip(keys,(profile>=5 or profile==i for i in range(5))))
    d.update(countK=4,gain=gain,teacherExperience=.12,teacherDamage=.0015,cultDamage=.035,fighterPerRound=.025,
             heroinePerLayer=.035,ladyDamage=.25,ladyMembersPerSlot=3)
    return d


def pack(roster):
    members,items=ev.pack(roster)
    for member,row in zip(members,roster):member.level=row['level']
    return members,items


def summary(team):
    c=team.counts;coverage=0
    if team.active('lady'):coverage=min(len(team.members),max(1,__import__('math').ceil(c['淑女']/team.cfg['lady_slots'])))
    return dict(students=c['学生'],teachers=c['老师'],studentLevels=sum(level for m,level in zip(team.members,team.levels) if m.identity=='学生'),
        cultists=c['拜火教'],fighters=c['格斗家'],heroines=c['侠女'],ladies=c['淑女'],coveredPositions=coverage,
        heroineLayers=team.heroine_layers,round=team.turn,fighterMultiplier=fighter_factor(team),
        studentExperienceMultiplier=1+team.cfg['teacher_xp']*c['老师']*team.gain if team.active('academy') else 1.)


def main():
    source=HERE.parent/'runtime_parity_cases.json';fixtures=json.loads(source.read_text(encoding='utf-8-sig'));cases=[]
    patterns=[('老师','学生','学生','老师','学生'),('拜火教','拜火教','拜火教','学生'),('格斗家',),('侠女',),
              ('学生','学生','淑女','淑女','淑女'),('老师','学生','拜火教','格斗家','侠女','淑女','学生'),
              ('老师','学生','拜火教','格斗家','侠女','淑女','学者','剑士','剑士','军人','忍者','水手','行商')]
    for index,base in enumerate(fixtures):
        for profile in range(7):
            fixture=copy.deepcopy(base);ev.CAPACITY=len(fixture['left']);ev.FACTORS=(.7,.7,.8,.5,.9) if profile==6 else (1.,)*5
            gain=2 if profile==6 else 1;amp=rules(profile,gain)
            s=sup.support(profile==6,profile==6,gain);er=ev.evasion(profile==6,profile==6,gain)
            enabled=[name for name in ('academy','cult','fighter','heroine','lady') if amp[name]]
            if profile==6:enabled+=['scholar','sword','military','ninja','sailor','merchant']
            for side in ('left','right'):
                for pos,row in enumerate(fixture[side]):
                    row['traits']=dict(personId=f'parity:{side}:{pos}',identity=patterns[profile][pos%len(patterns[profile])]);row['level']=1+(index+pos)%30
            left,li=pack(fixture['left']);right,ri=pack(fixture['right'])
            cfg=ev.cfg(er);cfg.update(scholar=s['scholarChance'],scholar_restore=s['scholarRestore'],sword=s['swordChance'],sword_decay=s['swordDecay'],sword_extras=s['swordExtras'])
            sup.TRACE.clear();ev.TEAMS.clear()
            result,*_=simulate(left,right,290000+index*10+profile,li,ri,p=fixture.get('macro'),enabled=enabled,enemy_enabled=enabled,
                config=cfg,enemy_config=cfg,max_turns=fixture['rounds'],legacy=True)
            a,b=ev.TEAMS
            for i,row in enumerate(sup.TRACE):
                nxt=sup.TRACE[i+1] if i+1<len(sup.TRACE) else None
                row['hasContinuation']=bool(nxt and nxt['round']==row['round'] and nxt['side']==row['side'] and nxt['chainDepth']==row['chainDepth']+1)
            opening=dict(sailor=profile==6,merchant=profile==6,countK=4,gain=gain,sailorCoefficient=.006,merchantCoefficient=.30)
            cases.append(dict(name=fixture['name']+':amplification-'+str(profile),capacity=ev.CAPACITY,left=fixture['left'],right=fixture['right'],
                leftAmplification=amp,rightAmplification=amp,leftSupport=s,rightSupport=s,leftEvasion=er,rightEvasion=er,leftOpening=opening,rightOpening=opening,
                limits=dict(zip(('bp','courage','resilience','initiative','magic'),ev.FACTORS)),macro=fixture.get('macro'),rounds=fixture['rounds'],
                random=ev.g.tape.values,actions=list(sup.TRACE),hp=result['hp'],enemy_hp=result['enemy_hp'],turns=result['turns'],win=result['win'],censored=result['censored'],draw=result['draw'],
                left_received=a.metrics['damage_received'],right_received=b.metrics['damage_received'],left_min=a.minimum,right_min=b.minimum,
                left_stats=a.get_effective_stats(),right_stats=b.get_effective_stats(),left_uses=[a.usage.get(i,0) for i in range(len(left))],right_uses=[b.usage.get(i,0) for i in range(len(right))],
                left_summary=summary(a),right_summary=summary(b)))
    (HERE/'amplification_cases.json').write_text(json.dumps(cases,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    sources=[source,Path(__file__),Path(sup.__file__),Path(ev.__file__),Path(native.__file__),Path(ev.joint.__file__),Path(ev.g.__file__),Path(ev.g.core.__file__),Path(ev.g.natural_core.__file__),ev.g.core.SOURCE,
             ROOT/'combat_numerical_paradigms/synergy_research/settings.py']
    (HERE/'parity_sources.json').write_text(json.dumps(dict(cases=len(cases),profiles=7,sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}),indent=2),encoding='utf-8')
    print(f'{len(cases)} native amplification fixtures generated')


if __name__=='__main__':main()
