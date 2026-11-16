param([int]$Workers = 8)
$ErrorActionPreference = 'Stop'
$researchRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $researchRoot
$pythonPath = Join-Path $researchRoot 'combat_numerical_paradigms/v11_research/.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    $localEnvironment = Join-Path $PSScriptRoot '.venv'
    $pythonPath = Join-Path $localEnvironment 'Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $pythonPath)) {
        & python -m venv $localEnvironment
        if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed' }
        & $pythonPath -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
        if ($LASTEXITCODE -ne 0) { throw 'Research dependency installation failed' }
    }
}
function Invoke-Research([string]$Script, [string[]]$Arguments) {
    & $pythonPath (Join-Path $PSScriptRoot $Script) @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Research failed; completed checkpoints are preserved: $Script" }
}
Invoke-Research 'run_natural.py' @('--phase','all','--workers',"$Workers")
Invoke-Research 'enrich_discovery.py' @()
Invoke-Research 'advanced_study.py' @('--phase','all','--workers',"$Workers")
Invoke-Research 'refine_delivery.py' @('--workers',"$Workers")
Invoke-Research 'calibrate_equipment.py' @('--workers',"$Workers")
Invoke-Research 'calibrate_unique.py' @('--workers',"$Workers")
Invoke-Research 'unique_mechanism_holdout.py' @()
Invoke-Research 'calibrate_counter.py' @()
Invoke-Research 'embedding_audit.py' @()
Invoke-Research 'plot_research.py' @('--workers',"$Workers")
Invoke-Research 'derive_design_tables.py' @()
Invoke-Research 'build_report.py' @()
Invoke-Research 'validate_natural.py' @()
Invoke-Research 'validate_delivery.py' @()
Invoke-Research 'package_delivery.py' @()
