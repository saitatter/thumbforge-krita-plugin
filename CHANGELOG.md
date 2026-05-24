# Changelog

## 0.1.2 - 2026-05-25

- Expanded Krita text-shape SVG fallback handling to try additional serialization modes during export.
- Added a wrapped SVG fallback for vector text reimport and richer logging for failed shape imports.
- Added a version sync test so the version shown in the docker stays aligned with `pyproject.toml`.

## 0.1.1 - 2026-05-24

- Added plugin manual metadata and bundled `Manual.html` so Thumbforge shows a manual entry in Krita's Python Plugin Manager.
- Fixed release packaging so Krita's `Import Python Plugin...` accepts the generated zip archive.
- Improved text-shape export replacement by trying a richer SVG serialization before falling back to the default one.
- Added packaging guards and test coverage for plugin metadata and archive compatibility.