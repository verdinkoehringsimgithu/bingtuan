"""Member-owned skills and one equipment per member; live V11 action pipeline.

The production research uses receiver initiative for evasion, as mathematical
specification 01 requires. The source adapter is only an exact parity fixture.
Skills spend a use on activation, including a miss, and never bypass conditions.
"""
from __future__ import annotations
import ast
import copy
import hashlib
import importlib.util
import inspect
import math
import random
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'test_30man_combat_simulator.py'
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
engine=module('roster_v11_source',SOURCE)
generator=module('roster_skill_generator',ROOT/'generate_skills_preview.py')
GENRES=('C_I','C_R','M_I','M_R','M_C','R_I')
STAGES=((5,60000,120,50,20,2),(10,180000,280,130,40,3),(15,360000,480,220,60,4),
        (20,600000,700,340,80,5),(25,820000,880,430,90,6),(30,1000000,1000,500,100,6))
FIELDS=('courage','resilience','initiative','magic')
LETTER={'C':0,'R':1,'I':2,'M':3}
CN={'C':'勇气','R':'坚韧','I':'先机','M':'魔力'}
CHANNELS=('physical','physical_crit','pure_true','pure_true_crit','max_dot','lost_dot','backlash','execute','overflow_true')
HEALS=('self_heal','lifesteal','macro_heal','death_lock')
MECHANICS=('skill_damage','skill_pierce','skill_crit','skill_heal','skill_dot','skill_chance',
           'extra_use','cast_ramp','chance_ramp','overheal_shield','opening_shield','death_lock','owner_stats','normal_damage','cleanse')
MACRO_NAMES=('alpha','beta','gamma','delta','theta','mu')
BOUNDS=np.array(((.3,3.5),(.3,2.5),(0,.8),(0,.5),(-200,500),(.8,2.)))

def seed(*parts):return int.from_bytes(hashlib.sha256('|'.join(map(str,parts)).encode()).digest()[:8],'little')
def stage_stats(stage,g):
    _,_,main,sub,other,_=STAGES[stage];v=[float(other)]*4
    v[LETTER[g[0]]]=main;v[LETTER[g[2]]]=sub;return v

@dataclass(frozen=True)
class Item:
    kind:str='none'
    value:float=0.
    stats:tuple=(0.,0.,0.,0.)
    bp:float=0.
    top:bool=False

@dataclass
class Member:
    uid:int
    role:str
    stats:tuple
    bp:float
    skill:object

def projected(skill,tier,role):
    s=copy.copy(skill);old_tier=s.tier;s.tier=min(tier,old_tier)
    if s.tier!=old_tier:
        # Global tier recipe, applied uniformly to all six flows.
        letter={'勇气':'C','坚韧':'R','先机':'I','魔力':'M'}.get(s.genre,'C')
        param,chance=generator.get_param_and_chance(CN[letter],s.tier,False)
        s.main_param=float(param);s.trigger_chance=float(chance)
        if s.ignore_def_ratio:s.ignore_def_ratio={1:.2,2:.3,3:.38,4:.5,5:.65,6:.8}[s.tier]
        if s.ini_bonus:s.ini_bonus={1:0,2:1,3:2,4:5,5:7,6:10}[s.tier]
        if s.main_type=='Heal':s.sub_param={1:.04,2:.06,3:.09,4:.12,5:.15,6:.18}[s.tier]
        elif s.sub_effect_name in ('虚弱压制','四维削弱'):
            if s.tier<3:s.sub_effect_name='';s.sub_param=0.
            else:s.sub_param=({'虚弱压制':{3:15,4:22,5:35,6:42},'四维削弱':{3:12,4:18,5:22,6:30}}[s.sub_effect_name])[s.tier]
        elif s.sub_effect_name in ('自身已损反噬','敌方已损斩杀'):
            if s.tier<4:s.sub_effect_name='';s.sub_param=0.
            else:s.sub_param=({'自身已损反噬':{4:.18,5:.25,6:.35},'敌方已损斩杀':{4:.15,5:.18,6:.20}}[s.sub_effect_name])[s.tier]
        elif s.sub_effect_name in ('最大流失','已损流失'):
            s.sub_param*=s.tier/old_tier
        elif s.sub_effect_name=='战力吸收':s.sub_param*=s.tier/old_tier
    if role=='backup':s.times_limit=999
    return s

def filler_skill(letter):
    p,chance=generator.get_param_and_chance(CN[letter],1,False)
    s=engine.BattleSkill(0,'F1_'+letter,1,CN[letter],main_param=p,trigger_chance=chance)
    if letter=='M':s.ignore_def_ratio=.2
    if letter=='I':s.ini_bonus=0
    if letter=='R':s.main_type='Heal';s.sub_param=.04;s.self_bp_cond2=80;s.sub_effect_name='总战力恢复'
    return s

@lru_cache(maxsize=4096)
def roster(stage,g,carry=2,backup=4,pool=0,order='default'):
    """Explicit benchmark members; budgets match stage table exactly before gear.

Core skill templates are the native four-skill portfolio assigned to owners.
Backup roles use repeatable portfolio skills; every filler owns a T1 skill from
the current generator. Individual shares vary, while total stage budget stays
fixed so equipment and ordering tests do not hide free base-stat increases.
"""
    random.seed(seed('roster-catalog',stage,g,pool))
    n,bp,*_,cap=STAGES[stage];carry=max(1,min(carry,n));backup=max(0,min(backup,n-carry))
    canonical=engine.assemble_hybrid_troop(g)
    members=[];raw=[];bweights=[]
    for j in range(n):
        role='carry' if j<carry else ('backup' if j<carry+backup else 'filler')
        if role=='carry':s=projected(canonical.skills[j%2],cap,role)
        elif role=='backup':s=projected(canonical.skills[2+(j-carry)%2],max(1,cap-1),role)
        else:s=filler_skill(g[0] if random.random()<.65 else g[2])
        s.id=j+1;s.name=f'{g}_{role}_{j+1}_T{s.tier}'
        weights=[random.uniform(.8,1.2)*(1.35 if role=='filler' else 1.) for _ in range(4)]
        raw.append(weights);bweights.append(random.uniform(.85,1.15)*{'carry':1.4,'backup':.85,'filler':1.2}[role])
        members.append(Member(j,role,(0.,)*4,0.,s))
    budget=stage_stats(stage,g)
    for k in range(4):
        total=sum(x[k] for x in raw)
        for j,m in enumerate(members):
            v=list(m.stats);v[k]=budget[k]*raw[j][k]/total;m.stats=tuple(v)
        v=list(members[-1].stats);v[k]+=budget[k]-sum(m.stats[k] for m in members);members[-1].stats=tuple(v)
    bt=sum(bweights)
    for j,m in enumerate(members):m.bp=bp*bweights[j]/bt
    members[-1].bp+=bp-sum(m.bp for m in members)
    if order=='backup_first':members.sort(key=lambda m:({'backup':0,'carry':1,'filler':2}[m.role],m.uid))
    elif order=='reverse':members.reverse()
    elif order=='chance':members.sort(key=lambda m:-m.skill.trigger_chance)
    return tuple(members)

def basic_items(members,points=0.,axis='theme',bp_each=0.,genre='C_I'):
    v=[0.]*4
    if axis=='theme':v[LETTER[genre[0]]]=points*2/3;v[LETTER[genre[2]]]=points/3
    elif axis=='balanced':v=[points/4]*4
    else:v[FIELDS.index(axis)]=points
    return [Item('basic',stats=tuple(v),bp=bp_each) for _ in members]

def equipment(members,genre,points=0.,axis='theme',bp_each=0.,top=None,allocation=None):
    items=basic_items(members,points,axis,bp_each,genre)
    if top:
        positions=allocation if allocation is not None else list(range(min(4,len(members))))
        for pos in positions:
            kind,value=top if isinstance(top,(tuple,list)) else (top['kind'],top['value'])
            items[pos]=Item(kind,float(value),items[pos].stats,items[pos].bp,True)
    assert len(items)==len(members) and sum(i.top for i in items)<=4
    return tuple(items)

class Team(engine.Troop):
    def __init__(self,members,items=None,name='player',parity=False):
        self.members=members;self.items=items or tuple(Item() for _ in members);self.parity=parity
        assert len(self.items)==len(members) and sum(i.top for i in self.items)<=4
        attrs=[round(sum(m.stats[k]+i.stats[k]+(m.stats[k]*i.value if i.kind=='owner_stats' else 0.) for m,i in zip(members,self.items)),10) for k in range(4)]
        bp=round(sum(m.bp+i.bp for m,i in zip(members,self.items)),6)
        super().__init__(1,name,len(members),*attrs,max_bp=bp)
        self.skills=[m.skill for m in members if m.skill is not None]
    def reset(self):
        super().reset();self.metrics=defaultdict(float);self.round_metrics=defaultdict(float)
        self.member_metrics=[defaultdict(float) for _ in self.members]
        self.failed=[0]*len(self.members);self.casts=[0]*len(self.members);self.lock_used=[False]*len(self.members)
        self.selected_owner=None;self.last_hit=False;self.shield=0.;self.attack_factor=1.;self.absorption=0.;self.regen=0.;self.mu=1.
        self.trace=False;self.heal_channel='self_heal';self.probabilities=[];self.turn=0
        self.selected_original=None;self.direct_factor=1.;self.overflow_convert=0.
    def add(self,k,v):self.metrics[k]+=v;self.round_metrics[k]+=v
    def heal(self,amount):
        result=super().heal(amount);self.add(self.heal_channel,result);excess=max(0.,amount-result);self.add('overheal',excess)
        p=self.selected_owner
        if p is not None:
            self.member_metrics[p][self.heal_channel]+=result
            item=self.items[p]
            if item.kind=='overheal_shield':
                gain=excess*item.value;self.shield+=gain;self.add('overheal_shield',gain);self.member_metrics[p]['gear_effect']+=gain
        return result

def eligibility(team,enemy,s,limit,turn):
    used=team.usage.get(s.id,0)
    if limit>0 and limit<999 and used>=limit:return False,'exhausted'
    if turn<=s.turn_cond1 or (s.turn_cond2>0 and turn>=s.turn_cond2):return False,'round_gate'
    if s.self_bp_cond2>0 and team.bp_pct>=s.self_bp_cond2:return False,'self_gate'
    if s.enemy_bp_cond2>0 and enemy.bp_pct>=s.enemy_bp_cond2:return False,'enemy_gate'
    return True,'eligible'

def skill_chance(team,pos,s):
    item=team.items[pos];p=s.trigger_chance/100.*team.mu
    if item.kind=='skill_chance':p+=item.value
    if item.kind=='chance_ramp':p+=item.value*team.failed[pos]
    return min(1.,max(0.,p))

def select_skill(team,enemy,turn):
    probs=[];reach=1.
    if team.trace:
        for pos,m in enumerate(team.members):
            s=m.skill;item=team.items[pos]
            if s is None:continue
            limit=s.times_limit+int(item.value) if item.kind=='extra_use' and 0<s.times_limit<999 else s.times_limit
            valid,reason=eligibility(team,enemy,s,limit,turn);p=skill_chance(team,pos,s) if valid else 0.
            q=reach*p;mm=team.member_metrics[pos];mm['expected_reached']+=reach;mm['expected_cast']+=q;mm[reason]+=1
            mm['eligible_rounds']+=int(valid)
            probs.append((pos,int(valid),p,reach,q,max(0,limit-team.usage.get(s.id,0)) if limit<999 else -1))
            reach*=1-p
        team.probabilities=probs;team.add('expected_normal',reach)
    for pos,m in enumerate(team.members):
        s=m.skill;item=team.items[pos]
        if s is None:continue
        limit=s.times_limit+int(item.value) if item.kind=='extra_use' and 0<s.times_limit<999 else s.times_limit
        valid,_=eligibility(team,enemy,s,limit,turn)
        if not valid:continue
        team.member_metrics[pos]['reached']+=1
        if random.random()<skill_chance(team,pos,s):
            team.usage[s.id]=team.usage.get(s.id,0)+1;team.casts[pos]+=1;team.failed[pos]=0
            team.selected_owner=pos;team.selected_original=s
            team.member_metrics[pos]['casts']+=1;team.add(m.role+'_casts',1);team.add('skill_casts',1)
            mod=copy.copy(s)
            if mod.main_type!='Heal':mod.main_param*=team.mu
            team.direct_factor=1.;team.overflow_convert=0.
            if item.kind=='skill_damage':team.direct_factor=1+item.value
            elif item.kind=='cast_ramp':team.direct_factor=1+item.value*(team.casts[pos]-1)
            elif item.kind=='skill_pierce':mod.ignore_def_ratio+=item.value
            elif item.kind=='skill_crit':mod.base_crit_rate+=item.value;team.overflow_convert=1.
            elif item.kind=='skill_heal' and (mod.main_type=='Heal' or mod.sub_effect_name=='战力吸收'):mod.sub_param*=1+item.value
            elif item.kind=='skill_dot' and mod.sub_effect_name in ('最大流失','已损流失'):mod.sub_param*=1+item.value
            return mod
        team.failed[pos]+=1
    team.add('normal_casts',1)
    team.selected_owner=None if team.parity else random.randrange(len(team.members))
    team.selected_original=None;team.direct_factor=1.;team.overflow_convert=0.
    if team.selected_owner is not None:
        item=team.items[team.selected_owner]
        if item.kind=='normal_damage':team.direct_factor=1+item.value
        team.member_metrics[team.selected_owner]['normal_casts']+=1
    return None

def deal(acting,defender,amount,kind,ctx=None,clamp=True,owner=-1):
    absorption=amount*defender.absorption;net=amount-absorption;shield=min(defender.shield,net);defender.shield-=shield;net-=shield
    defender.add('absorption_saved',absorption);defender.add('shield_saved',shield)
    old=defender.current_bp;defender.current_bp=max(0.,old-net) if clamp else old-net;actual=min(max(0.,old),net)
    acting.add('damage',actual);acting.add('nominal_damage',net);defender.add('damage_received',actual)
    if kind=='direct':
        raw0=ctx['raw_dmg'] if ctx['skill'].main_type=='Heal' else ctx['raw_dmg']*(ctx['skill'].main_param/100.)/ctx['mult']
        if ctx['is_pure_true']:nc=raw0*(1+(ctx['m_amp']-1)*.2)
        else:nc=max(1.,raw0*(1-max(0.,ctx['pct_dr']*(1-ctx['skill'].ignore_def_ratio*ctx['m_amp'])))-ctx['flat_dr'])
        share=max(0.,min(1.,(amount-nc)/amount)) if amount else 0.
        ch='pure_true' if ctx['is_pure_true'] else 'physical';acting.add(ch,actual*(1-share));acting.add(ch+'_crit',actual*share)
        acting.add('hits',1);acting.add('crit_hits',int(ctx['is_crit']));acting.last_hit=True
        nc0=max(1.,ctx['raw_dmg']*(1-ctx['pct_dr'])-ctx['flat_dr']);acting.add('penetration_credit',max(0.,amount-nc0)*(1-defender.absorption))
    else:acting.add(kind,actual)
    pos=acting.selected_owner if owner==-1 else owner
    if pos is not None:acting.member_metrics[pos]['damage']+=actual
    if defender.current_bp<=.0001:
        for j,item in enumerate(defender.items):
            if item.kind=='death_lock' and not defender.lock_used[j]:
                defender.lock_used[j]=True;defender.current_bp=defender.max_bp*item.value;defender.add('death_lock',defender.current_bp);break
    return net

def overflow(acting,defender,c):
    if c['is_crit'] and c['skill'].main_type!='Heal' and acting.overflow_convert and c['_original_overflow']>0:
        value=c['base_power']*c['_original_overflow']*c['preempt_factor']*acting.get_dmg_output_factor()*acting.direct_factor
        deal(acting,defender,value,'overflow_true')

def on_miss(team):team.add('misses',1);team.last_hit=False

class Adapter(ast.NodeTransformer):
    def __init__(self,spec=True):self.spec=spec
    def visit_For(self,n):
        if ast.unparse(n.target)=='s' and ast.unparse(n.iter)=='acting.skills':
            return ast.parse('skill = select_skill(acting, defender, turn)').body[0]
        return self.generic_visit(n)
    def visit_Dict(self,n):
        n=self.generic_visit(n)
        if any(isinstance(k,ast.Constant) and k.value=='source' and ast.unparse(v)=='acting' for k,v in zip(n.keys,n.values)):
            n.keys.append(ast.Constant('owner'));n.values.append(ast.parse('acting.selected_owner').body[0].value)
        return n
    def visit_Assign(self,n):
        n=self.generic_visit(n);names=[x.id for x in n.targets if isinstance(x,ast.Name)]
        if 'base_power' in names:n.value=ast.BinOp(n.value,ast.Mult(),ast.parse('acting.attack_factor').body[0].value)
        if 'raw_dmg' in names:return [n,*ast.parse('raw_dmg *= acting.direct_factor').body]
        if 'extra_overflow' in names:return [n,*ast.parse('_original_overflow = extra_overflow\nextra_overflow *= (1-acting.overflow_convert)').body]
        if len(n.targets)==1 and ast.unparse(n.targets[0])=='defender.current_bp':
            if 'actual_dmg' in ast.unparse(n.value):return ast.parse("actual_dmg = deal(acting, defender, actual_dmg, 'direct', locals())\noverflow(acting, defender, locals())").body
            return ast.parse('deal(acting, defender, max(1.0, extra), _sub_channel)').body[0]
        return n
    def visit_If(self,n):
        test=ast.unparse(n.test);n=self.generic_visit(n)
        if test=='random.random() < dodge_rate':
            if self.spec:n.test=ast.parse('random.random() < calc_initiative_stats(def_i, eff_i)[0]').body[0].value
            n.body.insert(0,ast.parse('on_miss(acting)').body[0])
        if test=="sub == '自身已损反噬'":n.body.insert(0,ast.parse("_sub_channel = 'backlash'").body[0])
        if test=="sub == '敌方已损斩杀'":n.body.insert(0,ast.parse("_sub_channel = 'execute'").body[0])
        if test=="sub == '战力吸收'":n.body.insert(0,ast.parse("acting.heal_channel = 'lifesteal'").body[0])
        return n

def action_function(spec=True):
    tree=Adapter(spec).visit(ast.parse(inspect.getsource(engine.execute_turn_action)));ast.fix_missing_locations(tree)
    ns=dict(engine.__dict__,select_skill=select_skill,deal=deal,overflow=overflow,on_miss=on_miss)
    exec(compile(tree,str(SOURCE)+'[member instrument]', 'exec'),ns);return ns['execute_turn_action']
ACTION=action_function(True)
PARITY_ACTION=action_function(False)

def macro(team,p):
    alpha,beta,gamma,delta,theta,mu=p;team.max_bp*=alpha;team.current_bp=team.max_bp
    team.attack_factor=beta/alpha;team.absorption=gamma;team.regen=delta;team.mu=mu
    team.base_initiative=team.cur_initiative=max(0.,team.base_initiative+theta)

def status(t):
    e=t.get_effective_stats()
    finite=[(m.skill,m.skill.times_limit+(int(t.items[j].value) if t.items[j].kind=='extra_use' else 0)) for j,m in enumerate(t.members) if m.skill is not None and 0<m.skill.times_limit<999]
    return dict(bp=max(0.,t.current_bp)/t.max_bp,initiative=e[2],weak=1-t.get_dmg_output_factor(),
                stat_weak=1-e[0]/t.cur_courage if t.cur_courage else 0.,shield=t.shield/t.max_bp,
                finite_left=sum(max(0,limit-t.usage.get(s.id,0)) for s,limit in finite))

def simulate(members,opponents,battle_seed,items=None,enemy_items=None,p=None,telemetry=False,max_turns=120,parity=False):
    a,b=Team(members,items,'player',parity),Team(opponents,enemy_items,'enemy',parity)
    random.seed(battle_seed);a.reset();b.reset();a.trace=b.trace=telemetry
    if p is not None:macro(b,p)
    for t in (a,b):
        for item in t.items:
            if item.kind=='opening_shield':t.shield+=t.max_bp*item.value
    rows=[];action=PARITY_ACTION if parity else ACTION
    for turn in range(1,max_turns+1):
        for t in (a,b):
            t.turn=turn;t.round_metrics.clear();t.heal_channel='self_heal'
            t.selected_owner=None;t.selected_original=None;t.probabilities=[];t.last_hit=False
        start=[status(t) for t in (a,b)] if telemetry else None
        for t in (a,b):
            if t.is_dead():continue
            dr=engine.calc_resilience_dr(t.cur_resilience if parity else t.get_effective_stats()[1])[1];dots=[]
            for d in t.max_bp_dots:
                src=d.get('source',t);v=max(1.,t.max_bp*d['val']*(1-dr)*src.get_dmg_output_factor());deal(src,t,v,'max_dot',clamp=False,owner=d.get('owner',-1))
                d['turns']-=1
                if d['turns']>0:dots.append(d)
            t.max_bp_dots=dots
        end=a.is_dead() or b.is_dead();first=None
        if not end:
            i,j=a.get_effective_stats()[2],b.get_effective_stats()[2]
            first,second=(a,b) if i>j or (i==j and random.random()<.5) else (b,a)
            action(first,second,True,turn);end=second.is_dead()
            if not end:action(second,first,False,turn);end=first.is_dead()
        if not end:
            for t in (a,b):
                if t.is_dead():continue
                dr=engine.calc_resilience_dr(t.cur_resilience if parity else t.get_effective_stats()[1])[1];dots=[]
                for d in t.lost_bp_dots:
                    src=d.get('source',t);v=max(1.,max(0.,t.max_bp-t.current_bp)*d['val']*(1-dr)*src.get_dmg_output_factor());deal(src,t,v,'lost_dot',clamp=False,owner=d.get('owner',-1))
                    d['turns']-=1
                    if d['turns']>0:dots.append(d)
                t.lost_bp_dots=dots
                for key in ('dmg_reduce_debuffs','stat_reduce_debuffs'):
                    buffs=[]
                    for d in getattr(t,key):
                        d['turns']-=1
                        if d['turns']>0:buffs.append(d)
                    setattr(t,key,buffs)
            end=a.is_dead() or b.is_dead()
            for t in (a,b):
                if t.regen and not t.is_dead():t.heal_channel='macro_heal';t.heal(t.regen*t.max_bp)
        # Successful owner skill may cleanse own current debuffs, with no effect on a miss.
        for t in (a,b):
            pos=t.selected_owner
            if pos is not None and t.last_hit and t.selected_original is not None and t.items[pos].kind=='cleanse' and t.items[pos].value>0:
                removed=0
                for key in ('stat_reduce_debuffs','dmg_reduce_debuffs'):
                    arr=getattr(t,key);count=min(len(arr),max(0,int(t.items[pos].value)-removed));del arr[:count];removed+=count
                t.add('cleanse',removed)
        if telemetry:
            row=dict(turn=turn,first=0 if first is a else (1 if first is b else -1))
            for side,t,initial in zip(('p','e'),(a,b),start):
                final=status(t)
                for k,v in initial.items():row[side+'_'+k+'_start']=v
                for k,v in final.items():row[side+'_'+k+'_end']=v
                for k in (*CHANNELS,*HEALS,'skill_casts','normal_casts','carry_casts','backup_casts','filler_casts','misses','hits','crit_hits','expected_normal','penetration_credit','shield_saved','absorption_saved'):
                    row[side+'_'+k]=t.round_metrics[k]/t.max_bp if k in (*CHANNELS,*HEALS,'penetration_credit','shield_saved','absorption_saved') else t.round_metrics[k]
                row[side+'_owners']=t.probabilities
                row[side+'_owner']=t.selected_owner
            rows.append(row)
        if end:break
    censored=not a.is_dead() and not b.is_dead();draw=a.is_dead() and b.is_dead()
    winner=(not a.is_dead() and b.is_dead())
    source_win=winner if not(censored or draw) else a.bp_pct>=b.bp_pct
    result=dict(win=int(winner),source_win=int(source_win),censored=int(censored),draw=int(draw),turns=turn,
                hp=max(0.,a.current_bp)/a.max_bp,enemy_hp=max(0.,b.current_bp)/b.max_bp,
                damage=a.metrics['damage']/b.max_bp,damage_per_round=a.metrics['damage']/b.max_bp/turn,
                normal_rate=a.metrics['normal_casts']/max(1.,a.metrics['normal_casts']+a.metrics['skill_casts']),
                carry_rate=a.metrics['carry_casts']/turn,backup_rate=a.metrics['backup_casts']/turn,filler_rate=a.metrics['filler_casts']/turn,
                top_count=sum(x.top for x in a.items),stat_gain=sum(sum(x.stats)+(sum(m.stats)*x.value if x.kind=='owner_stats' else 0.) for m,x in zip(a.members,a.items)),bp_gain=sum(x.bp for x in a.items))
    result['margin']=result['hp']-result['enemy_hp']
    result['downside']=min(0.,result['margin'])**2
    features=None;owners=None
    if telemetry:
        features={}
        for side,t in (('p',a),('e',b)):
            bp=np.array([rows[0][side+'_bp_start']]+[r[side+'_bp_end'] for r in rows]);vel=np.diff(bp);acc=np.diff(np.r_[0.,vel])
            for j,r in enumerate(rows):r[side+'_dbp']=float(vel[j]);r[side+'_d2bp']=float(acc[j])
            for key,val in (('bp',bp),('velocity',vel),('acceleration',acc)):
                for j,x in enumerate(np.interp(np.linspace(0,1,10),np.linspace(0,1,len(val)),val)):features[f'{side}_{key}_{j:02}']=float(x)
            for ch in (*CHANNELS,*HEALS):features[side+'_'+ch+'_flux']=t.metrics[ch]/t.max_bp/turn
            for k in ('weak','stat_weak','finite_left'):
                values=[r[side+'_'+k+'_start'] for r in rows];features[side+'_'+k+'_mean']=float(np.mean(values));features[side+'_'+k+'_change']=float(values[-1]-values[0])
            for role in ('carry','backup','filler'):
                ix=[j for j,m in enumerate(t.members) if m.role==role]
                features[side+'_'+role+'_cast_rate']=sum(t.member_metrics[j]['casts'] for j in ix)/turn
                features[side+'_'+role+'_reach_rate']=sum(t.member_metrics[j]['expected_reached'] for j in ix)/max(1,len(ix))/turn
                features[side+'_'+role+'_damage_flux']=sum(t.member_metrics[j]['damage'] for j in ix)/t.max_bp/turn
            normal=[r[side+'_expected_normal'] for r in rows]
            features[side+'_normal_probability_mean']=float(np.mean(normal));features[side+'_normal_probability_drift']=float(normal[-1]-normal[0])
        features['initiative_difference_mean']=float(np.mean([(r['p_initiative_start']-r['e_initiative_start'])/max(1.,sum(m.stats[2] for m in a.members)) for r in rows]))
        owners=[]
        for j,(m,it,mm) in enumerate(zip(a.members,a.items,a.member_metrics)):
            owners.append(dict(position=j+1,member_id=m.uid,role=m.role,tier=m.skill.tier if m.skill else 0,skill_id=m.skill.id if m.skill else 0,
                               raw_chance=m.skill.trigger_chance/100 if m.skill else 0,times_limit=m.skill.times_limit if m.skill else 0,
                               stats=list(m.stats),bp=m.bp,item=dict(kind=it.kind,value=it.value,stats=it.stats,bp=it.bp,top=it.top),**mm))
    return result,features,rows,owners

def parity_test(n=600):
    for j in range(n):
        g,h=GENRES[j%6],GENRES[(j//6)%6];a,b=engine.assemble_hybrid_troop(g),engine.assemble_hybrid_troop(h)
        def pack(t):
            members=[]
            for k,s in enumerate(t.skills):members.append(Member(k,'carry' if k<2 else 'backup',tuple(getattr(t,'base_'+f)/4 for f in FIELDS),t.max_bp/4,s))
            return tuple(members)
        s=seed('roster-pipeline-parity',j);random.seed(s);old=engine.run_battle(a,b)
        r,_,_,_=simulate(pack(a),pack(b),s,max_turns=40,parity=True)
        assert r['source_win']==int(old['winner'] is a) and r['turns']==old['turns'],j
        assert np.isclose(r['hp'],max(0.,a.current_bp)/a.max_bp,atol=1e-12),j
    return dict(native_pipeline_cases=n,source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),passed=True)

if __name__=='__main__':
    import json
    print(json.dumps(parity_test(),indent=2))
