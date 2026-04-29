$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$pluginRoot = Join-Path $repoRoot "krita-plugin"
$distRoot = Join-Path $repoRoot "dist"
$version = $env:THUMBFORGE_PLUGIN_VERSION
if (-not $version) {
    $version = "local"
}

$pyproject = Join-Path $repoRoot "pyproject.toml"
if ($version -eq "local" -and (Test-Path $pyproject)) {
    $match = Select-String -Path $pyproject -Pattern '^version\s*=\s*"([^"]+)"' | Select-Object -First 1
    if ($match) {
        $version = $match.Matches[0].Groups[1].Value
    }
}

New-Item -ItemType Directory -Force -Path $distRoot | Out-Null
Remove-Item -LiteralPath (Join-Path $pluginRoot "thumbforge_krita\__pycache__") -Recurse -Force -ErrorAction SilentlyContinue

$zipPath = Join-Path $distRoot "thumbforge-krita-plugin-v$version.zip"
Compress-Archive `
    -Path (Join-Path $pluginRoot "thumbforge_krita.desktop"), (Join-Path $pluginRoot "thumbforge_krita") `
    -DestinationPath $zipPath `
    -Force

Write-Host $zipPath
