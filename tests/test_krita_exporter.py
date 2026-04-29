"""Tests for core.krita_exporter."""
from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from tests import test_support as _test_support  # noqa: F401

from core.krita_exporter import batch_export_kra, export_kra_to_image
from core.project import TextLayerMapping


class KritaExporterTests(unittest.TestCase):
    @patch("core.krita_exporter.subprocess.run")
    def test_export_kra_to_image_invokes_krita_cli(self, run):
        run.return_value.returncode = 0
        run.return_value.stderr = ""
        run.return_value.stdout = ""

        export_kra_to_image("template.kra", "out.png", krita_executable="krita.exe")

        args = run.call_args.args[0]
        self.assertEqual(args[:3], ["krita.exe", "--export", "--export-filename"])
        self.assertEqual(args[3], "out.png")
        self.assertEqual(args[4], "template.kra")

    @patch("core.krita_exporter.export_kra_to_image")
    def test_batch_export_kra_writes_modified_templates(self, export):
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "template.kra"
            with zipfile.ZipFile(template, "w") as zf:
                zf.writestr("maindoc.xml", "<DOC />")
                zf.writestr(
                    "layers/text1/content.svg",
                    "<svg><text>Old</text></svg>",
                )

            exported = batch_export_kra(
                template,
                [
                    TextLayerMapping(
                        layer_name="Text 1",
                        variable_name="title",
                        svg_path="layers/text1/content.svg",
                        source_text="Old",
                    )
                ],
                [{"episode": "1", "title": "New"}],
                Path(tmp) / "out",
                name_pattern="ep_{episode}",
                krita_executable="krita.exe",
            )

            self.assertEqual(exported, [Path(tmp) / "out" / "ep_1.png"])
            self.assertEqual(export.call_count, 1)

