"""Generator-derived, individually summed member statistics; canonical combat."""
from __future__ import annotations
import os,sys,json,re,copy,math,random,hashlib
from pathlib import Path
from functools import lru_cache
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'combat_numerical_paradigms/roster_research'))
import roster_core as core
from roster_core import GENRES,STAGES,FIELDS,LETTER,Item,Member,stage_stats,seed,engine
CATALOG_PATH=Path(os.environ.get('NATURAL_CATALOG',str(Path(__file__).parent/'results/catalog_current.json')))
CATALOG=json.loads(CATALOG_PATH.read_text(encoding='utf-8')) if CATALOG_PATH.exists() else []
OLD_BUDGETS=((0,0),(1,2),(3,4),(5,7),(8,11),(12,16))
SECONDARY={'C':'M','R':'C','I':'C','M':'R'}
OTHER_ORDER={'C':('I','R'),'R':('I','M'),'I':('M','R'),'M':('I','C')}
NAME_TO_LETTER={'勇气':'C','坚韧':'R','先机':'I','魔力':'M'}
BASE_BP=(3200,5800,9600,16000,28000,50000)

def allocation(letter,total,primary=.6,secondary=.2):
    values=[0]*4;p=LETTER[letter];s=LETTER[SECONDARY[letter]];others=[LETTER[k] for k in OTHER_ORDER[letter]]
    values[p]=round(total*primary);values[s]=round(total*secondary);values[others[0]]=round(total*(1-primary-secondary)/2)
    values[others[1]]=total-sum(values)
    assert min(values)>=0 and sum(values)==total
    return tuple(values)

def convert(record):
    c=record['csv'];t=int(record['tier']);g=record['genre'];detail=record['detail']
    match=re.search(r'效果类型:\s*([^\s\[]+)',detail);sub=match.group(1) if match else ''
    match=re.search(r'效果数值:\s*([\d.]+)',detail);v=float(match.group(1)) if match else 0.
    if sub and sub!='固定流失':v/=100
    if sub in ('虚弱压制','四维削弱'):v*=100
    s=engine.BattleSkill(int(c['ID']),c['name'],t,g,'Heal' if g=='坚韧' else 'Attack',main_param=float(c['param']),trigger_chance=float(c['trigger_chance']),times_limit=int(c['times_limit']),
        turn_cond1=int(c['turn_cond1'] or 0),turn_cond2=int(c['turn_cond2'] or 0),self_bp_cond2=int(c['self_bp_cond2'] or 0),enemy_bp_cond2=int(c['enemy_bp_cond2'] or 0),
        base_crit_rate=(15+t*2)/100 if g=='勇气' else 0.,ignore_def_ratio=(.2,.3,.38,.5,.65,.8)[t-1] if g=='魔力' else 0.,sub_effect_name=sub,sub_param=v,sub_duration=2 if sub in ('虚弱压制','四维削弱','最大流失','已损流失','固定流失') else 0,
        ini_bonus=(1,2,3,5,7,10)[t-1] if g=='先机' else 0)
    stats=tuple(int(c[k]) for k in ('dodge','defense','speed','authority'))
    return s,stats

SKILLS={}
for r in CATALOG:
    s,v=convert(r);SKILLS.setdefault((s.tier,NAME_TO_LETTER[s.genre]),[]).append((s,v,r['sample']))
HOLDOUT_SKILLS={}
holdout_path=Path(__file__).parent/'results/catalog_holdout.json'
if holdout_path.exists():
    for r in json.loads(holdout_path.read_text(encoding='utf-8')):
        s,v=convert(r);HOLDOUT_SKILLS.setdefault((s.tier,NAME_TO_LETTER[s.genre]),[]).append((s,v,r['sample']))

def choice(rng,tier,letter,role,validation=False):
    rows=(HOLDOUT_SKILLS if validation else SKILLS)[(tier,letter)]
    if role=='backup':
        eligible=[x for x in rows if x[0].times_limit>=999 and x[0].turn_cond1==0 and x[0].turn_cond2==0]
        if eligible:rows=eligible
        elif tier>1:return choice(rng,tier-1,letter,role,validation)
    if role=='carry':
        rows=sorted(rows,key=lambda x:x[0].main_param*(1+x[0].base_crit_rate)+x[0].sub_param,reverse=True)[:max(8,len(rows)//2)]
    return rows[rng.randrange(len(rows))]

@lru_cache(maxsize=8192)
def roster(stage,g,pool=0,profile='mixed',carry=2,backup=4,mix=.7,order='default',budgets=None,primary=.6,secondary=.2,rank=False,validation=False):
    n,bp,*_,cap=STAGES[stage];rng=random.Random(seed('natural-members',stage,g,pool,profile,carry,backup,mix));members=[]
    carry=min(n,carry);backup=min(n-carry,backup)
    letters=[g[0]]*round(n*mix)+[g[2]]*(n-round(n*mix));rng.shuffle(letters)
    for pos in range(n):
        role='carry' if pos<carry else ('backup' if pos<carry+backup else 'filler')
        letter=letters[pos]
        if profile=='upper':tier=cap
        elif role=='carry':tier=cap
        elif role=='backup':tier=min(3,max(1,cap-1))
        else:tier=max(1,cap-1-rng.randrange(2))
        s,raw,sample=choice(rng,tier,letter,'filler' if profile=='upper' else role,validation);s=copy.copy(s);s.id=pos+1
        rawtuple=tuple(raw)
        if budgets is not None:
            lower,upper=budgets[s.tier-1];rr=random.Random(seed('natural-stat-budget',stage,g,pool,pos,s.tier,sample));total=rr.randint(lower,upper)
            rawtuple=allocation(letter,total,primary,secondary)
        if rank:rawtuple=tuple(v+x for v,x in zip(rawtuple,(5,5,5,2)))
        # BattlePower uses the stage's canonical BP ruler, equally owned by N members.
        # Four-stat totals always emerge from individual source records; never rescaled.
        members.append(Member(sample,role,rawtuple,bp/n,s))
    if order=='backup_first':members.sort(key=lambda m:({'backup':0,'carry':1,'filler':2}[m.role],m.skill.id))
    elif order=='chance':members.sort(key=lambda m:-m.skill.trigger_chance)
    elif order=='reverse':members.reverse()
    return tuple(members)

# Supported generator effects absent from the native four-skill fixture use the
# same canonical defense/output rules, without modifying the reference source.
_select=core.select_skill;_deal=core.deal;_team=core.Team;_adapter=core.Adapter
class NaturalTeam(_team):
    def heal(self,amount):
        if self.heal_channel=='self_heal' and self.selected_original is not None and self.selected_original.sub_effect_name=='当前战力自愈':
            amount*=max(0.,self.current_bp)/self.max_bp
        return super().heal(amount)
def select_skill(team,enemy,turn):
    s=_select(team,enemy,turn)
    if s is not None and s.sub_effect_name=='固定流失':
        s.sub_effect_name='最大流失';s.sub_param/=enemy.max_bp
        pos=team.selected_owner
        if team.items[pos].kind=='skill_dot':s.sub_param*=1+team.items[pos].value
    return s
def deal(acting,defender,amount,kind,ctx=None,clamp=True,owner=-1):
    if kind=='max_dot' and owner is not None and owner>=0 and acting.members[owner].skill.sub_effect_name=='固定流失':kind='fixed_dot'
    return _deal(acting,defender,amount,kind,ctx,clamp,owner)
class NaturalAdapter(_adapter):
    def visit_If(self,n):
        import ast
        test=ast.unparse(n.test);n=super().visit_If(n)
        if test=="sub == '自身已损反噬'":
            return [n,*ast.parse("if sub == '敌方当前压制':\n    extra = max(0.0, defender.current_bp) * skill.sub_param * (1.0-pct_dr)\n    deal(acting, defender, max(1.0,extra), 'current_pressure')").body]
        return n
core.Team=NaturalTeam;core.select_skill=select_skill;core.deal=deal;core.Adapter=NaturalAdapter
core.CHANNELS=core.CHANNELS+('fixed_dot','current_pressure');core.ACTION=core.action_function(True);core.PARITY_ACTION=core.action_function(False)
simulate=core.simulate;Team=core.Team;CHANNELS=core.CHANNELS;HEALS=core.HEALS

def equipment(members,g,points=0.,axis='theme',mix=.67,loadout=()):
    if axis=='theme':
        v=[0.]*4;v[LETTER[g[0]]]=points*mix;v[LETTER[g[2]]]=points*(1-mix)
        items=[Item('basic',stats=tuple(v)) for _ in members]
    else:items=list(core.equipment(members,g,points,axis))
    for pos,kind,value in loadout:
        old=items[pos];items[pos]=Item(kind,float(value),old.stats,old.bp,True)
    assert len({x[0] for x in loadout})==len(loadout) and len(loadout)<=4
    return tuple(items)
