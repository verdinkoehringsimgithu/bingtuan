$ErrorActionPreference='Stop'
$root=(Get-Item -LiteralPath $PSScriptRoot).Parent.Parent.Parent.FullName
$project=Join-Path $root 'LegionBattle/LegionBattle'
$trip=Join-Path $PSScriptRoot '../expedition_runtime_2026_10_27'
$opening=Join-Path $PSScriptRoot '../identity_runtime_2026_10_28'
$python='C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$unityData='C:/Program Files/Unity/Hub/Editor/2022.3.62f3c1/Editor/Data'
$refs=Join-Path $unityData 'UnityReferenceAssemblies/unity-4.8-api'
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH=Join-Path $root 'combat_numerical_paradigms/v11_research/.venv/Lib/site-packages'
if(!(Test-Path "$PSScriptRoot/evasion_cases.json"))
{& $python "$PSScriptRoot/generate_parity.py";if($LASTEXITCODE -ne 0){throw 'Evasion fixtures failed'}}
$sources=@("$project/Assets/Scripts/Battle/CombatRuntime.cs","$project/Assets/Scripts/Battle/CombatPersistentLimits.cs",
    "$project/Assets/Scripts/Battle/CharacterTraits.cs","$project/Assets/Scripts/Battle/OpeningBondRules.cs","$project/Assets/Scripts/Battle/CombatEvasionBonds.cs")
foreach($kind in @('evasion_invariants','evasion','opening','limited','baseline','invariants'))
{
    $harness=switch($kind)
    {
        'evasion_invariants' {"$PSScriptRoot/EvasionInvariantHarness.cs"}
        'evasion' {"$PSScriptRoot/EvasionParityHarness.cs"}
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
        'evasion_invariants' {& $exe "$PSScriptRoot/evasion_invariants.json"}
        'evasion' {& $exe "$PSScriptRoot/evasion_cases.json" "$PSScriptRoot/evasion_parity.json"}
        'opening' {& $exe "$opening/opening_cases.json" "$PSScriptRoot/opening_parity.json"}
        'limited' {& $exe "$trip/limited_parity_cases.json" "$PSScriptRoot/limited_parity.json"}
        'baseline' {& $exe "$PSScriptRoot/../runtime_parity_cases.json" "$PSScriptRoot/runtime_parity.json"}
        'invariants' {& $exe "$PSScriptRoot/runtime_invariants.json"}
    }
    if($LASTEXITCODE -ne 0){throw "$kind validation failed"}
}
& $python "$root/test_30man_combat_simulator.py" *> "$PSScriptRoot/baseline_regression.log"
if($LASTEXITCODE -ne 0){throw '37,500 battle regression failed'}
