"""Check actual mixed-hook coverage and the unchanged signed production build."""
from collections import Counter,defaultdict
import hashlib
import json
import sys
from pathlib import Path
from audit_coverage import action_hooks
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];PROJECT=ROOT/'LegionBattle/LegionBattle'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    result=read(HERE/'interaction_parity.json');assert result['passed'] and result['cases']==3120 and result['actions']==40479
    coverage=read(HERE/'coverage_after.json');assert set(coverage['by_capacity'])=={'5','10','15','20','25','30'}
    for cap,row in coverage['by_capacity'].items():
        assert row['cases']==520
        for key in ('engineer','scholar','sword','heroine','thief','rich','killer','maid','farmer','forced_hit','absolute_dodge'):
            if cap=='5' and key=='scholar':assert coverage['finite_source_skills'][cap]==0 and row['positive_cases'].get(key,0)==0
            else:assert row['positive_cases'].get(key,0)>0,(cap,key)
    for name,digest in read(HERE/'source_manifest.json').items():assert sha(ROOT/name)==digest,name
    production=HERE.parent/'compound_runtime_2026_10_28'
    for name,digest in read(production/'delivery_manifest.json').items():assert sha(ROOT/name)==digest,name
    for name,digest in read(HERE/'protected_assets.json').items():assert sha(PROJECT/name).upper()==digest.upper(),name
    cases=read(HERE/'interaction_cases.json');pairs=defaultdict(Counter);productive=defaultdict(Counter)
    for case in cases:
        cap=case['capacity'];seen=set()
        for action in case['actions']:seen.update(key for key,active in action_hooks(action).items() if active)
        keys=sorted(seen)
        for i,key in enumerate(keys):
            for other in keys[i+1:]:pairs[cap][key+'+'+other]+=1
        flags=Counter()
        for side in ('left','right'):
            aug=case[side+'AugmentationSummary'];ev=case[side+'EvasionSummary'];ta=case[side+'TacticalSummary'];co=case[side+'_summary']
            flags.update(engineer_growth_with_gear=aug['engineerGrowth']>0 and sum(aug['gearStats'])>0,
                ninja_growth=ev['ninjaGrowth']>0,rich_damage_saved=ta['richSaved']>0,killer_recovery_prevented=aug['healingPrevented']>0,
                worker_rescue=ta['workerProcs']>0,fruit_harvest=co['fruitHarvests']>0,adventure_boosted_cast=co['adventureBoostedCasts']>0)
        productive[cap].update(key for key,count in flags.items() if count>0)
    (HERE/'coactivation_cases.json').write_text(json.dumps(dict(by_capacity=pairs,productive_cases=productive),ensure_ascii=False,indent=2),encoding='utf-8')
    columns=('engineer','scholar','sword','heroine','thief','rich','killer','maid','farmer','forced_hit','absolute_dodge')
    names=('工程师排队增长','学者恢复次数','剑士实际追加','侠女首次技能','盗贼实际偷取','富翁产币','杀手命中标记','女仆长施法','农民果实事件','军人强制命中','忍者绝对闪避')
    lines=['# 混合触发覆盖记录','', '每阶段520场；表格数字为出现过该事件的场数，双方合计、同场最多计1。各类身份在不同测试配置中出现的次数不同，不能把这些数字当作流派强弱或胜率。','', '| 实际事件 | 5人 | 10人 | 15人 | 20人 | 25人 | 30人 |','|---|---:|---:|---:|---:|---:|---:|']
    for key,name in zip(columns,names):lines.append('|'+name+'|'+'|'.join(str(coverage['by_capacity'][str(cap)]['positive_cases'].get(key,0)) for cap in (5,10,15,20,25,30))+'|')
    lines+=['','5人阶段本批冻结技能全部不限次，学者恢复为0对应没有合格目标。该事实限定于本批技能样本；机制必要条件是存在已经消耗次数的有限次队友技能。','', '实际成长/减伤/减疗/收获等进一步记录见coactivation_cases.json的productive_cases。仅有技能发动不等于增益已经产生实际用途。']
    (HERE/'COVERAGE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    checks=dict(passed=True,added_cases=result['cases'],added_actions=result['actions'],maximum_relative_error=result['maximum_relative_error'],total_numerical_cases=25200,
        stage_cases={cap:row['cases'] for cap,row in coverage['by_capacity'].items()},unavailable=coverage['unavailable'],
        production_manifest_sha256=sha(production/'delivery_manifest.json'),production_unchanged=True,protected_assets_unchanged=True,
        scope='Interaction physics and state coverage; no new balance or best-order estimate.')
    (HERE/'delivery_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    files=['audit_coverage.py','generate_interactions.py','prepare_harness.py','InteractionParityHarness.cs','run_checks.ps1','verify_delivery.py','coverage_before.json','coverage_after.json','interaction_parity.json','COVERAGE.md','coactivation_cases.json','delivery_checks.json','README.md','SKILL_SUPPLY_GUIDANCE.md']
    manifest={name:sha(HERE/name) for name in files}
    if '--record' in sys.argv:(HERE/'delivery_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    assert read(HERE/'delivery_manifest.json')==manifest,'Interaction delivery files changed after recording'
    print(json.dumps(checks,ensure_ascii=False))
if __name__=='__main__':main()
