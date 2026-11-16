param([int]$Workers=6,[string[]]$Phases=@('stage-fit','stage-confirm','hard-calibrate','hard-confirm','precision','local25','terminal25','roster25','audit','regression','delivery'))
$ErrorActionPreference='Stop'
$python=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$previousPath=$env:PYTHONPATH;$previousEncoding=$env:PYTHONIOENCODING
try{
    $env:PYTHONIOENCODING='utf-8'
    $packages=Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) 'v11_research/.venv/Lib/site-packages'
    $env:PYTHONPATH=if($previousPath){"$packages;$previousPath"}else{$packages}
    foreach($phase in $Phases){
        if($phase -eq 'stage-fit'){& $python (Join-Path $PSScriptRoot 'stage25.py') --phase fit}
        elseif($phase -eq 'stage-confirm'){& $python (Join-Path $PSScriptRoot 'stage25.py') --phase confirm --workers $Workers}
        elseif($phase -eq 'hard-calibrate'){& $python (Join-Path $PSScriptRoot 'hard_regions.py') --phase calibrate --workers $Workers}
        elseif($phase -eq 'hard-confirm'){& $python (Join-Path $PSScriptRoot 'hard_regions.py') --phase confirm --workers $Workers}
        elseif($phase -eq 'precision'){& $python (Join-Path $PSScriptRoot 'baseline_extension.py')}
        elseif($phase -eq 'local25'){& $python (Join-Path $PSScriptRoot 'local25.py')}
        elseif($phase -eq 'terminal25'){& $python (Join-Path $PSScriptRoot 'terminal25.py')}
        elseif($phase -eq 'roster25'){& $python (Join-Path $PSScriptRoot 'roster25.py')}
        elseif($phase -eq 'audit'){& $python (Join-Path $PSScriptRoot 'analyze_gaps.py')}
        elseif($phase -eq 'regression'){
            $root=Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
            & $python (Join-Path $root 'test_30man_combat_simulator.py') *> (Join-Path $PSScriptRoot 'results/baseline_regression.txt')
        }
        elseif($phase -eq 'delivery'){& $python (Join-Path $PSScriptRoot 'verify_delivery.py')}
        else{throw "未知阶段: $phase"}
        if($LASTEXITCODE -ne 0){throw "研究步骤失败，检查点保留: $phase"}
    }
}finally{$env:PYTHONPATH=$previousPath;$env:PYTHONIOENCODING=$previousEncoding}
