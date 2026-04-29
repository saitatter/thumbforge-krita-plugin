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
    file_format: str = "png"
    compression: int = 6
    quality: int = 90
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


def export_extension(settings: PngExportSettings) -> str:
    file_format = (settings.file_format or "png").lower()
    if file_format in {"jpg", "jpeg"}:
        return "jpg"
    if file_format == "webp":
        return "webp"
    return "png"


def ensure_export_path(path: str, settings: PngExportSettings) -> str:
    if os.path.splitext(path)[1]:
        return path
    return path + "." + export_extension(settings)


def ensure_png_path(path: str) -> str:
    return ensure_export_path(path, PngExportSettings())


def substitute(text: str, variables: dict[str, str]) -> str:
    result = text
    for key, value in variables.items():
        result = result.replace("{" + key + "}", str(value))
    return result
