"""Tests for core.kra_writer."""
from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from lxml import etree

from tests import test_support as _test_support  # noqa: F401

from core.kra_writer import write_variable_kra
from core.project import TextLayerMapping


class KraWriterTests(unittest.TestCase):
    def test_write_variable_kra_replaces_mapped_svg_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.kra"
            output = Path(tmp) / "output.kra"
            svg_path = "layers/text1/content.svg"
            with zipfile.ZipFile(source, "w") as zf:
                zf.writestr("maindoc.xml", "<DOC />")
                zf.writestr("mergedimage.png", b"stale")
                zf.writestr("preview.png", b"stale")
                zf.writestr(
                    svg_path,
                    """
                    <svg xmlns="http://www.w3.org/2000/svg">
                      <text x="10" y="20"><tspan>Old Title</tspan></text>
                    </svg>
                    """,
                )

            write_variable_kra(
                source,
                output,
                [
                    TextLayerMapping(
                        layer_name="Text 1",
                        variable_name="title",
                        svg_path=svg_path,
                        source_text="Old Title",
                    )
                ],
                {"title": "New Title"},
            )

            with zipfile.ZipFile(output, "r") as zf:
                self.assertNotIn("mergedimage.png", zf.namelist())
                self.assertNotIn("preview.png", zf.namelist())
                root = etree.fromstring(zf.read(svg_path))
                text = "".join(root.xpath(".//*[local-name()='text']")[0].itertext()).strip()

            self.assertEqual(text, "New Title")

    def test_write_variable_kra_preserves_tspan_structure_and_style(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.kra"
            output = Path(tmp) / "output.kra"
            svg_path = "layers/text1/content.svg"
            with zipfile.ZipFile(source, "w") as zf:
                zf.writestr("maindoc.xml", "<DOC />")
                zf.writestr(
                    svg_path,
                    """
                    <svg xmlns="http://www.w3.org/2000/svg">
                      <text x="10" y="20">
                        <tspan style="font-weight:700">Old</tspan>
                        <tspan style="fill:#fff"> Title</tspan>
                      </text>
                    </svg>
                    """,
                )

            write_variable_kra(
                source,
                output,
                [
                    TextLayerMapping(
                        layer_name="Text 1",
                        variable_name="title",
                        svg_path=svg_path,
                        source_text="Old Title",
                    )
                ],
                {"title": "New Title"},
            )

            with zipfile.ZipFile(output, "r") as zf:
                root = etree.fromstring(zf.read(svg_path))
                tspans = root.xpath(".//*[local-name()='tspan']")

            self.assertEqual(len(tspans), 2)
            self.assertEqual(tspans[0].text, "New Title")
            self.assertEqual(tspans[0].get("style"), "font-weight:700")
            self.assertEqual(tspans[1].text or "", "")
