"""Final source, evidence shape and baseline checks for remaining-gap study."""
import csv
import hashlib
import json
from pathlib import Path
import re

from common import *
import hard_regions as hard
import stage25 as s25


def main():
    for p in (s25.ROOT/'manifest.json',hard.ROOT/'calibrate_manifest.json',hard.ROOT/'confirm_manifest.json'):check_manifest(p)
    audit=json.loads((OUT/'audit.json').read_text(encoding='utf-8'));assert audit['status']=='passed'
    for path,digest in audit['source_sha256'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
    for path,digest in audit['archives'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
    expected={'stage25_cases.csv':288,'stage25_states.csv':576,'hard_cases_96.csv':144,
        'independent_precision.csv':7,'three_battle_probes.csv':438}
    for name,n in expected.items():
        with (OUT/'report'/name).open(encoding='utf-8-sig',newline='') as f:assert sum(1 for _ in csv.DictReader(f))==n,name
    references=json.loads((OUT/'usable_references.json').read_text(encoding='utf-8'))['references']
    assert {r['capacity'] for r in references}=={20,25,30}
    for r in references:
        assert len(r['player'])==len(r['enemy'])==r['capacity']
        assert sum(m['item']['top'] for m in r['player'])<=4
        assert sorted(r['order'])==list(range(r['capacity']))
        assert r['enabled_player_bonds']==list(hard.ENABLED) and r['enemy_bonds']==[]
    links=0
    docs=('README.md','DESIGN_GUIDE.md','RECOMMENDATIONS.md','PROTOCOL.md','LOCAL25_PROTOCOL.md',
        'TERMINAL25_PROTOCOL.md','ROSTER25_PROTOCOL.md')
    for name in docs:
        for target in re.findall(r'\]\(([^)]+)\)',(HERE/name).read_text(encoding='utf-8')):
            if '://'in target:continue
            resolved=(HERE/target.split('#')[0]).resolve()
            if resolved!=(OUT/'delivery_checks.json').resolve():assert resolved.exists(),(name,target)
            links+=1
    log=OUT/'baseline_regression.txt';rates=[]
    for line in log.read_text(encoding='utf-8-sig').splitlines():
        p=re.findall(r'(\d+\.\d+)%',line)
        if len(p)==7:rates.append(float(p[-1]))
    assert len(rates)==6 and max(rates)-min(rates)<=15,rates
    result=dict(status='passed',report_rows=expected,archive_files=len(audit['archives']),document_links=links,
        executed_battles=audit['executed_battles'],native_journey_battles=audit['native_journey_battles'],
        exact_saved_battle_replays=audit['exact_saved_battle_replays'],
        regression=dict(battles=37500,overall_win_rates=rates,spread_pp=round(max(rates)-min(rates),2)),
        source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),OUT/'audit.json',log)},
        document_sha256={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in docs})
    atomic_json(OUT/'delivery_checks.json',result)
    print(json.dumps({k:v for k,v in result.items() if k in ('status','archive_files','document_links','executed_battles','exact_saved_battle_replays')}))


if __name__=='__main__':main()
