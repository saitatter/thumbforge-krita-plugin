"""Validation helpers for Thumbforge batch exports."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from .models import PngExportSettings, TextMapping, ensure_export_path, substitute


INVALID_FILENAME_CHARS = '<>:"/\\|?*'


@dataclass
class ExportPlanIssue:
    level: str
    message: str


def build_output_path(
    output_dir: str,
    pattern: str,
    variables: dict[str, str],
    settings: PngExportSettings | None = None,
) -> str:
    name = sanitize_path_pattern(substitute(pattern or "thumb_{episode}", variables))
    return ensure_export_path(os.path.join(output_dir, name), settings or PngExportSettings())


def build_output_paths(
    *,
    output_dir: str,
    pattern: str,
    rows: list[dict[str, str]],
    settings: PngExportSettings | None = None,
) -> list[str]:
    counts: dict[str, int] = {}
    paths = []
    for variables in rows:
        output_path = build_output_path(output_dir, pattern, variables, settings)
        stem, extension = os.path.splitext(output_path)
        count = counts.get(output_path, 0) + 1
        counts[output_path] = count
        if count > 1:
            output_path = stem + "_" + str(count) + extension
        paths.append(output_path)
    return paths


def sanitize_path_pattern(name: str) -> str:
    parts = [part for part in re.split(r"[\\/]+", name) if part not in {"", "."}]
    if not parts:
        return "thumbnail"
    return os.path.join(*(sanitize_filename(part) for part in parts))


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
    settings: PngExportSettings | None = None,
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
    return issues
