"""Review deliverables, persist file hashes, and bundle code/data/source snapshots."""
from run_study import *
import csv
import zipfile

def main():
    root=Path(__file__).parent.resolve();q=root/'results'
    # Display actual integer effects, matching the already measured int conversion.
    for filename in ('four_item_strength_curves.csv','regular_four_item_loadouts.csv','regular_four_item_holdout.csv'):
        f=pd.read_csv(q/filename)
        f['loadout']=f.loadout.map(lambda text:json.dumps([(p,k,int(v) if k in ('extra_use','cleanse') else v) for p,k,v in json.loads(text)]))
        f.to_csv(q/filename,index=False,encoding='utf-8-sig')
    config=json.loads((q/'regular_roster_equipment_configs.json').read_text(encoding='utf-8'))
    for record in config:
        assert len(record['members'])==STAGES[record['stage']-1][0]
        assert sum(m['equipment']['top'] for m in record['members'])<=4
        for m in record['members']:
            item=m['equipment']
            if item['kind'] in ('extra_use','cleanse'):item['value']=int(item['value'])
    save_json(q/'regular_roster_equipment_configs.json',config)
    from build_report import build
    build(q)
    # Only intended final CSVs: no duplicate columns or missing strata.
    for path in q.glob('*.csv'):
        with path.open(encoding='utf-8-sig',newline='') as f:header=next(csv.reader(f))
        assert len(header)==len(set(header)),path.name
    for name in ('equipped_difficulty_holdout.csv','operating_four_item_holdout.csv','regular_four_item_holdout.csv','common_stat_recommendations.csv','strategic_path_reference_checks.csv','heterogeneous_channel_holdout.csv'):
        d=pd.read_csv(q/name);assert set(d.stage)==set(range(6)) and set(d.genre)==set(GENRES),name
    for path in [root/'DESIGN_SPECIFICATION.md',*root.glob('stage_guides/*.md')]:
        import re
        content=path.read_text(encoding='utf-8')
        for target in re.findall(r'\]\(([^)]+)\)',content):
            assert Path(target).exists(),(path,target)
    expected=json.loads((q/'final_model_checks.json').read_text(encoding='utf-8'))['source_sha256']
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==expected
    # Ledger is the saved protocol cells incl. paired reference executions;
    # summaries and repeat verification are not independent battle samples.
    ledger=[]
    specs=[('roster_count_order_scan.csv',False),('enemy_global_scan.csv',False),('enemy_local_scan.csv',False),('difficulty_holdout.csv',False),
        ('common_stat_scan.csv',True),('mechanic_response_scan.csv',True),('four_item_allocation_search.csv',False),('four_item_holdout.csv',True),('top_item_scarcity_curve.csv',True),
        ('expanded_role_count_scan.csv',False),('expanded_role_count_holdout.csv',True),('equipped_difficulty_calibration.csv',False),('equipped_difficulty_holdout.csv',False),
        ('operating_mechanic_responses.csv',True),('operating_allocation_training.csv',False),('operating_four_item_holdout.csv',True),('strategic_paths_by_stage.csv',True),
        ('enemy_counter_equipment_by_stage.csv',False),('heterogeneous_embedding_by_stage.csv',True),('heterogeneous_channel_holdout.csv',True),('conditional_alpha_beta_surfaces.csv',False),
        ('four_item_strength_curves.csv',True),('regular_four_item_holdout.csv',True),('versatility_all_flow_matrix.csv',True)]
    for name,paired in specs:
        d=pd.read_csv(q/name);ledger.append(dict(file=name,cells=len(d),recorded_battle_executions=int(d.n.sum())*(2 if paired else 1),paired=paired))
    for name in ('telemetry_features.csv.gz','unique_owner_training.csv.gz','unique_owner_holdout_battles.csv.gz'):
        d=pd.read_csv(q/name);ledger.append(dict(file=name,cells=len(d),recorded_battle_executions=len(d),paired=False))
    pd.DataFrame(ledger).to_csv(q/'experiment_ledger.csv',index=False,encoding='utf-8-sig')
    save_json(q/'delivery_review.json',dict(all_six_stages_three_tasks=True,one_item_four_top=True,source_unchanged=True,csv_unique_columns=True,links_exist=True,
        recorded_battle_executions=sum(x['recorded_battle_executions'] for x in ledger),definition='Sum of protocol executions represented by saved cells; paired baselines count twice. Not independent observations. Calibration path training and repeated checks excluded.',
        full_telemetry=28800,rounds=294212,player_owner_records=504000))
    snapshots=[ROOT/'test_30man_combat_simulator.py',ROOT/'generate_skills_preview.py',ROOT/'skill_affixes.txt',ROOT/'AGENT.md',ROOT/'combat_numerical_paradigms/01_COMBAT_CORE_MATHEMATICAL_MODEL.md',ROOT/'combat_numerical_paradigms/02_PROGRESSION_STAGES_AND_BUDGETS.md',
        ROOT/'LegionBattle/LegionBattle/Assets/Scripts/Battle/BattleTroop.cs',ROOT/'LegionBattle/LegionBattle/Assets/Scripts/Battle/BattleMember.cs',ROOT/'LegionBattle/LegionBattle/Assets/Scripts/Battle/BattleSkill.cs']
    files=[p for p in root.rglob('*') if p.is_file() and not any(part in ('__pycache__','.venv') for part in p.parts) and p.suffix!='.zip' and p.name!='file_hashes.json']+snapshots
    save_json(q/'file_hashes.json',{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    destination=ROOT/'combat_numerical_paradigms/ROSTER_RESEARCH_DELIVERY.zip'
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for p in files+[q/'file_hashes.json']:archive.write(p,p.relative_to(ROOT))
    with zipfile.ZipFile(destination) as archive:assert archive.testzip() is None
    print(json.dumps(dict(package=str(destination),bytes=destination.stat().st_size,files=len(files)+1,recorded_battle_executions=sum(x['recorded_battle_executions'] for x in ledger)),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
