"""Template project model — serializable config for a thumbnail series."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from core.renderer import TemplateConfig, TextOverlay


@dataclass
class ThumbforgeProject:
    """A saved project: template config + variable definitions."""
    name: str = "Untitled"
    template_config: TemplateConfig = field(default_factory=TemplateConfig)
    variable_columns: list[str] = field(default_factory=lambda: ["episode"])
    rows: list[dict[str, str]] = field(default_factory=list)
    output_dir: str = ""
    name_pattern: str = "thumb_{episode}"

    def save(self, path: str | Path) -> None:
        """Save project to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> ThumbforgeProject:
        """Load project from a JSON file."""
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))

        # Reconstruct nested dataclasses
        tc_data = data.pop("template_config", {})
        overlays_data = tc_data.pop("overlays", [])
        overlays = [TextOverlay(**o) for o in overlays_data]
        template_config = TemplateConfig(overlays=overlays, **tc_data)

        return cls(template_config=template_config, **data)
