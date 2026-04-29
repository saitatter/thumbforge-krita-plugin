# Thumbforge

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Made with Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![PySide6/Qt](https://img.shields.io/badge/PySide6-Qt6-41CD52?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython-6/)

Batch thumbnail generator with Krita template support and AI background generation.

## ✨ Features

### 🎨 Template System
- Load `.kra` (Krita) templates — parse layers without requiring Krita at runtime
- Define variable text layers (episode number, title, date, etc.)
- Live preview with real-time variable substitution

### 📋 Batch Export
- Table-based variable editor — one row per thumbnail
- Batch export to PNG with customizable filename patterns
- CSV import for bulk variable sets

### 🤖 AI Backgrounds (optional)
- Generate backgrounds via ComfyUI / Stable Diffusion WebUI API
- Per-episode prompt customization

### 🖥️ Desktop UI
- Built with PySide6 / Qt6
- Cross-platform: Windows, macOS, Linux

## 🚀 Quick Start

### Run from source

```bash
git clone https://github.com/saitatter/thumbforge.git
cd thumbforge
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS / Linux
pip install -r requirements.txt
python main.py
```

### Build standalone executable

```bash
pip install pyinstaller
pyinstaller --noconfirm thumbforge.spec
# Portable single-file:
pyinstaller --noconfirm thumbforge-portable.spec
```

## 🤝 Contributing

PRs are welcome! Please:
- Keep commits small and conventional.
- Run `python -m pytest tests/` before submitting.

## 📄 License

MIT © saitatter
