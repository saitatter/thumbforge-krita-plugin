"""Tests for the bundled Krita plugin helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "krita-plugin"


def _load_text_replace_module():
    path = PLUGIN_ROOT / "thumbforge_krita" / "text_replace.py"
    spec = importlib.util.spec_from_file_location("thumbforge_krita_text_replace", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
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
