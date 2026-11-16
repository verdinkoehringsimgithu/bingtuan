"""Verify every research file is either tracked directly or in signed parts."""
import json,os,subprocess
from pathlib import Path
from restore_research import ROOT,digest
def git(*args):
 return subprocess.run(['git','-c','safe.directory='+str(ROOT),*args],cwd=ROOT,check=True,capture_output=True).stdout
def main():
 tracked={x.decode('utf-8').replace('\\','/') for x in git('ls-files','-z').split(b'\0') if x}
 m=json.loads((ROOT/'TransferData/manifest.json').read_text(encoding='utf-8'));archived={r['path'] for r in m['files']}
 missing=[];checked=0
 for base,dirs,names in os.walk(ROOT/'combat_numerical_paradigms'):
  dirs[:]=[d for d in dirs if d not in {'.venv','venv','__pycache__','.git'}]
  for name in names:
   p=Path(base)/name
   if p.suffix.lower() in {'.pyc','.pdb','.bak'}:continue
   rel=p.relative_to(ROOT).as_posix();checked+=1
   if rel not in tracked and rel not in archived:missing.append(rel)
 assert not missing,missing[:30]
 for row in m['parts']:
  path='TransferData/'+row['name'];assert path in tracked,path
  assert digest(ROOT/path)==row['sha256'],path
 required=['HOME_DEVELOPMENT.md','LegionBattle/LegionBattle/Assets/Scenes/BattleScene.unity','LegionBattle/LegionBattle/Assets/Resources/EffectTimingConfig.json',
  'LegionBattle/LegionBattle/Assets/Resources/FormationConfig.json','LegionBattle/LegionBattle/Assets/Characters/character_bond_labels.json',
  'LegionBattle/LegionBattle/Packages/manifest.json','LegionBattle/LegionBattle/ProjectSettings/ProjectVersion.txt']
 for path in required:assert path in tracked,path
 git('diff','--exit-code','--','LegionBattle/LegionBattle/Assets','LegionBattle/LegionBattle/Packages','LegionBattle/LegionBattle/ProjectSettings','TransferData')
 result=dict(passed=True,tracked_files=len(tracked),research_files_checked=checked,archived_files=len(archived),archive_parts=len(m['parts']),
  research_missing=0,archive_bytes=sum(x['bytes'] for x in m['parts']),source_commit=git('rev-parse','HEAD').decode().strip())
 (ROOT/'TransferData/repository_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
