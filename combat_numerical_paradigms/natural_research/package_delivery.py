"""Bundle reproducible inputs, experiment results and designs; verify every byte."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import hashlib,json,zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ARCHIVE=HERE.parent/'NATURAL_RESEARCH_DELIVERY_2026-10-13.zip'


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    inputs={}
    for path in HERE.rglob('*'):
        if not path.is_file() or '__pycache__' in path.parts or '.venv' in path.parts or path.name.startswith('calculation_checkpoints.sqlite') or path.name=='DELIVERY_MANIFEST.json' or path.name.endswith('.tmp'):continue
        inputs[path.relative_to(ROOT).as_posix()]=path
    for relative in ('test_30man_combat_simulator.py','generate_skills_preview.py','skill_affixes.txt','combat_numerical_paradigms/01_COMBAT_CORE_MATHEMATICAL_MODEL.md','combat_numerical_paradigms/02_PROGRESSION_STAGES_AND_BUDGETS.md','combat_numerical_paradigms/roster_research/roster_core.py','combat_numerical_paradigms/roster_research/run_study.py','combat_numerical_paradigms/roster_research/equipment_study.py','combat_numerical_paradigms/roster_research/results/common_operating_points.csv'):
        inputs[relative]=ROOT/relative
    inputs['SkillGenerator.cs']=HERE/'source_snapshots/SkillGenerator_checkpoint.cs'
    inputs['SkillGenerator.exe']=HERE/'source_snapshots/SkillGenerator_research.exe'
    records=[dict(path=name,bytes=path.stat().st_size,sha256=sha(path.read_bytes())) for name,path in sorted(inputs.items())]
    now=datetime.now(timezone(timedelta(hours=8))).isoformat();manifest=dict(saved_at=now,status='research_experiments_and_design_guides_delivered',experience_targets_not_all_met=True,protocol_executions=12029472,full_telemetry_battles=36000,player_owner_records=630000,stages=6,flows=6,top_cap=4,
        archived_root_generator='Frozen tested numerical source and its research executable; live parallel animation changes preserved in the workspace.',sqlite_checkpoints='Kept in the workspace; final result files and reproducible jobs are bundled.',files=records)
    file=HERE/'DELIVERY_MANIFEST.json';file.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');inputs[file.relative_to(ROOT).as_posix()]=file
    temporary=ARCHIVE.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temporary,'w') as bundle:
        for name,path in sorted(inputs.items()):bundle.write(path,name,compress_type=zipfile.ZIP_STORED if path.suffix in ('.gz','.png','.joblib') else zipfile.ZIP_DEFLATED,compresslevel=6)
    with zipfile.ZipFile(temporary) as bundle:
        bad=bundle.testzip();assert bad is None,bad
        for record in records:assert sha(bundle.read(record['path']))==record['sha256'],record['path']
    temporary.replace(ARCHIVE);value=sha(ARCHIVE.read_bytes());ARCHIVE.with_suffix('.zip.sha256').write_text(value+'  '+ARCHIVE.name+'\n',encoding='ascii')
    receipt=dict(saved_at=now,archive=str(ARCHIVE),files=len(inputs),bytes=ARCHIVE.stat().st_size,sha256=value,integrity_verified=True)
    (HERE/'results/package_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(receipt,ensure_ascii=False))


if __name__=='__main__':main()
