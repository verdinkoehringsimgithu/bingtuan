param([int]$Workers=6,[string[]]$Phases=@('fit','confirm','progressive','audit','regression','delivery'))
$ErrorActionPreference='Stop'
$python=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$previousPath=$env:PYTHONPATH;$previousEncoding=$env:PYTHONIOENCODING
try {
    $env:PYTHONIOENCODING='utf-8'
    $packages=Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) 'v11_research/.venv/Lib/site-packages'
    $env:PYTHONPATH=if($previousPath){"$packages;$previousPath"}else{$packages}
    foreach($phase in $Phases){
        if($phase -eq 'fit'){& $python (Join-Path $PSScriptRoot 'fit_policies.py')}
        elseif($phase -eq 'confirm'){& $python (Join-Path $PSScriptRoot 'confirm_policies.py') --workers $Workers}
        elseif($phase -eq 'progressive'){& $python (Join-Path $PSScriptRoot 'progressive_paths.py')}
        elseif($phase -eq 'audit'){& $python (Join-Path $PSScriptRoot 'analyze_retune.py')}
        elseif($phase -eq 'regression'){
            $root=Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
            & $python (Join-Path $root 'test_30man_combat_simulator.py') *> (Join-Path $PSScriptRoot 'results/baseline_regression.txt')
        }
        elseif($phase -eq 'delivery'){& $python (Join-Path $PSScriptRoot 'verify_delivery.py')}
        else{throw "未知步骤: $phase"}
        if($LASTEXITCODE -ne 0){throw "步骤失败，检查点保留: $phase"}
    }
}finally{$env:PYTHONPATH=$previousPath;$env:PYTHONIOENCODING=$previousEncoding}
