"""Krita document export service for Thumbforge."""

from __future__ import annotations

from collections import defaultdict

from krita import InfoObject, Krita

from .models import PngExportSettings, TextMapping
from .text_replace import replace_text_shape


class KritaTemplateExporter:
    def __init__(self, mappings: list[TextMapping], settings: PngExportSettings):
        self.mappings = mappings
        self.settings = settings

    def export_job(self, template_path: str, variables: dict[str, str], output_path: str) -> None:
        app = Krita.instance()
        old_batchmode = False
        doc = app.openDocument(template_path)
        if doc is None:
            raise RuntimeError("Krita could not open " + template_path)
        try:
            self._wait(doc)
            self._apply_variables(doc, variables)
            doc.refreshProjection()
            self._wait(doc)
            doc.flatten()
            self._wait(doc)
            doc.refreshProjection()
            self._wait(doc)
            old_batchmode = app.batchmode()
            app.setBatchmode(True)
            try:
                doc.setBatchmode(True)
            except Exception:
                pass
            ok = doc.exportImage(output_path, self._png_export_options())
            self._wait(doc)
            if ok is False:
                raise RuntimeError("Krita export failed for " + output_path)
        finally:
            try:
                app.setBatchmode(old_batchmode)
            except Exception:
                pass
            try:
                doc.setModified(False)
            except Exception:
                pass
            doc.close()

    def _apply_variables(self, doc, variables: dict[str, str]) -> None:
        mappings_by_layer = defaultdict(list)
        for mapping in self.mappings:
            mappings_by_layer[mapping.layer_name].append(mapping)
        for layer_name, mappings in mappings_by_layer.items():
            node = doc.nodeByName(layer_name)
            if node is None:
                raise RuntimeError("Layer not found: " + layer_name)
            svg = node.toSvg()
            matched_any = False
            for mapping in mappings:
                value = variables.get(mapping.variable_name, "")
                svg, matched = replace_text_shape(svg, mapping.source_text, value)
                matched_any = matched_any or matched
            if not matched_any:
                raise RuntimeError("No matching text shape found in layer: " + layer_name)
            for shape in list(node.shapes()):
                shape.setVisible(False)
                shape.update()
            added = node.addShapesFromSvg(svg)
            if not added:
                raise RuntimeError("Krita did not add replacement text for layer: " + layer_name)

    def _png_export_options(self):
        options = InfoObject()
        options.setProperty("alpha", self.settings.alpha)
        options.setProperty("compression", self.settings.compression)
        options.setProperty("forceSRGB", self.settings.force_srgb)
        options.setProperty("indexed", False)
        options.setProperty("interlaced", self.settings.interlaced)
        options.setProperty("saveSRGBProfile", self.settings.save_icc)
        return options

    def _wait(self, doc) -> None:
        try:
            doc.waitForDone()
        except Exception:
            pass
