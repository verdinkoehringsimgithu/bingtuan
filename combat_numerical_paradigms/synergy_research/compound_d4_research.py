"""D4 effect-budget curves and mission-packet comparisons; no test selection."""
import argparse
import concurrent.futures as cf
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3

import compound_research as pilot
from configured_compound_core import configured, variants
from order_search import initial_orders, optimize, rank_score, reordered, snapshot
from rosters import seed, GENRES, STAGES
from run_bonds import atomic_json
from settings import HERE, CN

OUT = HERE / 'results/compound_d4'


def signature():
    sig, previous = pilot.signature()
    paths = [Path(__file__), HERE / 'configured_compound_core.py']
    manifest = dict(pilot_signature=sig, sources={**previous['sources'],
        **{str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}})
    return hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(), manifest


def jobs(args):
    rows = pilot.jobs(args)
    for j in rows:
        j.update(pool=790000, difficulty='extremely_hard')
    return rows


def run_once(j, mm, ii, enemy, ei, macro, label, parameters, order, bs, trace=False):
    members, items = reordered(mm, ii, order)
    module = configured(parameters)
    r, rows, a, _ = module.simulate(members, enemy, bs, items, ei, p=macro,
        enabled=() if label == 'off' else (j['bond'],), config={'gain': 1.}, telemetry=trace)
    result = pilot.compact(r)
    result['adventure_casts'] = sum(a.casts[k] for k, m in enumerate(members) if m.identity == '冒险者')
    result['adventure_boosted_casts'] = a.metrics['adventure_boosted_casts']
    return result, rows


def evaluate(j):
    mm, ii, enemy, ei, macro = pilot.prepare(j)
    candidates = [('off', {})] + variants(j['bond'])
    models = dict(candidates)
    seeds = {split: [seed('compound-d4-20261021', j['stage'], j['genre'], j['bond'], j['count'], split, i)
                     for i in range(j[split + '_trials'])] for split in ('train', 'select', 'cross', 'test')}
    executions = 0

    def run(label, order, split, trace=False):
        nonlocal executions
        rows = []; traces = []
        for i, bs in enumerate(seeds[split]):
            r, telemetry = run_once(j, mm, ii, enemy, ei, macro, label, models[label], order, bs, trace and i == 0)
            rows.append(r)
            if telemetry: traces.append(telemetry)
        executions += len(rows)
        return rows, traces

    plans = {}
    for label in models:
        plans[label] = optimize(len(mm), initial_orders(mm, j['bond']),
            lambda order, split, model=label: rank_score(run(model, order, split)[0]),
            seed('compound-d4-search', j['stage'], j['genre'], j['bond'], j['count'], j['gear'], label),
            j['budget'], j['shortlist'])
    shared = list(dict.fromkeys(tuple(p['order']) for p in plans.values()))
    for label in models:
        score, order = max((rank_score(run(label, order, 'cross')[0]), order) for order in shared)
        plans[label]['order'] = order; plans[label]['cross'] = score
    trials = {}; traces = {}
    for label in models:
        trials[label], traces[label] = run(label, plans[label]['order'], 'test', True)
    metrics = {name: {k: sum(r[k] for r in rows) / len(rows) for k in
        ('win', 'censored', 'turns', 'hp', 'enemy_hp', 'margin', 'normal_rate', 'adventure_goals',
         'adventure_casts', 'adventure_boosted_casts')} for name, rows in trials.items()}
    differences = {name: dict(vs_off=pilot.paired(rows, trials['off']), vs_v1=pilot.paired(rows, trials['v1']))
                   for name, rows in trials.items()}
    diagnostics = {name: {k: sum(r['metrics'].get(k, 0.) for r in rows) / len(rows) for k in
        ('maid_casts', 'maid_heal', 'maid_stats_total', 'maid_true', 'maid_true_requested',
         'pure_true', 'pure_true_crit', 'fruit_harvest', 'fruit_heal', 'fruit_stats_total', 'adventure_completed')}
        for name, rows in trials.items()}
    raw = dict(job=j, models=models, seeds=seeds, plans=plans, shared_orders=shared,
        members=snapshot(mm, ii), enemy=snapshot(enemy, ei), macro=macro,
        trials=trials, traces=traces, executed_battles=executions)
    path = Path(j['output']) / 'replicates' / (j['key'] + '.json.gz'); path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path.with_suffix('.tmp'), 'wt', encoding='utf-8') as f: json.dump(raw, f, ensure_ascii=False)
    path.with_suffix('.tmp').replace(path)
    return dict(metrics=metrics, differences=differences, diagnostics=diagnostics, executed_battles=executions)


def report(data, out):
    evidence = []; grouped = {}
    for cell in data['rows']:
        j = cell['job']; result = cell['result']
        for label, metrics in result['metrics'].items():
            row = dict(stage=j['stage'] + 1, capacity=STAGES[j['stage']][0], bond=j['bond'], genre=j['genre'],
                density=j['density'], count=j['count'], gear=j['gear'], variant=label, trials=j['test_trials'],
                **metrics, **{'delta_' + ref + '_' + k: v for ref, values in result['differences'][label].items() for k, v in values.items()},
                **{'m_' + k: v for k, v in result['diagnostics'][label].items()})
            evidence.append(row)
            grouped.setdefault((j['stage'], j['bond'], j['density'], label), []).append(row)
    pilot.table(out / 'budget_and_goal_evidence.csv', evidence)
    stages = []
    for (s, key, density, label), rr in grouped.items():
        metric_keys = [k for k in rr[0] if k not in ('stage', 'capacity', 'bond', 'genre', 'density', 'count', 'gear', 'variant', 'trials')]
        stages.append(dict(stage=s + 1, capacity=STAGES[s][0], bond=key, density=density,
            count=rr[0]['count'], variant=label, cells=len(rr),
            **{k: sum(r[k] for r in rr) / len(rr) for k in metric_keys}))
    pilot.table(out / 'stage_responses.csv', stages)
    lines = ['# 三项复合羁绊：D4预算与目标组合指南', '',
        f'2026-10-21。{data["cells"]}单元、{data["executed_battles"]:,}次对战执行（含搜索），'
        '六阶段×六流派×三身份×小组合/满队×普通/四顶级。每格使用独立于D3试验的新人物/技能抽样池，固定D4敌方。', '',
        '所有候选分别搜索顺位，共享候选进行交叉验证，再用64条独立最终种子比较；5人120种训练排列穷举，更大队伍有限搜索。'
        '本轮保留全部预先列出的候选，不用最终胜率选一份并宣称最优。当前仍是每格一套人物/技能配置；同一阶段的表为六流派与两装备档等权均值。', '',
        '## 女仆长：复合效果数量与真伤预算分开', '',
        'v1为原复合候选：第5项把整次直接攻击切入原生纯真伤。新增addition候选：第5项在原有直伤后附加'
        '折前直伤×35%×q×s的真伤，q=n/(n+4)、s为0.25/0.5/1。附加真伤使用该次攻击已有暴击/先击结果，'
        '不再额外乘魔力；仍通过护盾、全域吸收与既有保命管线。普通直伤保留原生防御与装备破防结算。', '',
        'addition的攻击增幅、回复、四维增长、削弱、技能暴击率同时按s缩放；解锁密度沿用v1。'
        '这些是预算档与真伤表达的联合候选，不是把两者孤立后的因果消融。用户已确认复合效果方向，以上系数和真伤形式尚未定稿。', '',
        '| 人数上限 | 女仆数 | 关闭 | v1整段真伤 | 附加·1/4预算 | 附加·1/2预算 | 附加·完整预算 |',
        '| --- | --- | --- | --- | --- | --- | --- |']

    def lookup(s, key, density, label):
        return next(r for r in stages if r['stage'] == s + 1 and r['bond'] == key and r['density'] == density and r['variant'] == label)

    for s in range(6):
        for density in ('small', 'full'):
            rr = [lookup(s, 'maid', density, name) for name in ('off', 'v1', 'addition_0.25', 'addition_0.5', 'addition_1')]
            lines.append('| ' + ' | '.join([str(STAGES[s][0]), str(rr[0]['count'])] + [f'{r["win"]:.1%}' for r in rr]) + ' |')
    lines += ['', '## 果实：回复与四维收益拆分', '',
        'v1单次收获同时提供最大战力×12%×q×W回复，以及每种属性开局四维均值×10%×q×W。'
        'mixed_half/mixed_high分别把两部分乘0.5/1.5；heal_only/stats_only只关掉相应部分，保持成熟、加速、选属性和等待公式。'
        '开关后会重新排阵，因此下面是玩家实际编排收益；相互作用可计算为混合收益−回复单独收益−属性单独收益+关闭收益。', '',
        '| 人数上限 | 农民数 | 关闭 | 仅回复 | 仅四维 | 复合半量 | 复合标准 | 复合1.5倍 |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for s in range(6):
        for density in ('small', 'full'):
            rr = [lookup(s, 'farmer', density, name) for name in ('off', 'heal_only', 'stats_only', 'mixed_half', 'v1', 'mixed_high')]
            lines.append('| ' + ' | '.join([str(STAGES[s][0]), str(rr[0]['count'])] + [f'{r["win"]:.1%}' for r in rr]) + ' |')
    lines += ['', '## 冒险者：同最大预算下比较目标包', '',
        '- v1：100/75/50/25血线、暴击、闪避；每项6%×q。',
        '- progress：四条血线，每项9%×q。',
        '- sparse：75/25血线、暴击、闪避，每项9%×q。',
        '- channels：75血线、暴击、闪避、有效回复、流失、负面，每项6%×q。', '',
        '各包满完成时都为36%×q的冒险者直伤增幅；真实强度取决于完成时点、构筑可达性和后续冒险者出手。'
        '不同目标数量不通过奖励上限差异直接赢得比较；首次有效回复、流失和负面的定义沿用节点报告。', '',
        '| 人数上限 | 冒险者数 | 关闭 | v1六目标 | 四血线 | 两血线+暴击闪避 | 通道组合 |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    for s in range(6):
        for density in ('small', 'full'):
            rr = [lookup(s, 'adventurer', density, name) for name in ('off', 'v1', 'progress', 'sparse', 'channels')]
            lines.append('| ' + ' | '.join([str(STAGES[s][0]), str(rr[0]['count'])] + [f'{r["win"]:.1%}' for r in rr]) + ' |')
    lines += ['', '## 使用这些区间', '',
        '按阶段与人数先选行，再检查分流派、装备档与配对标准误，不把均值当作每套阵容的保底收益。'
        '候选曲线给出了可用的强度调节范围；超出本轮扫描值、改变目标包、混合多个身份或更换装备归属均需另测。'
        'D3与D4使用不同人物抽样池，不能把两页胜率差解释为仅由难度变化造成的因果量。', '',
        '[逐格预算/目标证据](results/compound_d4/budget_and_goal_evidence.csv)；'
        '[逐阶段响应](results/compound_d4/stage_responses.csv)；'
        '[候选参数生成代码](configured_compound_core.py)；[D3与节点定义](COMPOUND_EFFECT_DESIGN.md)。', '',
        '复现：`run_compound_d4.ps1 -Workers 6`。参数配置隔离于冻结v1命名空间，源哈希、逐场种子、'
        '真实人物/技能/装备快照、原始结果和首场时序均保存至`results/compound_d4/`。生产Unity与原研究文件保持。']
    (HERE / 'COMPOUND_D4_GUIDE.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workers', type=int, default=6); p.add_argument('--trials', type=int, default=64)
    p.add_argument('--budget', type=int, default=16); p.add_argument('--output', type=Path, default=OUT)
    args = p.parse_args(); assert args.trials >= 2 and args.budget >= 16
    args.output.mkdir(parents=True, exist_ok=True)
    sig, manifest = signature(); atomic_json(args.output / 'manifest.json', {**manifest, 'signature': sig})
    db = sqlite3.connect(args.output / 'checkpoints.sqlite'); db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS cells(key TEXT PRIMARY KEY,signature TEXT,job TEXT,result TEXT)'); db.commit()
    wanted = {}; pending = {}
    with cf.ProcessPoolExecutor(args.workers) as pool:
        for j in jobs(args):
            encoded = json.dumps(j, sort_keys=True); key = hashlib.sha256((sig + encoded).encode()).hexdigest(); wanted[key] = j
            if db.execute('SELECT 1 FROM cells WHERE key=?', (key,)).fetchone(): continue
            pending[pool.submit(evaluate, {**j, 'key': key, 'output': str(args.output.resolve())})] = (key, encoded)
        print(f'compound D4: {len(pending)} pending / {len(wanted)} cells', flush=True)
        for i, future in enumerate(cf.as_completed(pending), 1):
            key, encoded = pending[future]; result = future.result()
            db.execute('INSERT INTO cells VALUES(?,?,?,?)', (key, sig, encoded, json.dumps(result))); db.commit()
            if i % 12 == 0 or i == len(pending): print(f'compound D4: saved {i}/{len(pending)}', flush=True)
    rows = [dict(key=k, job=json.loads(j), result=json.loads(r)) for k, j, r in db.execute(
        'SELECT key,job,result FROM cells WHERE signature=?', (sig,)) if k in wanted]
    db.close(); assert len(rows) == len(wanted)
    data = dict(signature=sig, cells=len(rows), executed_battles=sum(r['result']['executed_battles'] for r in rows), rows=rows)
    atomic_json(args.output / 'summary.json', data); report(data, args.output)
    print(f'compound D4: complete {len(rows)} cells / {data["executed_battles"]:,} executions', flush=True)


if __name__ == '__main__': main()
