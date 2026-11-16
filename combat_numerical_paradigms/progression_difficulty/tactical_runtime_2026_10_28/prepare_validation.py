from pathlib import Path
HERE=Path(__file__).resolve().parent
PREV=HERE.parent/'augmentation_runtime_2026_10_28'
s=(PREV/'AugmentationParityHarness.cs').read_text(encoding='utf-8')
s=s.replace('ExpectedAugmentationAction','ExpectedTacticalAction').replace('AugmentationCase','TacticalCase').replace('AugmentationParityHarness','TacticalParityHarness')
s=s.replace('public bool heroineFirst,killerMarked;','public double coinsEarned;\n    public bool heroineFirst,killerMarked;')
s=s.replace('public CombatAugmentationSummary left_summary,right_summary;','public CombatTacticalRules leftTactical,rightTactical;\n    public CombatTacticalSummary left_summary,right_summary;')
start=s.index('    private static void Summary(');end=s.index('    public static void Main(',start)
s=s[:start]+'''    private static void Summary(CombatTacticalSummary a,CombatTacticalSummary b,string name)
    {
        if(a.mages!=b.mages||a.hunters!=b.hunters||a.gangs!=b.gangs||a.richMembers!=b.richMembers||a.workers!=b.workers||
            a.mageSame!=b.mageSame||a.mageSwitches!=b.mageSwitches||a.gangAttacks!=b.gangAttacks||a.richAttacks!=b.richAttacks||a.workerProcs!=b.workerProcs||a.lastAxis!=b.lastAxis)
            throw new Exception(name+" tactical counters");
        Near(a.hunterScheduled,b.hunterScheduled,name+" scheduled");Near(a.coins,b.coins,name+" coins");Near(a.richSaved,b.richSaved,name+" saved");
        if(a.axes.Length!=b.axes.Length)throw new Exception(name+" axes length");
        for(int k=0;k<a.axes.Length;k++)if(a.axes[k]!=b.axes[k]||a.percentLayers[k]!=b.percentLayers[k])throw new Exception(name+" axis layers");
    }
'''+s[end:]
s=s.replace('c.leftAmplification,c.leftAugmentation);','c.leftAmplification,c.leftAugmentation,c.leftTactical);').replace('c.rightAmplification,c.rightAugmentation);','c.rightAmplification,c.rightAugmentation,c.rightTactical);')
s=s.replace('Near(report.engineerQueued,','Near(report.coinsEarned,expected.coinsEarned,c.name+" earned");\n                Near(report.engineerQueued,')
s=s.replace('a.AugmentationBonds.Snapshot()','a.TacticalBonds.Snapshot()').replace('b.AugmentationBonds.Snapshot()','b.TacticalBonds.Snapshot()').replace(' augmentation cases',' tactical cases')
(HERE/'TacticalParityHarness.cs').write_text(s,encoding='utf-8')
s=(PREV/'run_numeric_checks.ps1').read_text(encoding='utf-8')
s=s.replace('$amplification=Join-Path',"$augmentation=Join-Path $PSScriptRoot '../augmentation_runtime_2026_10_28'\n$amplification=Join-Path",1)
s=s.replace('"$PSScriptRoot/augmentation_cases.json"','"$PSScriptRoot/tactical_cases.json"',1)
s=s.replace('"$project/Assets/Scripts/Battle/CombatAugmentationBonds.cs")','"$project/Assets/Scripts/Battle/CombatAugmentationBonds.cs","$project/Assets/Scripts/Battle/CombatTacticalBonds.cs")')
s=s.replace("@('augmentation_invariants'","@('tactical_invariants','tactical','augmentation_invariants'")
s=s.replace("'augmentation_invariants' {\"$PSScriptRoot/AugmentationInvariantHarness.cs\"}","'tactical_invariants' {\"$PSScriptRoot/TacticalInvariantHarness.cs\"}\n        'tactical' {\"$PSScriptRoot/TacticalParityHarness.cs\"}\n        'augmentation_invariants' {\"$augmentation/AugmentationInvariantHarness.cs\"}")
s=s.replace('"$PSScriptRoot/AugmentationParityHarness.cs"','"$augmentation/AugmentationParityHarness.cs"')
s=s.replace("'augmentation_invariants' {& $exe","'tactical_invariants' {& $exe \"$PSScriptRoot/tactical_invariants.json\"}\n        'tactical' {& $exe \"$PSScriptRoot/tactical_cases.json\" \"$PSScriptRoot/tactical_parity.json\"}\n        'augmentation_invariants' {& $exe")
s=s.replace('"$PSScriptRoot/augmentation_cases.json"','"$augmentation/augmentation_cases.json"')
(HERE/'run_numeric_checks.ps1').write_text(s,encoding='utf-8')
s=(PREV/'run_unity_checks.ps1').read_text(encoding='utf-8')
s=s.replace("@('augmentation'","@('tactical','augmentation'")
s=s.replace("'augmentation' {$env:LEGION_AUGMENTATION_VALIDATION=\"$PSScriptRoot/unity_validation.json\"", "'tactical' {$env:LEGION_TACTICAL_VALIDATION=\"$PSScriptRoot/unity_validation.json\";$method='LegionBattle.EditorTools.TacticalRuntimeValidation.Run'}\n        'augmentation' {$env:LEGION_AUGMENTATION_VALIDATION=\"$PSScriptRoot/augmentation_validation.json\"")
(HERE/'run_unity_checks.ps1').write_text(s,encoding='utf-8')
