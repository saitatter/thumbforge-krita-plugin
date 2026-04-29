"""CSV import/export helpers for thumbnail variable rows."""
from __future__ import annotations

import csv
from pathlib import Path


def read_variable_csv(path: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read variable columns and rows from a CSV file."""
    path = Path(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        rows = [{column: row.get(column, "") for column in columns} for row in reader]
    return columns, rows


def write_variable_csv(
    path: str | Path,
    columns: list[str],
    rows: list[dict[str, str]],
) -> None:
    """Write variable rows to a CSV file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
