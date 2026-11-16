param(
    [int]$Workers = 6,
    [int]$Rosters = 1,
    [string]$Python = '',
    [string[]]$StudyArguments = @()
)
$ErrorActionPreference = 'Stop'
$studyRoot = Split-Path -Parent $PSScriptRoot
$venvRoot = Join-Path $studyRoot 'v11_research/.venv'
$studyPackages = Join-Path $venvRoot 'Lib/site-packages'
$venvPython = Join-Path $venvRoot 'Scripts/python.exe'
$previousPythonPath = $env:PYTHONPATH
$previousEncoding = $env:PYTHONIOENCODING

function Invoke-OrderStep([string]$Script, [string[]]$StepArguments) {
    & $script:studyPython (Join-Path $PSScriptRoot $Script) @StepArguments
    if ($LASTEXITCODE -ne 0) { throw "研究停止，已完成单元保留：$Script" }
}

try {
    $env:PYTHONIOENCODING = 'utf-8'
    if ($Python) {
        $script:studyPython = $Python
    } else {
        # An existing Windows venv launcher can still point to a removed base.
        $venvConfig = Join-Path $venvRoot 'pyvenv.cfg'
        $basePythonExists = $false
        if (Test-Path -LiteralPath $venvConfig) {
            $baseLine = Get-Content -LiteralPath $venvConfig | Where-Object { $_ -match '^executable\s*=' } | Select-Object -First 1
            if ($baseLine) {
                $basePython = ($baseLine -split '=', 2)[1].Trim()
                $basePythonExists = Test-Path -LiteralPath $basePython
            }
        }
        $venvUsable = $false
        if ((Test-Path -LiteralPath $venvPython) -and $basePythonExists) {
            try {
                $null = & $venvPython -c 'pass' 2>$null
                $venvUsable = $LASTEXITCODE -eq 0
            } catch { $venvUsable = $false }
        }
        if ($venvUsable) {
            $script:studyPython = $venvPython
        } else {
            $bundledPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
            if (-not (Test-Path -LiteralPath $bundledPython)) {
                throw '未找到可用研究Python，请用 -Python 指定已安装研究依赖的解释器。'
            }
            $script:studyPython = $bundledPython
            # Reuse compiled dependencies only with the same Python ABI.
            $runtimeMinor = (& $script:studyPython -c 'import sys;print(str(sys.version_info.major)+"."+str(sys.version_info.minor))').Trim()
            if ($LASTEXITCODE -ne 0 -or $runtimeMinor -ne '3.12') {
                throw '旧研究依赖需要Python3.12，请用 -Python 指定匹配且已安装依赖的环境。'
            }
            if ($previousPythonPath) { $env:PYTHONPATH = "$studyPackages;$previousPythonPath" }
            else { $env:PYTHONPATH = $studyPackages }
        }
    }
    # Fail early before submitting an expensive process pool.
    & $script:studyPython -c 'import scipy,sklearn,pandas;print("Research dependencies ready")'
    if ($LASTEXITCODE -ne 0) { throw '研究Python缺少依赖，请按natural_research/README.md准备环境。' }
    $outputPath = Join-Path $PSScriptRoot 'results/optimal_order'
    for ($i = 0; $i -lt $StudyArguments.Count; $i++) {
        if ($StudyArguments[$i] -eq '--output' -and $i + 1 -lt $StudyArguments.Count) {
            $outputPath = $StudyArguments[$i + 1]
        }
    }
    $runArguments = @('--workers', "$Workers", '--rosters', "$Rosters") + $StudyArguments
    Invoke-OrderStep 'order_search.py' $runArguments
    Invoke-OrderStep 'verify_order_search.py' @('--output', $outputPath)
    Invoke-OrderStep 'replay_enemy_metrics.py' @('--output', $outputPath, '--workers', "$Workers")
    Invoke-OrderStep 'summarize_optimal_orders.py' @('--output', $outputPath)
} finally {
    $env:PYTHONPATH = $previousPythonPath
    $env:PYTHONIOENCODING = $previousEncoding
}
