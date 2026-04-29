"""Tests for core.kra_parser."""
from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from tests import test_support as _test_support  # noqa: F401

from core.kra_parser import KraTemplate, list_text_layer_details


class KraParserTests(unittest.TestCase):
    def test_list_text_layer_details_extracts_svg_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            kra_path = Path(tmp) / "template.kra"
            with zipfile.ZipFile(kra_path, "w") as zf:
                zf.writestr(
                    "maindoc.xml",
                    """
                    <DOC>
                      <IMAGE name="Template" width="1280" height="720">
                        <layers>
                          <layer name="Text 1" nodetype="shapelayer" filename="layers/text1" uuid="abc" />
                        </layers>
                      </IMAGE>
                    </DOC>
                    """,
                )
                zf.writestr(
                    "layers/text1/content.svg",
                    """
                    <svg xmlns="http://www.w3.org/2000/svg">
                      <text x="100" y="200" style="font-size:72px;fill:#ffcc00">Hello</text>
                    </svg>
                    """,
                )

            template = KraTemplate.load(kra_path)
            details = list_text_layer_details(template)

            self.assertEqual(len(details), 1)
            self.assertEqual(details[0].layer.name, "Text 1")
            self.assertEqual(details[0].text, "Hello")
            self.assertEqual(details[0].x, 100)
            self.assertEqual(details[0].y, 200)
            self.assertEqual(details[0].font_size, "72px")
            self.assertEqual(details[0].fill, "#ffcc00")

