"""Thumbnail rendering engine.

Composes layers from a .kra template with variable substitution
and exports to PNG. Does NOT require Krita at runtime.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Default YouTube thumbnail size
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720


@dataclass
class TextOverlay:
    """A text element to render on the thumbnail."""
    text: str
    x: int = 0
    y: int = 0
    font_path: str = ""
    font_size: int = 72
    color: str = "#ffffff"
    anchor: str = "lt"  # Pillow anchor: lt, mt, rt, mm, etc.
    max_width: int | None = None


@dataclass
class TemplateConfig:
    """Describes how to compose a thumbnail from layers + text overlays."""
    background_path: str = ""  # static background image
    overlays: list[TextOverlay] = field(default_factory=list)
    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT


def render_thumbnail(
    config: TemplateConfig,
    variables: dict[str, str] | None = None,
    background_image: Image.Image | None = None,
) -> Image.Image:
    """Render a thumbnail from a template config and variables.

    Args:
        config: Template configuration with background and text overlays.
        variables: Dict of placeholder -> value (e.g. {"episode": "42"}).
        background_image: Optional pre-loaded background (overrides config.background_path).

    Returns:
        Composed PIL Image ready for saving.
    """
    variables = variables or {}

    # Create or load background
    if background_image is not None:
        canvas = background_image.copy().convert("RGBA")
        canvas = canvas.resize((config.width, config.height), Image.Resampling.LANCZOS)
    elif config.background_path and Path(config.background_path).is_file():
        canvas = Image.open(config.background_path).convert("RGBA")
        canvas = canvas.resize((config.width, config.height), Image.Resampling.LANCZOS)
    else:
        canvas = Image.new("RGBA", (config.width, config.height), (30, 30, 30, 255))

    draw = ImageDraw.Draw(canvas)

    for overlay in config.overlays:
        text = _substitute(overlay.text, variables)
        font = _load_font(overlay.font_path, overlay.font_size)
        draw.text(
            (overlay.x, overlay.y),
            text,
            fill=overlay.color,
            font=font,
            anchor=overlay.anchor,
        )

    return canvas


def export_thumbnail(
    image: Image.Image,
    output_path: str | Path,
    *,
    format: str = "PNG",
) -> None:
    """Save the rendered thumbnail to disk."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(str(output_path), format=format)
    logger.info("Exported thumbnail: %s", output_path)


def batch_export(
    config: TemplateConfig,
    variable_sets: list[dict[str, str]],
    output_dir: str | Path,
    *,
    name_pattern: str = "thumb_{episode}",
    background_image: Image.Image | None = None,
) -> list[Path]:
    """Render and export thumbnails for each variable set.

    Args:
        config: Template configuration.
        variable_sets: List of variable dicts, one per thumbnail.
        output_dir: Directory to write PNGs.
        name_pattern: Filename pattern with {placeholders}.
        background_image: Optional shared background.

    Returns:
        List of exported file paths.
    """
    output_dir = Path(output_dir)
    exported: list[Path] = []

    for variables in variable_sets:
        image = render_thumbnail(config, variables, background_image)
        filename = _substitute(name_pattern, variables) + ".png"
        out_path = output_dir / filename
        export_thumbnail(image, out_path)
        exported.append(out_path)

    return exported


def _substitute(text: str, variables: dict[str, str]) -> str:
    """Replace {key} placeholders with values from variables dict."""
    result = text
    for key, value in variables.items():
        result = result.replace(f"{{{key}}}", str(value))
    return result


def _load_font(font_path: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a font, falling back to Pillow's default."""
    if font_path and Path(font_path).is_file():
        try:
            return ImageFont.truetype(font_path, size)
        except (OSError, ValueError):
            logger.warning("Failed to load font %s, using default", font_path)
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def parse_font_size(value: str, default: int = 72) -> int:
    """Parse CSS/Krita font-size strings into an integer pixel size."""
    match = re.search(r"\d+(?:\.\d+)?", value or "")
    if not match:
        return default
    return max(1, int(float(match.group(0))))
