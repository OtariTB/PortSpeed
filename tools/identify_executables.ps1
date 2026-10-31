$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$config = Get-Content -LiteralPath (Join-Path $workspace 'config/local.json') | ConvertFrom-Json
$source = [System.IO.Path]::GetFullPath($config.game_root)
$inventory = Get-Content -LiteralPath (Join-Path $workspace 'research/local/inventory/inventory.json') | ConvertFrom-Json
$output = Join-Path $workspace 'research/local/phase2/executables.json'
if ($output.StartsWith($source + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Output overlaps game tree' }
$results = foreach ($row in $inventory.files) {
    if ($row.path -notmatch 'nfs\.exe(\.org)?$') { continue }
    $file = [System.IO.Path]::GetFullPath((Join-Path $source $row.path))
    if (-not $file.StartsWith($source + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Source escaped game tree' }
    $item = Get-Item -LiteralPath $file
    $ancestor = $item
    while ($ancestor) {
        if ($ancestor.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse path refused' }
        if ($ancestor -is [IO.FileInfo]) { $ancestor = $ancestor.Directory } else { $ancestor = $ancestor.Parent }
    }
    $hash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLower()
    if ($hash -ne $row.sha256) { throw 'Source changed since inventory; refresh PE evidence before proceeding' }
    $v = [Diagnostics.FileVersionInfo]::GetVersionInfo($file)
    [pscustomobject]@{
        path=$row.path; size=$item.Length; sha256=$hash; pe=$row.pe
        file_version=$v.FileVersion; product_version=$v.ProductVersion
        description=$v.FileDescription; original_filename=$v.OriginalFilename
        evidence='PE metadata from Phase 1 snapshot, verified against current SHA-256; version resources read statically now'
    }
}
New-Item -ItemType Directory -Path (Split-Path -Parent $output) -Force | Out-Null
$results | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $output -Encoding UTF8
$results | Select-Object path,size,file_version,product_version,sha256 | Format-List
