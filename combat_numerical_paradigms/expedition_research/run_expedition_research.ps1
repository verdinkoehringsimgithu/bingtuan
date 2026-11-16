param([int]$Workers=6,[string]$Python='',
    [string[]]$Phases=@('verify-core','regions','curves','low-regions','low-curves','audit-measurements','fit','prototype','refine','confirm','audit-prototype','audit-refined','verify-recovery','recovery','audit-recovery','strong','audit-strong','report','regression','delivery-check'))
$ErrorActionPreference='Stop'
$savedPath=$env:PYTHONPATH
$savedEncoding=$env:PYTHONIOENCODING
try {
    $env:PYTHONIOENCODING='utf-8'
    if (-not $Python) {
        $Python=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
        $packages=Join-Path (Split-Path -Parent $PSScriptRoot) 'v11_research/.venv/Lib/site-packages'
        $env:PYTHONPATH=if ($savedPath) { "$packages;$savedPath" } else { $packages }
    }
    foreach ($phase in $Phases) {
        if ($phase -eq 'verify-core') { & $Python (Join-Path $PSScriptRoot 'verify_trip_core.py') }
        elseif ($phase -eq 'regions') { & $Python (Join-Path $PSScriptRoot 'measure_response.py') --phase regions --workers $Workers }
        elseif ($phase -eq 'curves') { & $Python (Join-Path $PSScriptRoot 'measure_response.py') --phase curves --workers $Workers }
        elseif ($phase -eq 'low-regions') { & $Python (Join-Path $PSScriptRoot 'low_margin_reference.py') --phase regions --workers $Workers }
        elseif ($phase -eq 'low-curves') { & $Python (Join-Path $PSScriptRoot 'low_margin_reference.py') --phase curves --workers $Workers }
        elseif ($phase -eq 'audit-measurements') { & $Python (Join-Path $PSScriptRoot 'audit_research.py') --scope measurements }
        elseif ($phase -eq 'fit') { & $Python (Join-Path $PSScriptRoot 'fit_paths.py') --workers $Workers }
        elseif ($phase -eq 'prototype') { & $Python (Join-Path $PSScriptRoot 'confirm_paths.py') --workers $Workers }
        elseif ($phase -eq 'refine') { & $Python (Join-Path $PSScriptRoot 'refine_policy_targets.py') }
        elseif ($phase -eq 'confirm') { & $Python (Join-Path $PSScriptRoot 'confirm_refined.py') --workers $Workers }
        elseif ($phase -eq 'audit-prototype') { & $Python (Join-Path $PSScriptRoot 'audit_research.py') --scope prototype }
        elseif ($phase -eq 'audit-refined') { & $Python (Join-Path $PSScriptRoot 'audit_research.py') --scope refined }
        elseif ($phase -eq 'verify-recovery') { & $Python (Join-Path $PSScriptRoot 'verify_bond_trip.py') }
        elseif ($phase -eq 'recovery') { & $Python (Join-Path $PSScriptRoot 'recovery_stress.py') --workers $Workers }
        elseif ($phase -eq 'audit-recovery') { & $Python (Join-Path $PSScriptRoot 'analyze_recovery.py') }
        elseif ($phase -eq 'strong') { & $Python (Join-Path $PSScriptRoot 'strong_pressure.py') --workers $Workers }
        elseif ($phase -eq 'audit-strong') { & $Python (Join-Path $PSScriptRoot 'audit_strong_pressure.py') }
        elseif ($phase -eq 'report') { & $Python (Join-Path $PSScriptRoot 'analyze_expedition.py') }
        elseif ($phase -eq 'delivery-check') { & $Python (Join-Path $PSScriptRoot 'verify_delivery.py') }
        elseif ($phase -eq 'regression') {
            $root=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
            & $Python (Join-Path $root 'test_30man_combat_simulator.py') *> (Join-Path $PSScriptRoot 'results/baseline_regression.txt')
        } else { throw "未知阶段：$phase" }
        if ($LASTEXITCODE -ne 0) { throw "研究步骤失败，已提交的检查点保留：$phase" }
    }
} finally {
    $env:PYTHONPATH=$savedPath
    $env:PYTHONIOENCODING=$savedEncoding
}
