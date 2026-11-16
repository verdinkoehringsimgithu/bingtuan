"""Verify the new runtime revision without re-signing previous research outputs."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PROJECT=ROOT/'LegionBattle/LegionBattle'


def read(name):return json.loads((HERE/name).read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def strip_traits(text):
    result=[];skipping=False
    for line in text.splitlines():
        if line=='    traits:':skipping=True;continue
        if skipping and line.startswith('      '):continue
        skipping=False;result.append(line)
    return result


def main():
    for name,count in (('opening_parity.json',1920),('limited_parity.json',2400),('runtime_parity.json',480)):
        data=read(name);assert data['passed'] and data['cases']==count,name
    assert read('runtime_invariants.json')==dict(passed=True,invariant_checks=11)
    labels=read('label_validation.json');assert labels['passed'] and labels['portraits']==1229 and labels['people']==1213
    unity=read('unity_validation.json');assert unity['passed'] and len(unity['checks'])>=70
    expedition=read('expedition_validation.json');assert expedition['passed'] and len(expedition['checks'])==135
    assert read('lifecycle_validation.json')==dict(passed=True,lifecycle_checks=73,navigation_owner='caller')
    protected={p:sha(PROJECT/p).upper()==value.upper() for p,value in read('protected_assets.json').items()}
    assert all(protected.values()),protected
    original=(HERE/'baseline/CharacterDatabase.asset').read_text(encoding='utf-8-sig')
    current=(PROJECT/'Assets/Characters/CharacterDatabase.asset').read_text(encoding='utf-8-sig')
    assert strip_traits(current)==original.splitlines(),'Non-trait database fields changed'
    for name,digest in read('baseline_manifest.json').items():
        assert sha(HERE/'baseline'/Path(name).name).upper()==digest.upper(),name
    for name,digest in read('parity_sources.json')['sources'].items():assert sha(ROOT/name)==digest,name
    wins=[float(m.group(1)) for line in (HERE/'baseline_regression.log').read_text(encoding='utf-8-sig').splitlines()
          if (m:=re.search(r'\s(\d+\.\d+)%\s*$',line))]
    assert len(wins)==6 and max(wins)-min(wins)<=15,wins
    runtime=['CharacterTraits','OpeningBondRules','IdentityRuntimeProbe','CharacterSheetData','BattleMember','CombatRuntime',
             'BattleTroop','BattleSceneRequest','BattleSceneFlow','BattleSceneController','BattleInspectionManager']
    editor=['CharacterTraitsImporter','IdentityRuntimeValidation','BattleSceneSetupTool']
    files=[PROJECT/'Assets/Scripts/Battle'/f'{n}.cs' for n in runtime]+[PROJECT/'Assets/Editor'/f'{n}.cs' for n in editor]
    files += [Path(str(p)+'.meta') for p in list(files)]
    files.append(PROJECT/'Assets/Characters/CharacterDatabase.asset')
    if '--record' in sys.argv:
        manifest={str(p.relative_to(ROOT)):sha(p) for p in files}
        for p in files:
            target=HERE/'delivered_sources'/p.relative_to(PROJECT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
        (HERE/'delivery_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    for name,digest in read('delivery_manifest.json').items():
        p=ROOT/name;assert sha(p)==digest,name
        assert sha(HERE/'delivered_sources'/p.relative_to(PROJECT))==digest,name
    result=dict(passed=True,portraits=1229,people=1213,label_checks=len(labels['checks']),opening_battle_cases=1920,
        opening_max_relative_error=read('opening_parity.json')['maximum_relative_error'],previous_battle_cases=2880,
        unity_checks=len(unity['checks']),expedition_checks=135,lifecycle_checks=73,
        baseline_battles=37500,overall_win_rates=wins,spread_percentage_points=round(max(wins)-min(wins),3),
        protected_unchanged=protected,database_only_traits_changed=True,production_mechanisms=['sailor','merchant'])
    (HERE/'delivery_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
