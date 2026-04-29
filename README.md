# Thumbforge Krita Plugin

Thumbforge is now a Krita plugin for batch-exporting thumbnail variants from a saved `.kra` template.

## Features

- Detect vector text shapes in the active Krita document.
- Map text shapes to CSV/table variables.
- Save and load Thumbforge setup directly inside the `.kra` file.
- Import/export variable CSV files.
- Batch export PNG thumbnails with configurable compression, alpha, sRGB, ICC, and interlace options.
- Validate duplicate output filenames and missing variable columns before exporting.

## Install Locally

```powershell
.\scripts\install-krita-plugin.ps1
```

Then restart Krita, enable **Thumbforge** in `Settings > Configure Krita > Python Plugin Manager`, restart Krita again, and open it from `Settings > Dockers > Thumbforge`.

## Test

```powershell
python -m pytest
```
