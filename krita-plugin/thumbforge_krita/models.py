"""Small data models shared by the Thumbforge Krita plugin."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class TextMapping:
    layer_name: str
    source_text: str
    variable_name: str
    shape_name: str = ""


@dataclass
class PngExportSettings:
    compression: int = 6
    alpha: bool = True
    force_srgb: bool = True
    save_icc: bool = True
    interlaced: bool = False


@dataclass
class ExportReport:
    exported: list[str]
    failures: list[str]

    @property
    def succeeded(self) -> int:
        return len(self.exported)

    @property
    def failed(self) -> int:
        return len(self.failures)


def ensure_png_path(path: str) -> str:
    if os.path.splitext(path)[1]:
        return path
    return path + ".png"


def substitute(text: str, variables: dict[str, str]) -> str:
    result = text
    for key, value in variables.items():
        result = result.replace("{" + key + "}", str(value))
    return result
