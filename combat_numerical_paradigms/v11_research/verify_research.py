"""Meaningful verification of instrumented physics and exported evidence."""
import gzip
import json
from pathlib import Path
import numpy as np
from research_core import *

def verify_extensions():
    checks=0
    disjoint=("physical","physical_crit","pure_true","pure_true_crit","max_dot","lost_dot","backlash","execute","overflow_true")
    for stage in range(6):
        for g in GENRES:
            for config in ({},{"attack":3.,"pierce":2.},{"death_lock":.3},{"crit":40.,"overflow_true":1.},
                           {"overheal_shield":1.,"shield_cap":1.},{"ramp":2.,"hit_floor":1.}):
                player,enemy=assemble(stage,g),assemble(stage,GENRES[(GENRES.index(g)+1)%6])
                p=[1.2,1.1,.2,.05,50.,1.2]
                res,features,rounds=run(player,enemy,stable_seed("extensions",stage,g,str(config)),p,config,True)
                for t in (player,enemy):
                    component_sum=sum(t.metrics[c] for c in disjoint)
                    assert np.isclose(component_sum,t.metrics["effective_damage"],rtol=1e-10,atol=1e-7)
                    assert t.shield>=0
                    assert np.isfinite(list(features.values())).all()
                # HP conservation uses effective damage and effective healing,
                # with both death-lock restore and terminal negative DoT clamped.
                for row in rounds:
                    for side,opp in (("p","e"),("e","p")):
                        bp=player.max_bp if side=="p" else enemy.max_bp
                        opp_bp=enemy.max_bp if side=="p" else player.max_bp
                        incoming=sum(row[f"{opp}_{c}"] for c in disjoint)*opp_bp/bp
                        healed=sum(row[f"{side}_{c}"] for c in ("lifesteal","self_heal","macro_heal","death_lock"))
                        assert np.isclose(row[f"{side}_bp_start"]-incoming+healed,row[f"{side}_bp_end"],atol=1e-10), (stage,g,config,row["turn"],side)
                checks+=1
    return dict(intervention_cases=checks,disjoint_damage_and_hp_conservation=True)

def verify_files(directory):
    import pandas as pd
    directory=Path(directory)
    feat=pd.read_csv(directory/"telemetry_features.csv.gz",dtype={"seed":str})
    raw_count=raw_rounds=0
    for path in sorted(directory.glob("rounds_*.jsonl.gz")):
        with gzip.open(path,"rt",encoding="utf-8") as f:
            for line in f:
                b=json.loads(line);raw_count+=1;raw_rounds+=len(b["rounds"])
                assert b["summary"]["turns"]==len(b["rounds"])
    assert raw_count==len(feat)
    assert raw_rounds==feat.turns.sum()
    assert feat.battle_id.nunique()==len(feat)
    models=__import__("joblib").load(directory/"discovery_models.joblib")
    assert not set(models["features"])&{"win","decisive_win","censored","hp","enemy_hp","turns","stage","difficulty","seed"}
    # Preserve 64-bit seeds through CSV read and replay exact complete traces.
    for r in feat.iloc[::max(1,len(feat)//30)].itertuples():
        p=[getattr(r,k) for k in PARAMS]
        summary,features,rounds=run(assemble(r.stage-1,r.genre),assemble(r.stage-1,r.opponent),int(r.seed),p,telemetry=True)
        assert summary["win"]==r.win and summary["turns"]==r.turns
        assert np.isclose(summary["hp"],r.hp,atol=1e-12)
        for key,val in features.items(): assert np.isclose(val,getattr(r,key),atol=1e-10),key
    audit=json.loads((directory/"audit.json").read_text(encoding="utf-8"))
    assert audit["source_sha256"]==hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    return dict(telemetry_battles=raw_count,telemetry_rounds=raw_rounds,unique_battle_ids=True,exact_seed_replay_cases=30,outcome_excluded_from_discovery=True,source_unchanged=True)

def verify_parallel():
    from concurrent.futures import ProcessPoolExecutor
    from run_research import batch_worker
    jobs=[(j%6,GENRES[j%6],[1.1,.9,.1,.02,25.,1.1],24,"parallel-parity",{"ramp":1.},None,None) for j in range(12)]
    serial=[batch_worker(j) for j in jobs]
    with ProcessPoolExecutor(max_workers=2) as pool:parallel=list(pool.map(batch_worker,jobs))
    assert serial==parallel
    return dict(serial_parallel_identical=True,parallel_comparison_cells=len(jobs))

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--output",default=str(Path(__file__).parent/"results"));args=p.parse_args()
    result={**parity(),**verify_extensions(),**verify_files(args.output),**verify_parallel()}
    Path(args.output,"verification.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
