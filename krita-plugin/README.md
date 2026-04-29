# Thumbforge Krita Plugin

Krita docker for batch-exporting thumbnails from the active `.kra` document.

## Install Locally

Copy `thumbforge_krita.desktop` and the `thumbforge_krita` folder into Krita's `pykrita` resource folder:

```powershell
.\scripts\install-krita-plugin.ps1
```

Then restart Krita, enable **Thumbforge** in `Settings > Configure Krita > Python Plugin Manager`, restart again, and open it from `Settings > Dockers > Thumbforge`.

## MVP Workflow

1. Open and save a `.kra` template in Krita.
2. Open the Thumbforge docker.
3. Click `Detect Text`.
4. Rename mapping variables if needed.
5. Import a CSV or add rows manually.
6. Click `Save Setup` to persist mappings and rows inside the `.kra`.
7. Export the selected row or export all rows.
