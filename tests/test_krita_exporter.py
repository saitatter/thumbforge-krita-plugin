"""Tests for core.krita_exporter."""
from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from tests import test_support as _test_support  # noqa: F401

from core.krita_exporter import (
    batch_export_kra,
    batch_export_kra_report,
    batch_export_kra_script_report,
    export_kra_jobs_with_script,
    export_kra_to_image,
)
from core.project import TextLayerMapping


class KritaExporterTests(unittest.TestCase):
    @patch("core.krita_exporter.subprocess.run")
    def test_export_kra_to_image_invokes_krita_cli(self, run):
        run.return_value.returncode = 0
        run.return_value.stderr = ""
        run.return_value.stdout = ""

        export_kra_to_image("template.kra", "out.png", krita_executable="krita.exe")

        args = run.call_args.args[0]
        self.assertEqual(args[:4], ["krita.exe", "--nosplash", "--export", "--export-filename"])
        self.assertEqual(args[4], "out.png")
        self.assertEqual(args[5], "template.kra")
        self.assertEqual(run.call_args.kwargs["timeout"], 120)

    @patch("core.krita_exporter.subprocess.run")
    def test_export_kra_to_image_times_out(self, run):
        import subprocess

        from core.krita_exporter import KritaExportError

        run.side_effect = subprocess.TimeoutExpired("krita.exe", 1)

        with self.assertRaises(KritaExportError) as raised:
            export_kra_to_image(
                "template.kra",
                "out.png",
                krita_executable="krita.exe",
                timeout_seconds=1,
            )

        self.assertIn("timed out", str(raised.exception))

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

    @patch("core.krita_exporter.export_kra_to_image")
    def test_batch_export_kra_report_tracks_failures(self, export):
        export.side_effect = RuntimeError("boom")
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "template.kra"
            with zipfile.ZipFile(template, "w") as zf:
                zf.writestr("maindoc.xml", "<DOC />")

            report = batch_export_kra_report(
                template,
                [],
                [{"episode": "1"}],
                Path(tmp) / "out",
                krita_executable="krita.exe",
            )

            self.assertEqual(report.succeeded, 0)
            self.assertEqual(report.failed, 1)
            self.assertIn("Row 1", report.failures[0])

    @patch("core.krita_exporter.subprocess.run")
    def test_export_kra_jobs_with_script_invokes_krita_script(self, run):
        run.return_value.returncode = 0
        run.return_value.stderr = ""
        run.return_value.stdout = ""
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "template.kra"
            output = Path(tmp) / "out.png"
            with zipfile.ZipFile(template, "w") as zf:
                zf.writestr("maindoc.xml", "<DOC />")
                zf.writestr("layers/text1/content.svg", "<svg><text>Old</text></svg>")

            report = export_kra_jobs_with_script(
                template,
                [
                    TextLayerMapping(
                        layer_name="Text 1",
                        variable_name="title",
                        svg_path="layers/text1/content.svg",
                        source_text="Old",
                    )
                ],
                [({"title": "New"}, output)],
                krita_executable="kritarunner.exe",
            )

            args = run.call_args.args[0]
            self.assertEqual(args[0], "kritarunner.exe")
            self.assertIn("-s", args)
            script_arg = args[args.index("-s") + 1]
            self.assertFalse(str(script_arg).endswith(".py"))
            self.assertEqual(run.call_args.kwargs["timeout"], 300)
            self.assertEqual(report.succeeded, 0)
            self.assertEqual(report.failed, 1)

    @patch("core.krita_exporter.export_kra_jobs_with_script")
    def test_batch_export_kra_script_report_builds_output_names(self, export):
        from core.krita_exporter import BatchExportReport

        export.return_value = BatchExportReport(exported=[Path("out/ep_1.png")], failures=[])

        report = batch_export_kra_script_report(
            "template.kra",
            [],
            [{"episode": "1"}],
            "out",
            name_pattern="ep_{episode}",
            krita_executable="krita.exe",
        )

        self.assertEqual(report.succeeded, 1)
        jobs = export.call_args.args[2]
        self.assertEqual(jobs[0][1], Path("out") / "ep_1.png")
