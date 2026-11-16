"""Resumable six-stage D3 pilot of the three newly specified effect families.

Off, prior single-effect model, and compound model each search their own order.
No parameters or missions are selected using held-out battle outcomes.
"""
import argparse
import concurrent.futures as cf
import csv
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
import sqlite3
import time

import compound_core as engine
import joint_core as old
import joint_research as lab
from order_search import initial_orders, optimize, rank_score, reordered, snapshot
from rosters import build, encounter, seed, GENRES, STAGES
from run_bonds import atomic_json, signature as frozen_signature
from settings import HERE, ROOT, CN

BONDS = ('maid', 'farmer', 'adventurer')
MODELS = ('off', 'previous', 'compound')
OUT = HERE / 'results/compound'


def signature():
    core_sig, inputs = frozen_signature()
    paths = [HERE / name for name in ('joint_core.py', 'joint_research.py', 'order_search.py',
        'compound_core.py', 'compound_effects.json', 'compound_research.py')]
    paths += [ROOT / 'combat_numerical_paradigms/natural_research/results/equipment_operating_candidates.csv']
    sources = {str(ROOT / k): v for k, v in inputs.items()}
    sources.update({str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    manifest = dict(frozen_combat_signature=core_sig, sources=sources)
    return hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(), manifest


def jobs(args):
    out = []
    for s, g, key, density, gear in itertools.product(range(6), GENRES, BONDS,
                                                    ('small', 'full'), ('basic', 'four_top')):
        n = STAGES[s][0]; count = max(1, n // 3) if density == 'small' else n
        out.append(dict(stage=s, genre=g, bond=key, density=density, count=count, gear=gear,
                        pool=610000, bank='final', difficulty='hard', budget=args.budget,
                        shortlist=3, train_trials=2, select_trials=6, cross_trials=6, test_trials=args.trials))
    return out


def prepare(j):
    mm, _ = build(j['stage'], j['genre'], j['pool'], ((j['bond'], j['count']),), 'front', j['bank'])
    ii = lab.equipment(mm, j['genre'], j['stage'], j['gear'])
    h, macro = encounter(j['stage'], j['difficulty'])
    enemy, ei = build(j['stage'], h, j['pool'] + 100003, (), 'front', j['bank'])
    return mm, ii, enemy, ei, macro


def compact(r):
    return {k: r[k] for k in ('win', 'censored', 'draw', 'turns', 'hp', 'enemy_hp', 'margin',
        'normal_rate', 'metrics', 'enemy_metrics', 'owner_casts', 'final_stats', 'enemy_final_stats',
        'adventure_goals') + tuple(k for k in ('first_events', 'enemy_first_events', 'maid_effect_level') if k in r)}


def paired(left, right):
    values = [a['win'] - b['win'] for a, b in zip(left, right)]
    mean = sum(values) / len(values)
    se = math.sqrt(sum((x - mean)**2 for x in values) / (len(values) - 1) / len(values))
    return dict(mean=mean, se=se, normal_95_low=mean - 1.96 * se, normal_95_high=mean + 1.96 * se)


def evaluate(j):
    started = time.perf_counter(); mm, ii, enemy, ei, macro = prepare(j)
    seeds = {split: [seed('compound-20261021', j['stage'], j['genre'], j['bond'], j['count'], split, i)
                     for i in range(j[split + '_trials'])] for split in ('train', 'select', 'cross', 'test')}
    executions = 0
    # Equal amplitude multiplier isolates model bundles. This is not the old
    # stage-selected gain, and is explicitly recorded rather than silently fit.
    config = dict(gain=1.)

    def run(model, order, split, trace=False):
        nonlocal executions
        members, items = reordered(mm, ii, order)
        simulate = old.simulate if model == 'previous' else engine.simulate
        results = []; traces = []
        for i, bs in enumerate(seeds[split]):
            r, rows, a, _ = simulate(members, enemy, bs, items, ei, p=macro,
                enabled=() if model == 'off' else (j['bond'],), config=config, telemetry=trace and i == 0)
            if model != 'previous':
                # Cast timing makes milestone availability distinguishable
                # from having later opportunities to benefit from it.
                r['adventure_casts'] = sum(a.casts[k] for k, m in enumerate(members) if m.identity == '冒险者')
                r['adventure_boosted_casts'] = a.metrics['adventure_boosted_casts']
            value = compact(r)
            if model != 'previous':
                value.update(adventure_casts=r['adventure_casts'], adventure_boosted_casts=r['adventure_boosted_casts'])
            results.append(value)
            if rows: traces.append(rows)
        executions += len(results)
        return results, traces

    plans = {}
    for model in MODELS:
        plans[model] = optimize(len(mm), initial_orders(mm, j['bond']),
            lambda order, split, m=model: rank_score(run(m, order, split)[0]),
            seed('compound-search', j['stage'], j['genre'], j['bond'], j['count'], j['gear'], model),
            j['budget'], j['shortlist'])
    candidates = list(dict.fromkeys(tuple(plan['order']) for plan in plans.values()))
    for model in MODELS:
        score, order = max((rank_score(run(model, order, 'cross')[0]), order) for order in candidates)
        plans[model]['order'] = order; plans[model]['cross'] = score
    trials = {}; traces = {}
    for model in MODELS:
        trials[model], traces[model] = run(model, plans[model]['order'], 'test', True)
    trials['off_at_compound'], _ = run('off', plans['compound']['order'], 'test')
    metrics = {model: {k: sum(r[k] for r in rows) / len(rows)
                      for k in ('win', 'censored', 'turns', 'hp', 'enemy_hp', 'margin', 'normal_rate')}
               for model, rows in trials.items()}
    differences = {name: paired(trials['compound'], trials[control]) for name, control in (
        ('vs_off_optimized', 'off'), ('vs_previous_optimized', 'previous'), ('vs_off_same_order', 'off_at_compound'))}
    raw = dict(job=j, config=config, seeds=seeds, plans=plans, candidates=candidates,
               members=snapshot(mm, ii), enemy=snapshot(enemy, ei), macro=macro,
               trials=trials, traces=traces, executed_battles=executions)
    path = Path(j['output']) / 'replicates' / (j['key'] + '.json.gz'); path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path.with_suffix('.tmp'), 'wt', encoding='utf-8') as f: json.dump(raw, f, ensure_ascii=False)
    path.with_suffix('.tmp').replace(path)
    return dict(metrics=metrics, differences=differences, executed_battles=executions,
                seconds=time.perf_counter() - started)


def table(path, rows):
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def report(data, output):
    evidence = []; events = []; diagnostics = []; stages = []
    for cell in data['rows']:
        j = cell['job']; r = cell['result']
        base = dict(stage=j['stage'] + 1, capacity=STAGES[j['stage']][0], bond=j['bond'], genre=j['genre'],
                    density=j['density'], count=j['count'], gear=j['gear'], trials=j['test_trials'])
        evidence.append({**base, **{m + '_' + k: v for m, rows in r['metrics'].items() for k, v in rows.items()},
                         **{m + '_' + k: v for m, rows in r['differences'].items() for k, v in rows.items()}})
        with gzip.open(output / 'replicates' / (cell['key'] + '.json.gz'), 'rt', encoding='utf-8') as f: raw = json.load(f)
        rows = raw['trials']['compound']
        for metric in ('maid_casts', 'maid_heal_requested', 'maid_heal', 'maid_stats_total', 'fruit_harvest',
                       'fruit_heal_requested', 'fruit_heal', 'fruit_stats_total', 'fruit_stat_kinds',
                       'adventure_completed', 'adventure_boosted_casts'):
            diagnostics.append({**base, 'metric': metric, 'mean': sum(x['metrics'].get(metric, 0.) for x in rows) / len(rows)})
        if j['bond'] == 'adventurer':
            for model in ('off', 'compound'):
                rr = raw['trials'][model]
                for event in engine.ALL_EVENTS:
                    times = [x['first_events'][event]['turn'] for x in rr if event in x['first_events']]
                    terminal = sum(not x['censored'] and event in x['first_events'] and x['first_events'][event]['turn'] == x['turns'] for x in rr)
                    events.append({**base, 'model': model, 'event': event, 'completed': len(times),
                        'probability': len(times) / len(rr), 'mean_turn_if_completed': sum(times) / len(times) if times else '',
                        'terminal_round_fraction_of_completed': terminal / len(times) if times else ''})
    table(output / 'effect_evidence.csv', evidence); table(output / 'event_evidence.csv', events)
    table(output / 'effect_diagnostics.csv', diagnostics)
    for s in range(6):
        for bond in BONDS:
            for density in ('small', 'full'):
                group = [x for x in evidence if x['stage'] == s + 1 and x['bond'] == bond and x['density'] == density]
                avg = lambda k: sum(x[k] for x in group) / len(group)
                stages.append(dict(stage=s + 1, capacity=STAGES[s][0], bond=bond, density=density,
                    count=group[0]['count'], off_wr=avg('off_win'), previous_wr=avg('previous_win'),
                    compound_wr=avg('compound_win'), compound_censored=avg('compound_censored'),
                    compound_vs_off=avg('vs_off_optimized_mean'), compound_vs_previous=avg('vs_previous_optimized_mean')))
    table(output / 'stage_summary.csv', stages)
    lines = ['# 女仆长、果实与冒险者目标：复合效果研究', '',
        '2026-10-21。承接用户最新效果定义；本页的解锁点、效果预算、属性选取与结算时点是可替换的研究候选。', '',
        f'本轮{data["cells"]}单元，{data["executed_battles"]:,}次对战执行，含顺位搜索；'
        f'每单元{data["rows"][0]["job"]["test_trials"]}条独立于搜索的测试种子。六阶段、六流派、D3固定敌人、小组合与全身份、全普通/四顶级两装备档。', '',
        '关闭、旧单项候选、新复合候选分别搜索顺位，再共享候选顺位交叉验证，最后盲测。5人穷举120种顺位；更大队伍为有限搜索，不能保证全局最优。'
        '三者均gain=1，旧候选对照不沿用原阶段各自校准的gain；跨人数时实际人物、技能与构筑会变化，不是只改变人数的因果偏导。'
        '每格一套人物/技能样本，三方案技能、等级、四维、装备归属和敌方一致；装备按既有方案分配，未重做复合技能专属装备归属寻优。', '',
        '## 已确认的方向与本次候选', '',
        '- 女仆长保留100%发动、无限次、不可封印、无回合/战力门槛；复合效果随强度扩展。候选顺序为回复→自方四维→敌方四维削弱→技能暴击率→原生纯真伤。',
        '- 果实仍为全队共用，5回合成熟、攻击加速，成熟后攻击收获。现在一次收获同时回复和增加四维，属性种类、每种数值与回复量随强度变化。',
        '- 冒险者使用真实节点。血线严格低于100/75/50/25%，同次打击跨多条线可同时完成，每场每项目一次；回血不重置。首次暴击、首次防守闪避都可完成。', '',
        '强度候选q=n/(n+4)，本次gain=1。女仆长5项解锁点q=0.20/0.40/0.55/0.70/0.80，对应最少1/3/5/10/16人。'
        '这不是已确认的人数门槛；不要求全部阶段都解锁所有复合效果。回复为最大战力×8%×q，动作后每维增加开局该维×2.5%×q；'
        '削弱基值12%×q、持续2回合，沿用魔力与贤者管线；新增技能暴击率20%×q，不取消较低档的原生勇气暴击；纯真伤沿用原生破防与魔力增幅。'
        '自方回复在施法时执行，敌方削弱需命中；本次未把自方回复绑定敌方命中。自方四维在动作后生效，本场按固定开局基数累加，未额外设增长上限。', '',
        '果实候选：回复最大战力×12%×q×W；每种属性增加开局四维均值×10%×q×W，W=1+0.15×成熟后等待回合。'
        '属性种类在q=0/0.4/0.6/0.8增加，顺序按开局最低属性优先；这是待比较的属性分配候选。恢复不改最大战力；四维仅本场累加。', '',
        '冒险者当前候选6个目标为4条敌方血线、首次暴击、首次闪避；完成后只强化后续冒险者技能，直伤倍率×(1+完成数×6%×q)。'
        '额外观察首次命中、有效回血、施加流失、施加负面、绝对闪避，供后续筛选目标；并未把所有观察节点都变成目标。'
        '战团共享完成状态，敌方行动中的闪避也即时登记；伤害阈值在保命/复活回血前观察。', '',
        '## 六阶段结果', '',
        '下表等权汇总六流派和两装备档；开启收益不能全归因于新效果数量，新候选本身也增加效果预算。', '',
        '| 人数上限 | 身份 | 投入人数 | 关闭胜率 | 旧候选 | 复合候选 | 相对关闭 | 相对旧候选 | 120回合未结束 |',
        '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for r in stages:
        lines.append(f'| {r["capacity"]} | {CN[r["bond"]]} | {r["count"]} | {r["off_wr"]:.1%} | {r["previous_wr"]:.1%} | {r["compound_wr"]:.1%} | {r["compound_vs_off"]*100:+.2f}pp | {r["compound_vs_previous"]*100:+.2f}pp | {r["compound_censored"]:.1%} |')
    lines += ['', '## 冒险者目标的实际可达性', '',
        '先看关闭羁绊的最优顺位样本，避免用奖励自身造成的节点频率定目标；再对照开启后的分布。'
        '完成率按单元等权，完成回合按实际完成场次加权；终局同回合指标不能区分该回合是否还可出手，需结合后续强化施法次数。', '',
        '| 观察节点 | 关闭时完成率 | 完成回合均值 | 完成场次中位于终局回合比例 |',
        '| --- | --- | --- | --- |']
    for event in engine.ALL_EVENTS:
        rr = [r for r in events if r['event'] == event and r['model'] == 'off']
        count = sum(r['completed'] for r in rr)
        turn = sum(r['completed'] * r['mean_turn_if_completed'] for r in rr if r['completed']) / max(1, count)
        terminal = sum(r['completed'] * r['terminal_round_fraction_of_completed'] for r in rr if r['completed']) / max(1, count)
        probability = sum(r['probability'] for r in rr) / len(rr)
        lines.append(f'| {event} | {probability:.1%} | {turn:.2f} | {terminal:.1%} |')
    lines += ['', '以上是D3单羁绊首轮证据，尚未选出最终目标组合或最终预算。'
        '目标频率、节点之间的相关性、完成后的出手兑现必须一起考察；首次打下100%通常属于基础进度奖励，较低血线可能在最后一击同时完成。'
        '首次流失/负面依赖技能供给，首次闪避依赖双方先机与暴击，不能强迫所有构筑都完成同一全部清单。', '',
        '## 复现与数据', '',
        '- 定义与全部候选参数：[compound_effects.json](compound_effects.json)。',
        '- 引擎：[compound_core.py](compound_core.py)；运行：`run_compound_research.ps1 -Workers 6`，逐格存档。',
        '- 逐格胜率、配对差值与标准误：[effect_evidence.csv](results/compound/effect_evidence.csv)。',
        '- 分阶段节点完成率及回合：[event_evidence.csv](results/compound/event_evidence.csv)；效果记账：[effect_diagnostics.csv](results/compound/effect_diagnostics.csv)。',
        '- 逐场种子、完整人物与技能装备快照、测试结果及首场时序：`results/compound/replicates/`；源哈希与矩阵清单：`manifest.json`。',
        '- 既有完整研究：[JOINT_DESIGN_GUIDE.md](JOINT_DESIGN_GUIDE.md)。本轮补充不会覆盖旧矩阵或把旧结果称作复合效果结果。', '',
        '该研究层不改Unity、生成器、人物标签、钱包或经验。下一轮应比较解锁密度/效果预算、D4和多套独立人物样本；'
        '复合女仆长的回复/暴击/破防装备、农民属性种类选择、冒险目标组合均需各自寻优，而非只把单一伤害系数继续抬高。']
    (HERE / 'COMPOUND_EFFECT_DESIGN.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workers', type=int, default=6); p.add_argument('--trials', type=int, default=64)
    p.add_argument('--budget', type=int, default=16); p.add_argument('--output', type=Path, default=OUT)
    args = p.parse_args(); assert args.trials >= 2 and args.budget >= 16
    args.output.mkdir(parents=True, exist_ok=True)
    sig, manifest = signature(); manifest.update(signature=sig)
    atomic_json(args.output / 'manifest.json', manifest)
    db = sqlite3.connect(args.output / 'checkpoints.sqlite'); db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS cells(key TEXT PRIMARY KEY, signature TEXT, job TEXT, result TEXT)'); db.commit()
    wanted = {}; pending = {}
    with cf.ProcessPoolExecutor(args.workers) as pool:
        for j in jobs(args):
            encoded = json.dumps(j, sort_keys=True); key = hashlib.sha256((sig + encoded).encode()).hexdigest()
            wanted[key] = j
            if db.execute('SELECT 1 FROM cells WHERE key=?', (key,)).fetchone(): continue
            pending[pool.submit(evaluate, {**j, 'key': key, 'output': str(args.output.resolve())})] = (key, encoded)
        print(f'compound: {len(pending)} pending / {len(wanted)} cells', flush=True)
        for i, future in enumerate(cf.as_completed(pending), 1):
            key, encoded = pending[future]; r = future.result()
            db.execute('INSERT INTO cells VALUES(?,?,?,?)', (key, sig, encoded, json.dumps(r))); db.commit()
            if i % 12 == 0 or i == len(pending): print(f'compound: saved {i}/{len(pending)}', flush=True)
    rows = [dict(key=k, job=json.loads(j), result=json.loads(r)) for k, j, r in db.execute(
        'SELECT key,job,result FROM cells WHERE signature=?', (sig,)) if k in wanted]
    db.close(); assert len(rows) == len(wanted)
    data = dict(signature=sig, cells=len(rows), executed_battles=sum(r['result']['executed_battles'] for r in rows), rows=rows)
    atomic_json(args.output / 'summary.json', data); report(data, args.output)
    print(f'compound: complete {len(rows)} cells / {data["executed_battles"]:,} executions', flush=True)


if __name__ == '__main__': main()
