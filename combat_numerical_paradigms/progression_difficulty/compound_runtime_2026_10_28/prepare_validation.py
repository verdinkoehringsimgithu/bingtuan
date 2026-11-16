from pathlib import Path
HERE=Path(__file__).resolve().parent;PREV=HERE.parent/'tactical_runtime_2026_10_28'
s=(PREV/'TacticalParityHarness.cs').read_text(encoding='utf-8')
s=s.replace('ExpectedTacticalAction','ExpectedCompoundAction').replace('TacticalCase','CompoundCase').replace('TacticalParityHarness','CompoundParityHarness')
s=s.replace('public double coinsEarned;','public double coinsEarned;\n    public bool maidCast;public string fruitEvent;')
s=s.replace('public CombatTacticalSummary left_summary,right_summary;','public CombatCompoundRules leftCompound,rightCompound;\n    public CombatCompoundSummary left_summary,right_summary;')
start=s.index('    private static void Summary(');end=s.index('    public static void Main(',start)
s=s[:start]+'''    private static void Summary(CombatCompoundSummary a,CombatCompoundSummary b,string name)
    {
        if(a.maids!=b.maids||a.farmers!=b.farmers||a.adventurers!=b.adventurers||a.maidOwner!=b.maidOwner||a.maidLevel!=b.maidLevel||a.maidCasts!=b.maidCasts||
            a.fruitReady!=b.fruitReady||a.fruitPlanted!=b.fruitPlanted||a.fruitAccelerated!=b.fruitAccelerated||a.fruitHarvests!=b.fruitHarvests||a.fruitWait!=b.fruitWait||a.fruitKinds!=b.fruitKinds||
            a.adventureCompleted!=b.adventureCompleted||a.adventureBoostedCasts!=b.adventureBoostedCasts)
            throw new Exception(name+" compound counters: "+new JavaScriptSerializer().Serialize(new {a,b}));
        Near(a.maidHealRequested,b.maidHealRequested,name+" maid heal request");Near(a.maidStatsTotal,b.maidStatsTotal,name+" maid stats");
        Near(a.maidTrueRequested,b.maidTrueRequested,name+" maid true request");Near(a.fruitHealRequested,b.fruitHealRequested,name+" fruit heal request");
        for(int k=0;k<4;k++){Near(a.openingStats[k],b.openingStats[k],name+" opening stat");Near(a.fruitStats[k],b.fruitStats[k],name+" fruit stat");}
        if(a.events.Length!=b.events.Length)throw new Exception(name+" event count: "+new JavaScriptSerializer().Serialize(new {a,b}));
        for(int k=0;k<a.events.Length;k++)if(a.events[k].key!=b.events[k].key||a.events[k].round!=b.events[k].round||a.events[k].phase!=b.events[k].phase)
            throw new Exception(name+" event mismatch: "+new JavaScriptSerializer().Serialize(new {a=a.events[k],b=b.events[k]}));
    }
'''+s[end:]
s=s.replace('c.leftAugmentation,c.leftTactical);','c.leftAugmentation,c.leftTactical,c.leftCompound);').replace('c.rightAugmentation,c.rightTactical);','c.rightAugmentation,c.rightTactical,c.rightCompound);')
s=s.replace('report.killerMarked!=expected.killerMarked)','report.killerMarked!=expected.killerMarked||report.maidCast!=expected.maidCast||report.fruitEvent!=expected.fruitEvent)')
s=s.replace('a.TacticalBonds.Snapshot()','a.CompoundBonds.Snapshot()').replace('b.TacticalBonds.Snapshot()','b.CompoundBonds.Snapshot()').replace(' tactical cases',' compound cases')
(HERE/'CompoundParityHarness.cs').write_text(s,encoding='utf-8')
s=(PREV/'run_numeric_checks.ps1').read_text(encoding='utf-8')
s=s.replace('$augmentation=Join-Path',"$tactical=Join-Path $PSScriptRoot '../tactical_runtime_2026_10_28'\n$augmentation=Join-Path",1)
s=s.replace('"$PSScriptRoot/tactical_cases.json"','"$PSScriptRoot/compound_cases.json"',1)
s=s.replace('"$project/Assets/Scripts/Battle/CombatTacticalBonds.cs")','"$project/Assets/Scripts/Battle/CombatTacticalBonds.cs","$project/Assets/Scripts/Battle/CombatCompoundBonds.cs")')
s=s.replace("@('tactical_invariants'","@('compound_invariants','compound','tactical_invariants'")
s=s.replace("'tactical_invariants' {\"$PSScriptRoot/TacticalInvariantHarness.cs\"}","'compound_invariants' {\"$PSScriptRoot/CompoundInvariantHarness.cs\"}\n        'compound' {\"$PSScriptRoot/CompoundParityHarness.cs\"}\n        'tactical_invariants' {\"$tactical/TacticalInvariantHarness.cs\"}")
s=s.replace('"$PSScriptRoot/TacticalParityHarness.cs"','"$tactical/TacticalParityHarness.cs"')
s=s.replace("'tactical_invariants' {& $exe","'compound_invariants' {& $exe \"$PSScriptRoot/compound_invariants.json\"}\n        'compound' {& $exe \"$PSScriptRoot/compound_cases.json\" \"$PSScriptRoot/compound_parity.json\"}\n        'tactical_invariants' {& $exe")
s=s.replace('"$PSScriptRoot/tactical_cases.json"','"$tactical/tactical_cases.json"')
(HERE/'run_numeric_checks.ps1').write_text(s,encoding='utf-8')
s=(PREV/'run_unity_checks.ps1').read_text(encoding='utf-8')
s=s.replace("@('tactical'","@('compound','tactical'")
s=s.replace("'tactical' {$env:LEGION_TACTICAL_VALIDATION=\"$PSScriptRoot/unity_validation.json\"", "'compound' {$env:LEGION_COMPOUND_VALIDATION=\"$PSScriptRoot/unity_validation.json\";$method='LegionBattle.EditorTools.CompoundRuntimeValidation.Run'}\n        'tactical' {$env:LEGION_TACTICAL_VALIDATION=\"$PSScriptRoot/tactical_validation.json\"")
(HERE/'run_unity_checks.ps1').write_text(s,encoding='utf-8')
