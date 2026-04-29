# Thumbforge Krita Plugin

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![GitHub Release](https://img.shields.io/github/v/release/saitatter/thumbforge-krita-plugin)
[![Issues](https://img.shields.io/github/issues/saitatter/thumbforge-krita-plugin)](https://github.com/saitatter/thumbforge-krita-plugin/issues)
![Made with Python](https://img.shields.io/badge/Made%20with-Python-3776AB?logo=python&logoColor=white)
![Krita](https://img.shields.io/badge/Krita-Python%20Plugin-3BABFF)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

> Data-driven thumbnail batch exporter for Krita templates.

Thumbforge turns a saved `.kra` design into a reusable thumbnail template. Map Krita vector text shapes to variables, paste or import spreadsheet rows, preview a row, and export a whole batch while preserving Krita's native rendering and layer effects.

---

## ✨ Features

### 🎨 Krita Template Workflow

- Detect vector text shapes from the active `.kra` document
- Map each text shape by layer name and shape name for stable exports
- Support multiple text shapes in the same vector layer
- Refresh mappings from the current document while preserving variable names
- Save/load mappings, rows, filename pattern, and export settings inside the `.kra` file
- Guard exports when the active template has unsaved changes

### 📋 CSV & Spreadsheet Data

- Import/export CSV variable rows
- Paste rows directly from Excel, Google Sheets, or any tab-separated clipboard data
- Add/remove variable columns in the docker
- Generate default rows for episode/text variables
- Import filenames as rows for title/filename-driven batches
- Validate missing mapped values and highlight problem cells

### 🚀 Batch Export

- Preview the selected row through Krita's real renderer
- Export current, selected, or all rows
- Progress dialog with cancel support
- Final export report with successes and per-row failures
- Filename patterns with variables, subfolders, sanitization, and duplicate suffixes
- PNG presets for YouTube, small files, and transparent output
- PNG, JPEG, and WebP export support
- Optional resize on export, including 1280x720 YouTube output
- Activity and error log at `%APPDATA%\krita\thumbforge.log`

---

## 📦 Install

Download the latest `thumbforge-krita-plugin-vX.Y.Z.zip` from [GitHub Releases](https://github.com/saitatter/thumbforge-krita-plugin/releases).

In Krita:

1. Open `Tools > Scripts > Import Python Plugin...`
2. Select the downloaded zip
3. Restart Krita
4. Open `Settings > Configure Krita > Python Plugin Manager`
5. Enable `Thumbforge`
6. Restart Krita again
7. Open `Settings > Dockers > Thumbforge`

### Manual Install

Extract the release zip into Krita's `pykrita` resource folder so it contains:

```text
pykrita/
  thumbforge_krita.desktop
  thumbforge_krita/
```

On Windows this is usually:

```text
%APPDATA%\krita\pykrita
```

For local development on Windows:

```powershell
.\scripts\install-krita-plugin.ps1
```

---

## 🧭 Workflow

1. Open a saved `.kra` template in Krita.
2. Open `Settings > Dockers > Thumbforge`.
3. Click `Detect Text`.
4. Rename variables in the mappings table if needed.
5. Import CSV, paste rows, generate rows, or add rows manually.
6. Configure filename pattern and export settings.
7. Click `Save Setup` to persist the setup in the `.kra`.
8. Use `Preview Row`, `Export Current`, `Export Selected`, or `Export All`.

Example filename patterns:

| Pattern | Output |
|---------|--------|
| `thumb_{episode}` | `thumb_1.png` |
| `{series}/thumb_{episode}` | `my-series/thumb_1.png` |
| `{title}` | `Some_Title.png` |

---

## ⚙️ Export Settings

| Setting | Notes |
|---------|-------|
| Format | `png`, `jpg`, or `webp` |
| Preset | YouTube PNG, Small PNG, Transparent PNG |
| Compression | PNG compression level, 0-9 |
| Quality | JPEG/WebP quality, 1-100 |
| Alpha | Preserve transparency where supported |
| sRGB / ICC | Color export hints for Krita |
| Resize | `0 x 0` keeps original size; use `1280 x 720` for YouTube thumbnails |

---

## 🧪 Development

Run tests:

```powershell
.\venv\Scripts\python.exe -m pytest
```

Package the plugin zip:

```powershell
.\scripts\package-krita-plugin.ps1
```

Install into the local Krita profile:

```powershell
.\scripts\install-krita-plugin.ps1
```

---

## 🔄 Releases

This repository uses **semantic-release** with Conventional Commits. On every push to `main`, CI checks if a new version should be published.

- Use Conventional Commits: `feat: ...`, `fix: ...`, `refactor: ...`, `docs: ...`
- The release workflow publishes `thumbforge-krita-plugin-vX.Y.Z.zip`
- The zip is ready for Krita's `Import Python Plugin...` action

---

## 🛠 Troubleshooting

- **Docker is not visible** — restart Krita after enabling the plugin, then check `Settings > Dockers > Thumbforge`.
- **Plugin zip does not import** — make sure the zip contains `thumbforge_krita.desktop` and the `thumbforge_krita/` folder at the root.
- **Export uses old template state** — save the `.kra` or accept the save prompt before exporting.
- **Krita shows an export error** — check `%APPDATA%\krita\thumbforge.log`.
- **Text does not change** — click `Refresh Text`, verify the mapping row points to the right layer and shape, then save setup.

---

## 🤝 Contributing

PRs are welcome. Please:

- Keep commits small and conventional.
- Run `python -m pytest` before submitting.
- Avoid copying GPL plugin code into this MIT project; use architecture ideas only unless licensing changes are intentional.

---

## 📄 License

MIT © saitatter
