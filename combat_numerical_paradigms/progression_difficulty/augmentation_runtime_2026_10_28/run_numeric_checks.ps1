$ErrorActionPreference='Stop'
$root=(Get-Item -LiteralPath $PSScriptRoot).Parent.Parent.Parent.FullName
$project=Join-Path $root 'LegionBattle/LegionBattle'
$amplification=Join-Path $PSScriptRoot '../amplification_runtime_2026_10_28'
$support=Join-Path $PSScriptRoot '../support_runtime_2026_10_28'
$evasion=Join-Path $PSScriptRoot '../evasion_runtime_2026_10_28'
$trip=Join-Path $PSScriptRoot '../expedition_runtime_2026_10_27'
$opening=Join-Path $PSScriptRoot '../identity_runtime_2026_10_28'
$python='C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$unityData='C:/Program Files/Unity/Hub/Editor/2022.3.62f3c1/Editor/Data'
$refs=Join-Path $unityData 'UnityReferenceAssemblies/unity-4.8-api'
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH=Join-Path $root 'combat_numerical_paradigms/v11_research/.venv/Lib/site-packages'
if(!(Test-Path "$PSScriptRoot/augmentation_cases.json"))
{& $python "$PSScriptRoot/generate_parity.py";if($LASTEXITCODE -ne 0){throw 'Evasion fixtures failed'}}
$sources=@("$project/Assets/Scripts/Battle/CombatRuntime.cs","$project/Assets/Scripts/Battle/CombatPersistentLimits.cs",
    "$project/Assets/Scripts/Battle/CharacterTraits.cs","$project/Assets/Scripts/Battle/OpeningBondRules.cs","$project/Assets/Scripts/Battle/CombatEvasionBonds.cs","$project/Assets/Scripts/Battle/CombatSupportBonds.cs","$project/Assets/Scripts/Battle/CombatAmplificationBonds.cs","$project/Assets/Scripts/Battle/CombatAugmentationBonds.cs")
foreach($kind in @('augmentation_invariants','augmentation','amplification_invariants','amplification','support_invariants','support','evasion_invariants','evasion','opening','limited','baseline','invariants'))
{
    $harness=switch($kind)
    {
        'augmentation_invariants' {"$PSScriptRoot/AugmentationInvariantHarness.cs"}
        'augmentation' {"$PSScriptRoot/AugmentationParityHarness.cs"}
        'amplification_invariants' {"$amplification/AmplificationInvariantHarness.cs"}
        'amplification' {"$amplification/AmplificationParityHarness.cs"}
        'support_invariants' {"$support/SupportInvariantHarness.cs"}
        'support' {"$support/SupportParityHarness.cs"}
        'evasion_invariants' {"$evasion/EvasionInvariantHarness.cs"}
        'evasion' {"$evasion/EvasionParityHarness.cs"}
        'opening' {"$opening/OpeningParityHarness.cs"}
        'limited' {"$trip/LimitedParityHarness.cs"}
        'baseline' {"$PSScriptRoot/../RuntimeParityHarness.cs"}
        'invariants' {"$PSScriptRoot/../RuntimeInvariantHarness.cs"}
    }
    $exe="$PSScriptRoot/$kind.exe"
    & "$unityData/NetCoreRuntime/dotnet.exe" "$unityData/DotNetSdkRoslyn/csc.dll" /nologo /nostdlib+ /target:exe `
        "/r:$refs/mscorlib.dll" "/r:$refs/System.dll" "/r:$refs/System.Core.dll" "/r:$refs/System.Web.Extensions.dll" "/out:$exe" @sources $harness
    if($LASTEXITCODE -ne 0){throw "$kind compilation failed"}
    switch($kind)
    {
        'augmentation_invariants' {& $exe "$PSScriptRoot/augmentation_invariants.json"}
        'augmentation' {& $exe "$PSScriptRoot/augmentation_cases.json" "$PSScriptRoot/augmentation_parity.json"}
        'amplification_invariants' {& $exe "$PSScriptRoot/amplification_invariants.json"}
        'amplification' {& $exe "$amplification/amplification_cases.json" "$PSScriptRoot/amplification_parity.json"}
        'support_invariants' {& $exe "$PSScriptRoot/support_invariants.json"}
        'support' {& $exe "$support/support_cases.json" "$PSScriptRoot/support_parity.json"}
        'evasion_invariants' {& $exe "$PSScriptRoot/evasion_invariants.json"}
        'evasion' {& $exe "$evasion/evasion_cases.json" "$PSScriptRoot/evasion_parity.json"}
        'opening' {& $exe "$opening/opening_cases.json" "$PSScriptRoot/opening_parity.json"}
        'limited' {& $exe "$trip/limited_parity_cases.json" "$PSScriptRoot/limited_parity.json"}
        'baseline' {& $exe "$PSScriptRoot/../runtime_parity_cases.json" "$PSScriptRoot/runtime_parity.json"}
        'invariants' {& $exe "$PSScriptRoot/runtime_invariants.json"}
    }
    if($LASTEXITCODE -ne 0){throw "$kind validation failed"}
}
& $python "$root/test_30man_combat_simulator.py" *> "$PSScriptRoot/baseline_regression.log"
if($LASTEXITCODE -ne 0){throw '37,500 battle regression failed'}
