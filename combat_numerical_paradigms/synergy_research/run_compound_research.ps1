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
    & $Python (Join-Path $PSScriptRoot 'verify_compound_core.py')
    if ($LASTEXITCODE -ne 0) { throw '复合机制行为检查失败。' }
    & $Python (Join-Path $PSScriptRoot 'compound_research.py') --workers $Workers --trials $Trials
    if ($LASTEXITCODE -ne 0) { throw '研究失败，已完成单元保留。' }
    & $Python (Join-Path $PSScriptRoot 'verify_compound_research.py')
    if ($LASTEXITCODE -ne 0) { throw '矩阵审计失败。' }
    & $Python (Join-Path $PSScriptRoot 'analyze_compound_nodes.py')
    if ($LASTEXITCODE -ne 0) { throw '目标节点分析失败。' }
} finally {
    $env:PYTHONPATH=$savedPath
    $env:PYTHONIOENCODING=$savedEncoding
}
