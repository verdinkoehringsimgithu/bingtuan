"""Identity experiment layer over the existing canonical instrumented action.

No production files are patched. The baseline action is AST-derived by the
existing natural research module; only explicit extension hooks are inserted.
"""
import ast
import copy
import math
import random
from collections import Counter, defaultdict
import inspect

from rosters import natural, STAGES
from settings import DEFAULTS, IDENTITIES

core=natural.core
engine=natural.engine
ATTRS=('courage','resilience','initiative','magic')


class World:
    def __init__(self, battle_seed, legacy=False):
        self.seed=battle_seed;self.legacy=legacy;self.actor=None;self.draw_index=0
        if legacy: random.seed(battle_seed)

    def roll(self, team, channel, owner=0, depth=0):
        if self.legacy: return random.random()
        # Addressed random values keep unaffected owner/round/channels paired.
        mask=(1<<64)-1
        z=(self.seed + (team.side+1)*0x9E3779B97F4A7C15 + team.turn*0xD1B54A32D192ED03
           + channel*0x94D049BB133111EB + (owner+2)*0xBF58476D1CE4E5B9
           + depth*0xDB4F0B9175AE2165)&mask
        z=((z^(z>>30))*0xBF58476D1CE4E5B9)&mask
        z=((z^(z>>27))*0x94D049BB133111EB)&mask
        z=z^(z>>31)
        return (z>>11)/(1<<53)

    def random(self):
        self.draw_index+=1
        return self.roll(self.actor, 20+self.draw_index,
                         self.actor.selected_owner if self.actor.selected_owner is not None else -1,
                         self.actor.depth)


class Team(natural.Team):
    def __init__(self, members, items, side, world, enabled=(), config=None):
        self.side=side;self.world=world;self.enabled=set(enabled)
        self.cfg={**DEFAULTS,**(config or {})}
        self.gain=float(self.cfg.get('gain',1.))
        self.counts=Counter(getattr(m,'identity','') for m in members)
        self.levels=[getattr(m,'level',30) for m in members]
        self.depth=0;self.forced_owner=None;self.force_hit=False
        self.maid_owner=next((i for i,m in enumerate(members) if getattr(m,'identity','')=='女仆'),None)
        self.engineer_growth=0.;self.ninja_growth=0.;self.pending_engineer=0.;self.pending_ninja=0.
        self.first_heroine=set();self.heroine_layers=0
        self.last_genre=None;self.mage_pct_layers=defaultdict(int);self.mage_switches=0
        self.adventure_done=set();self.fruit_ready=None
        self.coins=0.;self.worker_used=False;self.next_heal_penalty=0.;self.recovery_factor=1.
        self.true_dots=[];self.chain_length=0
        self._base_ready=False
        super().__init__(members,items,'player' if side==0 else 'enemy')
        self._base_ready=True
        self.gear_stats=[sum(i.stats[k] for i in items) for k in range(4)]
        self.initial_cur=[getattr(self,'cur_'+f) for f in ATTRS]
        if self.active('engineer'):
            for k,f in enumerate(ATTRS):
                setattr(self,'cur_'+f,getattr(self,'cur_'+f)+self.gear_stats[k]*self.v('engineer_base','工程师'))
        if self.active('sailor'):
            per=sum(sum(m.stats) for m in members)/len(members)
            amount=per*len(self.counts)*self.v('sailor','水手')
            for f in ATTRS:setattr(self,'cur_'+f,getattr(self,'cur_'+f)+amount)
        if self.active('merchant'):
            vals=[getattr(self,'cur_'+f) for f in ATTRS]
            low=min(range(4),key=lambda k:(vals[k],k));amount=max(vals)*self.v('merchant','行商')
            setattr(self,'cur_'+ATTRS[low],vals[low]+amount)
            self.add('merchant_stats',amount)

    def active(self,key):
        return self.gain>0 and key in self.enabled and any(self.counts[x]>0 for x in IDENTITIES[key])
    def q(self,identity):
        n=self.counts[identity]
        return n/(n+self.cfg['count_k']) if n else 0.
    def v(self,key,identity):return self.cfg[key]*self.q(identity)*self.gain
    def roll(self,channel,owner=0,depth=0):return self.world.roll(self,channel,owner,depth)

    def heal(self,amount):
        if self._base_ready and self.recovery_factor<1:
            before=amount;amount*=self.recovery_factor
            self.add('killer_healing_prevented',before-amount)
        if self._base_ready and self.active('maid') and self.selected_owner==self.maid_owner:
            return core.Team.heal(self,amount)
        return super().heal(amount)

    def get_dmg_output_factor(self):
        x=super().get_dmg_output_factor()
        if self._base_ready and self.active('fighter'):
            x*=1+self.v('fighter','格斗家')*max(0,self.turn-1)
        return x

    def round_commit(self):
        if self.pending_engineer:
            for k,f in enumerate(ATTRS):
                setattr(self,'cur_'+f,getattr(self,'cur_'+f)+self.gear_stats[k]*self.pending_engineer)
            self.engineer_growth+=self.pending_engineer;self.pending_engineer=0.
        self.ninja_growth+=self.pending_ninja;self.pending_ninja=0.


def valid(team,enemy,pos,turn):
    m=team.members[pos];s=m.skill;it=team.items[pos]
    if s is None:return False
    if team.active('maid') and pos==team.maid_owner:return True
    if team.active('gang') and getattr(m,'identity','')=='帮派':return True
    limit=s.times_limit+int(it.value) if it.kind=='extra_use' and 0<s.times_limit<999 else s.times_limit
    return core.eligibility(team,enemy,s,limit,turn)[0]


def select(team,enemy,turn):
    team.force_hit=False;team.recovery_factor=1.
    selected=None
    positions=[team.forced_owner] if team.forced_owner is not None else range(len(team.members))
    for pos in positions:
        m=team.members[pos];s=m.skill
        if not valid(team,enemy,pos,turn):continue
        team.member_metrics[pos]['reached']+=1
        p=1. if (team.forced_owner is not None or (team.active('maid') and pos==team.maid_owner)) else core.skill_chance(team,pos,s)
        if team.roll(1,pos,team.depth)<p:
            selected=pos;break
        team.failed[pos]+=1
    team.selected_owner=selected;team.selected_original=None;team.direct_factor=1.;team.overflow_convert=0.
    if selected is None:
        team.add('normal_casts',1)
        team.selected_owner=(random.randrange(len(team.members)) if team.world.legacy else min(len(team.members)-1,int(team.roll(2)*len(team.members))))
        item=team.items[team.selected_owner]
        if item.kind=='normal_damage':team.direct_factor=1+item.value
        team.member_metrics[team.selected_owner]['normal_casts']+=1
        return None
    pos=selected;m=team.members[pos];original=m.skill;item=team.items[pos]
    identity=getattr(m,'identity','')
    if team.active('gang') and identity=='帮派':
        team.add('normal_casts',1);team.add('gang_attacks',1)
        team.direct_factor=1+team.v('gang','帮派')
        if item.kind=='normal_damage':team.direct_factor*=1+item.value
        team.member_metrics[pos]['normal_casts']+=1
        return None
    team.selected_original=original
    team.usage[original.id]=team.usage.get(original.id,0)+1
    team.casts[pos]+=1;team.failed[pos]=0
    team.member_metrics[pos]['casts']+=1;team.add(m.role+'_casts',1);team.add('skill_casts',1)
    mod=copy.copy(original)
    if mod.main_type!='Heal':mod.main_param*=team.mu
    if team.active('maid') and pos==team.maid_owner:
        # Replace the base skill FIRST, then apply its owner's equipment.
        mod.main_type='Attack';mod.main_param=100*(1+team.cfg['maid_power']*team.q('女仆')*team.gain)
        mod.sub_effect_name='';mod.sub_param=0.;mod.ignore_def_ratio=0.;mod.base_crit_rate=0.;mod.ini_bonus=0
        if team.cfg['maid_kind']=='heal':
            mod.main_type='Heal';mod.sub_param=team.v('maid_heal','女仆')
        team.add('maid_casts',1)
    if item.kind=='skill_damage':team.direct_factor=1+item.value
    elif item.kind=='cast_ramp':team.direct_factor=1+item.value*(team.casts[pos]-1)
    elif item.kind=='skill_pierce':mod.ignore_def_ratio+=item.value
    elif item.kind=='skill_crit':mod.base_crit_rate+=item.value;team.overflow_convert=1.
    elif item.kind=='skill_heal' and (mod.main_type=='Heal' or mod.sub_effect_name=='战力吸收'):mod.sub_param*=1+item.value
    elif item.kind=='skill_dot' and mod.sub_effect_name in ('最大流失','已损流失','固定流失'):mod.sub_param*=1+item.value
    team.recovery_factor=1-team.next_heal_penalty;team.next_heal_penalty=0.
    if team.active('academy') and identity=='老师':
        student_levels=sum(l for x,l in zip(team.members,team.levels) if getattr(x,'identity','')=='学生')
        team.direct_factor*=1+team.cfg['teacher_damage']*student_levels*team.gain
    if team.active('cult') and identity=='拜火教':
        lower=sum(getattr(x,'identity','')=='拜火教' and x.skill.tier<original.tier for x in team.members)
        team.direct_factor*=1+team.cfg['cult']*lower*team.gain
    if team.active('heroine') and identity=='侠女':
        team.direct_factor*=1+team.heroine_layers*team.v('heroine','侠女')
    if team.active('lady'):
        slots=min(len(team.members),max(1,math.ceil(team.counts['淑女']/team.cfg['lady_slots'])))
        if pos<slots:team.direct_factor*=1+team.v('lady','淑女')
    if team.active('mage'):
        if team.last_genre==original.genre:
            team.mage_pct_layers[original.genre]+=1;team.add('mage_same',1)
        elif team.last_genre is not None:
            team.mage_switches+=1;team.add('mage_switch',1)
        team.last_genre=original.genre
        f=1+team.mage_pct_layers[original.genre]*team.v('mage_pct','魔法师')
        mod.ignore_def_ratio*=f;mod.base_crit_rate*=f;mod.sub_param*=f
        team.direct_factor*=1+team.mage_switches*team.v('mage_damage','魔法师')
    if team.active('adventurer') and identity=='冒险者':
        team.direct_factor*=1+len(team.adventure_done)*team.v('adventurer','冒险者')
    # Negative-effect amplitude only; duration remains a separate future parameter.
    out=team.v('sage_out','贤者') if team.active('sage') else 0.
    resist=enemy.v('sage_in','贤者') if enemy.active('sage') else 0.
    if mod.sub_effect_name in ('虚弱压制','四维削弱','最大流失','已损流失','固定流失'):
        mod.sub_param*=(1+out)*max(0,1-resist)
    if mod.sub_effect_name=='固定流失':mod.sub_effect_name='最大流失';mod.sub_param/=enemy.max_bp
    if team.active('military') and identity=='军人':
        ratio=team.counts['军人']/len(team.members)
        if ratio>=.5:
            p=min(1,team.cfg['military_hit']*(.25+.75*(2*ratio-1))*team.gain)
            team.force_hit=team.roll(3,pos,team.depth)<p
            team.add('force_hit',int(team.force_hit))
    return mod


def absolute_miss(acting,defender):
    if acting.force_hit:return False
    if not defender.active('ninja'):return False
    p=min(defender.cfg['ninja_cap'],defender.v('ninja_base','忍者')+defender.ninja_growth)
    if acting.roll(4,acting.selected_owner,acting.depth)<p:
        defender.add('absolute_dodges',1);return True
    return False


def deal(acting,defender,amount,kind,ctx=None,clamp=True,owner=-1):
    if kind=='direct' and acting.active('hunter'):
        fraction=min(1,acting.v('hunter','猎手'))
        raw=ctx['raw_dmg'];converted=raw*fraction;remainder=raw-converted
        if ctx['is_pure_true']:amount=remainder*(1+(ctx['m_amp']-1)*.2)
        else:amount=max(1.,remainder*(1-max(0.,ctx['pct_dr']*(1-ctx['skill'].ignore_def_ratio*ctx['m_amp'])))-ctx['flat_dr']) if remainder>0 else 0.
        duration=int(acting.cfg['hunter_turns'])
        defender.true_dots.append(dict(amount=converted/duration,left=duration,start=acting.turn+1,source=acting,owner=acting.selected_owner))
        acting.add('hunter_scheduled',converted)
    if defender.active('rich'):
        reduction=min(defender.cfg['rich_cap'],defender.coins*defender.cfg['rich_dr']*defender.gain)
        defender.add('rich_saved',amount*reduction);amount*=1-reduction
    result=natural.deal(acting,defender,amount,kind,ctx,clamp,owner)
    if defender.current_bp<=0 and defender.active('worker') and not defender.worker_used:
        defender.worker_used=True;defender.current_bp=1.
        # This resurrection recovery is not a skill recovery and ignores killer.
        saved=defender.recovery_factor;defender.recovery_factor=1.
        defender.heal_channel='death_lock';defender.heal(defender.max_bp*min(1.,defender.v('worker','社畜')))
        defender.recovery_factor=saved;defender.add('worker_procs',1)
    return result


class Adapter(natural.NaturalAdapter):
    def visit_Assign(self,node):
        text=ast.unparse(node)
        result=super().visit_Assign(node)
        if text.startswith('raw_skill_crit ='):
            return ast.parse('if absolute_miss(acting, defender):\n    on_miss(acting)\n    return').body+[result]
        return result

    def visit_If(self,node):
        test=ast.unparse(node.test)
        result=super().visit_If(node)
        if test=='random.random() < dodge_rate':
            result.test=ast.BoolOp(op=ast.And(),values=[ast.UnaryOp(op=ast.Not(),operand=ast.Attribute(value=ast.Name(id='acting',ctx=ast.Load()),attr='force_hit',ctx=ast.Load())),result.test])
        return result


def compile_action():
    tree=Adapter(True).visit(ast.parse(inspect.getsource(engine.execute_turn_action)))
    ast.fix_missing_locations(tree)
    return compile(tree,'[identity action extension]','exec')


ACTION_CODE=compile_action()


def overflow(acting,defender,c):
    if c['is_crit'] and c['skill'].main_type!='Heal' and acting.overflow_convert and c['_original_overflow']>0:
        value=c['base_power']*c['_original_overflow']*c['preempt_factor']*acting.get_dmg_output_factor()*acting.direct_factor
        deal(acting,defender,value,'overflow_true')


def make_action(world):
    ns=dict(engine.__dict__,select_skill=select,deal=deal,overflow=overflow,
            on_miss=core.on_miss,absolute_miss=absolute_miss,random=world)
    exec(ACTION_CODE,ns)
    return ns['execute_turn_action']


def post_attack(team,enemy,owner,was_skill,hit):
    if owner is None:return
    identity=getattr(team.members[owner],'identity','');depth=team.depth
    team.add('attacks',1)
    if team.active('heroine') and identity=='侠女' and was_skill and owner not in team.first_heroine:
        team.first_heroine.add(owner);team.heroine_layers+=1;team.add('heroine_first',1)
    if team.active('engineer') and identity=='工程师' and was_skill:
        team.pending_engineer+=team.v('engineer_cast','工程师');team.add('engineer_casts',1)
    if team.active('ninja') and identity=='忍者' and was_skill:
        team.pending_ninja+=team.v('ninja_cast','忍者');team.add('ninja_casts',1)
    if team.active('scholar') and identity=='学者' and team.roll(5,owner,depth)<min(1.,team.v('scholar','学者')):
        candidates=[]
        for pos,m in enumerate(team.members):
            if pos==owner or (team.active('maid') and pos==team.maid_owner):continue
            s=m.skill
            if s is not None and 0<s.times_limit<999 and team.usage.get(s.id,0)>0:candidates.append(pos)
        if candidates:
            pos=candidates[min(len(candidates)-1,int(team.roll(6,owner,depth)*len(candidates)))]
            sid=team.members[pos].skill.id;amount=min(team.cfg['scholar_restore'],team.usage[sid])
            team.usage[sid]-=amount;team.add('scholar_restored',amount)
    if team.active('thief') and identity=='盗贼':
        eff=enemy.get_effective_stats();rate=min(1.,team.v('thief','盗贼'))
        for k,f in enumerate(ATTRS):
            available=getattr(enemy,'cur_'+f);amount=min(available,max(0,eff[k])*rate)
            setattr(enemy,'cur_'+f,available-amount)
            setattr(team,'cur_'+f,getattr(team,'cur_'+f)+amount)
            team.add('thief_stolen',amount)
    if team.active('rich') and identity=='富翁':
        team.coins+=team.cfg['rich_coin']*team.gain;team.add('coins',team.cfg['rich_coin']*team.gain)
    if team.active('killer') and identity=='杀手' and was_skill and hit:
        enemy.next_heal_penalty=max(enemy.next_heal_penalty,min(1.,team.v('killer','杀手')))
        team.add('killer_marks',1)
    if team.active('farmer') and identity=='农民':
        if team.fruit_ready is None:
            team.fruit_ready=team.turn+team.cfg['farmer_ripen'];team.add('fruit_planted',1)
        elif team.turn<team.fruit_ready:
            team.fruit_ready=max(team.turn,team.fruit_ready-team.cfg['farmer_accelerate']);team.add('fruit_accelerated',1)
        else:
            wait=team.turn-team.fruit_ready
            amount=team.max_bp*team.v('farmer_value','农民')*(1+wait*team.cfg['farmer_wait'])
            kind=team.cfg['farmer_kind']
            if kind=='heal':
                saved=team.recovery_factor;team.recovery_factor=1.;team.heal_channel='fruit_heal';team.heal(amount);team.recovery_factor=saved
            elif kind=='shield':team.shield+=amount
            elif kind=='damage':deal(team,enemy,amount,'fruit_damage')
            team.add('fruit_harvest',1);team.add('fruit_wait',wait);team.fruit_ready=None
    if team.active('maid') and owner==team.maid_owner and was_skill and team.cfg['maid_kind']=='shield':
        team.shield+=team.max_bp*team.v('maid_shield','女仆')


def attack(team,enemy,is_first,turn,action):
    team.chain_length=0;team.depth=0;team.forced_owner=None
    while True:
        team.world.actor=team;team.world.draw_index=0;team.last_hit=False
        before={k:team.metrics[k] for k in ('crit_hits','self_heal','lifesteal','max_dot','lost_dot')}
        old_dots=len(enemy.max_bp_dots)+len(enemy.lost_bp_dots)
        action(team,enemy,is_first,turn)
        owner=team.selected_owner;was_skill=team.selected_original is not None
        hit=team.last_hit
        if hit:team.adventure_done.add('hit')
        if team.metrics['crit_hits']>before['crit_hits']:team.adventure_done.add('crit')
        if team.metrics['self_heal']+team.metrics['lifesteal']>before['self_heal']+before['lifesteal']:team.adventure_done.add('heal')
        if len(enemy.max_bp_dots)+len(enemy.lost_bp_dots)>old_dots:team.adventure_done.add('dot')
        if len(enemy.stat_reduce_debuffs)+len(enemy.dmg_reduce_debuffs)>0 and hit and was_skill and team.selected_original.sub_effect_name in ('虚弱压制','四维削弱'):team.adventure_done.add('debuff')
        team.adventure_done.intersection_update(team.cfg['adventure_goals'])
        post_attack(team,enemy,owner,was_skill,hit)
        team.recovery_factor=1.
        if enemy.is_dead() or team.is_dead():break
        if not(team.active('sword') and was_skill and owner is not None and getattr(team.members[owner],'identity','')=='剑士'):break
        if team.depth>=int(team.cfg['sword_extras']):break
        candidates=[i for i,m in enumerate(team.members) if i!=owner and getattr(m,'identity','')=='剑士' and valid(team,enemy,i,turn)]
        if not candidates:break
        p=min(1.,team.v('sword','剑士')*team.cfg['sword_decay']**team.depth)
        if team.roll(7,owner,team.depth)>=p:break
        chosen=candidates[min(len(candidates)-1,int(team.roll(8,owner,team.depth)*len(candidates)))]
        team.depth+=1;team.chain_length+=1;team.add('sword_extras',1)
        team.forced_owner=chosen
    team.add('max_chain',0)
    team.metrics['max_chain']=max(team.metrics['max_chain'],team.chain_length)
    team.forced_owner=None;team.depth=0


def simulate(members,opponents,battle_seed,items,enemy_items=None,p=None,
             enabled=(),enemy_enabled=(),config=None,enemy_config=None,max_turns=120,
             telemetry=False,legacy=False):
    world=World(battle_seed,legacy)
    a=Team(members,items,0,world,enabled,config)
    b=Team(opponents,enemy_items or tuple(natural.Item() for _ in opponents),1,world,enemy_enabled,enemy_config)
    if p is not None:core.macro(b,p)
    for t in (a,b):
        for it in t.items:
            if it.kind=='opening_shield':t.shield+=t.max_bp*it.value
    action=make_action(world);rows=[]
    for turn in range(1,max_turns+1):
        for t in (a,b):
            t.turn=turn;t.round_metrics.clear();t.heal_channel='self_heal'
            t.selected_owner=None;t.selected_original=None;t.last_hit=False
        initial=[max(0,t.current_bp)/t.max_bp for t in (a,b)]
        for t in (a,b):
            if t.is_dead():continue
            dr=engine.calc_resilience_dr(t.get_effective_stats()[1])[1];survivors=[]
            for dot in t.max_bp_dots:
                src=dot.get('source',t)
                amount=max(1.,t.max_bp*dot['val']*(1-dr)*src.get_dmg_output_factor())
                deal(src,t,amount,'max_dot',clamp=False,owner=dot.get('owner',-1));dot['turns']-=1
                if dot['turns']>0:survivors.append(dot)
            t.max_bp_dots=survivors;survivors=[]
            for dot in t.true_dots:
                if turn>=dot['start']:
                    deal(dot['source'],t,dot['amount'],'hunter_true',clamp=False,owner=dot['owner']);dot['left']-=1
                if dot['left']>0:survivors.append(dot)
            t.true_dots=survivors
        end=a.is_dead() or b.is_dead()
        if not end:
            i,j=a.get_effective_stats()[2],b.get_effective_stats()[2]
            first,second=(a,b) if i>j or (i==j and a.roll(10)<.5) else (b,a)
            attack(first,second,True,turn,action);end=second.is_dead() or first.is_dead()
            if not end:attack(second,first,False,turn,action);end=first.is_dead() or second.is_dead()
        if not end:
            for t in (a,b):
                dr=engine.calc_resilience_dr(t.get_effective_stats()[1])[1];survivors=[]
                for dot in t.lost_bp_dots:
                    src=dot.get('source',t)
                    amount=max(1.,max(0.,t.max_bp-t.current_bp)*dot['val']*(1-dr)*src.get_dmg_output_factor())
                    deal(src,t,amount,'lost_dot',clamp=False,owner=dot.get('owner',-1));dot['turns']-=1
                    if dot['turns']>0:survivors.append(dot)
                t.lost_bp_dots=survivors
                for key in ('dmg_reduce_debuffs','stat_reduce_debuffs'):
                    arr=[]
                    for buff in getattr(t,key):
                        buff['turns']-=1
                        if buff['turns']>0:arr.append(buff)
                    setattr(t,key,arr)
            end=a.is_dead() or b.is_dead()
            for t in (a,b):
                if not t.is_dead() and t.regen:t.heal_channel='macro_heal';t.heal(t.max_bp*t.regen)
        for t in (a,b):
            pos=t.selected_owner
            if pos is not None and t.last_hit and t.selected_original is not None and t.items[pos].kind=='cleanse':
                remaining=max(0,int(t.items[pos].value))
                for key in ('stat_reduce_debuffs','dmg_reduce_debuffs'):
                    arr=getattr(t,key);count=min(len(arr),remaining);del arr[:count];remaining-=count
            if telemetry:
                side='p' if t is a else 'e';eff=t.get_effective_stats()
                row=locals().get('row',{}) if t is b else dict(turn=turn)
                row.update({side+'_bp_start':initial[t.side],side+'_bp_end':max(0,t.current_bp)/t.max_bp,
                            side+'_stats':list(eff),side+'_owner':pos,
                            side+'_metrics':dict(t.round_metrics),side+'_finite_left':sum(max(0,m.skill.times_limit-t.usage.get(m.skill.id,0)) for m in t.members if 0<m.skill.times_limit<999)})
            # Deferred modifiers commit only after BOTH sides finish this round.
            t.round_commit()
        if telemetry:rows.append(row)
        if end:break
    win=int(not a.is_dead() and b.is_dead());censored=int(not a.is_dead() and not b.is_dead())
    hp=max(0,a.current_bp)/a.max_bp;ehp=max(0,b.current_bp)/b.max_bp
    result=dict(win=win,censored=censored,draw=int(a.is_dead() and b.is_dead()),turns=turn,hp=hp,enemy_hp=ehp,margin=hp-ehp,
                normal_rate=a.metrics['normal_casts']/max(1,a.metrics['skill_casts']+a.metrics['normal_casts']),
                damage=a.metrics['damage']/b.max_bp,coins=a.coins,
                teacher_xp_multiplier=1+a.cfg['teacher_xp']*a.counts['老师']*a.gain if a.active('academy') else 1.,
                metrics=dict(a.metrics),enemy_metrics=dict(b.metrics),owner_casts=list(a.casts),
                owner_reached=[r['reached'] for r in a.member_metrics],final_stats=list(a.get_effective_stats()),
                enemy_final_stats=list(b.get_effective_stats()),heroine_layers=a.heroine_layers,
                adventure_goals=len(a.adventure_done))
    return result,rows,a,b
