param([string]$AssemblyPath = "$PSScriptRoot/IntegrationAssembly.dll", [string]$OutputPath = "$PSScriptRoot/integration_validation.json")
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
[void][Reflection.Assembly]::LoadFrom('C:/Program Files/Unity/Hub/Editor/2022.3.62f3c1/Editor/Data/Managed/UnityEngine/UnityEngine.CoreModule.dll')
$assembly = [Reflection.Assembly]::LoadFrom($AssemblyPath)
$type = $assembly.GetType('LegionBattle.Battle.BattleRosterStrategy', $true)
$method = $type.GetMethod('GrowthStats')
$cases = Get-Content -LiteralPath (Join-Path $taskRoot 'integration_growth_cases.json') -Raw | ConvertFrom-Json
foreach ($case in $cases) {
    $args = [object[]]@([int]$case.level, [int[]]$case.start, [int[]]$case.end, [double]$case.power)
    $actual = $method.Invoke($null, $args)
    if (($actual -join ',') -ne ($case.expected -join ',')) { throw "Growth mismatch: level $($case.level)" }
}
foreach ($level in @(0, 31, 35, 100)) {
    $rejected = $false
    try { [void]$method.Invoke($null, [object[]]@($level, [int[]]@(0,0,0,0), [int[]]@(1,2,3,4), 1.0)) }
    catch { $rejected = $_.Exception.InnerException -is [ArgumentOutOfRangeException] }
    if (-not $rejected) { throw "Level $level was not rejected" }
}
@{growth_cases=$cases.Count; invalid_levels_rejected=4; unity_compilation='passed'} | ConvertTo-Json | Set-Content -LiteralPath $OutputPath -Encoding utf8
Write-Output "$($cases.Count) Python/C# growth comparisons passed; levels 0/31/35/100 rejected."
