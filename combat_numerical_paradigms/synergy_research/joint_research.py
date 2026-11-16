"""Frozen-engine identity / skill-supply / four-item / counter-scenario study.

New protocol and checkpoints; previous order experiments remain unchanged.
"""
import argparse
from collections import Counter
import concurrent.futures as cf
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time

from joint_core import simulate
from order_search import optimize, initial_orders, reordered, rank_score, snapshot
from rosters import build, bank, encounter, availability, GENRES, STAGES, seed, natural, study
from run_bonds import atomic_json, count_options, fit_skills, signature as combat_signature
from settings import HERE, ROOT, IDENTITIES
from skill_supply import transform

POLICIES = ('random', 'repeatable', 'throughput', 'matched')
GEARS = ('basic', 'four_top')
SCENARIOS = ('military_ninja', 'killer_recovery', 'sage_debuff', 'hunter_resilience')


def configs():
    rows = json.loads((HERE / 'results/selected_coefficients.json').read_text(encoding='utf-8'))
    return {(r['stage'], r['bond']): r['config'] for r in rows if r['soft_delta_reference'] == .1}


def count_for(s, key):
    options = count_options(s, key)
    if not options: return None
    n = STAGES[s][0]
    value = min(options, key=lambda x: abs(x - max(1, n // 3)))
    if key in ('academy', 'sword', 'cult'): value = max(2, value)
    if key == 'military': value = max(value, math.ceil(n / 2))
    return value


def player_members(job):
    for attempt in range(64):
        pool = job['pool'] + attempt * 1009
        mm, ii = build(job['stage'], job['genre'], pool, ((job['bond'], job['count']),), 'front', job['bank'])
        if job['bond'] != 'cult' or len({m.skill.tier for m in mm if m.identity == '拜火教'}) >= 2:
            return mm, ii, pool
    raise ValueError('No legitimate cult tier pair in deterministic sampling attempts')


def skill_supply(mm, ii, policy, bank_name, key):
    if policy == 'matched': return fit_skills(mm, 0, bank_name), ii
    if policy == 'random': return mm, ii
    return transform(mm, ii, policy, bank_name, key)


def equipment(mm, genre, stage, gear, scale=1.):
    basic = natural.equipment(mm, genre, study.COMMON[(stage, genre)] * scale)
    if gear == 'basic': return basic
    load = study.LOADS[(stage, genre)]
    assert len(load) == 4
    remaining = set(range(len(mm))); out = list(basic)
    # An explicit allocation candidate, fixed before order search. Gear follows
    # its owner afterward. The item mechanisms/values come from the frozen CSV.
    for _, kind, value in sorted(load, key=lambda x: x[1] == 'opening_shield'):
        def score(i):
            m = mm[i]; sk = m.skill; p = sk.trigger_chance / 100
            gate = int(bool(sk.turn_cond1 or sk.turn_cond2 or sk.self_bp_cond2 or sk.enemy_bp_cond2))
            coverage = 1 if sk.times_limit <= 0 or sk.times_limit >= 999 else min(1, sk.times_limit / 8)
            output = p * sk.main_param / 100 * coverage / (1 + gate)
            if kind == 'owner_stats': return sum(m.stats)
            if kind == 'opening_shield': return -output
            if kind == 'normal_damage': return 10 * (m.identity == '帮派') + 1 - p
            if kind in ('skill_heal', 'overheal_shield'): return p * (sk.main_type == 'Heal' or sk.sub_effect_name == '战力吸收')
            if kind == 'skill_dot': return p * (sk.sub_effect_name in ('最大流失', '已损流失', '固定流失'))
            if kind == 'extra_use': return p * (0 < sk.times_limit < 999)
            return output if sk.main_type != 'Heal' else -1
        pos = max(remaining, key=lambda i: (score(i), -i)); remaining.remove(pos)
        old = out[pos]; out[pos] = natural.Item(kind, float(value), old.stats, old.bp, True)
    assert len(out) == len(mm) and sum(i.top for i in out) == 4
    assert all(a.stats == b.stats for a, b in zip(out, basic))
    return tuple(out)


def profile_enemy(mm, ii, bank_name, profile):
    rows, _, _ = bank(bank_name); pairs = []
    for m, item in zip(mm, ii):
        x = copy.copy(m); sk = m.skill; candidates = rows[(sk.tier, natural.NAME_TO_LETTER[sk.genre])]
        if profile == 'debuff' and sk.genre == '先机':
            eligible = [r for r in candidates if r[0].sub_effect_name in ('虚弱压制', '四维削弱', '最大流失', '已损流失')]
            if eligible:
                chosen = max(eligible, key=lambda r: r[0].trigger_chance * r[0].sub_param /
                             (1 + int(bool(r[0].turn_cond1 or r[0].turn_cond2 or r[0].self_bp_cond2 or r[0].enemy_bp_cond2))))
                x.skill = copy.copy(chosen[0]); x.skill.id = sk.id
        pairs.append((x, item))
    # Fixed authored NPC order; no player test outcomes are used to build it.
    pairs.sort(key=lambda p: (p[0].skill.main_type == 'Heal',
                             not (0 < p[0].skill.times_limit < 999),
                             -p[0].skill.main_param * p[0].skill.trigger_chance))
    if profile == 'recovery':
        maids = [p for p in pairs if p[0].identity == '女仆']
        others = [p for p in pairs if p[0].identity != '女仆']
        pairs = others[:2] + maids + others[2:]
    return tuple(p[0] for p in pairs), tuple(p[1] for p in pairs)


def enemy_states(job, all_configs):
    s = job['stage']; scenario = job.get('scenario', 'ordinary'); n = STAGES[s][0]
    h, macro = encounter(s, job['difficulty'])
    enemy_pool = job['pool'] + 100003
    enabled = (); cfg = {}; composition = (); profile = 'standard'
    if scenario == 'military_ninja':
        h = 'M_I'; key = 'ninja'; profile = 'standard'
    elif scenario == 'killer_recovery':
        h = 'C_I'; key = 'maid'; profile = 'recovery'
    elif scenario == 'sage_debuff':
        h = 'R_I'; key = None
    else: key = None
    if key:
        available = next(r['available'] for r in availability() if r['stage'] == s + 1 and r['bond'] == key)
        composition = ((key, min(available, math.ceil(n / 2))),)
        cfg = dict(all_configs[(s, key)])
        if key == 'maid': cfg['maid_kind'] = 'heal'
    mm, ii = build(s, h, enemy_pool, composition, 'front', job['bank'])
    ii = equipment(mm, h, s, 'four_top' if job['phase'] == 'counters' else 'basic')
    mm, ii = profile_enemy(mm, ii, job['bank'], profile)
    ordinary = dict(name='control', members=mm, items=ii, enabled=(), config={}, macro=macro)
    if scenario == 'ordinary': return [ordinary]
    if key:
        return [ordinary, dict(ordinary, name='challenge', enabled=(key,), config=cfg)]
    if scenario == 'sage_debuff':
        dm, di = profile_enemy(mm, ii, job['bank'], 'debuff')
        return [ordinary, dict(ordinary, name='challenge', members=dm, items=di)]
    if scenario == 'hunter_resilience':
        states = []
        for share in (.25, .65):
            changed = []
            for m in mm:
                x = copy.copy(m); total = sum(m.stats)
                x.stats = (total * (1-share)/3, total * share, total * (1-share)/3, total * (1-share)/3)
                assert abs(sum(x.stats) - sum(m.stats)) < 1e-9
                changed.append(x)
            states.append(dict(ordinary, name='control' if share == .25 else 'challenge', members=tuple(changed)))
        return states
    raise ValueError(scenario)


def compact(r):
    keep = ('win', 'censored', 'draw', 'turns', 'hp', 'enemy_hp', 'margin', 'normal_rate',
            'damage', 'owner_casts', 'owner_reached', 'metrics', 'enemy_metrics', 'final_stats', 'enemy_final_stats')
    return {k: r[k] for k in keep}


def solve(mm, ii, enemy, job, all_configs, prefix):
    key = job['bond']; cfg = all_configs[(job['stage'], key)]; execution_count = 0
    seed_map = {split: [seed('joint-20261020', job['phase'], job['stage'], job['genre'], job['pool'],
                             job['difficulty'], split, i) for i in range(job[split + '_trials'])]
                for split in ('train', 'select', 'cross', 'test')}
    assert len({v for seq in seed_map.values() for v in seq}) == sum(map(len, seed_map.values()))
    def run(order, split, active, trace=False):
        nonlocal execution_count
        m, it = reordered(mm, ii, order); results = []; traces = []
        for j, bs in enumerate(seed_map[split]):
            r, telemetry, _, defender = simulate(m, enemy['members'], bs, it, enemy['items'], p=enemy['macro'],
                          enabled=(key,) if active else (), config=cfg,
                          enemy_enabled=enemy['enabled'], enemy_config=enemy['config'], telemetry=trace and j == 0)
            r = compact(r)
            r['enemy_prevented_request_fraction'] = r['enemy_metrics'].get('killer_healing_prevented', 0.) / defender.max_bp
            results.append(r)
            if telemetry: traces.append(telemetry)
        execution_count += len(results)
        return results, traces
    plans = {}
    for state in ('off', 'on'):
        plans[state] = optimize(len(mm), initial_orders(mm, key),
            lambda order, split: rank_score(run(order, split, state == 'on')[0]),
            seed('joint-search', job['stage'], key, job['genre'], job['pool'], state),
            job['budget'], job['shortlist'])
    # Both states receive the union of the independently selected solutions.
    # A second validation stream chooses within it, before blind final seeds.
    candidates = list(dict.fromkeys(tuple(p['order']) for p in plans.values()))
    for state in ('off', 'on'):
        ranked = [(rank_score(run(o, 'cross', state == 'on')[0]), o) for o in candidates]
        value, order = max(ranked, key=lambda pair: (pair[0], tuple(-x for x in pair[1])))
        plans[state]['order'] = order; plans[state]['cross'] = value
    finals = {}; traces = {}
    for name, order, active in (('on', plans['on']['order'], True), ('off', plans['off']['order'], False),
                                 ('off_at_on', plans['on']['order'], False)):
        finals[name], traces[name] = run(order, 'test', active, job['phase'] == 'counters')
    metrics = {name: {k: sum(r[k] for r in rows) / len(rows)
                     for k in ('win','censored','turns','hp','enemy_hp','margin','normal_rate','damage','enemy_prevented_request_fraction')}
               for name, rows in finals.items()}
    differences = {}
    for label, control in (('practical', 'off'), ('mechanical', 'off_at_on')):
        vals = [a['win'] - b['win'] for a,b in zip(finals['on'], finals[control])]; avg = sum(vals)/len(vals)
        se = math.sqrt(sum((v-avg)**2 for v in vals)/(len(vals)-1)/len(vals))
        differences[label] = dict(mean=avg, se=se)
    return dict(name=prefix, plans=plans, seeds=seed_map, metrics=metrics, differences=differences,
                executed_battles=execution_count, trials=finals, traces=traces)


def evaluate(job):
    started = time.perf_counter(); all_configs = configs(); mm, original_items, actual_pool = player_members(job)
    enemies = enemy_states(job, all_configs); variants = []; fingerprints = {}; executed = 0
    for variant in job['variants']:
        members, _ = skill_supply(mm, original_items, variant['policy'], job['bank'], job['bond'])
        items = equipment(members, job['genre'], job['stage'], variant['gear'], variant.get('scale', 1.))
        assert all(a.person_id == b.person_id and a.stats == b.stats and a.level == b.level and
                   a.skill.id == b.skill.id and a.skill.tier == b.skill.tier and a.skill.genre == b.skill.genre
                   for a,b in zip(mm, members))
        assert len(members) == STAGES[job['stage']][0] and len(items) == len(members)
        snap = snapshot(members, items); fingerprint = hashlib.sha256(json.dumps(snap, sort_keys=True).encode()).hexdigest()
        if fingerprint in fingerprints:
            variants.append(dict(variant=variant, alias=fingerprints[fingerprint])); continue
        index = len(variants); fingerprints[fingerprint] = index
        outcomes = []
        for enemy in enemies:
            outcome = solve(members, items, enemy, job, all_configs, enemy['name'])
            executed += outcome['executed_battles']; outcomes.append(outcome)
        variants.append(dict(variant=variant, snapshot=snap, outcomes=outcomes))
    raw = dict(job=job, actual_player_pool=actual_pool, variants=variants,
               enemies=[{**e, 'members':snapshot(e['members'], e['items']), 'items':None} for e in enemies])
    target = Path(job['output']) / 'replicates' / (job['key'] + '.json.gz'); target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix('.tmp')
    with gzip.open(tmp, 'wt', encoding='utf-8') as stream: json.dump(raw, stream, ensure_ascii=False)
    tmp.replace(target)
    summaries = []
    for entry in variants:
        physical = variants[entry['alias']] if 'alias' in entry else entry
        summaries.append(dict(variant=entry['variant'], alias=entry.get('alias'), outcomes=[
            {k:v for k,v in outcome.items() if k not in ('trials','traces','seeds')}
            for outcome in physical['outcomes']]))
    return dict(variants=summaries, executed_battles=executed, seconds=time.perf_counter()-started,
                actual_player_pool=actual_pool)


def jobs_for(phase, args, selection=None):
    all_cfg = configs(); jobs = []
    for s in range(6):
        for key in IDENTITIES:
            if (s,key) not in all_cfg or (args.bonds and key not in args.bonds): continue
            if phase == 'counters' and key not in ('military','killer','sage','hunter'): continue
            for g in GENRES:
                for difficulty in (('hard','extremely_hard') if phase != 'screen' else ('hard',)):
                    variants = []
                    if phase == 'counters': variants = [dict(policy='random',gear='four_top',scale=1.)]
                    elif phase == 'screen': variants = [dict(policy=p,gear=e,scale=1.) for e in GEARS for p in POLICIES]
                    else:
                        for e in GEARS:
                            chosen = selection[f'{s}:{key}:{e}']
                            variants += [dict(policy='random',gear=e,scale=1.),dict(policy=chosen,gear=e,scale=1.)]
                            if args.bounds:
                                variants += [dict(policy=chosen,gear=e,scale=z) for z in (.75,1.25)]
                    jobs.append(dict(phase=phase,stage=s,bond=key,genre=g,count=count_for(s,key),difficulty=difficulty,
                           scenario={'military':'military_ninja','killer':'killer_recovery','sage':'sage_debuff','hunter':'hunter_resilience'}.get(key,'ordinary') if phase=='counters' else 'ordinary',
                           variants=variants,bank='validation' if phase=='screen' else 'final',
                           pool=170000 if phase=='counters' else 180000 if phase=='screen' else 200000,
                           budget=args.budget,shortlist=args.shortlist,train_trials=args.train_trials,
                           select_trials=args.select_trials,cross_trials=args.cross_trials,test_trials=args.test_trials))
    return jobs


def select_policies(rows):
    scores = {}
    for cell in rows:
        j = cell['job']
        for entry in cell['result']['variants']:
            v = entry['variant']; score = entry['outcomes'][0]['metrics']['on']
            key = (j['stage'],j['bond'],v['gear'],v['policy'])
            scores.setdefault(key,[]).append((score['win'],score['margin']))
    selected = {}
    for s,key,e,_ in scores:
        candidates = []
        for p in POLICIES:
            group = scores[(s,key,e,p)]
            candidates.append(((sum(x[0] for x in group)/len(group),sum(x[1] for x in group)/len(group),-POLICIES.index(p)),p))
        selected[f'{s}:{key}:{e}'] = max(candidates)[1]
    return selected


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phase',choices=('counters','screen','confirm'),required=True)
    p.add_argument('--workers',type=int,default=6); p.add_argument('--output',type=Path,default=HERE/'results/joint')
    p.add_argument('--bonds',nargs='+',choices=tuple(IDENTITIES))
    p.add_argument('--budget',type=int,default=24);p.add_argument('--shortlist',type=int,default=3)
    p.add_argument('--train-trials',type=int,default=4);p.add_argument('--select-trials',type=int,default=12)
    p.add_argument('--cross-trials',type=int,default=12);p.add_argument('--test-trials',type=int,default=64)
    p.add_argument('--bounds',action='store_true')
    args = p.parse_args(); assert args.budget>=16 and args.test_trials>=2
    args.output.mkdir(exist_ok=True,parents=True)
    core_sig,sources = combat_signature()
    assert core_sig == json.loads((HERE/'results/input_manifest.json').read_text(encoding='utf-8'))['signature']
    paths = [Path(__file__),HERE/'joint_core.py',HERE/'order_search.py',HERE/'skill_supply.py',HERE/'results/selected_coefficients.json',
             ROOT/'combat_numerical_paradigms/natural_research/results/equipment_operating_candidates.csv']
    manifest = dict(combat_signature=core_sig, sources={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in paths})
    sig = hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest();manifest['signature']=sig
    atomic_json(args.output/'manifest.json',manifest)
    db = sqlite3.connect(args.output/'checkpoints.sqlite');db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS cells (key TEXT PRIMARY KEY,phase TEXT,signature TEXT,job TEXT,result TEXT)');db.commit()
    selection = json.loads((args.output/'selected_supply.json').read_text(encoding='utf-8')) if args.phase=='confirm' else None
    if args.phase == 'confirm':
        provenance = json.loads((args.output/'selected_supply_provenance.json').read_text(encoding='utf-8'))
        screen_path = args.output/'screen.json'
        assert provenance['signature'] == sig, 'Skill selection came from different source inputs'
        assert provenance['screen_sha256'] == hashlib.sha256(screen_path.read_bytes()).hexdigest()
        assert provenance['selection_sha256'] == hashlib.sha256((args.output/'selected_supply.json').read_bytes()).hexdigest()
        assert selection == select_policies(json.loads(screen_path.read_text(encoding='utf-8'))['rows'])
    jobs = jobs_for(args.phase,args,selection); wanted = set(); pending = {}
    try:
        with cf.ProcessPoolExecutor(args.workers) as pool:
            for job in jobs:
                encoded=json.dumps(job,sort_keys=True); key=hashlib.sha256((sig+encoded).encode()).hexdigest();wanted.add(key)
                if db.execute('SELECT key FROM cells WHERE key=?',(key,)).fetchone(): continue
                pending[pool.submit(evaluate,{**job,'key':key,'output':str(args.output.resolve())})]=(key,encoded)
            print(f'{args.phase}: {len(pending)} pending / {len(jobs)} cells',flush=True)
            for i,future in enumerate(cf.as_completed(pending),1):
                key,encoded=pending[future];result=future.result()
                db.execute('INSERT INTO cells VALUES (?,?,?,?,?)',(key,args.phase,sig,encoded,json.dumps(result)));db.commit()
                if i%6==0 or i==len(pending):print(f'{args.phase}: saved {i}/{len(pending)}',flush=True)
        rows=[dict(key=k,job=json.loads(j),result=json.loads(r)) for k,j,r in db.execute('SELECT key,job,result FROM cells WHERE signature=? AND phase=?',(sig,args.phase)) if k in wanted]
        atomic_json(args.output/(args.phase+'.json'),dict(signature=sig,cells=len(rows),executed_battles=sum(x['result']['executed_battles'] for x in rows),rows=rows))
        if args.phase=='screen':
            atomic_json(args.output/'selected_supply.json',select_policies(rows))
            atomic_json(args.output/'selected_supply_provenance.json',dict(signature=sig,cells=len(rows),
                screen_sha256=hashlib.sha256((args.output/'screen.json').read_bytes()).hexdigest(),
                selection_sha256=hashlib.sha256((args.output/'selected_supply.json').read_bytes()).hexdigest()))
        print(f'{args.phase}: complete {len(rows)} cells / {sum(x["result"]["executed_battles"] for x in rows):,} executions',flush=True)
    finally: db.close()


if __name__=='__main__':main()
