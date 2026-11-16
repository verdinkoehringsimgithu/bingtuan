"""Final artifact/source checks; does not replace physical battle audits."""
import csv
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE/'results'


def main():
    provenance=json.loads((ROOT/'report/provenance.json').read_text(encoding='utf-8'))
    for path,digest in provenance['sources'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
    counts={'native_travel_curves.csv':25920,'heldout_response_forecasts.csv':25920,
        'dungeon_event_sensitivity.csv':155520,'dungeon_loot_sensitivity.csv':7776,
        'return_trip_sensitivity.csv':18144,'case_horizons.csv':864,'stage_horizons.csv':48,
        'regions_by_stage.csv':36,'retreat_break_even.csv':15}
    for name,count in counts.items():
        with (ROOT/'report'/name).open(encoding='utf-8-sig',newline='') as f:assert sum(1 for _ in csv.DictReader(f))==count,name
    extra_counts={'recovery_stress/case_evidence.csv':432,'recovery_stress/native_curves.csv':12960,
        'recovery_stress/state_responses.csv':2808,'recovery_stress/response_forecasts.csv':12960,
        'recovery_stress/stage_summary.csv':72,'strong_pressure/case_evidence.csv':72,'strong_pressure/stage_summary.csv':6}
    for name,count in extra_counts.items():
        with (ROOT/name).open(encoding='utf-8-sig',newline='') as f:assert sum(1 for _ in csv.DictReader(f))==count,name
    with (ROOT/'report/stage_horizons.csv').open(encoding='utf-8-sig',newline='') as f:stage=list(csv.DictReader(f))
    assert sum(int(r['cases']) for r in stage)==864
    assert {(int(r['stage']),r['policy'],r['cohort']) for r in stage}=={
        (s,p,c) for s in range(1,7) for p in ('global_policy','stage_policy')
        for c in ('dominant','low_margin_above_half','intermediate','already_at_or_below_half')}
    audits={}
    for name in ('measurements','prototype','refined'):
        d=json.loads((ROOT/f'audit_{name}.json').read_text(encoding='utf-8'));assert d['status']=='passed'
        audits[name]=d['results']
    recovery=json.loads((ROOT/'recovery_stress/audit.json').read_text(encoding='utf-8'))
    assert recovery['status']=='passed'
    assert hashlib.sha256((ROOT/'recovery_stress/summary.json').read_bytes()).hexdigest()==recovery['summary_sha256']
    assert hashlib.sha256((HERE/'analyze_recovery.py').read_bytes()).hexdigest()==recovery['analyzer_sha256']
    assert hashlib.sha256((HERE/'analyze_expedition.py').read_bytes()).hexdigest()==recovery['forecast_source_sha256']
    for source,digest in json.loads((ROOT/'recovery_stress/manifest.json').read_text(encoding='utf-8'))['sources'].items():
        assert hashlib.sha256(Path(source).read_bytes()).hexdigest()==digest,source
    links=0
    strong=json.loads((ROOT/'strong_pressure/audit.json').read_text(encoding='utf-8'))
    assert strong['status']=='passed'
    assert hashlib.sha256((ROOT/'strong_pressure/summary.json').read_bytes()).hexdigest()==strong['summary_sha256']
    assert hashlib.sha256((HERE/'audit_strong_pressure.py').read_bytes()).hexdigest()==strong['validator_sha256']
    for source,digest in json.loads((ROOT/'strong_pressure/manifest.json').read_text(encoding='utf-8'))['sources'].items():
        assert hashlib.sha256(Path(source).read_bytes()).hexdigest()==digest,source
    for name in ('README.md','DESIGN_GUIDE.md','RECOVERY_STRESS.md','STRONG_PRESSURE.md'):
        file=HERE/name
        for target in re.findall(r'\]\(([^)]+)\)',file.read_text(encoding='utf-8')):
            if '://' in target:continue
            assert (file.parent/target.split('#')[0]).exists(),(name,target)
            links+=1
    log=max(ROOT.glob('baseline_regression*.txt'),key=lambda p:p.stat().st_mtime_ns)
    rates=[]
    for line in log.read_text(encoding='utf-8-sig').splitlines():
        values=re.findall(r'(\d+\.\d+)%',line)
        if len(values)==7:rates.append(float(values[-1]))
    assert len(rates)==6 and max(rates)-min(rates)<=15,rates
    core=json.loads((ROOT/'core_validation.json').read_text(encoding='utf-8'));assert core['status']=='passed'
    recovery_core=json.loads((ROOT/'recovery_stress/core_verification.json').read_text(encoding='utf-8'));assert recovery_core['passed']
    measurements=audits['measurements'].values()
    original_executions=sum(p['executed_battles'] for m in measurements for p in m['phases'].values())
    original_executions+=sum(c['executed_battles'] for name in ('prototype','refined') for c in audits[name].values())
    original_replays=sum(m['exact_saved_battle_replays'] for m in audits['measurements'].values())
    original_replays+=sum(c['exact_saved_battle_replays'] for name in ('prototype','refined') for c in audits[name].values())
    total=original_executions+recovery['executed_battles']+strong['actual_journey_battles']
    result=dict(status='passed',report_rows=counts,additional_report_rows=extra_counts,local_document_links=links,
        baseline_regression=dict(log=str(log),sha256=hashlib.sha256(log.read_bytes()).hexdigest(),
            battles=37500,six_overall_win_rates=rates,spread_percentage_points=max(rates)-min(rates)),
        research_executions_including_search=total,
        exact_saved_battle_replays=original_replays+recovery['exact_saved_battle_replays']+strong['exact_saved_battle_replays'],
        recovery_core=recovery_core,base_core=core,
        checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (ROOT/'delivery_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k in ('status','research_executions_including_search','exact_saved_battle_replays','local_document_links')},ensure_ascii=False))


if __name__=='__main__':main()
