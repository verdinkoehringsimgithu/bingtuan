$ErrorActionPreference='Stop'
$root=(Get-Item -LiteralPath $PSScriptRoot).Parent.Parent.Parent.FullName
$project=Join-Path $root 'LegionBattle/LegionBattle'
foreach($kind in @('evasion','identity','expedition','lifecycle'))
{
    switch($kind)
    {
        'evasion' {$env:LEGION_EVASION_VALIDATION="$PSScriptRoot/unity_validation.json";$method='LegionBattle.EditorTools.EvasionRuntimeValidation.Run'}
        'identity' {
            $env:LEGION_IDENTITY_LABEL_VALIDATION="$PSScriptRoot/label_validation.json"
            $env:LEGION_IDENTITY_RUNTIME_VALIDATION="$PSScriptRoot/identity_validation.json"
            $method='LegionBattle.EditorTools.IdentityRuntimeValidation.Run'
        }
        'expedition' {$env:LEGION_EXPEDITION_VALIDATION="$PSScriptRoot/expedition_validation.json";$method='LegionBattle.EditorTools.ExpeditionValidation.Run'}
        'lifecycle' {$env:LEGION_SCENE_VALIDATION="$PSScriptRoot/lifecycle_validation.json";$method='LegionBattle.EditorTools.ExpeditionValidation.RunExistingLifecycle'}
    }
    $process=Start-Process -FilePath 'C:/Program Files/Unity/Hub/Editor/2022.3.62f3c1/Editor/Unity.exe' `
        -ArgumentList @('-batchmode','-nographics','-projectPath',$project,'-executeMethod',$method,'-logFile',"$PSScriptRoot/$kind-final.log") `
        -PassThru -WindowStyle Hidden
    $process.WaitForExit();Write-Output "$kind Unity exit: $($process.ExitCode)"
    if($process.ExitCode -ne 0){throw "$kind Unity validation failed"}
}
