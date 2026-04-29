"""Tests for core.renderer."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests import test_support as _test_support  # noqa: F401

from core.renderer import (
    TemplateConfig,
    TextOverlay,
    batch_export,
    render_thumbnail,
    export_thumbnail,
)


class RendererTests(unittest.TestCase):
    def test_render_thumbnail_creates_image_with_correct_size(self):
        config = TemplateConfig(width=1280, height=720)
        image = render_thumbnail(config)
        self.assertEqual(image.size, (1280, 720))

    def test_render_thumbnail_substitutes_variables(self):
        overlay = TextOverlay(text="EP {episode}", x=100, y=100, font_size=48)
        config = TemplateConfig(width=1280, height=720, overlays=[overlay])
        image = render_thumbnail(config, {"episode": "42"})
        self.assertIsNotNone(image)

    def test_export_thumbnail_creates_file(self):
        config = TemplateConfig(width=640, height=360)
        image = render_thumbnail(config)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "test.png"
            export_thumbnail(image, out)
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 0)

    def test_batch_export_creates_multiple_files(self):
        config = TemplateConfig(width=640, height=360)
        variable_sets = [
            {"episode": "1"},
            {"episode": "2"},
            {"episode": "3"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            exported = batch_export(config, variable_sets, tmp)
            self.assertEqual(len(exported), 3)
            for p in exported:
                self.assertTrue(p.exists())


class ProjectTests(unittest.TestCase):
    def test_project_save_and_load_round_trip(self):
        from core.project import ThumbforgeProject, TextLayerMapping

        project = ThumbforgeProject(
            name="Test Series",
            kra_template_path="template.kra",
            variable_columns=["episode", "title"],
            text_layer_mappings=[
                TextLayerMapping(
                    layer_name="Text 1",
                    variable_name="title",
                    svg_path="layers/text1/content.svg",
                    source_text="Title",
                )
            ],
            rows=[
                {"episode": "1", "title": "Pilot"},
                {"episode": "2", "title": "Second"},
            ],
            name_pattern="thumb_ep{episode}",
        )
        project.template_config.width = 1920
        project.template_config.height = 1080
        project.template_config.overlays.append(
            TextOverlay(text="EP {episode}", x=50, y=50, font_size=72)
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.tfproj"
            project.save(path)
            loaded = ThumbforgeProject.load(path)

            self.assertEqual(loaded.name, "Test Series")
            self.assertEqual(loaded.kra_template_path, "template.kra")
            self.assertEqual(loaded.template_config.width, 1920)
            self.assertEqual(len(loaded.text_layer_mappings), 1)
            self.assertEqual(loaded.text_layer_mappings[0].variable_name, "title")
            self.assertEqual(len(loaded.rows), 2)
            self.assertEqual(loaded.rows[0]["title"], "Pilot")
            self.assertEqual(len(loaded.template_config.overlays), 1)
            self.assertEqual(loaded.template_config.overlays[0].text, "EP {episode}")
