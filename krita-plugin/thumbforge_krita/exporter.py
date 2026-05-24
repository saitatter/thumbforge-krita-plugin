"""Krita document export service for Thumbforge."""

from __future__ import annotations

from collections import defaultdict
import re

from krita import InfoObject, Krita

from .models import PngExportSettings, TextMapping
from .text_replace import replace_text_shape
from .logging_utils import log


SVG_ROOT_RE = re.compile(r"<svg\b", re.IGNORECASE)


class KritaTemplateExporter:
    def __init__(self, mappings: list[TextMapping], settings: PngExportSettings):
        self.mappings = mappings
        self.settings = settings

    def export_job(self, template_path: str, variables: dict[str, str], output_path: str) -> None:
        log("Exporting " + output_path + " from " + template_path)
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
            if self.settings.target_width > 0 and self.settings.target_height > 0:
                doc.scaleImage(
                    self.settings.target_width,
                    self.settings.target_height,
                    doc.resolution(),
                    doc.resolution(),
                    "bicubic",
                )
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
            log("Exported " + output_path)
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
            for mapping in mappings:
                self._apply_mapping_to_layer(doc, node, mapping, variables)

    def _apply_mapping_to_layer(self, doc, node, mapping: TextMapping, variables: dict[str, str]) -> None:
        value = variables.get(mapping.variable_name, "")
        for shape in list(node.shapes()):
            if mapping.shape_name and shape.name() != mapping.shape_name:
                continue
            matched = False
            for label, source_svg in self._shape_svg_candidates(doc, shape):
                svg, candidate_matched = replace_text_shape(source_svg, mapping.source_text, value)
                if not candidate_matched:
                    continue
                matched = True
                added = node.addShapesFromSvg(svg)
                if added:
                    log(
                        "SVG import succeeded for layer "
                        + mapping.layer_name
                        + " shape "
                        + (mapping.shape_name or "<unnamed>")
                        + " using "
                        + label
                        + " serialization."
                    )
                    shape.setVisible(False)
                    shape.update()
                    return
                log(
                    "SVG import failed for layer "
                    + mapping.layer_name
                    + " shape "
                    + (mapping.shape_name or "<unnamed>")
                    + " using "
                    + label
                    + " serialization (len="
                    + str(len(svg))
                    + ")."
                )
            if matched:
                raise RuntimeError("Krita did not add replacement text for layer: " + mapping.layer_name)
        detail = mapping.shape_name or mapping.source_text or mapping.variable_name
        raise RuntimeError("No matching text shape found: " + mapping.layer_name + " / " + detail)

    def _shape_svg_candidates(self, doc, shape):
        seen: set[str] = set()
        variants = [
            ("text mode preserved", (False, False)),
            ("styled text", (True, False)),
            ("default", ()),
            ("styled default", (True, True)),
        ]
        for label, args in variants:
            try:
                svg = shape.toSvg(*args)
            except TypeError:
                continue
            except Exception as exc:
                log("Could not serialize shape SVG with " + label + ": " + str(exc))
                continue
            for candidate_label, candidate_svg in self._normalize_svg_candidates(doc, label, svg):
                if not candidate_svg or candidate_svg in seen:
                    continue
                seen.add(candidate_svg)
                yield candidate_label, candidate_svg

    def _normalize_svg_candidates(self, doc, label: str, svg: str):
        yield label, svg
        if SVG_ROOT_RE.search(svg):
            return
        width_pt, height_pt = self._document_size_points(doc)
        wrapped = (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink" '
            'xmlns:krita="http://krita.org/namespaces/svg/krita" '
            'xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd" '
            'width="'
            + width_pt
            + 'pt" height="'
            + height_pt
            + 'pt" viewBox="0 0 '
            + width_pt
            + ' '
            + height_pt
            + '">'
            '<defs/>'
            + svg
            + '</svg>'
        )
        yield label + " wrapped", wrapped

    def _document_size_points(self, doc) -> tuple[str, str]:
        resolution = float(doc.resolution() or 72.0)
        width_pt = (float(doc.width()) * 72.0) / resolution
        height_pt = (float(doc.height()) * 72.0) / resolution
        return self._format_svg_number(width_pt), self._format_svg_number(height_pt)

    def _format_svg_number(self, value: float) -> str:
        return ("{:.6f}".format(value)).rstrip("0").rstrip(".")

    def _png_export_options(self):
        options = InfoObject()
        options.setProperty("quality", self.settings.quality)
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
