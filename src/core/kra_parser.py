"""Krita .kra template parser.

A .kra file is a ZIP archive containing:
- maindoc.xml: document structure (layers, sizes, offsets)
- mergedimage.png: flattened preview
- <layer_name>/: directories with per-layer pixel data
"""
from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

from lxml import etree
from PIL import Image


@dataclass
class KraLayer:
    """A single layer extracted from a .kra template."""
    name: str
    visible: bool
    opacity: int  # 0-255
    x: int
    y: int
    node_type: str  # "paintlayer", "grouplayer", "shapelayer" (vector/text)
    uuid: str
    filename: str  # internal zip path prefix
    compositeop: str = "normal"
    children: list[KraLayer] = field(default_factory=list)


@dataclass
class KraTemplate:
    """Parsed .kra template with layer tree and metadata."""
    width: int
    height: int
    name: str
    layers: list[KraLayer]
    merged_preview: Image.Image | None
    _zip_path: str = ""

    @classmethod
    def load(cls, path: str | Path) -> KraTemplate:
        """Parse a .kra file and return a KraTemplate."""
        path = str(path)
        with zipfile.ZipFile(path, "r") as zf:
            doc_xml = etree.parse(zf.open("maindoc.xml"))
            root = doc_xml.getroot()

            ns = {"krita": root.nsmap.get(None, "")}
            image_el = root.find(".//IMAGE", namespaces=None)
            if image_el is None:
                # Fallback: look without namespace
                for el in root.iter():
                    if el.tag.endswith("IMAGE") or el.tag == "IMAGE":
                        image_el = el
                        break
            if image_el is None:
                raise ValueError(f"No IMAGE element found in {path}")

            width = int(image_el.get("width", 1280))
            height = int(image_el.get("height", 720))
            name = image_el.get("name", Path(path).stem)

            layers = _parse_layer_tree(image_el)

            # Load merged preview if available
            preview = None
            if "mergedimage.png" in zf.namelist():
                preview = Image.open(BytesIO(zf.read("mergedimage.png")))

        return cls(
            width=width,
            height=height,
            name=name,
            layers=layers,
            merged_preview=preview,
            _zip_path=path,
        )


def _parse_layer_tree(parent_el) -> list[KraLayer]:
    """Recursively parse layer elements from the XML tree."""
    layers: list[KraLayer] = []
    # Krita XML uses <layers><layer .../></layers> structure
    layers_el = None
    for child in parent_el:
        if child.tag == "layers" or child.tag.endswith("}layers"):
            layers_el = child
            break

    if layers_el is None:
        return layers

    for layer_el in layers_el:
        if not (layer_el.tag == "layer" or layer_el.tag.endswith("}layer")):
            continue

        children = _parse_layer_tree(layer_el)
        layer = KraLayer(
            name=layer_el.get("name", ""),
            visible=layer_el.get("visible", "1") == "1",
            opacity=int(layer_el.get("opacity", "255")),
            x=int(layer_el.get("x", "0")),
            y=int(layer_el.get("y", "0")),
            node_type=layer_el.get("nodetype", "paintlayer"),
            uuid=layer_el.get("uuid", ""),
            filename=layer_el.get("filename", ""),
            compositeop=layer_el.get("compositeop", "normal"),
            children=children,
        )
        layers.append(layer)

    return layers


def list_text_layers(template: KraTemplate) -> list[KraLayer]:
    """Return all text/vector layers (shapelayer) from the template."""
    result: list[KraLayer] = []
    _collect_layers(template.layers, result, node_type="shapelayer")
    return result


def list_all_layers_flat(template: KraTemplate) -> list[KraLayer]:
    """Return all layers flattened."""
    result: list[KraLayer] = []
    _collect_layers(template.layers, result)
    return result


def _collect_layers(
    layers: list[KraLayer],
    result: list[KraLayer],
    node_type: str | None = None,
) -> None:
    for layer in layers:
        if node_type is None or layer.node_type == node_type:
            result.append(layer)
        _collect_layers(layer.children, result, node_type)
