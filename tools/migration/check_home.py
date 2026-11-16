"""Offline check of the portable project and signed production files."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 required=['LegionBattle/LegionBattle/Assets/Scenes/BattleScene.unity','LegionBattle/LegionBattle/Assets/Scenes/BattleEffectTestScene.unity',
  'LegionBattle/LegionBattle/Packages/manifest.json','LegionBattle/LegionBattle/ProjectSettings/ProjectVersion.txt',
  'LegionBattle/LegionBattle/Assets/Characters/character_bond_labels.json','LegionBattle/LegionBattle/Assets/Resources/EffectTimingConfig.json',
  'LegionBattle/LegionBattle/Assets/Resources/FormationConfig.json','CharaClassifier.cs','CharacterTagging.cs','SkillGenerator.cs','skill_affixes.txt','effect_names.json']
 for name in required:assert (ROOT/name).is_file(),'Missing '+name
 manifest=ROOT/'combat_numerical_paradigms/progression_difficulty/compound_runtime_2026_10_28/delivery_manifest.json'
 checks=json.loads(manifest.read_text(encoding='utf-8-sig'));checked=0
 for name,digest in checks.items():
  p=ROOT/name.replace('\\','/')
  assert p.is_file(),'Restore research first: '+str(p)
  assert hashlib.sha256(p.read_bytes()).hexdigest()==digest,'Changed since signed production: '+str(p)
  checked+=1
 print('Home development files present;',checked,'signed production/doc files verified.')
if __name__=='__main__':main()
