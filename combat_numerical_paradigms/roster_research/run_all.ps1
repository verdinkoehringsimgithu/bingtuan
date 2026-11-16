param(
    [int]$Workers = 8,
    [string]$Output = (Join-Path $PSScriptRoot 'results'),
    [string]$Python = ''
)
$ErrorActionPreference = 'Stop'
if (-not $Python) {
    $Python = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $Python)) {
        python -m venv (Join-Path $PSScriptRoot '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed' }
    }
    & $Python -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
}
& $Python (Join-Path $PSScriptRoot 'run_study.py') --phase all --workers $Workers --output $Output
if ($LASTEXITCODE -ne 0) { throw 'Research phase failed; completed outputs have been preserved' }
