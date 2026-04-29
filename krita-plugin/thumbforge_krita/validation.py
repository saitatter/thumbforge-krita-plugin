"""Validation helpers for Thumbforge batch exports."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .models import TextMapping, ensure_png_path, substitute


INVALID_FILENAME_CHARS = '<>:"/\\|?*'


@dataclass
class ExportPlanIssue:
    level: str
    message: str


def build_output_path(output_dir: str, pattern: str, variables: dict[str, str]) -> str:
    name = sanitize_filename(substitute(pattern or "thumb_{episode}", variables))
    return ensure_png_path(os.path.join(output_dir, name))


def sanitize_filename(name: str) -> str:
    cleaned = "".join("_" if char in INVALID_FILENAME_CHARS else char for char in name)
    cleaned = cleaned.strip().strip(".")
    return cleaned or "thumbnail"


def validate_export_plan(
    *,
    mappings: list[TextMapping],
    columns: list[str],
    rows: list[dict[str, str]],
    output_dir: str,
    name_pattern: str,
) -> list[ExportPlanIssue]:
    issues: list[ExportPlanIssue] = []
    if not mappings:
        issues.append(ExportPlanIssue("error", "No text mappings detected."))
    if not rows:
        issues.append(ExportPlanIssue("error", "No rows to export."))
    mapped_variables = [mapping.variable_name for mapping in mappings if mapping.variable_name]
    for variable in mapped_variables:
        if variable not in columns:
            issues.append(ExportPlanIssue("error", "Missing variable column: " + variable))
    outputs: dict[str, int] = {}
    for index, variables in enumerate(rows, start=1):
        output_path = build_output_path(output_dir, name_pattern, variables)
        previous = outputs.get(output_path)
        if previous is not None:
            issues.append(
                ExportPlanIssue(
                    "error",
                    "Rows "
                    + str(previous)
                    + " and "
                    + str(index)
                    + " export to the same filename: "
                    + os.path.basename(output_path),
                )
            )
        outputs[output_path] = index
    return issues
