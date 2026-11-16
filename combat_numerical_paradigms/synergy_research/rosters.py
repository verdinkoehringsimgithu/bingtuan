"""Real labelled people + frozen generator skills + measured 1..30 growth.

Identity/skill associations are synthetic assignments: the labelling file has
no production skill binding. No portrait or authored label file is modified.
"""
import copy
import json
import random
import sys
from collections import Counter
from functools import lru_cache

from settings import ROOT, IDENTITIES

sys.path.insert(0, str(ROOT/'combat_numerical_paradigms/progression_difficulty'))
import study
from study import natural, GENRES, STAGES, Member, seed, NAME_TO_LETTER


@lru_cache(None)
def people():
    path = ROOT/'combat_numerical_paradigms/progression_difficulty/character_statistics/distribution_2026-10-15.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    tags = {r['id']: r['name'] for r in data['identities']}
    rows = []
    for row in data['cards']:
        ids = row['identities']
        if len(ids) != 1:
            raise ValueError('Resolve missing/multiple identities before sampling')
        rows.append(dict(id=row['id'], tier=int(row['tier']), identity=tags[ids[0]]))
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate person IDs')
    return rows


@lru_cache(None)
def bank(name):
    # Cache detached tables: study's bank switch otherwise invalidates old caches.
    study.set_bank(name)
    skills = {key: tuple(rows) for key, rows in natural.SKILLS.items()}
    return skills, dict(study.OLD), dict(study.NEW)


@lru_cache(maxsize=16384)
def growth(start,end):
    return study.grow_path(start,end)


@lru_cache(maxsize=32768)
def build(stage, genre, pool, composition=(), placement='front', bank_name='training',
          preparation='standard'):
    """composition=((bond_key, exact_total_people), ...); one identity/person."""
    n, bp, *_, cap = STAGES[stage]
    rng = random.Random(seed('identity-roster', stage, genre, pool, composition, bank_name))
    available = [dict(r) for r in people() if 1 <= r['tier'] <= cap]
    chosen = []
    targets = set()
    for key, count in composition:
        names = IDENTITIES[key]
        candidates = [r for r in available if r['identity'] in names]
        if count > len(candidates) or count < 0:
            raise ValueError(f'unavailable {key}: requested {count}, available {len(candidates)}')
        if key == 'academy' and count >= 2:
            # Explicit experimental ratio: 1 teacher per three academy members.
            t = min(max(1, count//3), sum(r['identity']=='老师' for r in candidates))
            teachers = rng.sample([r for r in candidates if r['identity']=='老师'], t)
            students = rng.sample([r for r in candidates if r['identity']=='学生'], count-t)
            picks = teachers + students
        else:
            picks = rng.sample(candidates, count)
        chosen.extend(picks)
        ids = {r['id'] for r in picks}
        available = [r for r in available if r['id'] not in ids]
        targets.update(names)
    if len(chosen) > n:
        raise ValueError('Composition exceeds stage capacity')
    # Non-target slots retain real identities but their effects are switched off
    # for single-mechanism ablations. Mixed tests explicitly activate each key.
    available = [r for r in available if r['identity'] not in targets]
    chosen.extend(rng.sample(available, n-len(chosen)))
    chosen.sort(key=lambda r: (r['identity'] not in targets, -r['tier']))
    skills, old, new = bank(bank_name)
    lower, upper = study.LEVEL_BANDS[stage]
    if preparation == 'underdeveloped': upper=(lower+upper)//2
    if preparation == 'strong_collection': lower=(lower+upper+1)//2
    members=[]
    letters=[genre[0]]*round(n*.7)+[genre[2]]*(n-round(n*.7))
    rng.shuffle(letters)
    for pos, (card, letter) in enumerate(zip(chosen, letters)):
        tier = card['tier']
        rows = skills[(tier, letter)]
        role = 'carry' if pos < 2 else 'backup' if pos < min(6,n) else 'filler'
        if role == 'backup':
            repeatable=[r for r in rows if r[0].times_limit>=999 and not r[0].turn_cond1 and not r[0].turn_cond2]
            if repeatable: rows=repeatable
        s, _, sample = rows[rng.randrange(len(rows))]
        s=copy.copy(s);s.id=pos+1
        level=rng.randint(lower,upper)
        key=(tier,letter,sample)
        raw=tuple(int(v) for v in growth(old[key],new[key])[level-1])
        m=Member(sample,role,raw,bp/n,s)
        m.identity=card['identity'];m.person_id=card['id'];m.level=level
        members.append(m)
    multiplier=.75 if preparation=='underdeveloped' else 1.25 if preparation=='strong_collection' else 1.
    points=study.COMMON[(stage,genre)]*multiplier
    load=study.LOADS[(stage,genre)] if preparation=='four_top' else []
    items=natural.equipment(tuple(members),genre,points,loadout=load)
    pairs=list(zip(members,items))
    if placement=='back':pairs.sort(key=lambda x:getattr(x[0],'identity','') in targets)
    elif placement=='shuffle':random.Random(seed('identity-order',stage,genre,pool)).shuffle(pairs)
    elif placement=='interleave':
        x=[r for r in pairs if r[0].identity in targets];y=[r for r in pairs if r[0].identity not in targets];pairs=[]
        while x or y:
            if x:pairs.append(x.pop(0))
            if y:pairs.append(y.pop(0))
    elif placement!='front':raise ValueError(placement)
    return tuple(x[0] for x in pairs),tuple(x[1] for x in pairs)


@lru_cache(None)
def encounter(stage, difficulty):
    data=json.loads((ROOT/'combat_numerical_paradigms/progression_difficulty/results/encounter_model.json').read_text(encoding='utf-8'))
    row=next(r for r in data['recommended'] if r['stage']==stage and r['difficulty']==difficulty)
    rho=row['rho_center']
    return row['enemy_genre'], (row['alpha']*rho,row['beta']*rho,0.,0.,0.,1.)


def availability():
    rows=[]
    for stage, info in enumerate(STAGES):
        counts=Counter(r['identity'] for r in people() if r['tier']<=info[-1])
        for key,names in IDENTITIES.items():
            rows.append(dict(stage=stage+1,members_cap=info[0],bond=key,
                             available=sum(counts[x] for x in names),tier_cap=info[-1]))
    return rows
