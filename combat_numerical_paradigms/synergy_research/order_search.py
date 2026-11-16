"""Optimize fixed rosters before evaluating identity strength; resumable PvE study.

No member, skill, level, stat, or equipment changes during order search.
Training, selection and held-out battle seeds are disjoint. N=5 enumerates
all 120 permutations on the finite training sample; larger N uses bounded
multi-start insertion/swap search, not a proof of global optimum.
"""
import argparse
import concurrent.futures as cf
import csv
import gzip
import hashlib
import itertools
import json
import math
import platform
import random
import sqlite3
import sys
import time
from pathlib import Path

from bond_core import simulate
from rosters import build, encounter, seed, GENRES, STAGES
from run_bonds import atomic_json, count_options, signature
from settings import HERE, IDENTITIES, CN


def reordered(members, items, order):
    assert sorted(order) == list(range(len(members))), 'Order must be a permutation'
    return tuple(members[i] for i in order), tuple(items[i] for i in order)


def initial_orders(members, key):
    n = len(members)
    original = tuple(range(n))
    target = set(IDENTITIES[key])
    orders = [original, original[::-1]]
    def add(score):
        orders.append(tuple(sorted(original, key=lambda i: (score(members[i]), i))))
    finite = lambda s: 0 < s.times_limit < 999
    gated = lambda s: bool(s.turn_cond1 or s.turn_cond2 or s.self_bp_cond2 or s.enemy_bp_cond2)
    # These are search seeds only; no priority rule is imposed on the result.
    add(lambda m: (m.identity not in target, -m.skill.tier))
    add(lambda m: (m.identity in target, -m.skill.tier))
    add(lambda m: (not finite(m.skill), -m.skill.main_param * m.skill.trigger_chance))
    add(lambda m: (-m.skill.main_param * m.skill.trigger_chance, -m.skill.tier))
    add(lambda m: (-m.skill.trigger_chance, -m.skill.main_param))
    add(lambda m: (not gated(m.skill), not finite(m.skill), -m.skill.main_param))
    add(lambda m: (2 if m.identity == '女仆' else 0 if finite(m.skill) or gated(m.skill) else 3,
                   -m.skill.main_param))
    add(lambda m: (0 if m.identity in target and finite(m.skill) else 1 if finite(m.skill) or gated(m.skill) else 2,
                   -m.skill.trigger_chance))
    # A different first maid is a different headmaid, with her OWN equipment.
    if key == 'maid':
        support = orders[-2]
        for i in original:
            if members[i].identity == '女仆':
                for pos in (0, n // 2, n - 1):
                    rest = [j for j in support if j != i]
                    rest.insert(pos, i)
                    orders.append(tuple(rest))
    return list(dict.fromkeys(orders))


def rank_score(rows):
    n = len(rows)
    # Lexicographic: win rate first. Margin only breaks finite-sample ties.
    return (sum(r['win'] for r in rows) / n,
            sum(r['margin'] for r in rows) / n,
            -sum(r['censored'] for r in rows) / n)


def optimize(n, starting, score, rng_seed, budget=128, shortlist=8):
    """score(order, split) owns the battle seeds; never receives test results."""
    rng = random.Random(rng_seed)
    scored = {}
    def visit(order):
        order = tuple(order)
        if order not in scored:
            scored[order] = tuple(score(order, 'train'))
    if n <= 5:
        for order in itertools.permutations(range(n)):
            visit(order)
    else:
        for order in starting[:budget]:
            visit(order)
        # Include exploration instead of trusting a single local optimum.
        while len(scored) < budget:
            if rng.random() < .18:
                order = list(range(n)); rng.shuffle(order)
            else:
                best = sorted(scored, key=lambda x: (scored[x], tuple(-i for i in x)), reverse=True)[:6]
                order = list(rng.choice(best))
                for _ in range(1 if rng.random() < .8 else 3):
                    a, b = rng.sample(range(n), 2)
                    if rng.random() < .5:
                        order[a], order[b] = order[b], order[a]
                    else:
                        order.insert(b, order.pop(a))
            visit(order)
    ranked = sorted(scored, key=lambda x: (scored[x], tuple(-i for i in x)), reverse=True)
    selected = [(order, tuple(score(order, 'select'))) for order in ranked[:shortlist]]
    selected.sort(key=lambda x: (x[1], scored[x[0]], tuple(-i for i in x[0])), reverse=True)
    order, validation = selected[0]
    return dict(order=order, train=scored[order], selection=validation,
                searched_orders=len(scored), selected_orders=len(selected),
                exhaustive_training=n <= 5, global_population_optimum_proven=False)


def snapshot(members, items):
    return [dict(person_id=m.person_id, identity=m.identity, level=m.level,
                 uid=m.uid, role=m.role, bp=m.bp, stats=list(m.stats),
                 skill=vars(m.skill), item=vars(it)) for m, it in zip(members, items)]


def evaluate(job):
    started = time.perf_counter()
    stage, key, genre, pool = (job[x] for x in ('stage', 'bond', 'genre', 'pool'))
    h, p = encounter(stage, job['difficulty'])
    members, items = build(stage, genre, pool, ((key, job['count']),), 'front', 'final')
    enemy, enemy_items = build(stage, h, pool + 100003, (), 'front', 'final')
    ref, ref_items = build(stage, genre, pool, (), 'front', 'final')
    split_seeds = {split: tuple(seed('order-20261016', stage, genre, pool, job['difficulty'], split, i)
                               for i in range(job[split + '_trials']))
                   for split in ('train', 'select', 'test')}
    assert all(not set(split_seeds[a]) & set(split_seeds[b])
               for a, b in itertools.combinations(split_seeds, 2))
    executed = 0
    def battles(mm, ii, order, split, active):
        nonlocal executed
        mm, ii = reordered(mm, ii, order)
        rows = []
        for bs in split_seeds[split]:
            r, *_ = simulate(mm, enemy, bs, ii, enemy_items, p=p,
                             enabled=(key,) if active else (), config=job['config'])
            rows.append(r)
        executed += len(rows)
        return rows
    plans = {}
    for name, mm, ii, active in (('off', members, items, False),
                                  ('on', members, items, True), ('reference', ref, ref_items, False)):
        plans[name] = optimize(len(mm), initial_orders(mm, key),
                               lambda order, split: rank_score(battles(mm, ii, order, split, active)),
                               seed('order-search', stage, key, genre, pool, name),
                               job['budget'], job['shortlist'])
    # Hold out once, AFTER all three orders are frozen. Never select by test WR.
    finals = {}
    for name, mm, ii, active in (('off', members, items, False),
                                  ('on', members, items, True), ('reference', ref, ref_items, False)):
        finals[name] = battles(mm, ii, plans[name]['order'], 'test', active)
    finals['off_at_on_order'] = battles(members, items, plans['on']['order'], 'test', False)
    keep = ('win', 'turns', 'hp', 'enemy_hp', 'margin', 'censored', 'draw', 'normal_rate')
    # Full member-level casting diagnostics reveal blocked backups/unused recovery.
    final_rows = [{name: {k: r[k] for k in keep + ('owner_casts', 'owner_reached', 'metrics')}
                   for name, r in zip(finals, batch)} for batch in zip(*finals.values())]
    metrics = {name: {k: sum(r[k] for r in rows) / len(rows) for k in keep}
               for name, rows in finals.items()}
    differences = {}
    for label, left, right in (('practical_gain', 'on', 'off'),
                                ('mechanical_same_order', 'on', 'off_at_on_order'),
                                ('net_vs_unrestricted', 'on', 'reference')):
        vals = [a['win'] - b['win'] for a, b in zip(finals[left], finals[right])]
        mean = sum(vals) / len(vals)
        se = math.sqrt(sum((v - mean) ** 2 for v in vals) / (len(vals) - 1) / len(vals))
        differences[label] = dict(mean=mean, se=se)
    target = Path(job['output']) / 'replicates' / (job['key'] + '.json.gz')
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix('.tmp')
    with gzip.open(tmp, 'wt', encoding='utf-8') as stream:
        json.dump(dict(job=job, plans=plans, seeds=split_seeds,
                       members=snapshot(members, items), enemy=snapshot(enemy, enemy_items),
                       reference=snapshot(ref, ref_items), trials=final_rows), stream, ensure_ascii=False)
    tmp.replace(target)
    return dict(plans=plans, metrics=metrics, differences=differences, executed_battles=executed,
                seconds=time.perf_counter() - started, trials=job['test_trials'])


def summarize(rows, output, sig):
    flat = []
    for row in rows:
        job, r = row['job'], row['result']
        flat.append(dict(stage=job['stage'] + 1, capacity=STAGES[job['stage']][0], bond=job['bond'],
                         identity=CN[job['bond']], genre=job['genre'], count=job['count'],
                         pool=job['pool'], difficulty=job['difficulty'], trials=r['trials'],
                         optimized_on=r['metrics']['on']['win'], optimized_off=r['metrics']['off']['win'],
                         optimized_reference=r['metrics']['reference']['win'],
                         **{name: val['mean'] for name, val in r['differences'].items()},
                         censored=r['metrics']['on']['censored'], executed_battles=r['executed_battles']))
    with (output / 'optimized_order_summary.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=flat[0]); writer.writeheader(); writer.writerows(flat)
    atomic_json(output / 'completed.json', dict(signature=sig, cells=len(rows),
                                              executed_battles=sum(r['executed_battles'] for r in flat), rows=rows))
    lines = ['# 最优顺位评估：2026-10-16修订', '',
             '正式强度口径改为固定成员、技能、等级与装备后的搜索最优顺位。前置、后置、随机与人工编排只用于搜索起点或诊断，不取其平均值定强度。', '',
             '有羁绊、同成员关闭羁绊、不限制身份的参考阵容分别搜索；三者面对同一固定阶段敌人。敌方是固定PvE遭遇，不能据此宣称双方优化的PvP均衡。', '',
             '搜索种子、候选选择种子和最终确认种子分开。测试期间顺位固定，不窥视当场随机结果，也不逐回合重排。装备随角色一起移动，技能ID与剩余次数归属保持不变。', '',
             '5人对有限训练样本穷举120种排列；10～30人多起点交换/插入搜索。两者都不证明真实胜率的全局最优，报告只称“搜索最优”。', '',
             '实用收益＝各自优化后的有羁绊胜率−关闭羁绊胜率；同顺位机制收益＝有羁绊−在该有羁绊最优顺位关闭效果；整队净收益＝优化后的有羁绊−优化后的不限制身份参考。', '',
             f'当前累计{len(flat)}个固定阵容单元，{sum(r["executed_battles"] for r in flat):,}次对战执行。下表为本次抽样验证，误差需按独立阵容单元评估，不能把同阵容的多次ROLL当成同样数量的独立阵容。', '',
             '| 身份 | 阶段覆盖 | 独立阵容单元 | 搜索最优开启胜率 | 搜索最优关闭胜率 | 实用收益 | 整队净收益 |',
             '| --- | --- | --- | --- | --- | --- | --- |']
    for key in IDENTITIES:
        group = [r for r in flat if r['bond'] == key]
        if not group: continue
        avg = lambda k: sum(r[k] for r in group) / len(group)
        stages = '/'.join(str(s) for s in sorted({r['capacity'] for r in group}))
        lines.append(f'| {CN[key]} | {stages} | {len(group)} | {avg("optimized_on"):.1%} | {avg("optimized_off"):.1%} | {100*avg("practical_gain"):+.2f}个百分点 | {100*avg("net_vs_unrestricted"):+.2f}个百分点 |')
    lines += ['', '本次保留旧候选系数，用于核对顺位评估方法；未据本次小样本重新校准23项数值，也未改变技能投放。具体范围由CSV和作业记录列出，不外推到未测人数、阵容、难度、羁绊组合或经济收益。',
              '旧版表格仍是预设顺位下的历史数据。尤其“女仆负收益”“学者偏弱”等判断，不能再直接作为玩家优化顺位后的最终设计结论。', '',
              '后续系数、人数曲线、技能投放和两两组合的正式比较，统一在相同搜索预算下分别优化，再用新阵容及未参与选择的随机种子确认；本次结果不等于全部矩阵已经重跑。', '',
              '所有逐场结果、人物技能装备快照、三套顺位、搜索规模与随机种子见replicates/*.json.gz；程序签名见manifest.json。']
    (output / 'ORDER_GUIDE.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--bonds', nargs='+', choices=tuple(IDENTITIES), default=list(IDENTITIES))
    ap.add_argument('--stages', nargs='+', type=int, choices=range(1, 7), default=list(range(1, 7)))
    ap.add_argument('--genres', nargs='+', choices=GENRES, default=GENRES)
    ap.add_argument('--difficulty', choices=('hard', 'extremely_hard'), default='extremely_hard')
    ap.add_argument('--rosters', type=int, default=2)
    ap.add_argument('--count-mode', choices=('small', 'calibrated'), default='small')
    ap.add_argument('--budget', type=int, default=128)
    ap.add_argument('--shortlist', type=int, default=8)
    ap.add_argument('--train-trials', type=int, default=12)
    ap.add_argument('--select-trials', type=int, default=48)
    ap.add_argument('--test-trials', type=int, default=256)
    ap.add_argument('--output', type=Path, default=HERE / 'results' / 'optimal_order')
    args = ap.parse_args()
    assert args.budget >= 16 and 1 <= args.shortlist <= args.budget
    assert min(args.rosters, args.train_trials, args.select_trials) >= 1 and args.test_trials >= 2
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    current, sources = signature()
    original = json.loads((HERE / 'results/input_manifest.json').read_text(encoding='utf-8'))
    if current != original['signature']:
        raise RuntimeError('Frozen combat input changed: audit model before reusing previous coefficients')
    chosen_path = HERE / 'results/selected_coefficients.json'
    chosen = json.loads(chosen_path.read_text(encoding='utf-8'))
    coefficients = {(r['stage'], r['bond']): r for r in chosen if r['soft_delta_reference'] == .1}
    manifest = dict(combat_signature=current, sources=sources,
                    optimizer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    coefficient_sha256=hashlib.sha256(chosen_path.read_bytes()).hexdigest(),
                    python=sys.version, platform=platform.platform(), study='fixed-PvE-order-20261016')
    sig = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    # A run's CLI belongs to each job key, so different budgets never reuse cells.
    manifest['signature'] = sig
    atomic_json(output / 'manifest.json', manifest)
    db = sqlite3.connect(output / 'checkpoints.sqlite')
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS cells (key TEXT PRIMARY KEY, signature TEXT, job TEXT, result TEXT)')
    db.commit()
    jobs = []
    for ss in args.stages:
        s = ss - 1
        for key in args.bonds:
            if (s, key) not in coefficients: continue
            row = coefficients[(s, key)]; opts = count_options(s, key)
            count = row['count'] if args.count_mode == 'calibrated' else min(opts, key=lambda x: abs(x - max(1, STAGES[s][0] // 3)))
            # An inactive military group cannot test its strength.
            if key == 'military': count = max(count, math.ceil(STAGES[s][0] / 2))
            for g in args.genres:
                for j in range(args.rosters):
                    job = dict(stage=s, genre=g, bond=key, count=count, config=row['config'],
                               pool=160000 + j, difficulty=args.difficulty, budget=args.budget,
                               shortlist=args.shortlist, train_trials=args.train_trials,
                               select_trials=args.select_trials, test_trials=args.test_trials)
                    text = json.dumps(job, sort_keys=True)
                    key_hash = hashlib.sha256((sig + text).encode()).hexdigest()
                    jobs.append((key_hash, text, {**job, 'key': key_hash, 'output': str(output)}))
    if not jobs: raise RuntimeError('No available cells')
    wanted = {k for k, _, _ in jobs}
    try:
        with cf.ProcessPoolExecutor(args.workers) as pool:
            pending = {pool.submit(evaluate, job): (k, text) for k, text, job in jobs
                       if not db.execute('SELECT key FROM cells WHERE key=?', (k,)).fetchone()}
            print(f'order search: {len(pending)} pending / {len(jobs)} cells', flush=True)
            for i, future in enumerate(cf.as_completed(pending), 1):
                k, text = pending[future]; result = future.result()
                db.execute('INSERT INTO cells VALUES (?,?,?,?)', (k, sig, text, json.dumps(result)))
                db.commit()
                if i % 6 == 0 or i == len(pending):
                    print(f'order search: saved {i}/{len(pending)}', flush=True)
        rows = [dict(key=k, job=json.loads(j), result=json.loads(r)) for k, j, r in
                db.execute('SELECT key,job,result FROM cells WHERE signature=?', (sig,)) if k in wanted]
        summarize(rows, output, sig)
        print(f'completed {len(rows)} cells; {sum(r["result"]["executed_battles"] for r in rows):,} battles', flush=True)
    finally:
        db.close()


if __name__ == '__main__':
    main()
