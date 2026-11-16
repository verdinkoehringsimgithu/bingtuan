"""Smart scholar + recursive complete skills over frozen research physics.

Adapt only the confirmed smart-target policy, per-cast cleanse retention, and
strictly decreasing recursion after the first probability is capped at one.
"""
import ast
import copy
import hashlib
import inspect
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/'evasion_runtime_2026_10_28'))
import generate_parity as ev
native=ev.native
TRACE=[]


class Team(ev.Team):
    def __init__(self,*args,**kwargs):
        self.cleanse_charges=[];self.smart_target=-1;self.smart_amount=0
        super().__init__(*args,**kwargs)


def smart_restore(team,enemy,owner):
    choices=[]
    for pos,member in enumerate(team.members):
        skill=member.skill
        if pos==owner or skill is None or not 0<skill.times_limit<999 or team.usage.get(skill.id,0)<=0:continue
        if skill.turn_cond2>0 and team.turn>=skill.turn_cond2:continue
        extra=int(team.items[pos].value) if team.items[pos].kind=='extra_use' else 0
        ready=skill.can_trigger(team.turn,team.bp_pct,enemy.bp_pct,0)
        exhausted=team.usage[skill.id]>=skill.times_limit+extra
        choices.append(((0 if ready else 2)+(0 if exhausted else 1),pos))
    if not choices:return
    pos=min(choices)[1];skill=team.members[pos].skill;amount=min(team.cfg['scholar_restore'],team.usage[skill.id])
    team.usage[skill.id]-=amount;team.add('scholar_restored',amount);team.add('smart_procs',1)
    team.smart_target=pos;team.smart_amount=amount


class SmartAdapter(ast.NodeTransformer):
    def visit_If(self,node):
        node=self.generic_visit(node)
        if "team.active('scholar')" in ast.unparse(node.test):node.body=ast.parse('smart_restore(team,enemy,owner)').body
        return node


tree=SmartAdapter().visit(ast.parse(inspect.getsource(ev.old_post)));ast.fix_missing_locations(tree)
post_namespace=dict(vars(native),smart_restore=smart_restore)
exec(compile(tree,'<smart-scholar-post>','exec'),post_namespace)
smart_post=post_namespace['post_attack']


def post(a,b,owner,skill,hit):
    if owner is not None and a.active('scholar') and a.members[owner].identity=='学者':a.add('smart_checks',1)
    smart_post(a,b,owner,skill,hit)
    if skill and hit and a.items[owner].kind=='cleanse':a.cleanse_charges.append(int(a.items[owner].value))
    TRACE.append(dict(round=a.turn,side=a.side,owner=owner,normal=not skill,critical=a.metrics['crit_hits']>a._critical_before,
        missed=not hit,forcedHit=a.force_hit,absoluteEvaded=a._absolute,index=len(ev.g.tape.values),chainDepth=a.depth,
        leftBP=a.current_bp if a.side==0 else b.current_bp,rightBP=b.current_bp if a.side==0 else a.current_bp,
        scholarTarget=a.smart_target,scholarRestored=a.smart_amount))
native.post_attack=post
old_make=native.make_action
def make_action(world):
    action=old_make(world)
    def run(a,b,first,turn):
        a.smart_target=-1;a.smart_amount=0;a.heal_channel='self_heal';action(a,b,first,turn)
    return run
native.make_action=make_action
old_roll=native.World.roll
def roll(world,team,channel,owner=0,depth=0):
    value=old_roll(world,team,channel,owner,depth)
    if channel in (7,8) and TRACE:TRACE[-1]['index']=len(ev.g.tape.values)
    return value
native.World.roll=roll
attack_source=inspect.getsource(native.attack).replace(
    "min(1.,team.v('sword','剑士')*team.cfg['sword_decay']**team.depth)",
    "min(1.,team.v('sword','剑士'))*team.cfg['sword_decay']**team.depth")
attack_namespace=dict(vars(native));exec(compile(attack_source,'<bounded-sword-attack>','exec'),attack_namespace)
native.attack=attack_namespace['attack']


def apply_cleanse(team):
    for remaining in team.cleanse_charges:
        for key in ('stat_reduce_debuffs','dmg_reduce_debuffs'):
            arr=getattr(team,key);count=min(len(arr),remaining);del arr[:count];remaining-=count
    team.cleanse_charges.clear()


class CleanseAdapter(ast.NodeTransformer):
    def visit_If(self,node):
        if "t.items[pos].kind == 'cleanse'" in ast.unparse(node.test):return ast.parse('apply_cleanse(t)').body[0]
        return self.generic_visit(node)


tree=CleanseAdapter().visit(ast.parse(inspect.getsource(native.simulate)));ast.fix_missing_locations(tree)
namespace=dict(vars(native),Team=Team,apply_cleanse=apply_cleanse)
exec(compile(tree,'<support-battle-adapter>','exec'),namespace)
simulate=namespace['simulate']


def support(scholar,sword,gain=1):
    d=ev.DEFAULTS
    return dict(scholar=scholar,sword=sword,gain=gain,countK=d['count_k'],scholarChance=d['scholar'],scholarRestore=d['scholar_restore'],
                swordChance=d['sword'],swordDecay=d['sword_decay'],swordExtras=d['sword_extras'])


def summary(team):
    return dict(scholarChecks=int(team.metrics['smart_checks']),scholarProcs=int(team.metrics['smart_procs']),
        scholarRestored=int(team.metrics['scholar_restored']),swordProcs=int(team.metrics['sword_extras']),
        swordExtras=int(team.metrics['sword_extras']),maxChain=int(team.metrics['max_chain']))


def main():
    source=HERE.parent/'runtime_parity_cases.json';fixtures=json.loads(source.read_text(encoding='utf-8-sig'));cases=[]
    for index,base in enumerate(fixtures):
        for profile in range(4):
            fixture=copy.deepcopy(base);ev.CAPACITY=len(fixture['left']);ev.FACTORS=(.7,.7,.8,.5,.9) if profile==3 else (1.,)*5
            gain=3 if profile==3 else 1
            s=support(profile!=0,profile!=1,gain)
            er=ev.evasion(military=profile==3,ninja=profile>=2,gain=gain)
            enabled=[name for name in ('scholar','sword','military','ninja') if (s if name in s else er)[name]]
            if profile==3:enabled+=['sailor','merchant']
            for side in ('left','right'):
                for pos,row in enumerate(fixture[side]):
                    pattern=('剑士','剑士','学生') if profile==0 else ('学生','学者','学生') if profile==1 else ('剑士','剑士','学者','忍者') if profile==2 else ('军人','军人','军人','军人','军人','剑士','学者','忍者','水手','行商')
                    row['traits']=dict(personId=f'parity:{side}:{pos}',identity=pattern[pos%len(pattern)])
            left,li=ev.pack(fixture['left']);right,ri=ev.pack(fixture['right'])
            cfg=ev.cfg(er);cfg.update(scholar=s['scholarChance'],scholar_restore=s['scholarRestore'],sword=s['swordChance'],sword_decay=s['swordDecay'],sword_extras=s['swordExtras'])
            TRACE.clear();ev.TEAMS.clear()
            result,*_=simulate(left,right,289000+index*10+profile,li,ri,p=fixture.get('macro'),enabled=enabled,enemy_enabled=enabled,
                config=cfg,enemy_config=cfg,max_turns=fixture['rounds'],legacy=True)
            a,b=ev.TEAMS
            for i,row in enumerate(TRACE):
                nxt=TRACE[i+1] if i+1<len(TRACE) else None
                row['hasContinuation']=bool(nxt and nxt['round']==row['round'] and nxt['side']==row['side'] and nxt['chainDepth']==row['chainDepth']+1)
            opening=dict(sailor=profile==3,merchant=profile==3,countK=4,gain=gain,sailorCoefficient=.006,merchantCoefficient=.30)
            cases.append(dict(name=fixture['name']+':support-'+str(profile),capacity=ev.CAPACITY,left=fixture['left'],right=fixture['right'],
                leftSupport=s,rightSupport=s,leftEvasion=er,rightEvasion=er,leftOpening=opening,rightOpening=opening,
                limits=dict(zip(('bp','courage','resilience','initiative','magic'),ev.FACTORS)),macro=fixture.get('macro'),rounds=fixture['rounds'],
                random=ev.g.tape.values,actions=list(TRACE),hp=result['hp'],enemy_hp=result['enemy_hp'],turns=result['turns'],win=result['win'],censored=result['censored'],draw=result['draw'],
                left_received=a.metrics['damage_received'],right_received=b.metrics['damage_received'],left_min=a.minimum,right_min=b.minimum,
                left_stats=a.get_effective_stats(),right_stats=b.get_effective_stats(),left_uses=[a.usage.get(i,0) for i in range(len(left))],right_uses=[b.usage.get(i,0) for i in range(len(right))],
                left_summary=summary(a),right_summary=summary(b)))
    (HERE/'support_cases.json').write_text(json.dumps(cases,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    sources=[source,Path(__file__),Path(ev.__file__),Path(ev.native.__file__),Path(ev.joint.__file__),Path(ev.g.__file__),Path(ev.g.core.__file__),Path(ev.g.natural_core.__file__),ev.g.core.SOURCE,
        ROOT/'combat_numerical_paradigms/synergy_research/settings.py']
    (HERE/'parity_sources.json').write_text(json.dumps(dict(cases=len(cases),profiles=4,sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        adaptations=['smart scholar target policy','all recursive cleanse activations retained','healing channel reset for each recursive skill','decay applied after initial probability cap',
                     'stage capacity and opening initiative adapters inherited from previous revision']),indent=2),encoding='utf-8')
    print(f'{len(cases)} native support fixtures generated')


if __name__=='__main__':main()
