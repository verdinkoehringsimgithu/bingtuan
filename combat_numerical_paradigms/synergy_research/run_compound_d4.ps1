param([int]$Workers=6, [int]$Trials=64, [string]$Python='')
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
    & $Python (Join-Path $PSScriptRoot 'verify_configured_compound.py')
    if ($LASTEXITCODE -ne 0) { throw '配置版行为检查失败。' }
    & $Python (Join-Path $PSScriptRoot 'compound_d4_research.py') --workers $Workers --trials $Trials
    if ($LASTEXITCODE -ne 0) { throw 'D4矩阵中断，完成格已保留。' }
    & $Python (Join-Path $PSScriptRoot 'verify_compound_d4.py')
    if ($LASTEXITCODE -ne 0) { throw 'D4研究审计失败。' }
    & $Python (Join-Path $PSScriptRoot 'analyze_compound_responses.py')
    if ($LASTEXITCODE -ne 0) { throw 'D4响应分析失败。' }
} finally {
    $env:PYTHONPATH=$savedPath
    $env:PYTHONIOENCODING=$savedEncoding
}
