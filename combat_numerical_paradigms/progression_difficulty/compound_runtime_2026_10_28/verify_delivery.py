"""Audit all 23 supported mechanisms and preserve earlier evidence."""
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
    for name,count in (('compound_parity.json',3360),('tactical_parity.json',3360),('augmentation_parity.json',2880),('amplification_parity.json',3360),('support_parity.json',1920),('evasion_parity.json',2400),('opening_parity.json',1920),('limited_parity.json',2400),('runtime_parity.json',480)):
        result=read(name);assert result['passed'] and result['cases']==count,name
    evasion=read('compound_parity.json');assert evasion['actions']==63244
    compound=read('compound_invariants.json');assert compound['passed'] and len(compound['checks'])==35
    tactical=read('tactical_invariants.json');assert tactical['passed'] and len(tactical['checks'])==31
    aug=read('augmentation_invariants.json');assert aug['passed'] and len(aug['checks'])==38
    amp=read('amplification_invariants.json');assert amp['passed'] and len(amp['checks'])==29
    support=read('support_invariants.json');assert support['passed'] and len(support['checks'])==40
    invariant=read('evasion_invariants.json');assert invariant['passed'] and len(invariant['checks'])==54
    assert read('runtime_invariants.json')==dict(passed=True,invariant_checks=11)
    counts={}
    for name,count in (('unity_validation.json',117),('tactical_validation.json',114),('augmentation_validation.json',132),('amplification_validation.json',132),('support_validation.json',153),('evasion_validation.json',142),('identity_validation.json',71),('expedition_validation.json',135),('label_validation.json',3698)):
        result=read(name);assert result['passed'] and len(result['checks'])==count,name;counts[name]=count
    assert read('lifecycle_validation.json')==dict(passed=True,lifecycle_checks=73,navigation_owner='caller')
    protected={p:sha(PROJECT/p).upper()==digest.upper() for p,digest in read('protected_assets.json').items()}
    assert all(protected.values()),protected
    for name,digest in read('baseline_manifest.json').items():assert sha(HERE/'baseline'/Path(name).name).upper()==digest.upper(),name
    for name,digest in read('parity_sources.json')['sources'].items():assert sha(ROOT/name)==digest,name
    wins=[float(m.group(1)) for line in (HERE/'baseline_regression.log').read_text(encoding='utf-8-sig').splitlines()
          if (m:=re.search(r'\s(\d+\.\d+)%\s*$',line))]
    assert len(wins)==6 and max(wins)-min(wins)<=15,wins
    names=['CombatCompoundBonds','CombatTacticalBonds','CombatAugmentationBonds','CombatAmplificationBonds','CombatSupportBonds','CombatEvasionBonds','CombatRuntime','CombatPersistentLimits','CharacterTraits','OpeningBondRules','BattleTroop','BattleSceneRequest','BattleSceneFlow','BattleSceneController',
           'BattleInspectionManager','BattleEngine','BattleTurnReport','CompoundRuntimeProbe','ExpeditionRuntimeProbe']
    files=[PROJECT/'Assets/Scripts/Battle'/f'{name}.cs' for name in names]+[PROJECT/'Assets/Editor/CompoundRuntimeValidation.cs']
    files += [Path(str(path)+'.meta') for path in list(files)]
    files += [HERE.parent/'IDENTITY_RUNTIME_INTEGRATION.md',HERE/'README.md',HERE/'run_numeric_checks.ps1',HERE/'run_unity_checks.ps1',HERE/'generate_parity.py',HERE/'CompoundInvariantHarness.cs',HERE/'CompoundParityHarness.cs']
    if '--record' in sys.argv:
        manifest={str(path.relative_to(ROOT)):sha(path) for path in files}
        for path in files:
            relative=path.relative_to(PROJECT) if path.is_relative_to(PROJECT) else Path('evidence')/path.relative_to(ROOT)
            target=HERE/'delivered_sources'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
        (HERE/'delivery_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    for name,digest in read('delivery_manifest.json').items():
        path=ROOT/name;assert sha(path)==digest,name
        relative=path.relative_to(PROJECT) if path.is_relative_to(PROJECT) else Path('evidence')/path.relative_to(ROOT)
        assert sha(HERE/'delivered_sources'/relative)==digest,name
    result=dict(passed=True,new_battle_cases=3360,new_actions=evasion['actions'],maximum_relative_error=evasion['maximum_relative_error'],
        previous_battle_cases=18720,total_battle_cases=22080,new_invariant_checks=35,total_invariant_checks=238,unity_checks=counts,lifecycle_checks=73,baseline_battles=37500,
        overall_win_rates=wins,spread_percentage_points=round(max(wins)-min(wins),3),protected_unchanged=protected,
        added_mechanisms=['maid','farmer','adventurer'],total_ported_mechanisms=23)
    (HERE/'delivery_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()




