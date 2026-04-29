"""Tests for the bundled Krita plugin helpers."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "krita-plugin"


def _ensure_plugin_package():
    package = sys.modules.get("thumbforge_krita")
    if package is None:
        package = types.ModuleType("thumbforge_krita")
        package.__path__ = [str(PLUGIN_ROOT / "thumbforge_krita")]
        sys.modules["thumbforge_krita"] = package
    return package


def _load_text_replace_module():
    path = PLUGIN_ROOT / "thumbforge_krita" / "text_replace.py"
    spec = importlib.util.spec_from_file_location("thumbforge_krita_text_replace", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_plugin_module(name: str):
    _ensure_plugin_package()
    path = PLUGIN_ROOT / "thumbforge_krita" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"thumbforge_krita.{name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_plugin_descriptor_exists():
    desktop = (PLUGIN_ROOT / "thumbforge_krita.desktop").read_text(encoding="utf-8")

    assert "ServiceTypes=Krita/PythonPlugin" in desktop
    assert "X-KDE-Library=thumbforge_krita" in desktop


def test_replace_text_shape_preserves_tspan_attributes():
    text_replace = _load_text_replace_module()
    svg = (
        '<svg><text style="font-size:48;">'
        '<tspan x="0" fill="#fff">Old</tspan>'
        "</text></svg>"
    )

    updated, matched = text_replace.replace_text_shape(svg, "Old", "#42")

    assert matched is True
    assert '<tspan x="0" fill="#fff">#42</tspan>' in updated


def test_project_store_round_trips_setup():
    models = _load_plugin_module("models")
    project_store = _load_plugin_module("project_store")

    payload = project_store.serialize_project(
        mappings=[models.TextMapping("Layer", "Old", "title")],
        columns=["episode", "title"],
        rows=[{"episode": "1", "title": "New"}],
        name_pattern="ep_{episode}",
        png_settings=models.PngExportSettings(compression=4, alpha=False),
    )
    loaded = project_store.deserialize_project(payload)

    assert loaded["mappings"][0].layer_name == "Layer"
    assert loaded["columns"] == ["episode", "title"]
    assert loaded["rows"][0]["title"] == "New"
    assert loaded["name_pattern"] == "ep_{episode}"
    assert loaded["png_settings"].compression == 4
    assert loaded["png_settings"].alpha is False


def test_validation_sanitizes_and_detects_duplicate_outputs():
    models = _load_plugin_module("models")
    validation = _load_plugin_module("validation")

    path = validation.build_output_path("out", "bad:name_{episode}", {"episode": "1"})
    issues = validation.validate_export_plan(
        mappings=[models.TextMapping("Layer", "Old", "title")],
        columns=["episode", "title"],
        rows=[{"episode": "1", "title": "A"}, {"episode": "1", "title": "B"}],
        output_dir="out",
        name_pattern="thumb_{episode}",
    )

    assert path.endswith("bad_name_1.png")
    assert any("same filename" in issue.message for issue in issues)
