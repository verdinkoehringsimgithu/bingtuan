$ErrorActionPreference='Stop'
$root=(Get-Item -LiteralPath $PSScriptRoot).Parent.Parent.Parent.FullName
$project=Join-Path $root 'LegionBattle/LegionBattle'
$old=Join-Path $PSScriptRoot '../expedition_runtime_2026_10_27'
$python='C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$unityData='C:/Program Files/Unity/Hub/Editor/2022.3.62f3c1/Editor/Data'
$refs=Join-Path $unityData 'UnityReferenceAssemblies/unity-4.8-api'
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH=Join-Path $root 'combat_numerical_paradigms/v11_research/.venv/Lib/site-packages'
& $python "$PSScriptRoot/generate_parity.py"
if($LASTEXITCODE -ne 0){throw 'Opening fixture generation failed'}
$sources=@("$project/Assets/Scripts/Battle/CombatRuntime.cs","$project/Assets/Scripts/Battle/CombatPersistentLimits.cs",
           "$project/Assets/Scripts/Battle/CharacterTraits.cs","$project/Assets/Scripts/Battle/OpeningBondRules.cs")
foreach($kind in @('opening','limited','baseline','invariants'))
{
    $harness=switch($kind)
    {
        'opening' {"$PSScriptRoot/OpeningParityHarness.cs"}
        'limited' {"$old/LimitedParityHarness.cs"}
        'baseline' {"$PSScriptRoot/../RuntimeParityHarness.cs"}
        'invariants' {"$PSScriptRoot/../RuntimeInvariantHarness.cs"}
    }
    $exe="$PSScriptRoot/$kind.exe"
    & "$unityData/NetCoreRuntime/dotnet.exe" "$unityData/DotNetSdkRoslyn/csc.dll" /nologo /nostdlib+ /target:exe `
        "/r:$refs/mscorlib.dll" "/r:$refs/System.dll" "/r:$refs/System.Core.dll" "/r:$refs/System.Web.Extensions.dll" "/out:$exe" @sources $harness
    if($LASTEXITCODE -ne 0){throw "$kind compilation failed"}
    switch($kind)
    {
        'opening' {& $exe "$PSScriptRoot/opening_cases.json" "$PSScriptRoot/opening_parity.json"}
        'limited' {& $exe "$old/limited_parity_cases.json" "$PSScriptRoot/limited_parity.json"}
        'baseline' {& $exe "$PSScriptRoot/../runtime_parity_cases.json" "$PSScriptRoot/runtime_parity.json"}
        'invariants' {& $exe "$PSScriptRoot/runtime_invariants.json"}
    }
    if($LASTEXITCODE -ne 0){throw "$kind validation failed"}
}
& $python "$root/test_30man_combat_simulator.py" *> "$PSScriptRoot/baseline_regression.log"
if($LASTEXITCODE -ne 0){throw '37,500 battle regression failed'}
