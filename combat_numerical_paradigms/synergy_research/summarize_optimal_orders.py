"""Designer-facing evidence from held-out, optimized fixed-roster experiments.

Does not select coefficients, label failure clusters, or select orders using
test outcomes. Counts experiments separately from repeated battle executions.
"""
import argparse
from collections import defaultdict
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

from settings import HERE, IDENTITIES, CN


NOTES = {
    'academy': '编队应同时有学生与老师，再检验学生等级总和对老师出手的贡献。经验收益另做培养经济核算。',
    'military': '人数按阶段上限达到50%才生效。当前固定NPC没有开启忍者绝对闪避，不能据这组数据确定专门反制绝对闪避的价值。',
    'mage': '让玩家围绕两种原生技能流派安排续放与切换；先看两种事件是否实际发生，再设计技能供给。',
    'cult': '需要同时出现低阶和高阶教徒。当前研究候选强化高阶教徒本人的技能；先保留低阶支持与高阶出手机会。',
    'fighter': '定位为持续战斗增长；需同时看战斗时长、最优排阵后的收益与换人代价，不为追求成长主动拖延每场战斗。',
    'hunter': '比较折前直伤转换后的实际兑现量；后续伤害的未兑现部分与真实流失结算分别记账。',
    'heroine': '保证多位侠女有机会完成首次技能，有限次数与后续回转共同排阵；只增加无限保底可能挡住后续接力。',
    'maid': '最前的女仆成为女仆长。其位置与装备一起优化；具体攻击/恢复/护盾效果仍是候选，不把固定发动本身等同于足够强。',
    'lady': '优先把最值得强化的合法技能安排在受益位置；淑女自身是否靠前取决于原技能，不强制其本人占据前排。',
    'scholar': '先有值得恢复且已消耗次数的技能，再让学者参与回转；恢复次数与恢复后实际出手分别记录。',
    'sage': '按实际负面效果与敌方减益压力评估；当前候选强化/削弱幅度，不包含新增持续时间或封印体系。',
    'engineer': '先区分开局装备增益与实际技能成长。当前只倍增显式装备四维，不能把本轮结果外推为所有装备机制都会增强。',
    'sword': '至少有另一名合格剑士才有追加对象；保留次数资源，按完整技能递归结算。当前最多追加3次、共4次技能。',
    'ninja': '初始绝对闪避与技能增长分别看；增长下回合才生效，安排出手也要计算对主C技能机会的占用。',
    'adventurer': '当前五种共享目标只是研究候选；检查实际可完成目标，再决定技能投放覆盖，不能把一次测试的目标表固定为最终设计。',
    'sailor': '以队伍实际身份种类计算四维；可作混编支持，身份多样性、人物阶级及水手人数同时记账。',
    'gang': '按替代普通攻击评估。原技能附加效果不执行，顺位需要比较原技能机会损失与替代攻击收益。',
    'merchant': '开局一次补最低维；本人不必为羁绊高频出手。比较补短板与该角色原生技能的编队价值。',
    'farmer': '全队共享一颗果实。看种植、加速、收获是否兑现；当前恢复果实仍是效果候选，不以无收获的阵容判定整个身份无效。',
    'thief': '看实际偷取四维量与本人出手机会；偷取仅限本场，不能把战后永久收益计入。',
    'rich': '看本场金币产生与减伤兑现；正式金币价格和战后收益尚未标定，不据战斗胜率直接确定经济数值。',
    'worker': '看致死保留是否触发及救回后能否取胜；本人无需为救援机制占用技能顺位。',
    'killer': '需要技能命中、敌方下一次技能及其恢复同时成立；恢复压制量为零时，不能以胜率差直接定其反治疗系数。',
}
EVENTS = ('skill_casts', 'normal_casts', 'sword_extras', 'scholar_restored', 'engineer_casts',
          'ninja_casts', 'absolute_dodges', 'force_hit', 'mage_same', 'mage_switch',
          'fruit_planted', 'fruit_accelerated', 'fruit_harvest', 'fruit_wait', 'worker_procs',
          'hunter_scheduled', 'hunter_true', 'killer_marks', 'killer_healing_prevented',
          'thief_stolen', 'rich_saved', 'coins', 'heroine_first', 'maid_casts', 'gang_attacks')


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else 0.


def csv_file(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def aggregate(rows):
    result = dict(cells=len(rows), stages=sorted({r['capacity'] for r in rows}),
                  counts=sorted({r['count'] for r in rows}))
    for k in ('on_wr', 'off_wr', 'reference_wr', 'practical_pp', 'mechanical_pp', 'net_pp',
              'ordering_component_pp', 'censored', 'turns', 'target_casts', 'target_cast_share', 'distinct_identities', 'top_items'):
        result[k] = mean(r[k] for r in rows)
    for k in ('student_levels', 'teacher_casts'):
        result[k] = mean(r[k] for r in rows)
    for k in ('practical', 'mechanical', 'net'):
        # Conditional Monte Carlo uncertainty for THESE fixed scenarios only.
        result[k + '_mc95_radius_pp'] = 1.96 * math.sqrt(sum(r[k + '_se_pp'] ** 2 for r in rows)) / len(rows)
    result['flow_min_pp'] = min(r['practical_pp'] for r in rows)
    result['flow_max_pp'] = max(r['practical_pp'] for r in rows)
    result['structurally_unavailable_cells'] = sum(bool(r['missing_condition']) for r in rows)
    for event in EVENTS:
        available = [r['event_' + event] for r in rows if r['event_' + event] is not None]
        result['event_' + event] = mean(available) if available else None
    return result


def heatmap(stages, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    keys = list(IDENTITIES)
    arrays = [np.array([[stages[s].get(key, {}).get(field, float('nan'))
                         for s in range(1, 7)] for key in keys])
              for field in ('practical_pp', 'net_pp')]
    scale = max(1., max(float(np.nanmax(np.abs(a))) for a in arrays))
    fig, axes = plt.subplots(1, 2, figsize=(16, 12))
    cmap = plt.get_cmap('RdBu').copy(); cmap.set_bad('#dddddd')
    for ax, values, title in zip(axes, arrays, ('各自优化后的羁绊实用收益', '相对不限身份参考的整队净收益')):
        im = ax.imshow(values, aspect='auto', cmap=cmap, vmin=-scale, vmax=scale)
        ax.set_xticks(range(6), [f'{s*5}人' for s in range(1, 7)])
        ax.set_yticks(range(len(keys)), [CN[k] for k in keys])
        ax.set_title(title)
        for y, key in enumerate(keys):
            for x, s in enumerate(range(1, 7)):
                if np.isnan(values[y, x]): text = '—'
                else:
                    text = f'{values[y,x]:+.1f}'
                    if stages[s][key]['structurally_unavailable_cells']: text += '†'
                ax.text(x, y, text, ha='center', va='center', fontsize=8,
                        color='white' if abs(values[y,x]) > scale * .55 else 'black')
        fig.colorbar(im, ax=ax, fraction=.03, pad=.02, label='胜率变化／百分点')
    fig.suptitle('最优顺位复核：旧候选系数、固定PvE遭遇\n每格汇总已测流派；†表示有样本未满足机制必要条件；—表示未测或无供给', fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, .95))
    fig.savefig(out / 'optimized_order_stage_heatmap.png', dpi=140)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, default=HERE / 'results/optimal_order')
    args = ap.parse_args(); out = args.output
    source = out / 'completed.json'
    completed = json.loads(source.read_text(encoding='utf-8'))
    validation = json.loads((out / 'validation.json').read_text(encoding='utf-8'))
    assert validation['status'] == 'passed' and validation['signature'] == completed['signature']
    assert validation['cells'] == len(completed['rows'])
    replay_path = out / 'enemy_metrics_replay.json'
    replay = json.loads(replay_path.read_text(encoding='utf-8')) if replay_path.exists() else {}
    if replay: assert replay['signature'] == completed['signature']
    rows = []
    for cell in completed['rows']:
        job, result = cell['job'], cell['result']
        with gzip.open(out / 'replicates' / (cell['key'] + '.json.gz'), 'rt', encoding='utf-8') as stream:
            raw = json.load(stream)
        members = raw['members']; key = job['bond']; target = set(IDENTITIES[key])
        target_members = [m for m in members if m['identity'] in target]
        own_positions = [i for i, index in enumerate(raw['plans']['on']['order']) if members[index]['identity'] in target]
        missing = ''
        if key == 'academy' and {m['identity'] for m in target_members} != {'老师', '学生'}:
            missing = '未同时拥有学生和老师，战斗联动未成立'
        if key == 'sword' and len(target_members) < 2:
            missing = '不足两名剑士，没有另一名剑士作为追加对象'
        if key == 'cult' and len({m['skill']['tier'] for m in target_members}) < 2:
            missing = '教徒没有阶级差，高低阶联动未成立'
        if key == 'military':
            assert len(target_members) / len(members) >= .5
        r = dict(key=cell['key'], stage=job['stage'] + 1, capacity=5 * (job['stage'] + 1),
                 bond=key, identity=CN[key], genre=job['genre'], pool=job['pool'], difficulty=job['difficulty'],
                 count=job['count'], config=json.dumps(job['config'], sort_keys=True),
                 on_wr=result['metrics']['on']['win'], off_wr=result['metrics']['off']['win'],
                 reference_wr=result['metrics']['reference']['win'],
                 censored=result['metrics']['on']['censored'], turns=result['metrics']['on']['turns'],
                 distinct_identities=len({m['identity'] for m in members}),
                 top_items=sum(bool(m['item'].get('top', False)) for m in members), missing_condition=missing)
        r['target_positions'] = '/'.join(str(i + 1) for i in own_positions)
        r['on_order_person_ids'] = json.dumps([members[i]['person_id'] for i in raw['plans']['on']['order']])
        for label, field in (('practical', 'practical_gain'), ('mechanical', 'mechanical_same_order'), ('net', 'net_vs_unrestricted')):
            r[label + '_pp'] = result['differences'][field]['mean'] * 100
            r[label + '_se_pp'] = result['differences'][field]['se'] * 100
        r['ordering_component_pp'] = r['practical_pp'] - r['mechanical_pp']
        own_casts = [sum(t['on']['owner_casts'][i] for i in own_positions) for t in raw['trials']]
        r['target_casts'] = mean(own_casts)
        r['target_cast_share'] = mean(n / max(1, sum(t['on']['owner_casts'])) for n, t in zip(own_casts, raw['trials']))
        teacher_positions = [i for i, index in enumerate(raw['plans']['on']['order']) if members[index]['identity'] == '老师']
        r['student_levels'] = sum(m['level'] for m in members if m['identity'] == '学生')
        r['teacher_casts'] = mean(sum(t['on']['owner_casts'][i] for i in teacher_positions) for t in raw['trials'])
        for event in EVENTS:
            if event == 'killer_healing_prevented':
                measured = replay.get('cells', {}).get(cell['key'])
                r['event_' + event] = measured['means']['prevented_bp'] if measured else None
            else:
                r['event_' + event] = mean(t['on']['metrics'].get(event, 0.) for t in raw['trials'])
        measured = replay.get('cells', {}).get(cell['key'])
        r['prevented_enemy_bp_fraction'] = measured['means']['prevented_bp_fraction'] if measured else None
        rows.append(r)
    csv_file(out / 'optimized_order_evidence.csv', rows)
    groups = defaultdict(list); stage_groups = defaultdict(list)
    for r in rows:
        groups[r['bond']].append(r); stage_groups[(r['stage'], r['bond'])].append(r)
    totals = {key: aggregate(group) for key, group in groups.items()}
    stages = {s: {key: aggregate(group) for (ss, key), group in stage_groups.items() if ss == s} for s in range(1, 7)}
    available_pairs = {(r['stage'] + 1, r['bond']) for r in
                       json.loads((HERE / 'results/selected_coefficients.json').read_text(encoding='utf-8'))
                       if r['soft_delta_reference'] == .1}
    capacities = '/'.join(map(str, sorted({r['capacity'] for r in rows})))
    genres = '/'.join(sorted({r['genre'] for r in rows}))
    roster_counts = defaultdict(set)
    for r in rows: roster_counts[(r['stage'], r['bond'], r['genre'])].add(r['pool'])
    cardinalities = [len(x) for x in roster_counts.values()]
    stage_rows = [dict(stage=s, capacity=s * 5, bond=key, identity=CN[key],
                       **{k: v for k, v in result.items() if not isinstance(v, list)},
                       counts='/'.join(map(str, result['counts'])))
                  for s, table in stages.items() for key, result in table.items()]
    csv_file(out / 'optimized_order_stage_evidence.csv', stage_rows)
    heatmap(stages, out)
    lines = ['# 身份羁绊：最优顺位复核后的设计指南', '',
             '本轮按玩家会针对机制排阵的前提，补测其余身份。固定人物、技能、四维、等级及装备，有羁绊、无羁绊与不限身份参考阵容分别优化顺位，再以未参与选择的种子确认。', '',
             f'已确认{len(rows)}个固定阵容单元，覆盖{len(groups)}项身份组合、{capacities}人，流派为{genres}。研究执行{completed["executed_battles"]:,}次，其中最终确认{validation["heldout_battle_executions"]:,}次；{validation["replayed"]}次保存对战复现通过。重复ROLL和搜索执行不作为独立阵容数量。', '',
             f'每个已测阶段/流派/身份组合含{min(cardinalities)}～{max(cardinalities)}套固定阵容；使用旧候选系数与作业中记录的人数，军人按人数上限至少50%检验。固定PvE遭遇，难度为{"/".join(sorted({r["difficulty"] for r in rows}))}；敌人没有开启羁绊。结果是参数起点的复核，尚未重新定完所有人数曲线、系数、技能供给或双方混合羁绊。', '',
             f'装备基准：每人一件装备，本批每队实际顶级装备数量为{min(r["top_items"] for r in rows)}～{max(r["top_items"] for r in rows)}件；上限四件已校验。工程师等结论应连同这套装备基准读取。', '',
             '人物身份、阶级和数量来自冻结标注；标签本身没有正式技能绑定，本轮按阶级与流派抽取冻结生成器的技能。不能把这些研究赋值直接当作生产人物技能表。', '',
             f'仿真观察窗为120回合，当前单元平均截尾率{mean(r["censored"] for r in rows):.3%}，最高{max(r["censored"] for r in rows):.3%}。表中胜率为观察窗内获胜比例；未结束对局单独记为截尾，不标成已判定的败局。', '',
             '系数单位与六阶段候选起点见[数值表](DESIGN_GUIDE.md)。本页给出同一组系数在优化顺位后的复核，不把它改称已完成重新校准的数值。', '',
             '## 设计时读取哪些数值', '',
             '- 实用收益：各自优化后的有羁绊胜率−无羁绊胜率。',
             '- 同顺位机制收益：有羁绊最优排法下，仅开关机制。用于解释效果，不含两次搜索找到不同排法的差异。',
             '- 整队净收益：有羁绊阵容−不限身份参考阵容，双方都优化。用它判断凑身份后是否值得替换成员。',
             '- 下表区间只描述当前固定场景的随机ROLL误差，不含收集、换阵容、技能供给或有限搜索误差，不能当作真实玩家总体区间。', '',
             '区间是配对样本方差的近似估计；零半宽只表示本批样本没有配对差异，不能证明总体差异或误差恒为零。表格按实用收益点估计排序，不代表所有构筑的全局强度排名。', '',
             '同顺位机制收益与实用收益的差额包含两个搜索找到不同排法的影响。如果两项指标差别大或方向不同，应先扩大独立阵容与搜索规模，不能直接据此增减机制系数。逐单元证据另列ordering_component_pp。', '',
             '先把身份机制能否实际成立与数值收益分开。被动支持不要求支持者本人频繁释放技能；需要出手的成长效果应结合真实出手次数。全队正常行动仍只选一个技能，保底技能、限次与门槛始终参与计算。', '',
             '## 当前场景汇总', '',
             '单位均为胜率百分点；±为上述条件下约95%的Monte Carlo半宽。单元数逐行列出，贤者缺少5人阶段角色。', '',
             '| 身份 | 单元 | 实用收益 | 同顺位机制收益 | 整队净收益 | 成立条件未满足的单元 |',
             '| --- | --- | --- | --- | --- | --- |']
    for key in sorted(totals, key=lambda k: totals[k]['practical_pp'], reverse=True):
        r = totals[key]
        lines.append(f'| {CN[key]} | {r["cells"]} | {r["practical_pp"]:+.2f}±{r["practical_mc95_radius_pp"]:.2f} | {r["mechanical_pp"]:+.2f} | {r["net_pp"]:+.2f}±{r["net_mc95_radius_pp"]:.2f} | {r["structurally_unavailable_cells"]}/{r["cells"]} |')
    lines += ['', '## 六阶段复核', '',
              '每格“实用收益／整队净收益”，均为百分点；每格汇总已测流派。不能把六阶段平均的正值当作每阶段都适合，也不能把未满足机制条件的格当作最终强度判断。', '',
              '| 身份 | 5人 | 10人 | 15人 | 20人 | 25人 | 30人 |',
              '| --- | --- | --- | --- | --- | --- | --- |']
    for key in IDENTITIES:
        cells = []
        for s in range(1, 7):
            r = stages[s].get(key)
            if r is None: cells.append('未测' if (s, key) in available_pairs else '当前无供给')
            else: cells.append(f'{r["practical_pp"]:+.1f}／{r["net_pp"]:+.1f}' + ('†' if r['structurally_unavailable_cells'] else ''))
        lines.append('| ' + ' | '.join([CN[key], *cells]) + ' |')
    lines += ['', '†表示至少一个样本没有满足学生老师配对、两名剑士或教徒阶级差等机制必要条件。这些是效果成立的逻辑条件，不是新增人数解锁门槛。', '',
              '![六阶段最优顺位收益](results/optimal_order/optimized_order_stage_heatmap.png)', '',
              '## 身份定位与技能投放方向', '',
              '以下给出结合机制与事件日志的投放方向；本轮保持原技能不变，没有据此改动生成概率。不同技能供给的优劣仍需各自优化顺位后独立比较。', '']
    for key in IDENTITIES:
        if key not in totals: continue
        r = totals[key]
        lines += [f'### {CN[key]}', '', NOTES[key], '',
                  f'本次同顺位机制收益{r["mechanical_pp"]:+.2f}个百分点，实用收益{r["practical_pp"]:+.2f}，整队净收益{r["net_pp"]:+.2f}；六流派/阶段单元的实用收益范围{r["flow_min_pp"]:+.1f}～{r["flow_max_pp"]:+.1f}。', '']
        if r['structurally_unavailable_cells']:
            details = sorted({x['missing_condition'] for x in groups[key] if x['missing_condition']})
            lines += ['必要条件检查：' + '；'.join(details) + '。这部分样本保留记录，后续数值标定应另组满足条件的阵容。', '']
        evidence = {
            'military': [('force_hit', '强制命中判定成功')],
            'mage': [('mage_same', '同流派续放'), ('mage_switch', '流派切换')],
            'scholar': [('scholar_restored', '恢复次数')],
            'engineer': [('engineer_casts', '工程师技能成长触发')],
            'sword': [('sword_extras', '追加完整技能')],
            'ninja': [('ninja_casts', '忍者技能成长触发'), ('absolute_dodges', '绝对闪避')],
            'farmer': [('fruit_planted', '种植'), ('fruit_accelerated', '加速'), ('fruit_harvest', '收获')],
            'worker': [('worker_procs', '致死救援')],
            'heroine': [('heroine_first', '侠女首次技能')],
            'maid': [('maid_casts', '女仆长技能')],
            'gang': [('gang_attacks', '帮派替代普攻')],
            'killer': [('killer_marks', '恢复压制标记')],
        }.get(key, [])
        if evidence:
            lines += ['每场平均事件：' + '；'.join(f'{label}{r["event_"+event]:.2f}次' for event, label in evidence) + '。', '']
        if key == 'academy':
            lines += [f'本批学生等级总和平均{r["student_levels"]:.1f}，每场老师技能平均{r["teacher_casts"]:.2f}次；增伤与具体技能类型仍需一并核对。', '']
        if key == 'killer':
            measured = [x['prevented_enemy_bp_fraction'] for x in groups[key] if x['prevented_enemy_bp_fraction'] is not None]
            if measured:
                lines += [f'敌方事件补录：按锁定排法精确复现{len(measured)}个单元，每场平均削减的恢复请求量为敌方最大BP的{mean(measured):.3%}（BP封顶前）。这项量读取敌方日志，不使用己方缺失字段的默认零；它不等于扣除过量治疗后的有效BP差。', '']
            else:
                lines += ['敌方实际减疗量尚未补录，不把己方未保存的字段当作零。', '']
        examples = sorted((x for x in groups[key] if x['capacity'] == 30 and x['genre'] == 'C_I'), key=lambda x: x['pool'])
        if examples:
            example = examples[0]
            lines += [f'实际顺位样例：30人C_I、阵容池{example["pool"]}中，该身份位于第{example["target_positions"]}位；该组最终确认实用收益{example["practical_pp"]:+.2f}个百分点。这里只展示这套人物、技能和装备的搜索结果，不能当作固定位置模板。', '']
    lines += ['## 定稿前需要继续检验的边界', '',
              '本轮没有更改战斗规则、人物标签、技能生成器或Unity配置。旧数值继续作为候选；不能把一次排阵复核等同于全部完成平衡。', '',
              '1. 对机制未成立的样本补足配对与阶级差；对杀手、军人、贤者等验证相应恢复、绝对闪避和负面效果场景。',
              '2. 增加独立阵容、人数配比和搜索预算，再比较候选系数。搜索最佳方案尚不等于证明真实胜率的全局最优。',
              '3. 身份技能投放在相同四维/阶位/装备预算内比较，每个供给候选重新优化顺位；不把原预设顺位的供给收益直接移植过来。',
              '4. 当前统计来自最终标量与事件日志，未重新采集最优顺位的完整时序PCA；历史聚类不能充当这批排法的败因证据。', '',
              '逐单元数据：[optimized_order_evidence.csv](results/optimal_order/optimized_order_evidence.csv)；六阶段证据：[optimized_order_stage_evidence.csv](results/optimal_order/optimized_order_stage_evidence.csv)；复现入口：[顺位评估规范](ORDER_EVALUATION_PROTOCOL.md)。', '']
    (HERE / 'OPTIMAL_ORDER_DESIGN_GUIDE.md').write_text('\n'.join(lines), encoding='utf-8')
    meta = dict(signature=completed['signature'], input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                analyzer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                cells=len(rows), identities=len(groups), totals=totals, stages=stages,
                supplemental_replay_battles=replay.get('replayed_battles', 0))
    (out / 'design_evidence.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in meta.items() if k not in ('totals', 'stages')}, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
