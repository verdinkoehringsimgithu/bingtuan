"""Build this revision's harness and runners from the previous verified batch."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
PREV=HERE.parent/'amplification_runtime_2026_10_28'
s=(PREV/'AmplificationParityHarness.cs').read_text(encoding='utf-8')
s=s.replace('ExpectedAmplificationAction','ExpectedAugmentationAction').replace('AmplificationCase','AugmentationCase').replace('AmplificationParityHarness','AugmentationParityHarness')
s=s.replace('public bool heroineFirst;','public bool heroineFirst,killerMarked;\n    public double engineerQueued,appliedHealPenalty,healingPrevented;\n    public double[] stolenStats;')
s=s.replace('public CombatAmplificationSummary left_summary,right_summary;','public CombatAugmentationRules leftAugmentation,rightAugmentation;\n    public CombatAugmentationSummary left_summary,right_summary;')
start=s.index('    private static void Summary(');end=s.index('    public static void Main(',start)
s=s[:start]+'''    private static void Summary(CombatAugmentationSummary a,CombatAugmentationSummary b,string name)
    {
        if(a.engineers!=b.engineers||a.sages!=b.sages||a.thieves!=b.thieves||a.killers!=b.killers||a.engineerSkillCasts!=b.engineerSkillCasts||a.thiefAttacks!=b.thiefAttacks||a.killerMarks!=b.killerMarks)
            throw new Exception(name+" augmentation counters");
        Near(a.engineerMultiplier,b.engineerMultiplier,name+" gear factor");Near(a.engineerGrowth,b.engineerGrowth,name+" growth");
        Near(a.pendingEngineer,b.pendingEngineer,name+" pending engineer");Near(a.pendingHealPenalty,b.pendingHealPenalty,name+" next skill penalty");
        Near(a.healingPrevented,b.healingPrevented,name+" healing prevented");
        for(int k=0;k<4;k++){Near(a.gearStats[k],b.gearStats[k],name+" gear stat");Near(a.stolenStats[k],b.stolenStats[k],name+" stolen stat");}
    }
'''+s[end:]
s=s.replace('c.leftSupport,c.leftAmplification);','c.leftSupport,c.leftAmplification,c.leftAugmentation);').replace('c.rightSupport,c.rightAmplification);','c.rightSupport,c.rightAmplification,c.rightAugmentation);')
s=s.replace('if(report.hasContinuation){Near', '''Near(report.engineerQueued,expected.engineerQueued,c.name+" engineer queued");
                Near(report.appliedHealPenalty,expected.appliedHealPenalty,c.name+" applied penalty");
                Near(report.healingPrevented,expected.healingPrevented,c.name+" healing prevented");
                if((report.stolenStats==null)!=(expected.stolenStats==null))throw new Exception(c.name+" stolen array mismatch");
                if(report.stolenStats!=null)for(int k=0;k<4;k++)Near(report.stolenStats[k],expected.stolenStats[k],c.name+" stolen stat");
                if(report.hasContinuation){Near''')
s=s.replace('report.heroineFirst!=expected.heroineFirst)','report.heroineFirst!=expected.heroineFirst||report.killerMarked!=expected.killerMarked)')
s=s.replace('a.AmplificationBonds.Snapshot()','a.AugmentationBonds.Snapshot()').replace('b.AmplificationBonds.Snapshot()','b.AugmentationBonds.Snapshot()')
s=s.replace(' amplification cases',' augmentation cases')
(HERE/'AugmentationParityHarness.cs').write_text(s,encoding='utf-8')
s=(PREV/'run_numeric_checks.ps1').read_text(encoding='utf-8')
s=s.replace("$support=Join-Path", "$amplification=Join-Path $PSScriptRoot '../amplification_runtime_2026_10_28'\n$support=Join-Path",1)
s=s.replace('"$PSScriptRoot/amplification_cases.json"','"$PSScriptRoot/augmentation_cases.json"',1)
s=s.replace('"$project/Assets/Scripts/Battle/CombatAmplificationBonds.cs")','"$project/Assets/Scripts/Battle/CombatAmplificationBonds.cs","$project/Assets/Scripts/Battle/CombatAugmentationBonds.cs")')
s=s.replace("@('amplification_invariants'", "@('augmentation_invariants','augmentation','amplification_invariants'")
s=s.replace("'amplification_invariants' {\"$PSScriptRoot/AmplificationInvariantHarness.cs\"}", "'augmentation_invariants' {\"$PSScriptRoot/AugmentationInvariantHarness.cs\"}\n        'augmentation' {\"$PSScriptRoot/AugmentationParityHarness.cs\"}\n        'amplification_invariants' {\"$amplification/AmplificationInvariantHarness.cs\"}")
s=s.replace('"$PSScriptRoot/AmplificationParityHarness.cs"','"$amplification/AmplificationParityHarness.cs"')
s=s.replace("'amplification_invariants' {& $exe", "'augmentation_invariants' {& $exe \"$PSScriptRoot/augmentation_invariants.json\"}\n        'augmentation' {& $exe \"$PSScriptRoot/augmentation_cases.json\" \"$PSScriptRoot/augmentation_parity.json\"}\n        'amplification_invariants' {& $exe")
s=s.replace('"$PSScriptRoot/amplification_cases.json"','"$amplification/amplification_cases.json"')
(HERE/'run_numeric_checks.ps1').write_text(s,encoding='utf-8')
s=(PREV/'run_unity_checks.ps1').read_text(encoding='utf-8')
s=s.replace("@('amplification'", "@('augmentation','amplification'")
s=s.replace("'amplification' {$env:LEGION_AMPLIFICATION_VALIDATION=\"$PSScriptRoot/unity_validation.json\"", "'augmentation' {$env:LEGION_AUGMENTATION_VALIDATION=\"$PSScriptRoot/unity_validation.json\";$method='LegionBattle.EditorTools.AugmentationRuntimeValidation.Run'}\n        'amplification' {$env:LEGION_AMPLIFICATION_VALIDATION=\"$PSScriptRoot/amplification_validation.json\"")
(HERE/'run_unity_checks.ps1').write_text(s,encoding='utf-8')
