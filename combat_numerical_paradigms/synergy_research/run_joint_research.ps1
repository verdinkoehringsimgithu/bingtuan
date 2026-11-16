param(
    [int]$Workers = 6,
    [string]$Python = '',
    [string[]]$Phases = @('counters','screen','confirm','attribute','allocation','verify','analyze')
)
$ErrorActionPreference = 'Stop'
$savedPath = $env:PYTHONPATH
$savedEncoding = $env:PYTHONIOENCODING
try {
    $env:PYTHONIOENCODING = 'utf-8'
    if (-not $Python) {
        $Python = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
        if (-not (Test-Path -LiteralPath $Python)) { throw '请用 -Python 指定Python3.12研究解释器。' }
        $packages = Join-Path (Split-Path -Parent $PSScriptRoot) 'v11_research/.venv/Lib/site-packages'
        $env:PYTHONPATH = if ($savedPath) { "$packages;$savedPath" } else { $packages }
    }
    & $Python -c 'import sys,numpy,scipy,sklearn;assert sys.version_info[:2]==(3,12);print("Joint research runtime ready")'
    if ($LASTEXITCODE -ne 0) { throw '研究环境检查失败。' }
    foreach ($phase in $Phases) {
        if ($phase -eq 'counters') {
            & $Python (Join-Path $PSScriptRoot 'joint_research.py') --phase counters --workers $Workers --budget 32 --shortlist 3 --train-trials 6 --select-trials 16 --cross-trials 16 --test-trials 128
        } elseif ($phase -eq 'screen') {
            & $Python (Join-Path $PSScriptRoot 'joint_research.py') --phase screen --workers $Workers --budget 16 --shortlist 2 --train-trials 3 --select-trials 8 --cross-trials 8 --test-trials 24
        } elseif ($phase -eq 'confirm') {
            & $Python (Join-Path $PSScriptRoot 'joint_research.py') --phase confirm --workers $Workers --budget 32 --shortlist 3 --train-trials 4 --select-trials 12 --cross-trials 12 --test-trials 64
        } elseif ($phase -eq 'verify') {
            & $Python (Join-Path $PSScriptRoot 'verify_joint.py')
        } elseif ($phase -eq 'attribute') {
            & $Python (Join-Path $PSScriptRoot 'joint_attribute_sensitivity.py') --workers $Workers --trials 32
        } elseif ($phase -eq 'allocation') {
            & $Python (Join-Path $PSScriptRoot 'joint_allocation.py') --workers $Workers
        } elseif ($phase -eq 'analyze') {
            & $Python (Join-Path $PSScriptRoot 'analyze_joint.py')
        } else { throw "未知研究步骤：$phase" }
        if ($LASTEXITCODE -ne 0) { throw "研究步骤失败，已完成单元保留：$phase" }
    }
} finally {
    $env:PYTHONPATH = $savedPath
    $env:PYTHONIOENCODING = $savedEncoding
}
