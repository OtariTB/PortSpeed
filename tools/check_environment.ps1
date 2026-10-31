$ErrorActionPreference = 'Stop'
$workspace = Split-Path -Parent $PSScriptRoot
$output = Join-Path $workspace 'research/local/environment.json'
New-Item -ItemType Directory -Path (Split-Path -Parent $output) -Force | Out-Null
$checks = @(
    @{Name='python'; Args=@('--version')},
    @{Name='node'; Args=@('--version')},
    @{Name='npm.cmd'; Args=@('--version')},
    @{Name='java'; Args=@('-version')},
    @{Name='git'; Args=@('--version')},
    @{Name='emcc'; Args=@('--version')},
    @{Name='cmake'; Args=@('--version')},
    @{Name='ninja'; Args=@('--version')},
    @{Name='clang'; Args=@('--version')},
    @{Name='wasm-opt'; Args=@('--version')}
)
$results = foreach ($check in $checks) {
    $command = Get-Command $check.Name -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command) {
        $arguments = $check.Args
        # Java writes its version to stderr; preserve it as diagnostic output.
        $oldPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $version = (& $command.Source @arguments 2>&1 | Out-String).Trim()
        $status = $LASTEXITCODE
        $ErrorActionPreference = $oldPreference
        [pscustomobject]@{name=$check.Name; path=$command.Source; exit_code=$status; output=$version}
    } else {
        [pscustomobject]@{name=$check.Name; path=$null; output='Not found on PATH; installation elsewhere not ruled out'}
    }
}
[pscustomobject]@{checked_utc=[DateTime]::UtcNow.ToString('o'); tools=@($results)} |
    ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $output -Encoding UTF8
$results | Format-Table -AutoSize
