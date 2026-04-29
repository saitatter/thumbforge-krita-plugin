"""Tests for core.csv_io."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests import test_support as _test_support  # noqa: F401

from core.csv_io import read_variable_csv, write_variable_csv


class CsvIoTests(unittest.TestCase):
    def test_write_and_read_variable_csv_round_trips_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "variables.csv"
            write_variable_csv(
                path,
                ["episode", "text_1"],
                [
                    {"episode": "1", "text_1": "First"},
                    {"episode": "2", "text_1": "Second"},
                ],
            )

            columns, rows = read_variable_csv(path)

            self.assertEqual(columns, ["episode", "text_1"])
            self.assertEqual(rows[1]["text_1"], "Second")

