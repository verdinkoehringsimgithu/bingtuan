"""Archive the standalone numerical model and reproducible experimental inputs."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import hashlib,json,zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ARCHIVE=HERE.parent/'PROGRESSION_DIFFICULTY_DELIVERY_2026-10-13.zip'


def main():
    paths={}
    for p in HERE.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and '.venv' not in p.parts and not p.name.startswith('checkpoints.sqlite') and p.name!='DELIVERY_MANIFEST.json' and not p.name.endswith('.tmp'):paths[p.relative_to(ROOT).as_posix()]=p
    for relative in ('test_30man_combat_simulator.py','generate_skills_preview.py','skill_affixes.txt','combat_numerical_paradigms/01_COMBAT_CORE_MATHEMATICAL_MODEL.md','combat_numerical_paradigms/02_PROGRESSION_STAGES_AND_BUDGETS.md','combat_numerical_paradigms/roster_research/roster_core.py','combat_numerical_paradigms/roster_research/run_study.py','combat_numerical_paradigms/roster_research/equipment_study.py','combat_numerical_paradigms/natural_research/natural_core.py','combat_numerical_paradigms/natural_research/run_natural.py','combat_numerical_paradigms/natural_research/GeneratorBridge.cs','combat_numerical_paradigms/natural_research/export_catalog.ps1','combat_numerical_paradigms/natural_research/requirements.txt','combat_numerical_paradigms/natural_research/source_snapshots/SkillGenerator_before.cs','combat_numerical_paradigms/natural_research/source_snapshots/SkillGenerator_checkpoint.cs'):
        paths[relative]=ROOT/relative
    base='combat_numerical_paradigms/natural_research/results/'
    for name in ('selected_stat_profile.json','equipment_operating_candidates.csv','catalog_before.json','catalog_current.json','catalog_holdout.json','catalog_final_test.json','catalog_old_validation_growth.json','catalog_old_final_growth.json','catalog_growth_confirmation.json','catalog_old_growth_confirmation.json'):paths[base+name]=ROOT/(base+name)
    records=[dict(path=name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for name,p in sorted(paths.items())]
    manifest=HERE/'DELIVERY_MANIFEST.json';manifest.write_text(json.dumps(dict(saved_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),status='guidance_model_delivered',reference_level_bands_are_design_inputs=True,files=records),ensure_ascii=False,indent=2),encoding='utf-8');paths[manifest.relative_to(ROOT).as_posix()]=manifest
    temporary=ARCHIVE.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temporary,'w') as bundle:
        for name,p in sorted(paths.items()):bundle.write(p,name,compress_type=zipfile.ZIP_STORED if p.suffix in ('.gz','.png') else zipfile.ZIP_DEFLATED,compresslevel=6)
    with zipfile.ZipFile(temporary) as bundle:
        assert bundle.testzip() is None
        for record in records:assert hashlib.sha256(bundle.read(record['path'])).hexdigest()==record['sha256']
    temporary.replace(ARCHIVE);value=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest();ARCHIVE.with_suffix('.zip.sha256').write_text(value+'  '+ARCHIVE.name+'\n',encoding='ascii')
    print(json.dumps(dict(archive=str(ARCHIVE),files=len(paths),bytes=ARCHIVE.stat().st_size,sha256=value,verified=True)))


if __name__=='__main__':main()
