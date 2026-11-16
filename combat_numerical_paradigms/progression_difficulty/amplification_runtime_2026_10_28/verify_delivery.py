"""Audit the amplification runtime revision and preserve earlier evidence."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PROJECT=ROOT/'LegionBattle/LegionBattle'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(name):return json.loads((HERE/name).read_text(encoding='utf-8-sig'))


def main():
    for name,count in (('amplification_parity.json',3360),('support_parity.json',1920),('evasion_parity.json',2400),('opening_parity.json',1920),('limited_parity.json',2400),('runtime_parity.json',480)):
        result=read(name);assert result['passed'] and result['cases']==count,name
    evasion=read('amplification_parity.json');assert evasion['actions']==58552
    amp=read('amplification_invariants.json');assert amp['passed'] and len(amp['checks'])==29
    support=read('support_invariants.json');assert support['passed'] and len(support['checks'])==40
    invariant=read('evasion_invariants.json');assert invariant['passed'] and len(invariant['checks'])==54
    assert read('runtime_invariants.json')==dict(passed=True,invariant_checks=11)
    counts={}
    for name,count in (('unity_validation.json',132),('support_validation.json',153),('evasion_validation.json',142),('identity_validation.json',71),('expedition_validation.json',135),('label_validation.json',3698)):
        result=read(name);assert result['passed'] and len(result['checks'])==count,name;counts[name]=count
    assert read('lifecycle_validation.json')==dict(passed=True,lifecycle_checks=73,navigation_owner='caller')
    protected={p:sha(PROJECT/p).upper()==digest.upper() for p,digest in read('protected_assets.json').items()}
    assert all(protected.values()),protected
    for name,digest in read('baseline_manifest.json').items():assert sha(HERE/'baseline'/Path(name).name).upper()==digest.upper(),name
    for name,digest in read('parity_sources.json')['sources'].items():assert sha(ROOT/name)==digest,name
    wins=[float(m.group(1)) for line in (HERE/'baseline_regression.log').read_text(encoding='utf-8-sig').splitlines()
          if (m:=re.search(r'\s(\d+\.\d+)%\s*$',line))]
    assert len(wins)==6 and max(wins)-min(wins)<=15,wins
    names=['CombatAmplificationBonds','CombatSupportBonds','CombatEvasionBonds','CombatRuntime','CombatPersistentLimits','CharacterTraits','OpeningBondRules','BattleTroop','BattleSceneRequest','BattleSceneFlow','BattleSceneController',
           'BattleInspectionManager','BattleEngine','BattleTurnReport','AmplificationRuntimeProbe']
    files=[PROJECT/'Assets/Scripts/Battle'/f'{name}.cs' for name in names]+[PROJECT/'Assets/Editor/AmplificationRuntimeValidation.cs']
    files += [Path(str(path)+'.meta') for path in list(files)]
    if '--record' in sys.argv:
        manifest={str(path.relative_to(ROOT)):sha(path) for path in files}
        for path in files:
            target=HERE/'delivered_sources'/path.relative_to(PROJECT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
        (HERE/'delivery_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    for name,digest in read('delivery_manifest.json').items():
        path=ROOT/name;assert sha(path)==digest,name
        assert sha(HERE/'delivered_sources'/path.relative_to(PROJECT))==digest,name
    result=dict(passed=True,new_battle_cases=3360,new_actions=evasion['actions'],maximum_relative_error=evasion['maximum_relative_error'],
        previous_battle_cases=9120,new_invariant_checks=29,unity_checks=counts,lifecycle_checks=73,baseline_battles=37500,
        overall_win_rates=wins,spread_percentage_points=round(max(wins)-min(wins),3),protected_unchanged=protected,
        added_mechanisms=['academy','cult','fighter','heroine','lady'],total_ported_mechanisms=11)
    (HERE/'delivery_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
