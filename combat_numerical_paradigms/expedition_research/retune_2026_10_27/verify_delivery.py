"""Verify selection independence, source archives, reports and regression."""
import csv
import hashlib
import json
from pathlib import Path
import re

import confirm_policies as study
import progressive_paths as progressive
from audit_research import check_manifest
from run_bonds import atomic_json


def main():
    root=study.fit.OUT;here=study.fit.HERE
    for path in (root/'fit_manifest.json',study.OUT/'manifest.json',progressive.OUT/'manifest.json'):check_manifest(path)
    audit=json.loads((root/'audit.json').read_text(encoding='utf-8'));assert audit['status']=='passed'
    for path,digest in audit['sources'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
    parent_audit=json.loads((study.old.OUT/'audit.json').read_text(encoding='utf-8'))
    assert parent_audit['status']=='passed'
    for name,digest in parent_audit['archives'].items():
        assert hashlib.sha256((study.old.OUT/'replicates'/name).read_bytes()).hexdigest()==digest,name
    selected=json.loads((root/'selected.json').read_text(encoding='utf-8'))
    calibration=json.loads((root/'calibration.json').read_text(encoding='utf-8'))
    assert len(calibration['candidates'])==72 and calibration['signature']==selected['signature']
    assert hashlib.sha256((root/'calibration.json').read_bytes()).hexdigest()==selected['calibration_sha256']
    for stage,policy in selected['stage_policies'].items():
        winner=min(calibration['candidates'],key=lambda r:(r['stages'][stage]['score'],r['policy']['l0'],r['policy']['l1']))
        assert winner['policy']==policy
    expected={'case_evidence.csv':1440,'native_curves.csv':43200,'response_forecasts.csv':43200,
        'return_evidence.csv':8640,'dense_state_responses.csv':1728,'stage_summary.csv':120}
    for name,n in expected.items():
        with (root/'report'/name).open(encoding='utf-8-sig',newline='') as f:assert sum(1 for _ in csv.DictReader(f))==n,name
    with (root/'report/case_evidence.csv').open(encoding='utf-8-sig',newline='') as f:cases=list(csv.DictReader(f))
    for r in cases:
        assert 0<=float(r['survive6'])<=1 and 0<=float(r['reach30'])<=1
        if r['variant']=='control':assert float(r['relative_survive6'])==1.
    links=0
    for name in ('README.md','PROTOCOL.md','PROGRESSIVE_PROTOCOL.md','DESIGN_GUIDE.md','RECOMMENDATIONS.md'):
        for target in re.findall(r'\]\(([^)]+)\)',(here/name).read_text(encoding='utf-8')):
            if '://'in target:continue
            resolved=(here/target.split('#')[0]).resolve()
            if resolved!=(root/'delivery_checks.json').resolve():assert resolved.exists(),(name,target)
            links+=1
    log=root/'baseline_regression.txt';rates=[]
    for line in log.read_text(encoding='utf-8-sig').splitlines():
        values=re.findall(r'(\d+\.\d+)%',line)
        if len(values)==7:rates.append(float(values[-1]))
    assert len(rates)==6 and max(rates)-min(rates)<=15,rates
    result=dict(status='passed',calibration_candidates=72,calibration_input_archives_checked=len(parent_audit['archives']),
        report_rows=expected,document_links=links,executed_battles=audit['total_executions'],
        actual_journey_battles=audit['actual_native_journey_battles'],exact_saved_battle_replays=audit['exact_saved_battle_replays'],
        regression=dict(battles=37500,overall_win_rates=rates,spread_pp=round(max(rates)-min(rates),2)),
        sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (Path(__file__),root/'audit.json',study.old.OUT/'audit.json',log)},
        document_sha256={name:hashlib.sha256((here/name).read_bytes()).hexdigest() for name in
            ('README.md','PROTOCOL.md','PROGRESSIVE_PROTOCOL.md','DESIGN_GUIDE.md','RECOMMENDATIONS.md')})
    atomic_json(root/'delivery_checks.json',result)
    print(json.dumps({k:v for k,v in result.items() if k in ('status','calibration_input_archives_checked','document_links','executed_battles','actual_journey_battles','exact_saved_battle_replays')}))


if __name__=='__main__':main()
