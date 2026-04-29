"""Utilities for writing variable values into Krita .kra templates."""
from __future__ import annotations

import zipfile
from pathlib import Path

from lxml import etree

from core.project import TextLayerMapping


def write_variable_kra(
    template_path: str | Path,
    output_path: str | Path,
    mappings: list[TextLayerMapping],
    variables: dict[str, str],
) -> None:
    """Write a copy of a .kra with mapped text layers replaced by variables."""
    template_path = Path(template_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    replacements_by_svg: dict[str, list[TextLayerMapping]] = {}
    for mapping in mappings:
        if mapping.svg_path and mapping.variable_name in variables:
            replacements_by_svg.setdefault(mapping.svg_path, []).append(mapping)

    with zipfile.ZipFile(template_path, "r") as source:
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as target:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename in replacements_by_svg:
                    data = _replace_svg_text(
                        data,
                        replacements_by_svg[info.filename],
                        variables,
                    )
                target.writestr(info, data)


def _replace_svg_text(
    svg_bytes: bytes,
    mappings: list[TextLayerMapping],
    variables: dict[str, str],
) -> bytes:
    try:
        root = etree.fromstring(svg_bytes)
    except etree.XMLSyntaxError:
        return svg_bytes

    text_elements = root.xpath(".//*[local-name()='text']")
    used: set[int] = set()
    for mapping in mappings:
        value = variables.get(mapping.variable_name)
        if value is None:
            continue
        text_el = _find_text_element(text_elements, mapping.source_text, used)
        if text_el is None:
            continue
        used.add(id(text_el))
        _set_element_text(text_el, str(value))

    return etree.tostring(
        root,
        encoding="utf-8",
        xml_declaration=svg_bytes.lstrip().startswith(b"<?xml"),
    )


def _find_text_element(text_elements, source_text: str, used: set[int]):
    if source_text:
        for text_el in text_elements:
            if id(text_el) in used:
                continue
            if "".join(text_el.itertext()).strip() == source_text:
                return text_el
    for text_el in text_elements:
        if id(text_el) not in used:
            return text_el
    return None


def _set_element_text(text_el, value: str) -> None:
    """Replace text content while preserving Krita's SVG text structure."""
    tspans = text_el.xpath(".//*[local-name()='tspan']")
    if tspans:
        tspans[0].text = value
        tspans[0].tail = None
        for tspan in tspans[1:]:
            tspan.text = ""
            tspan.tail = None
        text_el.text = text_el.text if text_el.text and text_el.text.strip() else None
        return

    text_el.text = value
    for child in text_el:
        child.text = ""
        child.tail = None
