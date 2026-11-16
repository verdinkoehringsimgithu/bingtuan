"""Additional fixed fast-threat NPC references, calibrated before path fitting.

The first region grid often leaves healing builds with high winning HP. This
separate experiment broadens the fixed NPC family instead of relabelling them.
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
from pathlib import Path
import sqlite3

import measure_response as lab
from run_bonds import atomic_json

OUT = lab.OUT / 'low_margin'


def signature():
    sig, manifest = lab.signature()
    value = dict(base_response_signature=sig, sources={**manifest['sources'],
        str(Path(__file__)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest(),value


def tasks(phase):
    if phase=='regions':
        return [dict(stage=s,kind='fast_clutch',code=f'{a}:{b}',enemy_genre='C_I',
            macro=(a,b,0,0,500,1)) for s in range(6) for a in (.1,.2,.35) for b in (3.,4.,5.,6.,8.,10.,12.)]
    rows=json.loads((OUT/'regions.json').read_text(encoding='utf-8'))['regions']
    return [dict(stage=r['stage'],genre=g,gear=gear,region='low_margin',enemy_genre=r['enemy_genre'],macro=r['macro'],
        pool=1010000,bank='validation') for r in rows for g in lab.GENRES for gear in ('basic','four_top')]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',choices=('regions','curves'),required=True)
    p.add_argument('--workers',type=int,default=6);args=p.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    sig,manifest=signature();atomic_json(OUT/'manifest.json',{**manifest,'signature':sig})
    db=sqlite3.connect(OUT/'checkpoints.sqlite');db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS cells(key TEXT PRIMARY KEY,signature TEXT,phase TEXT,job TEXT,result TEXT)');db.commit()
    wanted=set();pending={};jobs=tasks(args.phase)
    with cf.ProcessPoolExecutor(args.workers) as pool:
        for j in jobs:
            encoded=json.dumps(j,sort_keys=True);key=hashlib.sha256((sig+args.phase+encoded).encode()).hexdigest();wanted.add(key)
            if db.execute('SELECT 1 FROM cells WHERE key=?',(key,)).fetchone():continue
            pending[pool.submit(lab.calibrate if args.phase=='regions' else lab.curve,{**j,'key':key,'output':str(OUT.resolve())})]=(key,encoded)
        print('low margin',args.phase,len(pending),'pending',flush=True)
        for i,f in enumerate(cf.as_completed(pending),1):
            key,encoded=pending[f];r=f.result()
            db.execute('INSERT INTO cells VALUES(?,?,?,?,?)',(key,sig,args.phase,encoded,json.dumps(r)));db.commit()
            if i%6==0 or i==len(pending):print('low margin',args.phase,'saved',i,'/',len(pending),flush=True)
    rows=[dict(key=k,job=json.loads(j),result=json.loads(r)) for k,j,r in db.execute(
        'SELECT key,job,result FROM cells WHERE signature=? AND phase=?',(sig,args.phase)) if k in wanted];db.close()
    assert len(rows)==len(jobs)
    atomic_json(OUT/(args.phase+'.json'),dict(signature=sig,cells=len(rows),rows=rows,
        executed_battles=sum(r['result']['executed_battles'] for r in rows)))
    if args.phase=='regions':
        selected=[]
        for s in range(6):
            def metric(r):
                flows=r['result']['by_flow'];wr=sum(f['metrics']['win'] for f in flows)/6
                hp=[q['hp'] for f in flows for q in f['trials'] if q['win']]
                return wr,sum(hp)/len(hp) if hp else 1.
            choices=[r for r in rows if r['job']['stage']==s]
            best=min(choices,key=lambda r:((metric(r)[0]-.65)/.15)**2+((metric(r)[1]-.15)/.12)**2)
            wr,hp=metric(best)
            selected.append(dict(stage=s,region='low_margin',enemy_genre=best['job']['enemy_genre'],macro=best['job']['macro'],
                calibration_wr=wr,calibration_winning_hp=hp,design_wr=.65,design_winning_hp=.15,source_cell=best['key']))
        atomic_json(OUT/'regions.json',dict(regions=selected))
    print('low margin',args.phase,'complete',len(rows),'cells',flush=True)


if __name__=='__main__':main()
