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
        & $pythonPath -m pip install -r (Join-Path $researchRoot 'combat_numerical_paradigms/natural_research/requirements.txt')
        if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
    }
}
& $pythonPath (Join-Path $PSScriptRoot 'study.py') --workers $Workers
if ($LASTEXITCODE -ne 0) { throw 'Growth study interrupted; parameter checkpoints retained' }
& $pythonPath (Join-Path $PSScriptRoot 'refine_bands.py')
if ($LASTEXITCODE -ne 0) { throw 'Band study interrupted; parameter checkpoints retained' }
& $pythonPath (Join-Path $PSScriptRoot 'balanced_templates.py')
if ($LASTEXITCODE -ne 0) { throw 'NPC stat-blend study interrupted; parameter checkpoints retained' }
& $pythonPath (Join-Path $PSScriptRoot 'report.py')
if ($LASTEXITCODE -ne 0) { throw 'Design report validation failed' }
& $pythonPath (Join-Path $PSScriptRoot 'validate.py')
if ($LASTEXITCODE -ne 0) { throw 'Delivery validation failed' }
& $pythonPath (Join-Path $PSScriptRoot 'package.py')
if ($LASTEXITCODE -ne 0) { throw 'Research package validation failed' }
