"""Final checked evidence index and nonproduction supply-adapter invariants."""
import csv
import hashlib
import json
import math
from pathlib import Path
import re

import study_closure as study
from audit_research import check_manifest
from state_contract import ExpeditionState
from supply_adapter import restore_missing_caps
from run_bonds import atomic_json


def main():
    audit=json.loads((study.OUT/'audit.json').read_text(encoding='utf-8'))
    assert audit['status']=='passed'
    check_manifest(study.OUT/'manifest.json')
    for path,digest in audit['sources'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
    rows={'case_evidence.csv':1728,'state_responses.csv':4032,'native_curves.csv':51840,
        'return_evidence.csv':8640,'return_risk_targets.csv':1728,'equipment_ownership.csv':4032,
        'bond_interactions.csv':576,'mechanism_diagnostics.csv':20160,'stage_supply_summary.csv':144,'supply_semantics.csv':16}
    for name,n in rows.items():
        with (study.OUT/'report'/name).open(encoding='utf-8-sig',newline='') as f:assert sum(1 for _ in csv.DictReader(f))==n,name
    for factor in (.2,.4,.6,.8,1.):
        for removal in (0.,.5,1.):
            s=ExpeditionState('adapter');s.apply_loss('initial',(1-factor,)*5,'example')
            result=restore_missing_caps(s,'supply',(removal,)*5)
            expected=factor+removal*(1-factor)
            assert all(abs(x-expected)<1e-12 for x in s.factors)
            try:restore_missing_caps(s,'supply',(removal,)*5)
            except ValueError:pass
            else:raise AssertionError('Duplicate supply accepted')
    links=0
    for name in ('PROTOCOL.md','INTEGRATION_SPEC.md','DESIGN_GUIDE.md','README.md','RECOMMENDATIONS.md'):
        path=study.HERE/name
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            if '://'in target:continue
            resolved=(path.parent/target.split('#')[0]).resolve()
            if resolved!=(study.OUT/'delivery_checks.json').resolve():
                assert resolved.exists(),(name,target)
            links+=1
    core=json.loads((study.OUT/'contract_verification.json').read_text(encoding='utf-8'));assert core['status']=='passed'
    log=study.OUT/'baseline_regression.txt';rates=[]
    for line in log.read_text(encoding='utf-8-sig').splitlines():
        values=re.findall(r'(\d+\.\d+)%',line)
        if len(values)==7:rates.append(float(values[-1]))
    assert len(rates)==6 and max(rates)-min(rates)<=15,rates
    result=dict(status='passed',source_checks=True,csv_rows=rows,document_links=links,
        regression=dict(battles=37500,overall_win_rates=rates,spread_pp=max(rates)-min(rates)),
        executed_battles=audit['executed_battles'],native_journey_battles=audit['actual_journey_battles'],
        exact_saved_battle_replays=audit['exact_saved_battle_replays'],
        missing_cap_adapter_examples=15,
        document_sha256={name:hashlib.sha256((study.HERE/name).read_bytes()).hexdigest() for name in
            ('PROTOCOL.md','INTEGRATION_SPEC.md','DESIGN_GUIDE.md','README.md','RECOMMENDATIONS.md')},
        supplemental_sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (Path(__file__),study.HERE/'supply_adapter.py',log)})
    atomic_json(study.OUT/'delivery_checks.json',result)
    assert (study.OUT/'delivery_checks.json').exists()
    print(json.dumps({k:v for k,v in result.items() if k in ('status','executed_battles','native_journey_battles','exact_saved_battle_replays','document_links')},ensure_ascii=False))


if __name__=='__main__':main()
