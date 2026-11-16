"""Audit joint-study source inputs, coverage, paired metrics and saved replays."""
import argparse
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path

import joint_research as lab
from joint_core import Team
from bond_core import World
from order_search import reordered, snapshot
from run_bonds import atomic_json, signature
from settings import HERE


def equivalent(a, b):
    return json.loads(json.dumps(a, sort_keys=True)) == json.loads(json.dumps(b, sort_keys=True))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=HERE/'results/joint')
    p.add_argument('--phases', nargs='+', default=['counters','screen','confirm'])
    args = p.parse_args(); out = args.output
    manifest = json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    assert signature()[0] == manifest['combat_signature']
    for path, expected in manifest['sources'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected, path
    pre_signature = {k:v for k,v in manifest.items() if k != 'signature'}
    assert hashlib.sha256(json.dumps(pre_signature,sort_keys=True).encode()).hexdigest() == manifest['signature']
    all_cfg = lab.configs(); summary = {}; archives = {}
    for phase in args.phases:
        data = json.loads((out/(phase+'.json')).read_text(encoding='utf-8'))
        assert data['signature'] == manifest['signature']
        actual = {(r['job']['stage'],r['job']['bond'],r['job']['genre'],r['job']['difficulty']) for r in data['rows']}
        expected = {(s,k,g,d) for s,k in all_cfg for g in lab.GENRES
                    for d in (('hard',) if phase=='screen' else ('hard','extremely_hard'))
                    if phase != 'counters' or k in ('military','killer','sage','hunter')}
        assert actual == expected and len(actual) == len(data['rows'])
        battles = heldout = replays = 0
        for cell in data['rows']:
            j = cell['job']; path = out/'replicates'/(cell['key']+'.json.gz')
            archives[cell['key']] = hashlib.sha256(path.read_bytes()).hexdigest()
            with gzip.open(path,'rt',encoding='utf-8') as stream: raw = json.load(stream)
            assert all(raw['job'][k] == v for k,v in j.items())
            assert len(raw['variants']) == len(cell['result']['variants'])
            mm, original, actual_pool = lab.player_members(j)
            assert raw['actual_player_pool'] == actual_pool
            assert len(mm) == lab.STAGES[j['stage']][0]
            assert len({m.person_id for m in mm}) == len(mm)
            assert len({m.skill.id for m in mm}) == len(mm)
            if j['bond'] == 'academy': assert {'学生','老师'} <= {m.identity for m in mm}
            if j['bond'] == 'sword': assert sum(m.identity=='剑士' for m in mm) >= 2
            if j['bond'] == 'cult': assert len({m.skill.tier for m in mm if m.identity=='拜火教'}) >= 2
            enemies = lab.enemy_states(j,all_cfg)
            physical_count = 0; counted = 0
            for index, entry in enumerate(raw['variants']):
                public=cell['result']['variants'][index]
                assert public['variant']==entry['variant']
                ref=raw['variants'][entry['alias']] if 'alias' in entry else entry
                assert public['alias']==entry.get('alias')
                assert public['outcomes']==[{k:v for k,v in o.items() if k not in ('trials','traces','seeds')} for o in ref['outcomes']]
                if 'alias' in entry:
                    assert 0 <= entry['alias'] < index and 'alias' not in raw['variants'][entry['alias']]
                    continue
                physical_count += 1; v = entry['variant']
                vm, _ = lab.skill_supply(mm,original,v['policy'],j['bank'],j['bond'])
                vi = lab.equipment(vm,j['genre'],j['stage'],v['gear'],v.get('scale',1.))
                assert equivalent(snapshot(vm,vi),entry['snapshot'])
                assert sum(it.top for it in vi) == (4 if v['gear']=='four_top' else 0)
                assert all(a.person_id==b.person_id and a.stats==b.stats and a.level==b.level and
                           a.skill.tier==b.skill.tier and a.skill.genre==b.skill.genre and a.skill.id==b.skill.id
                           for a,b in zip(mm,vm))
                for enemy, saved_enemy, result in zip(enemies,raw['enemies'],entry['outcomes']):
                    assert equivalent(snapshot(enemy['members'],enemy['items']),saved_enemy['members'])
                    seeds = result['seeds']
                    assert all(len(seeds[k])==j[k+'_trials'] for k in seeds)
                    assert all(not set(seeds[a]) & set(seeds[b]) for a,b in itertools.combinations(seeds,2))
                    n = len(mm)
                    for plan in result['plans'].values():
                        assert sorted(plan['order']) == list(range(n))
                        assert plan['searched_orders'] == (120 if n==5 else j['budget'])
                        assert not plan['global_population_optimum_proven']
                    searches = sum(x['searched_orders']*j['train_trials']+x['selected_orders']*j['select_trials']
                                   for x in result['plans'].values())
                    final = 3*j['test_trials']; residual = result['executed_battles']-searches-final
                    # One or two distinct solutions were shared before cross-selection.
                    assert residual in (2*j['cross_trials'],4*j['cross_trials'])
                    counted += result['executed_battles']; heldout += final
                    for name, metric in result['metrics'].items():
                        trials = result['trials'][name]; assert len(trials)==j['test_trials']
                        for k,value in metric.items():
                            assert math.isclose(sum(r[k] for r in trials)/len(trials),value,abs_tol=1e-11)
                    for label,other in (('practical','off'),('mechanical','off_at_on')):
                        ds=[a['win']-b['win'] for a,b in zip(result['trials']['on'],result['trials'][other])]
                        avg=sum(ds)/len(ds); se=math.sqrt(sum((x-avg)**2 for x in ds)/(len(ds)-1)/len(ds))
                        assert math.isclose(avg,result['differences'][label]['mean'],abs_tol=1e-12)
                        assert math.isclose(se,result['differences'][label]['se'],abs_tol=1e-12)
                    # Replay every saved C_I first test battle (all physical variants/enemies).
                    if j['genre']=='C_I':
                        a,ai=reordered(vm,vi,result['plans']['on']['order'])
                        r,trace,_,b=lab.simulate(a,enemy['members'],seeds['test'][0],ai,enemy['items'],p=enemy['macro'],
                            enabled=(j['bond'],),config=all_cfg[(j['stage'],j['bond'])],
                            enemy_enabled=enemy['enabled'],enemy_config=enemy['config'],telemetry=phase=='counters')
                        r=lab.compact(r);r['enemy_prevented_request_fraction']=r['enemy_metrics'].get('killer_healing_prevented',0.)/b.max_bp
                        assert equivalent(r,result['trials']['on'][0])
                        if phase=='counters': assert equivalent(trace,result['traces']['on'][0])
                        replays += 1
                # Independently check the corrected engineer equipment attribute base.
                team=Team(vm,vi,0,World(19),enabled=('engineer',) if j['bond']=='engineer' else ())
                expected_gear=[sum(it.stats[k]+(m.stats[k]*it.value if it.kind=='owner_stats' else 0.)
                                   for m,it in zip(vm,vi)) for k in range(4)]
                assert all(abs(a-b)<1e-9 for a,b in zip(team.gear_stats,expected_gear))
            assert counted == cell['result']['executed_battles']
            battles += counted
        assert battles == data['executed_battles']
        summary[phase]=dict(cells=len(actual),executed_battles=battles,heldout_executions=heldout,replayed=replays)
        print(phase,summary[phase],flush=True)
    if 'confirm' in args.phases:
        data=json.loads((out/'confirm.json').read_text(encoding='utf-8'))
        provenance=json.loads((out/'selected_supply_provenance.json').read_text(encoding='utf-8'))
        assert provenance['signature']==manifest['signature']
        assert provenance['screen_sha256']==hashlib.sha256((out/'screen.json').read_bytes()).hexdigest()
        assert provenance['selection_sha256']==hashlib.sha256((out/'selected_supply.json').read_bytes()).hexdigest()
        selected=json.loads((out/'selected_supply.json').read_text(encoding='utf-8'))
        screen=json.loads((out/'screen.json').read_text(encoding='utf-8'))
        assert selected==lab.select_policies(screen['rows'])
        assert {r['job']['pool'] for r in screen['rows']}.isdisjoint({r['job']['pool'] for r in data['rows']})
        assert {r['job']['bank'] for r in screen['rows']}.isdisjoint({r['job']['bank'] for r in data['rows']})
        if (out/'attribute_sensitivity.json').exists():
            attrs=json.loads((out/'attribute_sensitivity.json').read_text(encoding='utf-8'))
            am=json.loads((out/'attribute_manifest.json').read_text(encoding='utf-8'))
            assert am['joint_signature']==manifest['signature']
            assert am['confirm_sha256']==hashlib.sha256((out/'confirm.json').read_bytes()).hexdigest()
            assert am['source_sha256']==hashlib.sha256((HERE/'joint_attribute_sensitivity.py').read_bytes()).hexdigest()
            assert hashlib.sha256(json.dumps({k:v for k,v in am.items() if k!='signature'},sort_keys=True).encode()).hexdigest()==am['signature']==attrs['signature']
            amap={(r['stage']-1,r['bond'],r['genre'],r['difficulty'],r['gear'],r['scope']):r for r in attrs['rows']}
            assert len(amap)==3*len(data['rows'])
            executions=ar=0
            for cell in data['rows']:
                j=cell['job'];path=out/'attribute_replicates'/(cell['key']+'.json.gz')
                archives['attributes/'+cell['key']]=hashlib.sha256(path.read_bytes()).hexdigest()
                with gzip.open(path,'rt',encoding='utf-8') as stream:a=json.load(stream)
                with gzip.open(out/'replicates'/(cell['key']+'.json.gz'),'rt',encoding='utf-8') as stream:source=json.load(stream)
                assert a['cell']==cell['key'] and equivalent(a['job'],j)
                nt=min(am['trials'],j['test_trials']);assert a['executed_battles']==12*nt
                assert {(x['gear'],x['scope'],x['scale'],x['state']) for x in a['records']}=={(g,scope,s,t) for g,scope in (('basic','all_base'),('four_top','all_base'),('four_top','non_top')) for s in (.75,1.,1.25) for t in ('on','off')}
                for rec in a['records']:
                    chosen=selected[f'{j["stage"]}:{j["bond"]}:{rec["gear"]}'];assert rec['policy']==chosen
                    e=next(x for x in source['variants'] if x['variant']==dict(policy=chosen,gear=rec['gear'],scale=1.))
                    if 'alias' in e:e=source['variants'][e['alias']]
                    o=e['outcomes'][0]
                    assert rec['order']==o['plans'][rec['state']]['order']
                    assert rec['seeds']==o['seeds']['test'][:nt]
                    assert len(rec['trials'])==nt
                    for k,v in rec['metrics'].items():assert math.isclose(sum(r[k] for r in rec['trials'])/nt,v,abs_tol=1e-11)
                    if rec['scale']==1.:
                        assert rec['trials']==[{k:r[k] for k in rec['metrics']} for r in o['trials'][rec['state']][:nt]]
                    ev=amap[(j['stage'],j['bond'],j['genre'],j['difficulty'],rec['gear'],rec['scope'])]
                    assert ev[f'{rec["state"]}_wr_{rec["scale"]}']==rec['metrics']['win']
                    if j['genre']=='C_I' and rec['gear']=='four_top' and rec['scope']=='non_top' and rec['scale']==1.25 and rec['state']=='on':
                        mm,ii,_=lab.player_members(j);vm,_=lab.skill_supply(mm,ii,chosen,j['bank'],j['bond'])
                        vi=lab.equipment(vm,j['genre'],j['stage'],rec['gear'],1.)
                        vi=tuple(it if it.top else lab.natural.Item(it.kind,it.value,tuple(x*rec['scale'] for x in it.stats),it.bp,it.top) for it in vi)
                        vm,vi=reordered(vm,vi,rec['order']);enemy=lab.enemy_states(j,all_cfg)[0]
                        actual,*_=lab.simulate(vm,enemy['members'],rec['seeds'][0],vi,enemy['items'],p=enemy['macro'],enabled=(j['bond'],),config=all_cfg[(j['stage'],j['bond'])])
                        assert {k:actual[k] for k in rec['metrics']}==rec['trials'][0];ar+=1
                executions+=a['executed_battles']
            assert attrs['cells']==len(data['rows']) and executions==attrs['executed_battles']
            summary['attribute']=dict(cells=attrs['cells'],executed_battles=executions,replayed=ar,center_battles_reused=True)
            print('attribute',summary['attribute'],flush=True)
        if (out/'allocation_confirmation.json').exists():
            import joint_allocation as ownership
            allocation=json.loads((out/'allocation_confirmation.json').read_text(encoding='utf-8'))
            am=json.loads((out/'allocation_manifest.json').read_text(encoding='utf-8'))
            assert am['joint_signature']==manifest['signature']
            assert am['confirm_sha256']==hashlib.sha256((out/'confirm.json').read_bytes()).hexdigest()
            assert am['source_sha256']==hashlib.sha256((HERE/'joint_allocation.py').read_bytes()).hexdigest()
            assert hashlib.sha256(json.dumps({k:v for k,v in am.items() if k!='signature'},sort_keys=True).encode()).hexdigest()==am['signature']==allocation['signature']
            assert {c['cell']['key'] for c in allocation['rows']}=={c['key'] for c in data['rows']}
            executions=changed=ar=heldout=0
            for cell in allocation['rows']:
                j,mm,old,new,equal=ownership.prepare(cell['cell'],selected)
                public=cell['result'];assert equal==public['equivalent']
                if equal:
                    assert public['executed_battles']==0;continue
                changed+=1;path=out/'allocation_replicates'/(cell['cell']['key']+'.json.gz')
                archives['allocation/'+cell['cell']['key']]=hashlib.sha256(path.read_bytes()).hexdigest()
                with gzip.open(path,'rt',encoding='utf-8') as stream:raw=json.load(stream)
                job=raw['job'];enemy=lab.enemy_states(job,all_cfg)[0];count=0
                assert equivalent(snapshot(enemy['members'],enemy['items']),raw['enemy']['members'])
                for entry,items in zip(raw['variants'],(old,new)):
                    assert equivalent(snapshot(mm,items),entry['snapshot'])
                    assert sum(it.top for it in items)==4
                    o=entry['outcome'];seeds=o['seeds']
                    assert all(not set(seeds[a])&set(seeds[b]) for a,b in itertools.combinations(seeds,2))
                    assert all(len(seeds[k])==job[k+'_trials'] for k in seeds)
                    for plan in o['plans'].values():
                        assert sorted(plan['order'])==list(range(len(mm)))
                        assert not plan['global_population_optimum_proven']
                        assert plan['searched_orders']==(120 if len(mm)==5 else job['budget'])
                    base=sum(p['searched_orders']*job['train_trials']+p['selected_orders']*job['select_trials'] for p in o['plans'].values())
                    assert o['executed_battles']-base-3*job['test_trials'] in (2*job['cross_trials'],4*job['cross_trials'])
                    for state,metric in o['metrics'].items():
                        assert len(o['trials'][state])==job['test_trials']
                        assert all(math.isclose(sum(r[k] for r in o['trials'][state])/job['test_trials'],v,abs_tol=1e-11) for k,v in metric.items())
                    count+=o['executed_battles'];heldout+=3*job['test_trials']
                reference,refined=(x['outcome'] for x in raw['variants'])
                assert public['reference_wr']==reference['metrics']['on']['win']
                assert public['refined_wr']==refined['metrics']['on']['win']
                assert public['owner_gain']==public['refined_wr']-public['reference_wr']
                assert reference['seeds']==refined['seeds']
                assert count==public['executed_battles'];executions+=count
                a,ai=reordered(mm,new,refined['plans']['on']['order'])
                r,_,_,b=lab.simulate(a,enemy['members'],refined['seeds']['test'][0],ai,enemy['items'],p=enemy['macro'],enabled=(j['bond'],),config=all_cfg[(j['stage'],j['bond'])])
                r=lab.compact(r);r['enemy_prevented_request_fraction']=r['enemy_metrics'].get('killer_healing_prevented',0.)/b.max_bp
                assert equivalent(r,refined['trials']['on'][0]);ar+=1
            assert changed==allocation['changed_cells'] and executions==allocation['executed_battles']
            summary['allocation']=dict(cells=len(allocation['rows']),changed_cells=changed,executed_battles=executions,heldout_executions=heldout,replayed=ar)
            print('allocation',summary['allocation'],flush=True)
    result=dict(status='passed',signature=manifest['signature'],phases=summary,
                archives=archives,checks=['source hashes','complete six-stage six-genre coverage','one identity and unique people',
                'legitimate academy/sword/cult composition','skill tier/axis/stat/level budget preserved',
                'one item per member; four top items','engineer full equipment attribute accounting',
                'disjoint search/selection/cross/test streams','exact execution and alias accounting',
                'paired metric reconstruction','frozen-order battle and telemetry replay',
                'separate policy selection and independent confirmation inputs'])
    atomic_json(out/'validation.json',result)


if __name__=='__main__':main()
