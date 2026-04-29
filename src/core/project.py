"""Template project model — serializable config for a thumbnail series."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from core.renderer import TemplateConfig, TextOverlay


@dataclass
class TextLayerMapping:
    """Maps a Krita text layer payload to a variable column."""
    layer_name: str
    variable_name: str
    svg_path: str = ""
    source_text: str = ""


@dataclass
class ThumbforgeProject:
    """A saved project: template config + variable definitions."""
    name: str = "Untitled"
    kra_template_path: str = ""
    template_config: TemplateConfig = field(default_factory=TemplateConfig)
    variable_columns: list[str] = field(default_factory=lambda: ["episode"])
    text_layer_mappings: list[TextLayerMapping] = field(default_factory=list)
    rows: list[dict[str, str]] = field(default_factory=list)
    output_dir: str = ""
    name_pattern: str = "thumb_{episode}"

    def upsert_text_layer_mapping(
        self,
        *,
        layer_name: str,
        variable_name: str,
        svg_path: str = "",
        source_text: str = "",
    ) -> None:
        """Create or update a layer-to-variable mapping."""
        for mapping in self.text_layer_mappings:
            if mapping.layer_name == layer_name and mapping.svg_path == svg_path:
                mapping.variable_name = variable_name
                mapping.source_text = source_text
                return
        self.text_layer_mappings.append(
            TextLayerMapping(
                layer_name=layer_name,
                variable_name=variable_name,
                svg_path=svg_path,
                source_text=source_text,
            )
        )

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
        mappings_data = data.pop("text_layer_mappings", [])
        text_layer_mappings = [TextLayerMapping(**m) for m in mappings_data]

        return cls(
            template_config=template_config,
            text_layer_mappings=text_layer_mappings,
            **data,
        )
