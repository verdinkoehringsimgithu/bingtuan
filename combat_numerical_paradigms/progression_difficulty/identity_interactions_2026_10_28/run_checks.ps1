$ErrorActionPreference='Stop'
$root=(Get-Item -LiteralPath $PSScriptRoot).Parent.Parent.Parent.FullName
$project=Join-Path $root 'LegionBattle/LegionBattle'
$python='C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$unity='C:/Program Files/Unity/Hub/Editor/2022.3.62f3c1/Editor/Data'
$refs=Join-Path $unity 'UnityReferenceAssemblies/unity-4.8-api'
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH=Join-Path $root 'combat_numerical_paradigms/v11_research/.venv/Lib/site-packages'
if(!(Test-Path "$PSScriptRoot/interaction_cases.json"))
{& $python "$PSScriptRoot/generate_interactions.py";if($LASTEXITCODE -ne 0){throw 'Interaction fixture generation failed'}}
& $python "$PSScriptRoot/prepare_harness.py"
if($LASTEXITCODE -ne 0){throw 'Interaction harness preparation failed'}
$sources=@('CombatRuntime','CombatPersistentLimits','CharacterTraits','OpeningBondRules','CombatEvasionBonds','CombatSupportBonds','CombatAmplificationBonds','CombatAugmentationBonds','CombatTacticalBonds','CombatCompoundBonds') | ForEach-Object {"$project/Assets/Scripts/Battle/$_.cs"}
& "$unity/NetCoreRuntime/dotnet.exe" "$unity/DotNetSdkRoslyn/csc.dll" /nologo /nostdlib+ /target:exe `
    "/r:$refs/mscorlib.dll" "/r:$refs/System.dll" "/r:$refs/System.Core.dll" "/r:$refs/System.Web.Extensions.dll" "/out:$PSScriptRoot/interactions.exe" @sources "$PSScriptRoot/InteractionParityHarness.cs"
if($LASTEXITCODE -ne 0){throw 'Interaction harness compilation failed'}
& "$PSScriptRoot/interactions.exe" "$PSScriptRoot/interaction_cases.json" "$PSScriptRoot/interaction_parity.json"
if($LASTEXITCODE -ne 0){throw 'Interaction parity failed'}
& $python "$root/combat_numerical_paradigms/progression_difficulty/compound_runtime_2026_10_28/verify_delivery.py"
if($LASTEXITCODE -ne 0){throw 'Frozen production evidence changed'}
& $python "$PSScriptRoot/verify_delivery.py"
if($LASTEXITCODE -ne 0){throw 'Interaction coverage audit failed'}
