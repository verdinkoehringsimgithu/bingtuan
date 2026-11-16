"""Freeze completed research files without launching simulations."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
STAMP = '2026-10-12-20_54'
CHECKPOINT = HERE / 'CHECKPOINT_2026-10-12.md'
LOG = ROOT / 'CC-Session-Logs' / (STAMP + '-natural-combat-checkpoint.md')
MANIFEST = HERE / 'CHECKPOINT_MANIFEST_2026-10-12.json'
ARCHIVE = HERE.parent / ('NATURAL_RESEARCH_CHECKPOINT_' + STAMP + '.zip')


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def main():
    snapshot = HERE / 'source_snapshots' / 'SkillGenerator_checkpoint.cs'
    shutil.copy2(ROOT / 'SkillGenerator.cs', snapshot)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CHECKPOINT, LOG)
    files = set(p for p in HERE.rglob('*') if p.is_file()
                and '__pycache__' not in p.parts and p != MANIFEST)
    files.update(p for p in (ROOT / 'combat_numerical_paradigms/roster_research').iterdir()
                 if p.is_file() and p.suffix in ('.py', '.ps1', '.txt', '.md'))
    for relative in ('SkillGenerator.cs', 'test_30man_combat_simulator.py',
                     'generate_skills_preview.py', 'skill_affixes.txt', 'AGENT.md',
                     'combat_numerical_paradigms/01_COMBAT_CORE_MATHEMATICAL_MODEL.md',
                     'combat_numerical_paradigms/02_PROGRESSION_STAGES_AND_BUDGETS.md',
                     'combat_numerical_paradigms/roster_research/results/common_operating_points.csv'):
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        files.add(path)
    files.add(LOG)
    records = [dict(path=p.relative_to(ROOT).as_posix(), bytes=p.stat().st_size,
                    sha256=digest(p)) for p in sorted(files)]
    state = dict(saved_at_local=datetime.now().astimezone().isoformat(),
                 status='stopped_by_user_quota_condition',
                 observed_primary_usage_percent=96,
                 usage_percent_is_not_context_token_count=True,
                 simulation_process_stopped=True,
                 completed=['reachability', 'independent_reachability', 'difficulty',
                            'role_count_order', 'common_equipment_stats', 'model_validation'],
                 incomplete=['mechanism_response_scan', 'four_top_equipment',
                             'telemetry', 'unsupervised_discovery', 'unique_interventions',
                             'four_strategic_paths', 'final_design_specification'],
                 unsaved_interrupted_phase=dict(name='mechanism_response_scan',
                                               latest_logged_cells=6600, planned_cells=8100,
                                               persisted_cells=0),
                 caveats=['candidate_reachability and optimization training predate allocation mirror fix',
                          'generator source changed; GUI executable and Unity integration not updated',
                          'D2 joint targets not all met; all three tasks remain incomplete'],
                 archive_relative_path=ARCHIVE.relative_to(ROOT).as_posix(),
                 files=records)
    temporary = MANIFEST.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(MANIFEST)
    temporary_zip = ARCHIVE.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temporary_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as target:
        for path in sorted(files | {MANIFEST}):
            target.write(path, path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(temporary_zip) as target:
        bad = target.testzip()
        if bad:
            raise RuntimeError('Archive CRC failure: ' + bad)
        for record in records:
            if hashlib.sha256(target.read(record['path'])).hexdigest() != record['sha256']:
                raise RuntimeError('Archive SHA256 failure: ' + record['path'])
    temporary_zip.replace(ARCHIVE)
    archive_digest = digest(ARCHIVE)
    ARCHIVE.with_suffix('.zip.sha256').write_text(archive_digest + '  ' + ARCHIVE.name + '\n',
                                              encoding='ascii')
    print(json.dumps(dict(files=len(records), archive=str(ARCHIVE), bytes=ARCHIVE.stat().st_size,
                          sha256=archive_digest, checkpoint=str(CHECKPOINT), log=str(LOG),
                          integrity_verified=True), ensure_ascii=False))


if __name__ == '__main__':
    main()
