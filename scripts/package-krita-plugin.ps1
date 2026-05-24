$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

function Add-DirectoryToZip {
    param(
        [System.IO.Compression.ZipArchive]$Archive,
        [string]$SourcePath,
        [string]$EntryPath
    )

    $directoryEntry = ($EntryPath -replace "\\", "/").TrimEnd("/") + "/"
    $Archive.CreateEntry($directoryEntry) | Out-Null

    Get-ChildItem -LiteralPath $SourcePath | ForEach-Object {
        $childEntryPath = Join-Path $EntryPath $_.Name
        if ($_.PSIsContainer) {
            Add-DirectoryToZip -Archive $Archive -SourcePath $_.FullName -EntryPath $childEntryPath
            return
        }

        $archivePath = $childEntryPath -replace "\\", "/"
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $Archive,
            $_.FullName,
            $archivePath,
            [System.IO.Compression.CompressionLevel]::Optimal
        ) | Out-Null
    }
}

function Test-ZipContainsEntry {
    param(
        [string]$ZipPath,
        [string]$EntryPath
    )

    $archive = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
        foreach ($entry in $archive.Entries) {
            if ($entry.FullName -eq $EntryPath) {
                return $true
            }
        }

        return $false
    }
    finally {
        $archive.Dispose()
    }
}

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
if (Test-Path $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

$desktopPath = Join-Path $pluginRoot "thumbforge_krita.desktop"
$modulePath = Join-Path $pluginRoot "thumbforge_krita"

$archive = [System.IO.Compression.ZipFile]::Open($zipPath, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
        $archive,
        $desktopPath,
        "thumbforge_krita.desktop",
        [System.IO.Compression.CompressionLevel]::Optimal
    ) | Out-Null
    Add-DirectoryToZip -Archive $archive -SourcePath $modulePath -EntryPath "thumbforge_krita"
}
finally {
    $archive.Dispose()
}

if (-not (Test-ZipContainsEntry -ZipPath $zipPath -EntryPath "thumbforge_krita/")) {
    throw "Invalid plugin archive: missing thumbforge_krita/ directory entry required by Krita Plugin Importer."
}

if (-not (Test-ZipContainsEntry -ZipPath $zipPath -EntryPath "thumbforge_krita.desktop")) {
    throw "Invalid plugin archive: missing thumbforge_krita.desktop entry."
}

Write-Host $zipPath
