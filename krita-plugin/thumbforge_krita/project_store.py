"""Persist Thumbforge setup data inside Krita document annotations."""

from __future__ import annotations

import json
from dataclasses import asdict

from .models import PngExportSettings, TextMapping


ANNOTATION_KEY = "thumbforge-project"
ANNOTATION_DESCRIPTION = "Thumbforge Project"
PROJECT_VERSION = 1


def serialize_project(
    *,
    mappings: list[TextMapping],
    columns: list[str],
    rows: list[dict[str, str]],
    name_pattern: str,
    png_settings: PngExportSettings,
) -> str:
    data = {
        "version": PROJECT_VERSION,
        "mappings": [asdict(mapping) for mapping in mappings],
        "columns": columns,
        "rows": rows,
        "name_pattern": name_pattern,
        "png_settings": asdict(png_settings),
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def deserialize_project(payload: str) -> dict:
    data = json.loads(payload)
    mappings = [TextMapping(**item) for item in data.get("mappings", [])]
    settings = PngExportSettings(**data.get("png_settings", {}))
    return {
        "mappings": mappings,
        "columns": list(data.get("columns", ["episode"])),
        "rows": list(data.get("rows", [])),
        "name_pattern": data.get("name_pattern", "thumb_{episode}"),
        "png_settings": settings,
    }


def save_project_to_document(
    doc,
    *,
    mappings: list[TextMapping],
    columns: list[str],
    rows: list[dict[str, str]],
    name_pattern: str,
    png_settings: PngExportSettings,
) -> None:
    from PyQt5.QtCore import QByteArray

    payload = serialize_project(
        mappings=mappings,
        columns=columns,
        rows=rows,
        name_pattern=name_pattern,
        png_settings=png_settings,
    )
    doc.setAnnotation(
        ANNOTATION_KEY,
        ANNOTATION_DESCRIPTION,
        QByteArray(payload.encode("utf-8")),
    )


def load_project_from_document(doc) -> dict | None:
    if ANNOTATION_KEY not in doc.annotationTypes():
        return None
    payload = bytes(doc.annotation(ANNOTATION_KEY)).decode("utf-8")
    return deserialize_project(payload)
