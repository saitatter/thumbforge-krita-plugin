"""Tests for core.validation."""
from __future__ import annotations

import unittest

from tests import test_support as _test_support  # noqa: F401

from core.project import TextLayerMapping
from core.validation import validate_youtube_template


class ValidationTests(unittest.TestCase):
    def test_validate_youtube_template_accepts_standard_template(self):
        warnings = validate_youtube_template(
            1280,
            720,
            [TextLayerMapping(layer_name="Text 1", variable_name="text_1")],
        )

        self.assertEqual(warnings, [])

    def test_validate_youtube_template_warns_about_size_and_missing_text(self):
        warnings = validate_youtube_template(1000, 700, [])

        self.assertEqual(len(warnings), 3)
        self.assertIn("expected 1280x720", warnings[0])

