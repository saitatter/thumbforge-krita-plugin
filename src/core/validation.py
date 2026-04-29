"""Validation helpers for thumbnail templates."""
from __future__ import annotations

from core.project import TextLayerMapping


def validate_youtube_template(
    width: int,
    height: int,
    mappings: list[TextLayerMapping],
) -> list[str]:
    """Return warnings for common YouTube thumbnail template issues."""
    warnings: list[str] = []
    if (width, height) != (1280, 720):
        warnings.append(f"Template is {width}x{height}, expected 1280x720.")
    if width * 9 != height * 16:
        warnings.append("Template aspect ratio is not 16:9.")
    if not mappings:
        warnings.append("No editable text layers were detected.")
    return warnings
