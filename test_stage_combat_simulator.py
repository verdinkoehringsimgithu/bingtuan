"""Six-stage encounter simulator using real ordered skills and owner equipment.

Example: python test_stage_combat_simulator.py --stage 6 --difficulty hard --trials 128
Use the research virtual environment documented in the integration guide.
"""
import argparse
import concurrent.futures
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'combat_numerical_paradigms/progression_difficulty'))
from model import encounter


def run_job(job):
    from refine_bands import confirmation
    return {**job, **confirmation(job)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=int, choices=range(1, 7))
    parser.add_argument('--difficulty', choices=('hard', 'very_hard', 'extremely_hard'), default='hard')
    parser.add_argument('--preparation', choices=('standard', 'underdeveloped', 'different_order', 'strong_collection', 'four_top'), default='standard')
    parser.add_argument('--trials', type=int, default=128)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--position', choices=('lower', 'center', 'upper'), default='center')
    parser.add_argument('--output', type=Path, default=ROOT / 'combat_numerical_paradigms/progression_difficulty/runtime_results.json')
    args = parser.parse_args()
    if args.trials < 1 or args.workers < 1:
        parser.error('trials and workers must be positive')
    data = json.loads((ROOT / 'combat_numerical_paradigms/progression_difficulty/results/encounter_model.json').read_text(encoding='utf-8'))
    jobs = []
    for stage in ([args.stage] if args.stage else range(1, 7)):
        info = encounter(stage, args.difficulty, position=args.position)
        row = next(r for r in data['recommended'] if r['stage'] == stage - 1 and r['difficulty'] == args.difficulty)
        for genre in ('C_I', 'C_R', 'M_I', 'M_R', 'M_C', 'R_I'):
            jobs.append(dict(stage=stage-1, genre=genre, enemy_genre=info['enemy_genre'], alpha=row['alpha'], beta=row['beta'], rho=info['rho'], preparation=args.preparation, trials=args.trials, pool_offset=24576, stream='growth-template-confirmation'))
    with concurrent.futures.ProcessPoolExecutor(args.workers) as pool:
        results = list(pool.map(run_job, jobs))
    output = dict(character_max_level=30, troop_max_level=30, stage_members=[5,10,15,20,25,30], top_equipment_cap=4, difficulty=args.difficulty, position=args.position, battles=len(jobs)*args.trials, stage_index_base=0, results=results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix('.tmp')
    temporary.write_text(json.dumps(output, ensure_ascii=False, indent=2, default=lambda x: x.item()), encoding='utf-8')
    temporary.replace(args.output)
    print(f'{len(jobs)*args.trials} battles saved to {args.output}')


if __name__ == '__main__':
    main()
