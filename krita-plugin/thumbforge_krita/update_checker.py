"""GitHub release update checks for Thumbforge."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass


LATEST_RELEASE_URL = "https://api.github.com/repos/saitatter/thumbforge-krita-plugin/releases/latest"


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    url: str
    name: str


def parse_version(version: str) -> tuple[int, ...]:
    cleaned = version.strip().lower()
    if cleaned.startswith("v"):
        cleaned = cleaned[1:]
    numeric = []
    for part in cleaned.split("."):
        digits = ""
        for char in part:
            if not char.isdigit():
                break
            digits += char
        numeric.append(int(digits or "0"))
    return tuple(numeric)


def is_newer_version(latest: str, current: str) -> bool:
    latest_parts = parse_version(latest)
    current_parts = parse_version(current)
    length = max(len(latest_parts), len(current_parts))
    latest_parts += (0,) * (length - len(latest_parts))
    current_parts += (0,) * (length - len(current_parts))
    return latest_parts > current_parts


def fetch_latest_release(timeout: int = 8) -> ReleaseInfo:
    request = urllib.request.Request(
        LATEST_RELEASE_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Thumbforge-Krita-Plugin",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    tag = str(payload.get("tag_name") or "")
    if not tag:
        raise RuntimeError("GitHub release response did not include a tag.")
    return ReleaseInfo(
        version=tag.lstrip("v"),
        url=str(payload.get("html_url") or ""),
        name=str(payload.get("name") or tag),
    )
