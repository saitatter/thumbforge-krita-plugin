$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$sourceRoot = Join-Path $repoRoot "krita-plugin"
$targetRoot = Join-Path $env:APPDATA "krita\pykrita"
$targetPlugin = Join-Path $targetRoot "thumbforge_krita"

$kritaProcess = Get-Process krita -ErrorAction SilentlyContinue
if ($kritaProcess) {
    Write-Host "Krita is currently running. Close Krita, then run this installer again." -ForegroundColor Yellow
    exit 1
}

New-Item -ItemType Directory -Force -Path $targetRoot | Out-Null
if (Test-Path $targetPlugin) {
    Remove-Item -LiteralPath $targetPlugin -Recurse -Force
}
Copy-Item -LiteralPath (Join-Path $sourceRoot "thumbforge_krita.desktop") -Destination $targetRoot -Force
Copy-Item -LiteralPath (Join-Path $sourceRoot "thumbforge_krita") -Destination $targetRoot -Recurse -Force
Remove-Item -LiteralPath (Join-Path $targetPlugin "__pycache__") -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Installed Thumbforge Krita plugin to $targetRoot"
Write-Host "Restart Krita, enable Thumbforge in Python Plugin Manager, then restart Krita again."
