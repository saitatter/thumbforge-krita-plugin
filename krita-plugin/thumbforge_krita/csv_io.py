"""Small CSV helpers bundled with the Krita plugin."""

from __future__ import annotations

import csv


def read_variable_csv(path: str) -> tuple[list[str], list[dict[str, str]]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        rows = [{column: row.get(column, "") for column in columns} for row in reader]
    return columns, rows


def write_variable_csv(path: str, columns: list[str], rows: list[dict[str, str]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
