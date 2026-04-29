"""Krita command-line export integration."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from core.kra_writer import write_variable_kra
from core.project import TextLayerMapping


class KritaExportError(RuntimeError):
    """Raised when Krita cannot export a thumbnail."""


def find_krita_executable() -> str | None:
    """Return a Krita executable path if one is discoverable."""
    for name in ("krita", "krita.exe"):
        found = shutil.which(name)
        if found:
            return found
    common_paths = [
        Path("C:/Program Files/Krita (x64)/bin/krita.exe"),
        Path("C:/Program Files/Krita/bin/krita.exe"),
    ]
    for path in common_paths:
        if path.is_file():
            return str(path)
    return None


def export_kra_to_image(
    kra_path: str | Path,
    output_path: str | Path,
    *,
    krita_executable: str | None = None,
) -> None:
    """Export a .kra file to an image using Krita's CLI."""
    executable = krita_executable or find_krita_executable()
    if not executable:
        raise KritaExportError("Krita executable not found.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        executable,
        "--export",
        "--export-filename",
        str(output_path),
        str(kra_path),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise KritaExportError(f"Krita export failed: {detail}")


def batch_export_kra(
    template_path: str | Path,
    mappings: list[TextLayerMapping],
    variable_sets: list[dict[str, str]],
    output_dir: str | Path,
    *,
    name_pattern: str = "thumb_{episode}",
    krita_executable: str | None = None,
) -> list[Path]:
    """Apply variables to a .kra template and export each result with Krita."""
    from core.renderer import _substitute

    output_dir = Path(output_dir)
    exported: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="thumbforge_kra_") as tmp:
        tmp_dir = Path(tmp)
        for index, variables in enumerate(variable_sets, start=1):
            modified_kra = tmp_dir / f"thumb_{index}.kra"
            write_variable_kra(template_path, modified_kra, mappings, variables)
            output_path = output_dir / f"{_substitute(name_pattern, variables)}.png"
            export_kra_to_image(
                modified_kra,
                output_path,
                krita_executable=krita_executable,
            )
            exported.append(output_path)
    return exported
