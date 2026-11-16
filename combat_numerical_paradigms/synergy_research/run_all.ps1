param([int]$Workers = 8)
$ErrorActionPreference = 'Stop'
$studyPython = Join-Path (Split-Path -Parent $PSScriptRoot) 'v11_research/.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $studyPython)) { throw '请先按 natural_research/README.md 安装研究依赖。' }
$env:PYTHONIOENCODING='utf-8'
function Invoke-BondStudy([string]$Script, [string[]]$Arguments) {
    & $studyPython (Join-Path $PSScriptRoot $Script) @Arguments
    if ($LASTEXITCODE -ne 0) { throw "研究停止，已完成单元保留：$Script" }
}
Invoke-BondStudy 'verify.py' @()
Invoke-BondStudy 'run_bonds.py' @('--phase','all','--workers',"$Workers")
Invoke-BondStudy 'refine.py' @('--workers',"$Workers")
Invoke-BondStudy 'skill_supply.py' @('--workers',"$Workers")
Invoke-BondStudy 'composition_check.py' @('--workers',"$Workers")
Invoke-BondStudy 'analyze.py' @()
Invoke-BondStudy 'supplement_report.py' @()
Invoke-BondStudy 'verify_delivery.py' @()
Invoke-BondStudy 'write_reader_guide.py' @()
