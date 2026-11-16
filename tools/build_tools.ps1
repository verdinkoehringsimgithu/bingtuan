param([string]$UnityData='C:/Program Files/Unity/Hub/Editor/2022.3.62f3c1/Editor/Data')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$refs=Join-Path $UnityData 'UnityReferenceAssemblies/unity-4.8-api'
$output=Join-Path $PSScriptRoot 'build'
New-Item -ItemType Directory -Force $output | Out-Null
$arguments=@('/nologo','/nostdlib+','/target:winexe',"/r:$refs/mscorlib.dll","/r:$refs/System.dll","/r:$refs/System.Core.dll","/r:$refs/System.Data.dll","/r:$refs/System.Drawing.dll","/r:$refs/System.Windows.Forms.dll","/r:$refs/System.Web.Extensions.dll","/r:$refs/System.Xml.dll")
& "$UnityData/NetCoreRuntime/dotnet.exe" "$UnityData/DotNetSdkRoslyn/csc.dll" @arguments "/out:$output/CharaClassifier.exe" "$root/CharaClassifier.cs" "$root/CharacterTagging.cs"
if($LASTEXITCODE -ne 0){throw 'Character tool compilation failed'}
& "$UnityData/NetCoreRuntime/dotnet.exe" "$UnityData/DotNetSdkRoslyn/csc.dll" @arguments "/out:$output/SkillGenerator.exe" "$root/SkillGenerator.cs"
if($LASTEXITCODE -ne 0){throw 'Skill generator compilation failed'}
Write-Output "Built tools in $output"
