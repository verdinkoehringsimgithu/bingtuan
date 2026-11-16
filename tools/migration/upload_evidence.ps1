param([int]$StartPart=1)
$ErrorActionPreference='Stop'
$root=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location -LiteralPath $root
$manifest=Get-Content -LiteralPath 'TransferData/manifest.json' -Raw -Encoding UTF8 | ConvertFrom-Json
# Keep ignore matching fast; all result paths remain losslessly archived.
$ignore=Get-Content -LiteralPath '.gitignore' -Raw -Encoding UTF8
$marker='# Lossless evidence moved into TransferData; run restore_research.py.'
$prefix=$ignore.Split(@($marker),[StringSplitOptions]::None)[0]
$lines=[Collections.Generic.List[string]]::new()
$lines.Add($prefix.TrimEnd());$lines.Add('');$lines.Add($marker);$lines.Add('/combat_numerical_paradigms/**/results/')
foreach($file in $manifest.files)
{
    if($file.path.Split('/') -notcontains 'results')
    {
        $pattern=$file.path.Replace('[','[[]')
        $lines.Add('/'+$pattern)
    }
}
[IO.File]::WriteAllText((Join-Path $root '.gitignore'),($lines -join "`n")+"`n",[Text.UTF8Encoding]::new($false))
foreach($part in $manifest.parts)
{
    $path=Join-Path 'TransferData' $part.name
    if((Get-Item -LiteralPath $path).Length -ne $part.bytes -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $part.sha256){throw "Part checksum mismatch: $path"}
}
$gitOptions=@('-c',"safe.directory=$root",'-c','gc.auto=0','-c','pack.window=0','-c','pack.threads=2','-c','core.compression=1','-c','http.version=HTTP/1.1','-c','http.postBuffer=157286400')
& git @gitOptions add -- .gitignore TransferData/manifest.json tools/migration/upload_evidence.ps1
if($LASTEXITCODE -ne 0){throw 'Metadata staging failed'}
for($offset=$StartPart-1;$offset -lt $manifest.parts.Count;$offset++)
{
    $end=$offset+1
    $paths=@();for($i=$offset;$i -lt $end;$i++){$paths+=('TransferData/'+$manifest.parts[$i].name)}
    & git @gitOptions add -- @paths
    if($LASTEXITCODE -ne 0){throw 'Part staging failed'}
    & git @gitOptions diff --cached --quiet
    if($LASTEXITCODE -eq 1)
    {
        & git @gitOptions commit -q -m "Preserve research evidence parts $($offset+1)-$end of $($manifest.parts.Count)"
        if($LASTEXITCODE -ne 0){throw 'Evidence commit failed'}
    }
    $uploaded=$false
    for($attempt=1;$attempt -le 3;$attempt++)
    {
        & git @gitOptions push origin main
        if($LASTEXITCODE -eq 0){$uploaded=$true;break}
        if($attempt -lt 3){Start-Sleep -Seconds (3*$attempt)}
    }
    if(!$uploaded){throw "Evidence push failed; resume with -StartPart $($offset+1)"}
    Write-Output "Uploaded evidence parts through $end / $($manifest.parts.Count)"
}
