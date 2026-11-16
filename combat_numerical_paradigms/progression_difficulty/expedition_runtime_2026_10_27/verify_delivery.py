"""Read-only audit by default; --record freezes the reviewed production source set."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROJECT = ROOT/'LegionBattle/LegionBattle'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((HERE/name).read_text(encoding='utf-8-sig'))


def main():
    for name, count in (('runtime_parity.json',480),('limited_parity.json',2400)):
        result=read(name)
        assert result['passed'] and result['cases']==count, name
    assert read('runtime_invariants.json')==dict(passed=True,invariant_checks=11)
    unity=read('unity_validation.json')
    assert unity['passed'] and len(unity['checks'])>=135
    assert len(set(unity['checks']))==len(unity['checks'])
    assert read('lifecycle_validation.json')==dict(passed=True,lifecycle_checks=73,navigation_owner='caller')
    presentation={name:digest(PROJECT/name).upper()==sha for name,sha in read('presentation_before.json').items()}
    assert all(presentation.values()), presentation
    for path,sha in read('baseline_manifest.json').items():
        assert digest(HERE/'baseline'/Path(path).name).upper()==sha.upper(), path
    provenance=read('limited_parity_sources.json')
    assert provenance['stages']==[5,10,15,20,25,30] and len(provenance['profiles'])==5
    for path,sha in provenance['sources'].items():
        assert digest(ROOT/path)==sha, path
    log=(HERE/'baseline_regression.log').read_text(encoding='utf-8-sig')
    wins=[float(match.group(1)) for line in log.splitlines()
          if (match:=re.search(r'\s(\d+\.\d+)%\s*$',line))]
    assert len(wins)==6, wins
    spread=round(max(wins)-min(wins),3)
    assert spread<=15, wins
    source_names=['CombatRuntime','CombatPersistentLimits','ExpeditionState','BattleTroop',
                  'BattleSceneRequest','BattleSceneFlow','BattleSceneController','BattleInspectionManager','ExpeditionRuntimeProbe']
    paths=[PROJECT/'Assets/Scripts/Battle'/f'{name}.cs' for name in source_names]
    paths.append(PROJECT/'Assets/Editor/ExpeditionValidation.cs')
    paths += [Path(str(path)+'.meta') for path in list(paths)]
    if '--record' in sys.argv:
        manifest={str(path.relative_to(ROOT)):digest(path) for path in paths}
        for path in paths:
            target=HERE/'delivered_sources'/path.relative_to(PROJECT)
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(path,target)
        (HERE/'delivery_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    manifest=read('delivery_manifest.json')
    for name,sha in manifest.items():
        path=ROOT/name
        assert digest(path)==sha, name
        assert digest(HERE/'delivered_sources'/path.relative_to(PROJECT))==sha
    checks=dict(passed=True,baseline_cases=480,limited_cases=2400,limited_max_relative_error=read('limited_parity.json')['maximum_relative_error'],
                unity_checks=len(unity['checks']),lifecycle_checks=73,baseline_battles=37500,
                baseline_overall_wr_percent=wins,baseline_spread_percentage_points=spread,presentation_unchanged=presentation,
                production_source_files=len(paths),identity_synergy_runtime_ported=False)
    (HERE/'delivery_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(checks,ensure_ascii=False))


if __name__=='__main__':
    main()
