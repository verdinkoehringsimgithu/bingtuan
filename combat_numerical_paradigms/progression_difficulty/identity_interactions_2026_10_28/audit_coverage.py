"""Audit observed action hooks separately from enabled configuration flags."""
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'compound_runtime_2026_10_28/compound_cases.json'

def action_hooks(action):
    return dict(engineer=action['engineerQueued']>0,scholar=action['scholarRestored']>0,sword=action['chainDepth']>0,
        heroine=action['heroineFirst'],thief=any(action.get('stolenStats') or ()),rich=action['coinsEarned']>0,
        killer=action['killerMarked'],maid=action['maidCast'],farmer=action['fruitEvent'] is not None,
        forced_hit=action['forcedHit'],absolute_dodge=action['absoluteEvaded'])

def summarize(cases):
    by_capacity=defaultdict(lambda:dict(cases=0,actions=0,positive_actions=Counter(),cast_identities=Counter(),positive_cases=Counter()))
    for case in cases:
        row=by_capacity[case['capacity']];row['cases']+=1;seen=set()
        for action in case['actions']:
            row['actions']+=1;owner=case['left' if action['side']==0 else 'right'][action['owner']]
            row['cast_identities'][owner['traits']['identity']]+=1
            for name,active in action_hooks(action).items():
                if active:row['positive_actions'][name]+=1;seen.add(name)
        row['positive_cases'].update(seen)
    return dict(sorted(by_capacity.items()))

def main():
    cases=json.loads(SOURCE.read_text(encoding='utf-8'));mixed=[c for c in cases if c['name'].endswith(':compound-6')]
    result=dict(source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),all_profiles=summarize(cases),mixed_profile=summarize(mixed),
        interpretation='Observed action hooks only. Zero action hooks do not imply passive opening effects are absent; no balance or optimal-order claim.')
    (HERE/'coverage_before.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    for cap,row in result['mixed_profile'].items():print(cap,row['cases'],dict(row['positive_actions']),dict(row['cast_identities']))
if __name__=='__main__':main()
