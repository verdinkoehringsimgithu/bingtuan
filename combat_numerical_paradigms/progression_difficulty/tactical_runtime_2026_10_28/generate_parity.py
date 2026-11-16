"""Five tactical mechanisms, using the frozen native action and prior adapters."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('augmentation_oracle',HERE.parent/'augmentation_runtime_2026_10_28/generate_parity.py')
aug=importlib.util.module_from_spec(spec);sys.modules[spec.name]=aug;spec.loader.exec_module(aug)
amp=aug.amp;sup=aug.sup;ev=aug.ev;native=aug.native
old_post=native.attack.__globals__['post_attack']
def post(a,b,owner,skill,hit):
    before=a.coins;old_post(a,b,owner,skill,hit)
    if a.active('rich') and a.members[owner].identity=='富翁':a.add('rich_attacks',1)
    sup.TRACE[-1]['coinsEarned']=a.coins-before
native.attack.__globals__['post_attack']=post
simulate=aug.simulate

def rules(profile,gain):
    keys=('mage','hunter','gang','rich','worker');d=dict(zip(keys,(profile>=5 or profile==i for i in range(5))))
    d.update(countK=4,gain=gain,magePercent=.04,mageDamage=.04,hunterFraction=.35,hunterRounds=3,gangDamage=.65,richCoin=1,richReduction=.025,richCap=.60,workerRecovery=.20)
    return d

def summary(team):
    c=team.counts;axes=sorted(team.mage_pct_layers)
    return dict(mages=c['魔法师'],hunters=c['猎手'],gangs=c['帮派'],richMembers=c['富翁'],workers=c['社畜'],mageSame=int(team.metrics['mage_same']),mageSwitches=team.mage_switches,
        gangAttacks=int(team.metrics['gang_attacks']),richAttacks=int(team.metrics['rich_attacks']),workerProcs=int(team.metrics['worker_procs']),lastAxis=team.last_genre,
        axes=axes,percentLayers=[team.mage_pct_layers[x] for x in axes],hunterScheduled=team.metrics['hunter_scheduled'],coins=team.coins,richSaved=team.metrics['rich_saved'])

def main():
    source=HERE.parent/'runtime_parity_cases.json';fixtures=json.loads(source.read_text(encoding='utf-8-sig'));cases=[]
    patterns=[('魔法师',),('猎手',),('帮派',),('富翁',),('社畜',),('魔法师','猎手','帮派','富翁','社畜'),
        ('魔法师','猎手','帮派','富翁','社畜','工程师','贤者','盗贼','杀手','老师','学生','拜火教','格斗家','侠女','淑女','学者','剑士','剑士','军人','忍者','水手','行商')]
    for index,base in enumerate(fixtures):
        for profile in range(7):
            fixture=copy.deepcopy(base);ev.CAPACITY=len(fixture['left']);ev.FACTORS=(.7,.7,.8,.5,.9) if profile==6 else (1.,)*5
            gain=2 if profile==6 else 1;tr=rules(profile,gain);ar=aug.rules(5 if profile==6 else -1,gain);am=amp.rules(6 if profile==6 else -1,gain)
            s=sup.support(profile==6,profile==6,gain);er=ev.evasion(profile==6,profile==6,gain)
            enabled=[name for name in ('mage','hunter','gang','rich','worker') if tr[name]]
            if profile==6:enabled+=['engineer','sage','thief','killer','academy','cult','fighter','heroine','lady','scholar','sword','military','ninja','sailor','merchant']
            for side in ('left','right'):
                for pos,row in enumerate(fixture[side]):
                    row['traits']=dict(personId=f'parity:{side}:{pos}',identity=patterns[profile][pos%len(patterns[profile])]);row['level']=1+(index+pos)%30
            left,li=amp.pack(fixture['left']);right,ri=amp.pack(fixture['right'])
            cfg=ev.cfg(er);cfg.update(scholar=s['scholarChance'],scholar_restore=s['scholarRestore'],sword=s['swordChance'],sword_decay=s['swordDecay'],sword_extras=s['swordExtras'])
            sup.TRACE.clear();ev.TEAMS.clear()
            result,*_=simulate(left,right,292000+index*10+profile,li,ri,p=fixture.get('macro'),enabled=enabled,enemy_enabled=enabled,
                config=cfg,enemy_config=cfg,max_turns=fixture['rounds'],legacy=True)
            a,b=ev.TEAMS
            for i,row in enumerate(sup.TRACE):
                nxt=sup.TRACE[i+1] if i+1<len(sup.TRACE) else None
                row['hasContinuation']=bool(nxt and nxt['round']==row['round'] and nxt['side']==row['side'] and nxt['chainDepth']==row['chainDepth']+1)
            opening=dict(sailor=profile==6,merchant=profile==6,countK=4,gain=gain,sailorCoefficient=.006,merchantCoefficient=.30)
            cases.append(dict(name=fixture['name']+':tactical-'+str(profile),capacity=ev.CAPACITY,left=fixture['left'],right=fixture['right'],
                leftTactical=tr,rightTactical=tr,leftAugmentation=ar,rightAugmentation=ar,leftAmplification=am,rightAmplification=am,leftSupport=s,rightSupport=s,leftEvasion=er,rightEvasion=er,leftOpening=opening,rightOpening=opening,
                limits=dict(zip(('bp','courage','resilience','initiative','magic'),ev.FACTORS)),macro=fixture.get('macro'),rounds=fixture['rounds'],
                random=ev.g.tape.values,actions=list(sup.TRACE),hp=result['hp'],enemy_hp=result['enemy_hp'],turns=result['turns'],win=result['win'],censored=result['censored'],draw=result['draw'],
                left_received=a.metrics['damage_received'],right_received=b.metrics['damage_received'],left_min=a.minimum,right_min=b.minimum,
                left_stats=a.get_effective_stats(),right_stats=b.get_effective_stats(),left_uses=[a.usage.get(i,0) for i in range(len(left))],right_uses=[b.usage.get(i,0) for i in range(len(right))],
                left_summary=summary(a),right_summary=summary(b)))
    (HERE/'tactical_cases.json').write_text(json.dumps(cases,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    sources=[source,Path(__file__),Path(aug.__file__),Path(amp.__file__),Path(sup.__file__),Path(ev.__file__),Path(native.__file__),Path(ev.joint.__file__),Path(ev.g.__file__),Path(ev.g.core.__file__),Path(ev.g.natural_core.__file__),ev.g.core.SOURCE,ROOT/'combat_numerical_paradigms/synergy_research/settings.py']
    (HERE/'parity_sources.json').write_text(json.dumps(dict(cases=len(cases),profiles=7,sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}),indent=2),encoding='utf-8')
    print(f'{len(cases)} tactical fixtures generated')
if __name__=='__main__':main()
