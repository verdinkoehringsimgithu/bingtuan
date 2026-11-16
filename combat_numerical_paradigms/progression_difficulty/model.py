"""Dependency-free public numerical model for level growth and encounter bands."""
import json
from pathlib import Path

FIELDS=('courage','resilience','initiative','magic')


def character_stats(level,start,end,power=1.):
    """Interpolate four integer endpoints, retaining monotonic stats and budget."""
    if not 1<=level<=30 or int(level)!=level:raise ValueError('level must be an integer in 1..30')
    if power<=0:raise ValueError('power must be positive')
    a=[int(start[k]) for k in FIELDS] if isinstance(start,dict) else list(start)
    b=[int(end[k]) for k in FIELDS] if isinstance(end,dict) else list(end)
    if len(a)!=4 or len(b)!=4 or any(y<x for x,y in zip(a,b)):raise ValueError('endpoints must have four nondecreasing integer stats')
    current=a.copy()
    for step in range(2,int(level)+1):
        fraction=((step-1)/29)**power;desired=[x+(y-x)*fraction for x,y in zip(a,b)];total=round(sum(a)+(sum(b)-sum(a))*fraction)
        for _ in range(total-sum(current)):
            axis=max(range(4),key=lambda k:desired[k]-current[k]);current[axis]+=1
    return dict(zip(FIELDS,current))


def encounter(stage,difficulty,archetype=None,position='center',model_path=None):
    """Return one measured stage/difficulty band without player-adaptive enemies."""
    aliases={'难':'hard','很难':'very_hard','非常难':'extremely_hard'};difficulty=aliases.get(difficulty,difficulty)
    if not 1<=stage<=6 or int(stage)!=stage:raise ValueError('stage must be an integer in 1..6')
    if position not in ('lower','center','upper'):raise ValueError('position must be lower, center or upper')
    data=json.loads((Path(model_path) if model_path else Path(__file__).parent/'results/encounter_model.json').read_text(encoding='utf-8'))
    source=data['recommended'] if archetype is None else data['all_archetypes']
    rows=[r for r in source if r['stage']==stage-1 and r['difficulty']==difficulty and (archetype is None or r['enemy_genre']==archetype)]
    if len(rows)!=1:raise ValueError('unknown difficulty/archetype')
    row=rows[0];r=row['rho_'+position];ruler=data['stages'][stage-1]
    return dict(stage=stage,members_cap=ruler['members'],skill_tier_reference_cap=ruler['skill_tier_cap'],player_level_reference=ruler['level_band'],difficulty=difficulty,enemy_genre=row['enemy_genre'],rho=r,rho_range=[row['rho_lower'],row['rho_upper']],
                enemy_max_bp=row['alpha']*r*ruler['bp'],enemy_attack_factor=row['beta']/row['alpha'],enemy_full_bp_base_hit=.135*row['beta']*r*ruler['bp'],
                enemy_mean_four_stats=row['enemy_mean_four_stats'],standard_reference_wr=row.get('confirmed_standard_wr',row.get('measured_reference_wr')),
                all_player_flows_wr_range=row.get('confirmed_flow_range',row.get('measured_flow_range')),calibration='fixed encounter; player strength changes do not rescale this enemy')
