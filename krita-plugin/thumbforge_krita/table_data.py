"""Helpers for spreadsheet-like table data."""

from __future__ import annotations

import csv
from io import StringIO


def parse_clipboard_table(text: str, existing_columns: list[str]) -> tuple[list[str], list[dict[str, str]]]:
    rows = _read_rows(text)
    if not rows:
        return existing_columns, []
    first = [cell.strip() for cell in rows[0]]
    has_header = any(cell in existing_columns for cell in first)
    if has_header:
        columns = first
        data_rows = rows[1:]
    else:
        columns = existing_columns
        data_rows = rows
    parsed = []
    for row in data_rows:
        parsed.append({column: row[index] if index < len(row) else "" for index, column in enumerate(columns)})
    return columns, parsed


def _read_rows(text: str) -> list[list[str]]:
    sample = text.strip()
    if not sample:
        return []
    delimiter = "\t" if "\t" in sample else ","
    reader = csv.reader(StringIO(sample), delimiter=delimiter)
    return [row for row in reader if row]
