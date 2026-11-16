param([switch]$Unity)
$ErrorActionPreference='Stop'
$root=(Get-Item -LiteralPath $PSScriptRoot).Parent.Parent.Parent.FullName
$project=Join-Path $root 'LegionBattle/LegionBattle'
$python='C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$unityData='C:/Program Files/Unity/Hub/Editor/2022.3.62f3c1/Editor/Data'
$refs=Join-Path $unityData 'UnityReferenceAssemblies/unity-4.8-api'
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH=Join-Path $root 'combat_numerical_paradigms/v11_research/.venv/Lib/site-packages'
& $python (Join-Path $PSScriptRoot 'generate_limited_parity.py')
if($LASTEXITCODE -ne 0){throw 'Native fixtures failed'}
foreach($kind in @('limited','baseline','invariants'))
{
    $harness=switch($kind)
    {
        'limited' {Join-Path $PSScriptRoot 'LimitedParityHarness.cs'}
        'baseline' {Join-Path $PSScriptRoot '../RuntimeParityHarness.cs'}
        'invariants' {Join-Path $PSScriptRoot '../RuntimeInvariantHarness.cs'}
    }
    $exe=Join-Path $PSScriptRoot "$kind.exe"
    & "$unityData/NetCoreRuntime/dotnet.exe" "$unityData/DotNetSdkRoslyn/csc.dll" /nologo /nostdlib+ /target:exe `
        "/r:$refs/mscorlib.dll" "/r:$refs/System.dll" "/r:$refs/System.Core.dll" "/r:$refs/System.Web.Extensions.dll" `
        "/out:$exe" "$project/Assets/Scripts/Battle/CombatRuntime.cs" "$project/Assets/Scripts/Battle/CombatPersistentLimits.cs" $harness
    if($LASTEXITCODE -ne 0){throw "$kind compilation failed"}
    switch($kind)
    {
        'limited' {& $exe "$PSScriptRoot/limited_parity_cases.json" "$PSScriptRoot/limited_parity.json"}
        'baseline' {& $exe "$PSScriptRoot/../runtime_parity_cases.json" "$PSScriptRoot/runtime_parity.json"}
        'invariants' {& $exe "$PSScriptRoot/runtime_invariants.json"}
    }
    if($LASTEXITCODE -ne 0){throw "$kind validation failed"}
}
& $python "$root/test_30man_combat_simulator.py" *> "$PSScriptRoot/baseline_regression.log"
if($LASTEXITCODE -ne 0){throw '37,500 battle regression failed'}
if($Unity)
{
    foreach($run in @('expedition','lifecycle'))
    {
        if($run -eq 'expedition')
        {
            $env:LEGION_EXPEDITION_VALIDATION="$PSScriptRoot/unity_validation.json"
            $method='LegionBattle.EditorTools.ExpeditionValidation.Run'
        }
        else
        {
            $env:LEGION_SCENE_VALIDATION="$PSScriptRoot/lifecycle_validation.json"
            $method='LegionBattle.EditorTools.ExpeditionValidation.RunExistingLifecycle'
        }
        $process=Start-Process -FilePath "$unityData/../Unity.exe" -ArgumentList @('-batchmode','-nographics','-projectPath',$project,
            '-executeMethod',$method,'-logFile',"$PSScriptRoot/$run-recheck.log") -PassThru -WindowStyle Hidden
        $process.WaitForExit()
        if($process.ExitCode -ne 0){throw "$run Unity validation failed: $($process.ExitCode)"}
    }
}
& $python "$PSScriptRoot/verify_delivery.py"
if($LASTEXITCODE -ne 0){throw 'Delivery audit failed'}
