"""Four augmentation mechanisms over the verified eleven-mechanism oracle.

Research sources stay frozen. Only the prevented-healing telemetry is corrected
to use the actual current-BP recovery request, matching the unchanged physics.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('amplification_oracle',HERE.parent/'amplification_runtime_2026_10_28/generate_parity.py')
amp=importlib.util.module_from_spec(spec);sys.modules[spec.name]=amp;spec.loader.exec_module(amp)
sup=amp.sup;ev=amp.ev;native=amp.native


class Team(sup.Team):
    def __init__(self,*args,**kwargs):
        self.augmentation_stolen=[0.]*4
        super().__init__(*args,**kwargs)

    def heal(self,amount):
        before=self.metrics['killer_healing_prevented'] if self._base_ready else 0
        ratio=self.current_bp/self.max_bp if self._base_ready else 1
        selected=getattr(self,'selected_original',None)
        current_basis=self._base_ready and self.heal_channel=='self_heal' and selected is not None and selected.sub_effect_name=='当前战力自愈'
        result=super().heal(amount)
        if current_basis:
            delta=self.metrics['killer_healing_prevented']-before
            self.add('killer_healing_prevented',delta*(ratio-1))
        return result


old_make=amp.make_action
def make_action(world):
    action=old_make(world)
    def run(a,b,first,turn):
        a._prevented_before=a.metrics['killer_healing_prevented'];action(a,b,first,turn)
    return run


old_post=native.attack.__globals__['post_attack']
def post(a,b,owner,skill,hit):
    pending=a.pending_engineer;stats=[getattr(a,'cur_'+axis) for axis in native.ATTRS];marks=a.metrics['killer_marks']
    old_post(a,b,owner,skill,hit)
    stolen=None
    if a.active('thief') and a.members[owner].identity=='盗贼':
        stolen=[getattr(a,'cur_'+axis)-value for axis,value in zip(native.ATTRS,stats)]
        a.augmentation_stolen=[x+y for x,y in zip(a.augmentation_stolen,stolen)]
        a.add('augmentation_thief_attacks',1)
    sup.TRACE[-1].update(engineerQueued=a.pending_engineer-pending,appliedHealPenalty=1-a.recovery_factor,
        healingPrevented=a.metrics['killer_healing_prevented']-a._prevented_before,stolenStats=stolen,killerMarked=a.metrics['killer_marks']>marks)
native.attack.__globals__['post_attack']=post
namespace=dict(amp.namespace,Team=Team,make_action=make_action,attack=native.attack)
exec(compile(sup.tree,'<augmentation-oracle>','exec'),namespace)
simulate=namespace['simulate']


def rules(profile,gain):
    keys=('engineer','sage','thief','killer')
    d=dict(zip(keys,(profile>=4 or profile==i for i in range(4))))
    d.update(countK=4,gain=gain,engineerBase=.25,engineerCast=.035,sageOut=.25,sageIn=.25,thiefRate=.015,killerReduction=.60)
    return d


def summary(team):
    c=team.counts
    return dict(engineers=c['工程师'],sages=c['贤者'],thieves=c['盗贼'],killers=c['杀手'],
        engineerSkillCasts=int(team.metrics['engineer_casts']),thiefAttacks=int(team.metrics['augmentation_thief_attacks']),killerMarks=int(team.metrics['killer_marks']),
        engineerMultiplier=1+(team.v('engineer_base','工程师') if team.active('engineer') else 0)+team.engineer_growth,
        engineerGrowth=team.engineer_growth,pendingEngineer=team.pending_engineer,pendingHealPenalty=team.next_heal_penalty,
        healingPrevented=team.metrics['killer_healing_prevented'],gearStats=team.gear_stats,stolenStats=team.augmentation_stolen)


def main():
    source=HERE.parent/'runtime_parity_cases.json';fixtures=json.loads(source.read_text(encoding='utf-8-sig'));cases=[]
    patterns=[('工程师',),('贤者',),('盗贼',),('杀手',),('工程师','贤者','盗贼','杀手'),
        ('工程师','贤者','盗贼','杀手','老师','学生','拜火教','格斗家','侠女','淑女','学者','剑士','剑士','军人','忍者','水手','行商')]
    for index,base in enumerate(fixtures):
        for profile in range(6):
            fixture=copy.deepcopy(base);ev.CAPACITY=len(fixture['left']);ev.FACTORS=(.7,.7,.8,.5,.9) if profile==5 else (1.,)*5
            gain=2 if profile==5 else 1;aug=rules(profile,gain);am=amp.rules(6 if profile==5 else -1,gain)
            s=sup.support(profile==5,profile==5,gain);er=ev.evasion(profile==5,profile==5,gain)
            enabled=[name for name in ('engineer','sage','thief','killer') if aug[name]]
            if profile==5:enabled+=['academy','cult','fighter','heroine','lady','scholar','sword','military','ninja','sailor','merchant']
            for side in ('left','right'):
                for pos,row in enumerate(fixture[side]):
                    row['traits']=dict(personId=f'parity:{side}:{pos}',identity=patterns[profile][pos%len(patterns[profile])]);row['level']=1+(index+pos)%30
            left,li=amp.pack(fixture['left']);right,ri=amp.pack(fixture['right'])
            cfg=ev.cfg(er);cfg.update(scholar=s['scholarChance'],scholar_restore=s['scholarRestore'],sword=s['swordChance'],sword_decay=s['swordDecay'],sword_extras=s['swordExtras'])
            sup.TRACE.clear();ev.TEAMS.clear()
            result,*_=simulate(left,right,291000+index*10+profile,li,ri,p=fixture.get('macro'),enabled=enabled,enemy_enabled=enabled,
                config=cfg,enemy_config=cfg,max_turns=fixture['rounds'],legacy=True)
            a,b=ev.TEAMS
            for i,row in enumerate(sup.TRACE):
                nxt=sup.TRACE[i+1] if i+1<len(sup.TRACE) else None
                row['hasContinuation']=bool(nxt and nxt['round']==row['round'] and nxt['side']==row['side'] and nxt['chainDepth']==row['chainDepth']+1)
            opening=dict(sailor=profile==5,merchant=profile==5,countK=4,gain=gain,sailorCoefficient=.006,merchantCoefficient=.30)
            cases.append(dict(name=fixture['name']+':augmentation-'+str(profile),capacity=ev.CAPACITY,left=fixture['left'],right=fixture['right'],
                leftAugmentation=aug,rightAugmentation=aug,leftAmplification=am,rightAmplification=am,leftSupport=s,rightSupport=s,leftEvasion=er,rightEvasion=er,leftOpening=opening,rightOpening=opening,
                limits=dict(zip(('bp','courage','resilience','initiative','magic'),ev.FACTORS)),macro=fixture.get('macro'),rounds=fixture['rounds'],
                random=ev.g.tape.values,actions=list(sup.TRACE),hp=result['hp'],enemy_hp=result['enemy_hp'],turns=result['turns'],win=result['win'],censored=result['censored'],draw=result['draw'],
                left_received=a.metrics['damage_received'],right_received=b.metrics['damage_received'],left_min=a.minimum,right_min=b.minimum,
                left_stats=a.get_effective_stats(),right_stats=b.get_effective_stats(),left_uses=[a.usage.get(i,0) for i in range(len(left))],right_uses=[b.usage.get(i,0) for i in range(len(right))],
                left_summary=summary(a),right_summary=summary(b)))
    (HERE/'augmentation_cases.json').write_text(json.dumps(cases,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    sources=[source,Path(__file__),Path(amp.__file__),Path(sup.__file__),Path(ev.__file__),Path(native.__file__),Path(ev.joint.__file__),Path(ev.g.__file__),Path(ev.g.core.__file__),Path(ev.g.natural_core.__file__),ev.g.core.SOURCE,
             ROOT/'combat_numerical_paradigms/synergy_research/settings.py']
    (HERE/'parity_sources.json').write_text(json.dumps(dict(cases=len(cases),profiles=6,sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        adaptations=['inherited verified eleven-mechanism adapters','current-BP healing prevention metric uses actual recovery request']),indent=2),encoding='utf-8')
    print(f'{len(cases)} native augmentation fixtures generated')


if __name__=='__main__':main()
