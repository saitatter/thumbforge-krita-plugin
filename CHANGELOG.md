# Changelog

## 0.1.1 - 2026-05-24

- Added plugin manual metadata and bundled `Manual.html` so Thumbforge shows a manual entry in Krita's Python Plugin Manager.
- Fixed release packaging so Krita's `Import Python Plugin...` accepts the generated zip archive.
- Improved text-shape export replacement by trying a richer SVG serialization before falling back to the default one.
- Added packaging guards and test coverage for plugin metadata and archive compatibility.