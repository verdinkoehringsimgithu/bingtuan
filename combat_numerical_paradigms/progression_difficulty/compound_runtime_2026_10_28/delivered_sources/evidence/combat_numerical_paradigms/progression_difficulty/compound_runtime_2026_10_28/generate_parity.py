"""Compound-v1/configured successor, plus verified stage/support adapters.

All oracle adaptations are in-memory; frozen research files are unchanged.
"""
import ast
import copy
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'combat_numerical_paradigms/synergy_research'))
import configured_compound_core as configured
import bond_core as original
SELECT_SOURCE=inspect.getsource(original.select)
POST_SOURCE=inspect.getsource(original.post_attack)
ATTACK_SOURCE=inspect.getsource(original.attack)
SIMULATE_SOURCE=inspect.getsource(original.simulate)
PARAMETERS=[{}, {'maid':dict(true_mode='additional',true_addition=.175,attack_gain=.9,heal=.04,stats_per_cast=.0125,debuff_percent=6,skill_crit=.1)}, {}, {},
    {'adventurer':dict(goals=['enemy_below_100','enemy_below_75','enemy_below_50','enemy_below_25'],per_goal_damage=.09)},
    {'maid':dict(true_mode='additional',true_addition=.175,attack_gain=.9,heal=.04,stats_per_cast=.0125,debuff_percent=6,skill_crit=.1)},
    {'maid':dict(true_mode='additional',true_addition=.175,attack_gain=.9,heal=.04,stats_per_cast=.0125,debuff_percent=6,skill_crit=.1)}]
# Instantiate before installing the earlier adapters: inspect.getsource remains valid.
MODULES=[configured.configured(p) for p in PARAMETERS]
spec=importlib.util.spec_from_file_location('tactical_oracle',HERE.parent/'tactical_runtime_2026_10_28/generate_parity.py')
tac=importlib.util.module_from_spec(spec);sys.modules[spec.name]=tac;spec.loader.exec_module(tac)
aug=tac.aug;amp=tac.amp;sup=tac.sup;ev=tac.ev;native=tac.native


def smart_restore(team,enemy,owner):
    choices=[]
    for pos,member in enumerate(team.members):
        s=member.skill
        if pos==owner or (team.active('maid') and pos==team.maid_owner) or s is None or not 0<s.times_limit<999 or team.usage.get(s.id,0)<=0:continue
        if s.turn_cond2>0 and team.turn>=s.turn_cond2:continue
        extra=int(team.items[pos].value) if team.items[pos].kind=='extra_use' else 0
        ready=s.can_trigger(team.turn,team.bp_pct,enemy.bp_pct,0);exhausted=team.usage[s.id]>=s.times_limit+extra
        choices.append(((0 if ready else 2)+(0 if exhausted else 1),pos))
    if choices:
        pos=min(choices)[1];s=team.members[pos].skill;amount=min(team.cfg['scholar_restore'],team.usage[s.id]);team.usage[s.id]-=amount
        team.add('scholar_restored',amount);team.add('smart_procs',1);team.smart_target=pos;team.smart_amount=amount


def prepare(module):
    class Team(module.Team,aug.Team):pass
    tree=module.SelectAdapter().visit(ast.parse(SELECT_SOURCE.replace("ratio=team.counts['军人']/len(team.members)","ratio=team.counts['军人']/team.member_capacity")))
    ast.fix_missing_locations(tree);ns=dict(module._select_ns,random=ev.g.tape);exec(compile(tree,'<compound-capacity-select>','exec'),ns);module._select=ns['select']
    tree=module.PostAdapter().visit(sup.SmartAdapter().visit(ast.parse(POST_SOURCE)));ast.fix_missing_locations(tree)
    ns=dict(module._post_ns,smart_restore=smart_restore);exec(compile(tree,'<compound-smart-post>','exec'),ns);module._post_attack=ns['post_attack']
    def make_action(world):
        action=module.make_action(world)
        def run(a,b,first,turn):
            a._absolute=False;a._critical_before=a.metrics['crit_hits'];a._heroine_before=a.metrics['heroine_first'];a._prevented_before=a.metrics['killer_healing_prevented']
            a.smart_target=-1;a.smart_amount=0;a.heal_channel='self_heal';action(a,b,first,turn)
        return run
    def post(a,b,owner,skill,hit):
        pending=a.pending_engineer;stats=[getattr(a,'cur_'+axis) for axis in native.ATTRS];marks=a.metrics['killer_marks'];coins=a.coins
        fruit=[a.metrics[key] for key in ('fruit_planted','fruit_accelerated','fruit_harvest')]
        if a.active('scholar') and a.members[owner].identity=='学者':a.add('smart_checks',1)
        module.post_attack(a,b,owner,skill,hit)
        if skill and hit and a.items[owner].kind=='cleanse':a.cleanse_charges.append(int(a.items[owner].value))
        stolen=None
        if a.active('thief') and a.members[owner].identity=='盗贼':
            stolen=[getattr(a,'cur_'+axis)-value for axis,value in zip(native.ATTRS,stats)]
            a.augmentation_stolen=[x+y for x,y in zip(a.augmentation_stolen,stolen)];a.add('augmentation_thief_attacks',1)
        if a.active('rich') and a.members[owner].identity=='富翁':a.add('rich_attacks',1)
        gear=a.items[owner];baseline=1.
        if skill and gear.kind=='skill_damage':baseline=1+gear.value
        elif skill and gear.kind=='cast_ramp':baseline=1+gear.value*(a.casts[owner]-1)
        elif not skill and gear.kind=='normal_damage':baseline=1+gear.value
        fruit_event=None
        for key,old,label in zip(('fruit_planted','fruit_accelerated','fruit_harvest'),fruit,('planted','accelerated','harvested')):
            if a.metrics[key]>old:fruit_event=label
        sup.TRACE.append(dict(round=a.turn,side=a.side,owner=owner,normal=not skill,critical=a.metrics['crit_hits']>a._critical_before,missed=not hit,
            forcedHit=a.force_hit,absoluteEvaded=a._absolute,index=len(ev.g.tape.values),chainDepth=a.depth,
            leftBP=a.current_bp if a.side==0 else b.current_bp,rightBP=b.current_bp if a.side==0 else a.current_bp,
            scholarTarget=a.smart_target,scholarRestored=a.smart_amount,heroineFirst=a.metrics['heroine_first']>a._heroine_before,
            bondDirectMultiplier=a.direct_factor/baseline,bondOutputMultiplier=amp.fighter_factor(a),engineerQueued=a.pending_engineer-pending,
            appliedHealPenalty=1-a.recovery_factor,healingPrevented=a.metrics['killer_healing_prevented']-a._prevented_before,stolenStats=stolen,
            killerMarked=a.metrics['killer_marks']>marks,coinsEarned=a.coins-coins,maidCast=bool(skill and a.maid_mod is not None),fruitEvent=fruit_event))
    source=ATTACK_SOURCE.replace("min(1.,team.v('sword','剑士')*team.cfg['sword_decay']**team.depth)","min(1.,team.v('sword','剑士'))*team.cfg['sword_decay']**team.depth")
    tree=module.AttackAdapter().visit(ast.parse(source));ast.fix_missing_locations(tree)
    ns=dict(module._attack_ns,post_attack=post);exec(compile(tree,'<compound-bounded-chain>','exec'),ns);attack=ns['attack']
    tree=sup.CleanseAdapter().visit(ast.parse(SIMULATE_SOURCE));ast.fix_missing_locations(tree)
    ns=dict(module._simulate_ns,Team=Team,make_action=make_action,attack=attack,deal=module.deal,apply_cleanse=sup.apply_cleanse)
    exec(compile(tree,'<compound-verified-battle>','exec'),ns);return ns['simulate']


ORACLES={id(module):prepare(module) for module in MODULES}
def rules(profile,gain):
    return dict(maid=profile in (0,1,5,6),farmer=profile in (2,5,6),adventurer=profile>=3,countK=4,gain=gain,
        maidAdditionalTrue=profile in (1,5,6),maidBudget=.5 if profile in (1,5,6) else 1,
        maidAttack=1.8,maidHeal=.08,maidStats=.025,maidDebuff=12,maidCrit=.20,maidTrue=.35,maidDebuffRounds=2,
        fruitRipen=5,fruitAccelerate=1,fruitWait=.15,fruitHeal=.12,fruitStats=.1,
        maidUnlocks=[.2,.4,.55,.7,.8],fruitUnlocks=[0,.4,.6,.8],
        goals=MODULES[profile].DEFINITIONS['adventurer']['goals'],adventureDamage=MODULES[profile].DEFINITIONS['adventurer']['per_goal_damage'])


def summary(team):
    c=team.counts;m=team.metrics
    return dict(maids=c['女仆'],farmers=c['农民'],adventurers=c['冒险者'],maidOwner=team.maid_owner if team.maid_owner is not None else -1,
        maidLevel=team.maid_level if team.active('maid') else 0,maidCasts=int(m['maid_casts']),fruitReady=team.fruit_ready if team.fruit_ready is not None else -1,
        fruitPlanted=int(m['fruit_planted']),fruitAccelerated=int(m['fruit_accelerated']),fruitHarvests=int(m['fruit_harvest']),fruitWait=int(m['fruit_wait']),fruitKinds=int(m['fruit_stat_kinds']),
        adventureCompleted=int(m['adventure_completed']),adventureBoostedCasts=int(m['adventure_boosted_casts']),maidHealRequested=m['maid_heal_requested'],maidStatsTotal=m['maid_stats_total'],
        maidTrueRequested=m['maid_true_requested'],fruitHealRequested=m['fruit_heal_requested'],openingStats=team.opening_stats,
        fruitStats=[m['fruit_stats_'+axis] for axis in native.ATTRS],events=[dict(key=key,round=value['turn'],phase=value['phase']) for key,value in sorted(team.first_events.items())])


def main():
    source=HERE.parent/'runtime_parity_cases.json';fixtures=json.loads(source.read_text(encoding='utf-8-sig'));cases=[]
    patterns=[('女仆',),('女仆',),('农民',),('冒险者',),('冒险者',),('冒险者','农民','女仆','女仆','学生'),
        ('冒险者','农民','女仆','女仆','魔法师','猎手','帮派','富翁','社畜','工程师','贤者','盗贼','杀手','老师','学生','拜火教','格斗家','侠女','淑女','学者','剑士','剑士','军人','忍者','水手','行商')]
    for index,base in enumerate(fixtures):
        for profile in range(7):
            fixture=copy.deepcopy(base);ev.CAPACITY=len(fixture['left']);ev.FACTORS=(.7,.7,.8,.5,.9) if profile==6 else (1.,)*5
            gain=2 if profile==6 else 1;cr=rules(profile,gain);tr=tac.rules(6 if profile==6 else -1,gain);ar=aug.rules(5 if profile==6 else -1,gain);am=amp.rules(6 if profile==6 else -1,gain)
            s=sup.support(profile==6,profile==6,gain);er=ev.evasion(profile==6,profile==6,gain)
            enabled=[name for name in ('maid','farmer','adventurer') if cr[name]]
            if profile==6:enabled+=['mage','hunter','gang','rich','worker','engineer','sage','thief','killer','academy','cult','fighter','heroine','lady','scholar','sword','military','ninja','sailor','merchant']
            for side in ('left','right'):
                for pos,row in enumerate(fixture[side]):
                    row['traits']=dict(personId=f'parity:{side}:{pos}',identity=patterns[profile][pos%len(patterns[profile])]);row['level']=1+(index+pos)%30
            left,li=amp.pack(fixture['left']);right,ri=amp.pack(fixture['right']);cfg=ev.cfg(er)
            cfg.update(scholar=s['scholarChance'],scholar_restore=s['scholarRestore'],sword=s['swordChance'],sword_decay=s['swordDecay'],sword_extras=s['swordExtras'])
            sup.TRACE.clear();ev.TEAMS.clear();module=MODULES[profile]
            result,*_=ORACLES[id(module)](left,right,293000+index*10+profile,li,ri,p=fixture.get('macro'),enabled=enabled,enemy_enabled=enabled,
                config=cfg,enemy_config=cfg,max_turns=fixture['rounds'],legacy=True)
            a,b=ev.TEAMS
            for i,row in enumerate(sup.TRACE):
                nxt=sup.TRACE[i+1] if i+1<len(sup.TRACE) else None
                row['hasContinuation']=bool(nxt and nxt['round']==row['round'] and nxt['side']==row['side'] and nxt['chainDepth']==row['chainDepth']+1)
            opening=dict(sailor=profile==6,merchant=profile==6,countK=4,gain=gain,sailorCoefficient=.006,merchantCoefficient=.30)
            cases.append(dict(name=fixture['name']+':compound-'+str(profile),capacity=ev.CAPACITY,left=fixture['left'],right=fixture['right'],
                leftCompound=cr,rightCompound=cr,leftTactical=tr,rightTactical=tr,leftAugmentation=ar,rightAugmentation=ar,leftAmplification=am,rightAmplification=am,leftSupport=s,rightSupport=s,leftEvasion=er,rightEvasion=er,leftOpening=opening,rightOpening=opening,
                limits=dict(zip(('bp','courage','resilience','initiative','magic'),ev.FACTORS)),macro=fixture.get('macro'),rounds=fixture['rounds'],random=ev.g.tape.values,actions=list(sup.TRACE),
                hp=result['hp'],enemy_hp=result['enemy_hp'],turns=result['turns'],win=result['win'],censored=result['censored'],draw=result['draw'],left_received=a.metrics['damage_received'],right_received=b.metrics['damage_received'],left_min=a.minimum,right_min=b.minimum,
                left_stats=a.get_effective_stats(),right_stats=b.get_effective_stats(),left_uses=[a.usage.get(i,0) for i in range(len(left))],right_uses=[b.usage.get(i,0) for i in range(len(right))],left_summary=summary(a),right_summary=summary(b)))
    (HERE/'compound_cases.json').write_text(json.dumps(cases,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    sources=[source,Path(__file__),Path(tac.__file__),Path(aug.__file__),Path(amp.__file__),Path(sup.__file__),Path(ev.__file__),Path(native.__file__),Path(ev.joint.__file__),Path(ev.g.__file__),Path(ev.g.core.__file__),Path(ev.g.natural_core.__file__),ev.g.core.SOURCE,
        Path(configured.__file__),configured.SOURCE,configured.SOURCE.with_name('compound_effects.json'),ROOT/'combat_numerical_paradigms/synergy_research/settings.py']
    (HERE/'parity_sources.json').write_text(json.dumps(dict(cases=len(cases),profiles=7,sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        adaptations=['verified stage capacity, RNG tape, smart scholar, bounded chains, all cleanse activations','smart scholar excludes unlimited maid leader','current-BP prevented request telemetry']),indent=2),encoding='utf-8')
    print(f'{len(cases)} compound fixtures generated')
if __name__=='__main__':main()
