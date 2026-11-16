"""Audit and summarize the stronger region-pressure bound."""
import csv
import gzip
import hashlib
import json
from pathlib import Path

import strong_pressure as strong
from audit_research import check_manifest, equivalent
from confirm_paths import draw
from run_bonds import atomic_json


def main():
    root=strong.OUT;manifest=check_manifest(root/'manifest.json')
    summary=json.loads((root/'summary.json').read_text(encoding='utf-8'))
    assert summary['signature']==manifest['signature'] and len(summary['rows'])==72
    parent=json.loads((strong.stress.OUT/'summary.json').read_text(encoding='utf-8'))
    parent_cases={r['key']:r for r in parent['rows']}
    with (strong.stress.OUT/'case_evidence.csv').open(encoding='utf-8-sig',newline='') as f:comparison=list(csv.DictReader(f))
    total=0;replays=0;archives={};groups=[]
    for row in summary['rows']:
        path=root/'replicates'/(row['key']+'.json.gz')
        archives[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        with gzip.open(path,'rt',encoding='utf-8') as f:raw=json.load(f)
        pp=strong.stress.OUT/'replicates'/(row['key']+'.json.gz')
        assert raw['parent_archive_sha256']==hashlib.sha256(pp.read_bytes()).hexdigest()
        with gzip.open(pp,'rt',encoding='utf-8') as f:original=json.load(f)
        assert equivalent(raw['policy'],strong.POLICY) and len(raw['routes'])==64
        count=0;censored=0
        for index, route in enumerate(raw['routes']):
            wear=0.
            for node,q in enumerate(route,1):
                assert q['node']==node and q['wear_before']==wear
                roll=strong.stress.lab.seed('recovery-event',original['job'],index,node)/(1<<64)
                assert q['event_roll']==roll
                assert q['battle_seed']==strong.stress.lab.seed('recovery-native',original['job'],index,node)
                point=min(strong.stress.lab.GRID,key=lambda x:(abs(x-wear),x))
                assert equivalent(q['order'],original['prepared'][str(point)]['plan']['order'])
                delta=draw(strong.POLICY,q['result'],roll) if q['result']['win'] else 0.
                assert q['wear_after']==wear+delta
                if not q['result']['win']:assert node==len(route)
                wear+=delta;count+=1;censored+=q['result']['censored']
        assert count==raw['executed_battles']==row['executed_battles'] and censored==row['censored']
        assert row['reach30']==sum(len(r)>=30 for r in raw['routes'])/64
        assert row['forecast_half_battle']==strong.horizon(raw['forecast'])
        total+=count;replays+=raw['exact_saved_battle_replays']
    assert total==summary['executed_battles'] and replays==summary['exact_saved_battle_replays']
    lines=['# 地区损耗强度的较强备选档','','2026-10-22。在预先扫描空间内选最强战力上限/累计承伤候选，'
        '对六阶段×六流派×两固定敌方参照的女仆长全量预算做72格配对探索。'
        '沿用恢复补测的同一人物、装备、敌方、逐状态顺位及随机流；这是强度比较，不是重新抽样的独立泛化确认。', '',
        '**较强档**：P=min(1,累计实际承伤/有效上限)，触发概率=min(1,65%+50%×P)，'
        '触发后战力上限乘(1−8%−30%×P)。每战后回满受限上限；不携带残血。', '',
        '该参数属于地区损耗强度，不按身份另设惩罚。用女仆长测试是为检查强恢复情形；'
        '若把它用于所有地区，普通构筑可能更早需要补给，不能把强恢复结果当成普通旅行的默认体验。', '',
        f'{total:,}场额外原生连战，4,608条路线；C_I首条路线共{replays}场精确复演。'
        '能力降至50%的战数来自同一独立战斗响应的加权路径预测；到第30战的比例来自真实连战。', '',
        '| 人数 | 优势构筑数 | 基础档·承伤信号到第30战 | 较强档·到第30战 | 较强档·能力降至50%中位战数 | 较强档·30战内构筑比例 |',
        '| --- | --- | --- | --- | --- | --- |']
    for s in range(1,7):
        rr=[r for r in summary['rows'] if r['stage']==s and r['baseline_wr']>=.95]
        assert rr
        base=[r for r in comparison if int(r['stage'])==s and r['model']=='maid_full'
              and r['signal']=='exposure' and float(r['baseline_wr'])>=.95]
        assert len(base)==len(rr)
        hh=sorted(r['forecast_half_battle'] for r in rr);median=(hh[(len(hh)-1)//2]+hh[len(hh)//2])/2
        result=dict(stage=s,capacity=strong.stress.lab.STAGES[s-1][0],cases=len(rr),
            baseline_signal_reach30=sum(float(r['reach30']) for r in base)/len(base),
            strong_signal_reach30=sum(r['reach30'] for r in rr)/len(rr),forecast_half_battle_median=median,
            forecast_within_30=sum(r['forecast_half_battle']<=30 for r in rr)/len(rr))
        groups.append(result)
        show='>30' if median>30 else f'{median:g}'
        lines.append(f'| {result["capacity"]} | {len(rr)} | {result["baseline_signal_reach30"]:.1%} | {result["strong_signal_reach30"]:.1%} | {show} | {result["forecast_within_30"]:.1%} |')
    lines+=['','基础档为65%固定触发、8%＋20%×P降幅。两档保持同一个初始胜率筛选集。'
        '预测窗口内未到50%记为31，不把它当成第31战已达标。', '',
        '采用顺序：普通地区先用基础档，强恢复明显延长无补给深入时可用较强档作为地区候选；'
        '先复核往返风险和普通构筑承受程度，再作为实际地图默认值。两个档都不保证每条路线在固定场数结束。', '',
        '[逐格结果](results/strong_pressure/case_evidence.csv)、[参数与完整账本索引](results/strong_pressure/summary.json)。'
        '复现：`strong_pressure.py --workers 6`，随后`audit_strong_pressure.py`。']
    (strong.stress.lab.HERE/'STRONG_PRESSURE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    with (root/'stage_summary.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(groups[0]));writer.writeheader();writer.writerows(groups)
    atomic_json(root/'audit.json',dict(status='passed',cells=72,actual_journey_battles=total,
        physical_journeys=4608,exact_saved_battle_replays=replays,
        censored_actual_battles=sum(r['censored'] for r in summary['rows']),archive_sha256=archives,
        summary_sha256=hashlib.sha256((root/'summary.json').read_bytes()).hexdigest(),
        validator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    print('strong pressure audit passed:',total,'battles;',replays,'exact replays')


if __name__=='__main__':main()
