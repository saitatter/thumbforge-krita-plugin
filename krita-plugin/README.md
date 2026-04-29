# Thumbforge Krita Plugin

This directory contains the Krita plugin payload:

```text
thumbforge_krita.desktop
thumbforge_krita/
```

Use the repository-level scripts to install or package it:

```powershell
.\scripts\install-krita-plugin.ps1
.\scripts\package-krita-plugin.ps1
```

The packaged zip is created under `dist/` and can be installed with Krita's `Tools > Scripts > Import Python Plugin...`.
