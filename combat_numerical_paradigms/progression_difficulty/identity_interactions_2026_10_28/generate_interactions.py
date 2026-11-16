"""Rotate tags over frozen skill/equipment inputs; no numerical budget edits.

This is interaction coverage, not a balance or best-order experiment.
"""
import copy
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('compound_oracle',HERE.parent/'compound_runtime_2026_10_28/generate_parity.py')
cp=importlib.util.module_from_spec(spec);sys.modules[spec.name]=cp;spec.loader.exec_module(cp)
from settings import IDENTITIES
from audit_coverage import summarize,action_hooks
IDENTITY_LIST=[x for group in IDENTITIES.values() for x in group]
IDENTITY_LIST.insert(IDENTITY_LIST.index('剑士'),'剑士')

def labels(cap,rotation,side):
    if rotation==len(IDENTITY_LIST):return ['忍者']+['军人']*((cap+1)//2)+['女仆']*(cap-1-(cap+1)//2)
    values=[IDENTITY_LIST[(pos+rotation+(7 if side=='right' else 0))%len(IDENTITY_LIST)] for pos in range(cap)]
    return [v for v in values if v!='女仆']+[v for v in values if v=='女仆']

def main():
    source=HERE.parent/'runtime_parity_cases.json';fixtures=json.loads(source.read_text(encoding='utf-8-sig'));cases=[]
    enabled=list(IDENTITIES);gain=2;stage_rows=Counter();finite_sources=Counter();selected_sources=Counter()
    for index,base in enumerate(fixtures):
        cap=len(base['left']);ordinal=stage_rows[cap];stage_rows[cap]+=1
        if ordinal%4:continue
        selected_sources[cap]+=1
        finite_sources[cap]+=sum(m['skill'] is not None and 0<m['skill']['limit']<999 for side in ('left','right') for m in base[side])
        for rotation in range(len(IDENTITY_LIST)+1):
            f=copy.deepcopy(base);cp.ev.CAPACITY=len(f['left']);cp.ev.FACTORS=(.7,.7,.8,.5,.9)
            cr=cp.rules(6,gain);tr=cp.tac.rules(6,gain);ar=cp.aug.rules(5,gain);am=cp.amp.rules(6,gain);s=cp.sup.support(True,True,gain);er=cp.ev.evasion(True,True,gain)
            for side in ('left','right'):
                for pos,(row,identity) in enumerate(zip(f[side],labels(cp.ev.CAPACITY,rotation,side))):
                    row['traits']=dict(personId=f'interaction:{side}:{pos}',identity=identity);row['level']=1+(index+pos)%30
            left,li=cp.amp.pack(f['left']);right,ri=cp.amp.pack(f['right']);cfg=cp.ev.cfg(er)
            cfg.update(scholar=s['scholarChance'],scholar_restore=s['scholarRestore'],sword=s['swordChance'],sword_decay=s['swordDecay'],sword_extras=s['swordExtras'])
            cp.sup.TRACE.clear();cp.ev.TEAMS.clear();module=cp.MODULES[6]
            result,*_=cp.ORACLES[id(module)](left,right,294000+index*31+rotation,li,ri,p=f.get('macro'),enabled=enabled,enemy_enabled=enabled,config=cfg,enemy_config=cfg,max_turns=f['rounds'],legacy=True)
            a,b=cp.ev.TEAMS
            for i,row in enumerate(cp.sup.TRACE):
                nxt=cp.sup.TRACE[i+1] if i+1<len(cp.sup.TRACE) else None
                row['hasContinuation']=bool(nxt and nxt['round']==row['round'] and nxt['side']==row['side'] and nxt['chainDepth']==row['chainDepth']+1)
            opening=dict(sailor=True,merchant=True,countK=4,gain=gain,sailorCoefficient=.006,merchantCoefficient=.30)
            case=dict(name=f['name']+':interaction-'+str(rotation),capacity=cp.ev.CAPACITY,left=f['left'],right=f['right'],
                leftCompound=cr,rightCompound=cr,leftTactical=tr,rightTactical=tr,leftAugmentation=ar,rightAugmentation=ar,leftAmplification=am,rightAmplification=am,leftSupport=s,rightSupport=s,leftEvasion=er,rightEvasion=er,leftOpening=opening,rightOpening=opening,
                limits=dict(zip(('bp','courage','resilience','initiative','magic'),cp.ev.FACTORS)),macro=f.get('macro'),rounds=f['rounds'],random=cp.ev.g.tape.values,actions=list(cp.sup.TRACE),
                hp=result['hp'],enemy_hp=result['enemy_hp'],turns=result['turns'],win=result['win'],censored=result['censored'],draw=result['draw'],left_received=a.metrics['damage_received'],right_received=b.metrics['damage_received'],left_min=a.minimum,right_min=b.minimum,
                left_stats=a.get_effective_stats(),right_stats=b.get_effective_stats(),left_uses=[a.usage.get(i,0) for i in range(len(left))],right_uses=[b.usage.get(i,0) for i in range(len(right))],left_summary=cp.summary(a),right_summary=cp.summary(b))
            for side,team in (('left',a),('right',b)):
                for group,summary in (('Evasion',cp.ev.summary),('Support',cp.sup.summary),('Amplification',cp.amp.summary),('Augmentation',cp.aug.summary),('Tactical',cp.tac.summary)):
                    case[side+group+'Summary']=summary(team)
            cases.append(case)
    (HERE/'interaction_cases.json').write_text(json.dumps(cases,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    coverage=summarize(cases)
    assert set(coverage)=={5,10,15,20,25,30},'all six capacities must be sampled'
    unavailable={}
    for cap,row in coverage.items():
        for key in ('engineer','scholar','sword','heroine','thief','rich','killer','maid','farmer','forced_hit','absolute_dodge'):
            if key=='scholar' and finite_sources[cap]==0:
                unavailable[str(cap)+':scholar']='No finite-use skill in the frozen stage fixtures; restoration has no valid target.'
                assert row['positive_cases'][key]==0
                continue
            assert row['positive_cases'][key]>0,(cap,key,'not exercised')
    (HERE/'coverage_after.json').write_text(json.dumps(dict(cases=len(cases),selected_source_cases=selected_sources,finite_source_skills=finite_sources,by_capacity=coverage,unavailable=unavailable,
        interpretation='Fixed source skills/equipment, rotating identity test fixtures. No best-order or balance conclusion.'),ensure_ascii=False,indent=2),encoding='utf-8')
    paths=[source,Path(__file__),HERE/'audit_coverage.py',Path(cp.__file__)]
    paths += [ROOT/path for path in json.loads((cp.HERE/'parity_sources.json').read_text(encoding='utf-8'))['sources']]
    (HERE/'source_manifest.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2),encoding='utf-8')
    print(len(cases),'mixed identity cases generated; six capacities checked;',unavailable)
if __name__=='__main__':main()
