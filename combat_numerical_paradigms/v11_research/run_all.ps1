param([int]$Workers = 8, [string]$Output = (Join-Path $PSScriptRoot 'results'))
$ErrorActionPreference = 'Stop'
$researchPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $researchPython)) {
    python -m venv (Join-Path $PSScriptRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create Python environment' }
    $researchRequirements = Join-Path $PSScriptRoot 'requirements-lock.txt'
    if (-not (Test-Path -LiteralPath $researchRequirements)) { $researchRequirements = Join-Path $PSScriptRoot 'requirements.txt' }
    & $researchPython -m pip install -r $researchRequirements
    if ($LASTEXITCODE -ne 0) { throw 'Could not install research dependencies' }
}
& $researchPython (Join-Path $PSScriptRoot 'run_native_regression.py') --output $Output
if ($LASTEXITCODE -ne 0) { throw 'Native balance regression failed' }
& $researchPython (Join-Path $PSScriptRoot 'run_research.py') --workers $Workers --output $Output
if ($LASTEXITCODE -ne 0) { throw 'Research phase failed' }
& $researchPython (Join-Path $PSScriptRoot 'extended_validation.py') --workers $Workers --output $Output
if ($LASTEXITCODE -ne 0) { throw 'Extended validation failed' }
& $researchPython (Join-Path $PSScriptRoot 'target_unique.py') --workers $Workers --output $Output
if ($LASTEXITCODE -ne 0) { throw 'Targeted unique-character validation failed' }
& $researchPython (Join-Path $PSScriptRoot 'verify_research.py') --output $Output
if ($LASTEXITCODE -ne 0) { throw 'Evidence verification failed' }
& $researchPython (Join-Path $PSScriptRoot 'build_report.py') --output $Output
if ($LASTEXITCODE -ne 0) { throw 'Report generation failed' }
