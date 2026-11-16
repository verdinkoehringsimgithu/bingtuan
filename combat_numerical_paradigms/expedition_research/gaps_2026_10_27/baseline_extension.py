"""Fresh-seed precision check of held-out low-terminal-margin point estimates."""
import gzip
import hashlib
import json
from pathlib import Path

import hard_regions as hard
from common import *


def main():
    manifest=check_manifest(hard.ROOT/'confirm_manifest.json')
    data=json.loads((hard.ROOT/'confirm.json').read_text(encoding='utf-8'))
    candidates=[c for c in data['rows'] if c['result']['baseline']['wr']>.5
        and c['result']['baseline']['winning_hp']is not None and c['result']['baseline']['winning_hp']<=.2]
    rows=[]
    for c in candidates:
        path=hard.ROOT/'replicates'/(c['key']+'.json.gz')
        with gzip.open(path,'rt',encoding='utf-8') as f:raw=json.load(f)
        j=raw['job'];mm,ii,enemy,ei,sim=hard.prepare(j,j['pool'],'final')
        order=raw['prepared']['0']['plan']['order'];m,it=hard.reordered(mm,ii,order)
        seeds=[old.seed('hard-independent-extension',j,i) for i in range(512)]
        assert not set(seeds)&set(raw['prepared']['0']['seeds']['test'])
        trials=[hard.project(sim(m,enemy,bs,it,ei,p=j['macro'],enabled=hard.ENABLED)[0]) for bs in seeds]
        rows.append(dict(key=c['key'],job=j,order=order,seeds=seeds,trials=trials,
            parent_archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    result=dict(parent_signature=manifest['signature'],scope='additional independent seeds, same five selected rosters; not new people',
        executed_battles=512*len(rows),rows=rows,
        sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),hard.ROOT/'confirm.json')})
    atomic_json(hard.ROOT/'baseline_extension.json',result)
    for c in rows:
        won=[r for r in c['trials'] if r['win']]
        print((c['job']['stage']+1)*5,c['job']['genre'],c['job']['gear'],'WR',len(won)/512,
            'winning_hp',sum(r['hp'] for r in won)/len(won) if won else None,flush=True)


if __name__=='__main__':main()
