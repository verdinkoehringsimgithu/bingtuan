param([string]$Source = (Join-Path $PSScriptRoot 'source_snapshots/SkillGenerator_checkpoint.cs'), [string]$Output = (Join-Path $PSScriptRoot 'results/catalog_current.json'), [int]$Samples = 128, [int]$Offset = 0)
$ErrorActionPreference = 'Stop'
$researchRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$scratch = Join-Path $researchRoot '.archive_scratch/natural_research/export_build'
New-Item -ItemType Directory -Force -Path $scratch | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Output) | Out-Null
$compiler = 'C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe'
$exe = Join-Path $scratch 'GeneratorBridge.exe'
Copy-Item -LiteralPath $Source -Destination (Join-Path $scratch 'ResearchSource.cs') -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'GeneratorBridge.cs') -Destination (Join-Path $scratch 'GeneratorBridge.cs') -Force
Push-Location -LiteralPath $scratch
try {
    & $compiler /nologo /target:exe /main:GeneratorBridge /out:GeneratorBridge.exe /r:System.Windows.Forms.dll /r:System.Drawing.dll /r:System.Data.dll /r:System.Web.Extensions.dll ResearchSource.cs GeneratorBridge.cs
} finally { Pop-Location }
if ($LASTEXITCODE -ne 0) { throw 'Current generator source compilation failed' }
& $exe $Output $Samples $Offset
if ($LASTEXITCODE -ne 0) { throw 'Current generator export failed' }
