# Copilot Instructions for Thumbforge Krita Plugin

## Communication

- Raspunde in romana, concis si practic.
- Explica tradeoff-urile inainte de schimbari riscante in Krita API, export sau release automation.
- Verifica in cod, teste sau documentatie locala inainte sa presupui comportamentul pluginurilor Krita.

## Project Context

- Thumbforge is a Krita Python plugin for batch-exporting thumbnail variants from `.kra` templates.
- Plugin payload lives in `krita-plugin/thumbforge_krita/` with descriptor `krita-plugin/thumbforge_krita.desktop`.
- Tests live in `tests/` and avoid requiring a live Krita process unless explicitly marked as integration work.
- Release artifacts are plugin zips, not standalone executables.

## Git and Releases

- Use conventional commits. Examples:
  - `feat(krita): add export selected rows`
  - `fix(krita): avoid png option dialogs`
  - `test: cover filename sanitization`
  - `ci: package plugin release zip`
- `python-semantic-release` reads conventional commits from `pyproject.toml`.
- Do not manually edit generated changelog/release artifacts unless explicitly requested.
- Keep commits focused and avoid mixing UI, packaging, and export behavior unless the feature requires it.

## Krita Plugin Rules

- Keep the release zip root compatible with Krita: `thumbforge_krita.desktop` plus `thumbforge_krita/`.
- Avoid blocking Krita more than necessary; use progress dialogs and `QApplication.processEvents()` around batch loops.
- Treat Krita document/vector APIs as UI-thread-bound unless proven otherwise.
- Never destructively edit the source template during export; open a saved copy, modify it in memory, flatten/export, and close it without saving.
- Preserve Krita-specific effects by letting Krita render the final export.

## Python and Style

- Target Python 3.10+.
- Prefer standard-library helpers; this plugin should not need external runtime dependencies.
- Keep pure helpers testable without importing Krita or PyQt.
- Delay imports of Krita/PyQt-only objects when that makes helpers easier to test.
- Add type hints for new public helpers and dataclasses.

## Testing

- Preferred local command:
  - `.\venv\Scripts\python.exe -m pytest`
- Add tests for pure logic:
  - filename sanitization
  - export planning
  - project annotation serialization
  - clipboard/CSV parsing
  - SVG text replacement
- Do not require Krita in unit tests unless the test is explicitly isolated as an integration test.

## Packaging

- Use `scripts/package-krita-plugin.ps1` to create release zips.
- Use `scripts/install-krita-plugin.ps1` for local Windows install.
- Do not commit generated `dist/`, `build/`, or `__pycache__` contents.
