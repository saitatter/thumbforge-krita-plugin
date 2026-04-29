"""Krita command-line export integration."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from core.kra_writer import write_variable_kra
from core.project import TextLayerMapping


class KritaExportError(RuntimeError):
    """Raised when Krita cannot export a thumbnail."""


@dataclass
class BatchExportReport:
    """Result details for a batch export operation."""
    exported: list[Path]
    failures: list[str]

    @property
    def succeeded(self) -> int:
        return len(self.exported)

    @property
    def failed(self) -> int:
        return len(self.failures)


def find_krita_executable() -> str | None:
    """Return a Krita executable path if one is discoverable."""
    for name in ("krita.com", "krita", "krita.exe"):
        found = shutil.which(name)
        if found:
            return found
    common_paths = [
        Path("C:/Program Files/Krita (x64)/bin/krita.com"),
        Path("C:/Program Files/Krita (x64)/bin/krita.exe"),
        Path("C:/Program Files/Krita/bin/krita.com"),
        Path("C:/Program Files/Krita/bin/krita.exe"),
    ]
    for path in common_paths:
        if path.is_file():
            return str(path)
    return None


def find_krita_runner() -> str | None:
    """Return a kritarunner executable path if one is discoverable."""
    for name in ("kritarunner", "kritarunner.exe", "kritarunner.com"):
        found = shutil.which(name)
        if found:
            return found
    common_paths = [
        Path("C:/Program Files/Krita (x64)/bin/kritarunner.exe"),
        Path("C:/Program Files/Krita (x64)/bin/kritarunner.com"),
        Path("C:/Program Files/Krita/bin/kritarunner.exe"),
        Path("C:/Program Files/Krita/bin/kritarunner.com"),
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
    timeout_seconds: int = 120,
) -> None:
    """Export a .kra file to an image using Krita's CLI."""
    executable = krita_executable or find_krita_executable()
    if not executable:
        raise KritaExportError("Krita executable not found.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        executable,
        "--nosplash",
        "--export",
        "--export-filename",
        str(output_path),
        str(kra_path),
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise KritaExportError(
            f"Krita export timed out after {timeout_seconds} seconds."
        ) from exc
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
    timeout_seconds: int = 120,
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
                timeout_seconds=timeout_seconds,
            )
            exported.append(output_path)
    return exported


def batch_export_kra_report(
    template_path: str | Path,
    mappings: list[TextLayerMapping],
    variable_sets: list[dict[str, str]],
    output_dir: str | Path,
    *,
    name_pattern: str = "thumb_{episode}",
    krita_executable: str | None = None,
    timeout_seconds: int = 120,
) -> BatchExportReport:
    """Batch export a .kra template and keep per-row success/failure details."""
    from core.renderer import _substitute

    output_dir = Path(output_dir)
    exported: list[Path] = []
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="thumbforge_kra_") as tmp:
        tmp_dir = Path(tmp)
        for index, variables in enumerate(variable_sets, start=1):
            try:
                modified_kra = tmp_dir / f"thumb_{index}.kra"
                write_variable_kra(template_path, modified_kra, mappings, variables)
                output_path = output_dir / f"{_substitute(name_pattern, variables)}.png"
                export_kra_to_image(
                    modified_kra,
                    output_path,
                    krita_executable=krita_executable,
                    timeout_seconds=timeout_seconds,
                )
                exported.append(output_path)
            except Exception as exc:
                failures.append(f"Row {index}: {exc}")
    return BatchExportReport(exported=exported, failures=failures)


def export_kra_jobs_with_script(
    template_path: str | Path,
    mappings: list[TextLayerMapping],
    jobs: list[tuple[dict[str, str], str | Path]],
    *,
    krita_executable: str | None = None,
    timeout_seconds: int = 300,
) -> BatchExportReport:
    """Apply variables through Krita's Python API and export each job."""
    executable = krita_executable or find_krita_runner() or find_krita_executable()
    if not executable:
        raise KritaExportError("Krita runner/executable not found.")

    exported: list[Path] = []
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="thumbforge_krita_") as tmp:
        tmp_dir = Path(tmp)
        manifest_jobs = []
        for index, (variables, output_path) in enumerate(jobs, start=1):
            try:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                manifest_jobs.append(
                    {
                        "index": index,
                        "template": str(template_path),
                        "output": str(output_path),
                        "variables": variables,
                    }
                )
                exported.append(output_path)
            except Exception as exc:
                failures.append(f"Row {index}: {exc}")

        if not manifest_jobs:
            return BatchExportReport(exported=[], failures=failures)

        manifest_path = tmp_dir / "jobs.json"
        log_path = tmp_dir / "krita_export.log"
        manifest_path.write_text(
            json.dumps(
                {
                    "jobs": manifest_jobs,
                    "mappings": [
                        {
                            "layer_name": mapping.layer_name,
                            "variable_name": mapping.variable_name,
                            "source_text": mapping.source_text,
                        }
                        for mapping in mappings
                    ],
                    "log": str(log_path),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        if Path(executable).name.lower().startswith("kritarunner"):
            module_name = "thumbforge_krita_export_runner"
            script_path = _write_kritarunner_module(module_name)
            command = [
                executable,
                "-s",
                module_name,
                "-f",
                "run",
                str(manifest_path),
            ]
        else:
            script_path = tmp_dir / "thumbforge_krita_export.py"
            script_path.write_text(
                _krita_export_script(),
                encoding="utf-8",
            )
            command = [executable, "--nosplash", f"-scriptFile={script_path}"]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise KritaExportError(
                f"Krita scripted export timed out after {timeout_seconds} seconds."
            ) from exc

        log_text = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or log_text.strip()
            raise KritaExportError(f"Krita scripted export failed: {detail}")

        missing = [path for path in exported if not path.exists()]
        if missing:
            detail = log_text.strip() or "Krita did not create all expected files."
            for path in missing:
                failures.append(f"{path.name}: missing output. {detail}")
            exported = [path for path in exported if path.exists()]

    return BatchExportReport(exported=exported, failures=failures)


def batch_export_kra_script_report(
    template_path: str | Path,
    mappings: list[TextLayerMapping],
    variable_sets: list[dict[str, str]],
    output_dir: str | Path,
    *,
    name_pattern: str = "thumb_{episode}",
    krita_executable: str | None = None,
    timeout_seconds: int = 300,
) -> BatchExportReport:
    """Batch export .kra rows through Krita's Python API in one process."""
    from core.renderer import _substitute

    output_dir = Path(output_dir)
    jobs = [
        (variables, output_dir / f"{_substitute(name_pattern, variables)}.png")
        for variables in variable_sets
    ]
    return export_kra_jobs_with_script(
        template_path,
        mappings,
        jobs,
        krita_executable=krita_executable,
        timeout_seconds=timeout_seconds,
    )


def _write_kritarunner_module(module_name: str) -> Path:
    appdata = Path(os.environ.get("APPDATA", tempfile.gettempdir()))
    module_dir = appdata / "kritarunner" / "krita" / "pykrita"
    module_dir.mkdir(parents=True, exist_ok=True)
    module_path = module_dir / f"{module_name}.py"
    module_path.write_text(_krita_export_script(), encoding="utf-8")
    return module_path


def _krita_export_script() -> str:
    return r'''
import html
import json
import re
import sys
import traceback
from collections import defaultdict

from krita import Krita, InfoObject
from PyQt5.QtWidgets import QApplication


def write_log(message):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write(message + "\\n")
    except Exception:
        pass


LOG_PATH = ""
TEXT_RE = re.compile(r"(<text\b[^>]*>)(.*?)(</text>)", re.IGNORECASE | re.DOTALL)
TSPAN_RE = re.compile(r"(<tspan\b[^>]*>)(.*?)(</tspan>)", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")


def plain_text(svg_fragment):
    spans = TSPAN_RE.findall(svg_fragment)
    if spans:
        return "".join(html.unescape(TAG_RE.sub("", span[1])) for span in spans)
    return html.unescape(TAG_RE.sub("", svg_fragment))


def replace_tspan_text(text_body, value):
    escaped = html.escape(str(value), quote=False)
    replaced = False

    def replace_match(match):
        nonlocal replaced
        if replaced:
            return match.group(1) + match.group(3)
        replaced = True
        return match.group(1) + escaped + match.group(3)

    updated = TSPAN_RE.sub(replace_match, text_body)
    if replaced:
        return updated
    return escaped


def apply_mapping_to_svg(svg, source_text, value):
    target = str(source_text or "")
    consumed = False

    def replace_text(match):
        nonlocal consumed
        if consumed:
            return match.group(0)
        body = match.group(2)
        if target and plain_text(body) != target:
            return match.group(0)
        consumed = True
        return match.group(1) + replace_tspan_text(body, value) + match.group(3)

    updated = TEXT_RE.sub(replace_text, svg)
    if consumed:
        return updated, True
    return svg, False


def update_vector_layer(doc, layer_name, mappings, variables):
    node = doc.nodeByName(layer_name)
    if node is None:
        raise RuntimeError("Layer not found: " + layer_name)
    if str(node.type()).lower() != "vectorlayer":
        raise RuntimeError("Layer is not a vector layer: " + layer_name)

    svg = node.toSvg()
    matched_any = False
    for mapping in mappings:
        variable_name = mapping.get("variable_name", "")
        value = variables.get(variable_name, "")
        svg, matched = apply_mapping_to_svg(svg, mapping.get("source_text", ""), value)
        matched_any = matched_any or matched

    if not matched_any:
        raise RuntimeError("No matching text shape found in layer: " + layer_name)

    for shape in list(node.shapes()):
        shape.setVisible(False)
        shape.update()
    added = node.addShapesFromSvg(svg)
    if not added:
        raise RuntimeError("Krita did not add replacement text shapes for layer: " + layer_name)


def apply_variables(doc, mappings, variables):
    mappings_by_layer = defaultdict(list)
    for mapping in mappings:
        mappings_by_layer[mapping.get("layer_name", "")].append(mapping)
    for layer_name, layer_mappings in mappings_by_layer.items():
        update_vector_layer(doc, layer_name, layer_mappings, variables)


def run(*args):
    global LOG_PATH
    argv = args[0] if len(args) == 1 and isinstance(args[0], list) else list(args)
    if not argv:
        raise RuntimeError("No Thumbforge manifest path supplied.")
    manifest_path = argv[0]
    with open(manifest_path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    LOG_PATH = manifest.get("log", "")
    app = Krita.instance()
    mappings = manifest.get("mappings", [])

    try:
        for job in manifest["jobs"]:
            write_log("Opening " + job["template"])
            doc = app.openDocument(job["template"])
            if doc is None:
                raise RuntimeError("Krita could not open " + job["template"])
            try:
                doc.waitForDone()
            except Exception:
                pass
            apply_variables(doc, mappings, job.get("variables", {}))
            try:
                doc.refreshProjection()
                doc.waitForDone()
            except Exception:
                pass
            write_log("Exporting " + job["output"])
            ok = doc.exportImage(job["output"], InfoObject())
            try:
                doc.waitForDone()
            except Exception:
                pass
            if ok is False:
                raise RuntimeError("Krita exportImage returned false for " + job["output"])
            doc.close()
        write_log("Done")
    except Exception:
        write_log(traceback.format_exc())
        raise
    finally:
        qt_app = QApplication.instance()
        if qt_app is not None:
            qt_app.quit()
        else:
            sys.exit(0)


def __main__(*args):
    return run(*args)
'''
