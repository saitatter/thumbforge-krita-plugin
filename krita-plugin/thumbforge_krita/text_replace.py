"""SVG text replacement helpers for Krita vector text shapes."""

from __future__ import annotations

import html
import re


TEXT_RE = re.compile(r"(<text\b[^>]*>)(.*?)(</text>)", re.IGNORECASE | re.DOTALL)
TSPAN_RE = re.compile(r"(<tspan\b[^>]*>)(.*?)(</tspan>)", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")


def plain_text(svg_fragment: str) -> str:
    """Return the visible text inside a Krita SVG text fragment."""
    spans = TSPAN_RE.findall(svg_fragment)
    if spans:
        return "".join(html.unescape(TAG_RE.sub("", span[1])) for span in spans)
    return html.unescape(TAG_RE.sub("", svg_fragment))


def replace_first_tspan_text(text_body: str, value: str) -> str:
    """Replace the first tspan payload while preserving its attributes."""
    escaped = html.escape(str(value), quote=False)
    replaced = False

    def replace_match(match):
        nonlocal replaced
        if replaced:
            return match.group(0)
        replaced = True
        return match.group(1) + escaped + match.group(3)

    updated = TSPAN_RE.sub(replace_match, text_body)
    if replaced:
        return updated
    return escaped


def replace_text_shape(svg: str, source_text: str, value: str) -> tuple[str, bool]:
    """Replace one matching SVG text shape and report whether it matched."""
    target = str(source_text or "")
    consumed = False

    def replace_text(match):
        nonlocal consumed
        if consumed:
            return match.group(0)
        body = match.group(2)
        if target and plain_text(body) != target:
            return match.group(0)
        consumed = True
        return match.group(1) + replace_first_tspan_text(body, value) + match.group(3)

    updated = TEXT_RE.sub(replace_text, svg)
    return updated, consumed
