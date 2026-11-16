"""Post-process OFF-model telemetry, never choose by held-out win rate."""
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

import compound_research as lab
from run_bonds import atomic_json

LABELS = {
    'enemy_below_100': '首次打下100%', 'enemy_below_75': '首次打下75%',
    'enemy_below_50': '首次打下50%', 'enemy_below_25': '首次打下25%',
    'first_crit': '首次暴击', 'first_dodge': '首次闪避', 'first_hit': '首次命中',
    'first_heal': '首次有效回复', 'first_dot': '首次施加流失',
    'first_debuff': '首次施加负面', 'first_absolute_dodge': '首次绝对闪避'}


def mean(seq):
    return sum(seq) / len(seq)


def main():
    out = lab.OUT; source = out / 'summary.json'
    data = json.loads(source.read_text(encoding='utf-8'))
    samples = []; grouped = {}
    for cell in data['rows']:
        j = cell['job']
        if j['bond'] != 'adventurer': continue
        with gzip.open(out / 'replicates' / (cell['key'] + '.json.gz'), 'rt', encoding='utf-8') as f: raw = json.load(f)
        for r in raw['trials']['off']:
            row = {key: int(key in r['first_events']) for key in lab.engine.ALL_EVENTS}
            row['events'] = r['first_events']; row['turns'] = r['turns']; row['censored'] = r['censored']
            samples.append(row); grouped.setdefault(j['genre'], []).append(row)
    correlations = []; exact_pairs = []
    for a in lab.engine.ALL_EVENTS:
        av = mean([r[a] for r in samples]); va = av * (1 - av)
        row = dict(event=a)
        for b in lab.engine.ALL_EVENTS:
            bv = mean([r[b] for r in samples]); vb = bv * (1 - bv)
            cov = mean([r[a] * r[b] for r in samples]) - av * bv
            row[b] = cov / math.sqrt(va * vb) if va > 0 and vb > 0 else ''
            if a < b and all(r[a] == r[b] for r in samples):
                exact_pairs.append((a, b))
        correlations.append(row)
    lab.table(out / 'node_completion_correlations.csv', correlations)
    evidence = []
    for key in lab.engine.ALL_EVENTS:
        rr = [r for r in samples if r[key]]
        turns = sorted(r['events'][key]['turn'] for r in rr)
        terminal = sum(not r['censored'] and r['events'][key]['turn'] == r['turns'] for r in rr)
        probabilities = [mean([r[key] for r in group]) for group in grouped.values()]
        evidence.append(dict(event=key, label=LABELS[key], completed=len(rr), samples=len(samples),
            probability=len(rr) / len(samples), min_genre_probability=min(probabilities),
            max_genre_probability=max(probabilities), median_turn_if_completed=turns[len(turns) // 2] if turns else '',
            terminal_round_fraction=terminal / len(rr) if rr else '',
            has_later_round_fraction=sum(r['events'][key]['turn'] < r['turns'] for r in rr) / len(rr) if rr else ''))
    lab.table(out / 'node_selection_evidence.csv', evidence)
    lines = ['# 冒险者目标的节点筛选依据', '',
        f'来自本轮关闭羁绊、各自搜索顺位的{len(samples):,}场盲测记录；以下只用于提出下一批目标组合，不反过来改写本轮胜率。', '',
        '节点完成是战斗过程变量，不能用“完成者胜率更高”推导节点奖励的因果强度。'
        '“还有下一回合”也不等于冒险者必定有后续出手机会；当前动作后的真正技能兑现数另见逐场adventure_boosted_casts。', '',
        '| 节点 | 总完成率 | 六流派完成率范围 | 完成回合中位数 | 完成场中终局同回合比例 | 完成后还有下一回合 |',
        '| --- | --- | --- | --- | --- | --- |']
    for r in sorted(evidence, key=lambda x: x['probability'], reverse=True):
        fmt = lambda v: f'{v:.1%}' if v != '' else '—'
        lines.append(f'| {r["label"]} | {r["probability"]:.1%} | {r["min_genre_probability"]:.1%}～{r["max_genre_probability"]:.1%} | {r["median_turn_if_completed"] or "—"} | {fmt(r["terminal_round_fraction"])} | {fmt(r["has_later_round_fraction"])} |')
    lines += ['', '同一局里一次跨越多条血线时，会同时完成多个目标；这种相关性应计入总奖励预算。'
        '若以“打下100%”作为基础进度目标，不宜再把含义接近的“首次命中”当成独立等价目标重复计价。'
        '低血线目标要和较早的暴击/闪避等过程目标搭配，避免把大部分增强放在战斗结束时才发出。'
        '具体血线是否应稀疏选取、是否根据技能供给选不同目标包，仍需预先固定组合并在新样本复测。', '',
        '本轮样本内完成标记完全一致的节点对：' + ('；'.join(LABELS[a] + ' / ' + LABELS[b] for a, b in exact_pairs) if exact_pairs else '无') + '。'
        '二元相关性完整矩阵见[node_completion_correlations.csv](results/compound/node_completion_correlations.csv)，常量节点相关性留空，不能当成0相关。', '',
        '[逐节点证据表](results/compound/node_selection_evidence.csv)；[完整复合效果报告](COMPOUND_EFFECT_DESIGN.md)。']
    (lab.HERE / 'ADVENTURE_NODE_GUIDE.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    atomic_json(out / 'node_analysis_provenance.json', dict(signature=data['signature'],
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        analyzer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        off_battles=len(samples), exact_binary_completion_pairs=exact_pairs))
    print('adventure nodes:', len(samples), 'OFF-model battles;', len(evidence), 'observed event types')


if __name__ == '__main__': main()
