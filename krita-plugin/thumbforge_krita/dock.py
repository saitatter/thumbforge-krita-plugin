"""Thumbforge docker for Krita."""

from __future__ import annotations

import os
import tempfile

from krita import DockWidget, Krita
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QApplication,
    QDialog,
    QProgressDialog,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .csv_io import read_variable_csv, write_variable_csv
from .exporter import KritaTemplateExporter
from .models import ExportReport, PngExportSettings, TextMapping, ensure_export_path
from .project_store import load_project_from_document, save_project_to_document
from .text_replace import plain_text
from .validation import build_output_paths, validate_export_plan


class ThumbforgeDocker(DockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Thumbforge")
        self.mappings: list[TextMapping] = []
        self.columns: list[str] = ["episode"]
        self.rows: list[dict[str, str]] = []
        self._build_ui()
        self._connect_signals()

    def canvasChanged(self, canvas):
        self.load_setup(silent=True)

    def _build_ui(self):
        root = QWidget()
        layout = QVBoxLayout(root)

        toolbar = QHBoxLayout()
        self.detect_button = QPushButton("Detect Text")
        self.refresh_button = QPushButton("Refresh Text")
        self.load_setup_button = QPushButton("Load Setup")
        self.save_setup_button = QPushButton("Save Setup")
        self.import_button = QPushButton("Import CSV")
        self.export_csv_button = QPushButton("Export CSV")
        toolbar.addWidget(self.detect_button)
        toolbar.addWidget(self.refresh_button)
        toolbar.addWidget(self.load_setup_button)
        toolbar.addWidget(self.save_setup_button)
        toolbar.addWidget(self.import_button)
        toolbar.addWidget(self.export_csv_button)
        layout.addLayout(toolbar)

        filename_row = QHBoxLayout()
        filename_row.addWidget(QLabel("Filename"))
        self.name_pattern_edit = QLineEdit("thumb_{episode}")
        filename_row.addWidget(self.name_pattern_edit)
        layout.addLayout(filename_row)

        export_group = QGroupBox("Export Settings")
        export_layout = QHBoxLayout(export_group)
        export_layout.addWidget(QLabel("Format"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["png", "jpg", "webp"])
        export_layout.addWidget(self.format_combo)
        export_layout.addWidget(QLabel("Preset"))
        self.export_preset_combo = QComboBox()
        self.export_preset_combo.addItems(["YouTube PNG", "Small PNG", "Transparent PNG"])
        export_layout.addWidget(self.export_preset_combo)
        export_layout.addWidget(QLabel("Compression"))
        self.compression_spin = QSpinBox()
        self.compression_spin.setRange(0, 9)
        self.compression_spin.setValue(6)
        export_layout.addWidget(self.compression_spin)
        export_layout.addWidget(QLabel("Quality"))
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(90)
        export_layout.addWidget(self.quality_spin)
        self.alpha_check = QCheckBox("Alpha")
        self.alpha_check.setChecked(True)
        self.force_srgb_check = QCheckBox("sRGB")
        self.force_srgb_check.setChecked(True)
        self.save_icc_check = QCheckBox("ICC")
        self.save_icc_check.setChecked(True)
        self.interlaced_check = QCheckBox("Interlaced")
        export_layout.addWidget(self.alpha_check)
        export_layout.addWidget(self.force_srgb_check)
        export_layout.addWidget(self.save_icc_check)
        export_layout.addWidget(self.interlaced_check)
        layout.addWidget(export_group)

        resize_row = QHBoxLayout()
        resize_row.addWidget(QLabel("Resize"))
        self.target_width_spin = QSpinBox()
        self.target_width_spin.setRange(0, 10000)
        self.target_width_spin.setValue(0)
        self.target_height_spin = QSpinBox()
        self.target_height_spin.setRange(0, 10000)
        self.target_height_spin.setValue(0)
        resize_row.addWidget(self.target_width_spin)
        resize_row.addWidget(QLabel("x"))
        resize_row.addWidget(self.target_height_spin)
        resize_row.addWidget(QLabel("(0 = original)"))
        layout.addLayout(resize_row)

        mapping_group = QGroupBox("Text Layer Mappings")
        mapping_layout = QVBoxLayout(mapping_group)
        self.mapping_table = QTableWidget(0, 4)
        self.mapping_table.setHorizontalHeaderLabels(["Layer", "Shape", "Source Text", "Variable"])
        self.mapping_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        mapping_layout.addWidget(self.mapping_table)
        layout.addWidget(mapping_group)

        row_toolbar = QHBoxLayout()
        self.add_row_button = QPushButton("+ Row")
        self.remove_row_button = QPushButton("- Row")
        self.paste_rows_button = QPushButton("Paste Rows")
        self.preview_row_button = QPushButton("Preview Row")
        self.export_current_button = QPushButton("Export Current")
        self.export_selected_button = QPushButton("Export Selected")
        self.export_all_button = QPushButton("Export All")
        row_toolbar.addWidget(self.add_row_button)
        row_toolbar.addWidget(self.remove_row_button)
        row_toolbar.addWidget(self.paste_rows_button)
        row_toolbar.addStretch()
        row_toolbar.addWidget(self.preview_row_button)
        row_toolbar.addWidget(self.export_current_button)
        row_toolbar.addWidget(self.export_selected_button)
        row_toolbar.addWidget(self.export_all_button)
        layout.addLayout(row_toolbar)

        self.variables_table = QTableWidget(0, len(self.columns))
        self.variables_table.setHorizontalHeaderLabels(self.columns)
        self.variables_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.variables_table, stretch=1)

        self.status_label = QLabel("Open a saved .kra template, then detect text layers.")
        layout.addWidget(self.status_label)

        self.setWidget(root)

    def _connect_signals(self):
        self.detect_button.clicked.connect(self.detect_text_layers)
        self.refresh_button.clicked.connect(self.refresh_text_layers)
        self.load_setup_button.clicked.connect(self.load_setup)
        self.save_setup_button.clicked.connect(self.save_setup)
        self.import_button.clicked.connect(self.import_csv)
        self.export_csv_button.clicked.connect(self.export_csv)
        self.add_row_button.clicked.connect(self.add_row)
        self.remove_row_button.clicked.connect(self.remove_selected_row)
        self.paste_rows_button.clicked.connect(self.paste_rows)
        self.preview_row_button.clicked.connect(self.preview_row)
        self.export_current_button.clicked.connect(self.export_current)
        self.export_selected_button.clicked.connect(self.export_selected)
        self.export_all_button.clicked.connect(self.export_all)
        self.mapping_table.itemChanged.connect(self._mapping_changed)
        self.variables_table.itemChanged.connect(self._variables_changed)
        self.export_preset_combo.currentTextChanged.connect(self._apply_export_preset)

    def _active_template_path(self) -> str:
        doc = Krita.instance().activeDocument()
        if doc is None:
            raise RuntimeError("No active Krita document.")
        path = doc.fileName()
        if not path:
            raise RuntimeError("Save the .kra template before exporting.")
        return path

    def detect_text_layers(self):
        try:
            doc = Krita.instance().activeDocument()
            if doc is None:
                raise RuntimeError("No active Krita document.")
            self.mappings = self._detect_mappings(doc)
            for mapping in self.mappings:
                if mapping.variable_name not in self.columns:
                    self.columns.append(mapping.variable_name)
            self._refresh_mapping_table()
            self._refresh_variables_table()
            self.status_label.setText("Detected " + str(len(self.mappings)) + " text mapping(s).")
        except Exception as exc:
            self._show_error(exc)

    def refresh_text_layers(self):
        try:
            doc = Krita.instance().activeDocument()
            if doc is None:
                raise RuntimeError("No active Krita document.")
            detected = self._detect_mappings(doc)
            self.mappings = self._merge_mappings(self.mappings, detected)
            for mapping in self.mappings:
                if mapping.variable_name not in self.columns:
                    self.columns.append(mapping.variable_name)
            self._refresh_mapping_table()
            self._refresh_variables_table()
            self.status_label.setText("Refreshed " + str(len(self.mappings)) + " text mapping(s).")
        except Exception as exc:
            self._show_error(exc)

    def _detect_mappings(self, doc) -> list[TextMapping]:
        mappings: list[TextMapping] = []
        for node in self._walk_nodes(doc.rootNode()):
            if str(node.type()).lower() != "vectorlayer":
                continue
            for shape in list(node.shapes()):
                svg = shape.toSvg()
                text = self._first_text(svg)
                if text is None:
                    continue
                mappings.append(
                    TextMapping(
                        layer_name=node.name(),
                        shape_name=shape.name(),
                        source_text=text,
                        variable_name="text_" + str(len(mappings) + 1),
                    )
                )
        return mappings

    def _merge_mappings(
        self,
        existing: list[TextMapping],
        detected: list[TextMapping],
    ) -> list[TextMapping]:
        by_shape = {
            (mapping.layer_name, mapping.shape_name): mapping
            for mapping in existing
            if mapping.shape_name
        }
        by_source = {
            (mapping.layer_name, mapping.source_text): mapping
            for mapping in existing
        }
        merged = []
        for mapping in detected:
            previous = by_shape.get((mapping.layer_name, mapping.shape_name))
            if previous is None:
                previous = by_source.get((mapping.layer_name, mapping.source_text))
            if previous is not None:
                mapping.variable_name = previous.variable_name
            merged.append(mapping)
        return merged

    def _walk_nodes(self, node):
        yield node
        try:
            children = node.childNodes()
        except Exception:
            children = []
        for child in children:
            yield from self._walk_nodes(child)

    def _first_text(self, svg: str) -> str | None:
        from .text_replace import TEXT_RE

        match = TEXT_RE.search(svg)
        if not match:
            return None
        return plain_text(match.group(2))

    def _refresh_mapping_table(self):
        self.mapping_table.blockSignals(True)
        try:
            self.mapping_table.setRowCount(0)
            for mapping in self.mappings:
                row = self.mapping_table.rowCount()
                self.mapping_table.insertRow(row)
                self.mapping_table.setItem(row, 0, QTableWidgetItem(mapping.layer_name))
                self.mapping_table.setItem(row, 1, QTableWidgetItem(mapping.shape_name))
                self.mapping_table.setItem(row, 2, QTableWidgetItem(mapping.source_text))
                self.mapping_table.setItem(row, 3, QTableWidgetItem(mapping.variable_name))
        finally:
            self.mapping_table.blockSignals(False)

    def _refresh_variables_table(self):
        self.variables_table.blockSignals(True)
        try:
            self.variables_table.setColumnCount(len(self.columns))
            self.variables_table.setHorizontalHeaderLabels(self.columns)
            self.variables_table.setRowCount(0)
            for row_data in self.rows:
                row = self.variables_table.rowCount()
                self.variables_table.insertRow(row)
                for column, name in enumerate(self.columns):
                    self.variables_table.setItem(row, column, QTableWidgetItem(row_data.get(name, "")))
        finally:
            self.variables_table.blockSignals(False)

    def _mapping_changed(self, item):
        row = item.row()
        if row < 0 or row >= len(self.mappings):
            return
        mapping = self.mappings[row]
        old_variable = mapping.variable_name
        mapping.layer_name = self.mapping_table.item(row, 0).text().strip()
        mapping.shape_name = self.mapping_table.item(row, 1).text().strip()
        mapping.source_text = self.mapping_table.item(row, 2).text()
        mapping.variable_name = self.mapping_table.item(row, 3).text().strip()
        if mapping.variable_name and mapping.variable_name != old_variable:
            self._rename_variable_column(old_variable, mapping.variable_name)
            self._refresh_variables_table()

    def _rename_variable_column(self, old_name: str, new_name: str):
        if not new_name:
            return
        if old_name in self.columns and new_name not in self.columns:
            self.columns[self.columns.index(old_name)] = new_name
            for row in self.rows:
                row[new_name] = row.pop(old_name, "")
            return
        if new_name not in self.columns:
            self.columns.append(new_name)

    def _variables_changed(self, item):
        self._sync_rows_from_table()

    def _sync_rows_from_table(self):
        rows = []
        for row_index in range(self.variables_table.rowCount()):
            values = {}
            for column_index, column in enumerate(self.columns):
                item = self.variables_table.item(row_index, column_index)
                values[column] = item.text() if item else ""
            rows.append(values)
        self.rows = rows

    def add_row(self):
        self._sync_rows_from_table()
        self.rows.append({column: "" for column in self.columns})
        self._refresh_variables_table()

    def remove_selected_row(self):
        selected = self.variables_table.currentRow()
        if selected < 0:
            return
        self._sync_rows_from_table()
        if selected < len(self.rows):
            self.rows.pop(selected)
            self._refresh_variables_table()

    def import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import CSV", "", "CSV (*.csv);;All Files (*)")
        if not path:
            return
        try:
            columns, rows = read_variable_csv(path)
            for column in columns:
                if column not in self.columns:
                    self.columns.append(column)
            self.rows = rows
            self._refresh_variables_table()
            self.status_label.setText("Imported " + str(len(rows)) + " row(s).")
        except Exception as exc:
            self._show_error(exc)

    def paste_rows(self):
        try:
            from .table_data import parse_clipboard_table

            text = QApplication.clipboard().text()
            columns, rows = parse_clipboard_table(text, self.columns)
            for column in columns:
                if column not in self.columns:
                    self.columns.append(column)
            self.rows.extend(rows)
            self._refresh_variables_table()
            self.status_label.setText("Pasted " + str(len(rows)) + " row(s).")
        except Exception as exc:
            self._show_error(exc)

    def save_setup(self):
        self._sync_rows_from_table()
        try:
            doc = Krita.instance().activeDocument()
            if doc is None:
                raise RuntimeError("No active Krita document.")
            save_project_to_document(
                doc,
                mappings=self.mappings,
                columns=self.columns,
                rows=self.rows,
                name_pattern=self.name_pattern_edit.text().strip() or "thumb_{episode}",
                png_settings=self._png_settings(),
            )
            if doc.fileName():
                doc.save()
                doc.waitForDone()
            self.status_label.setText("Thumbforge setup saved in this .kra.")
        except Exception as exc:
            self._show_error(exc)

    def load_setup(self, silent: bool = False):
        try:
            doc = Krita.instance().activeDocument()
            if doc is None:
                return
            project = load_project_from_document(doc)
            if project is None:
                if not silent:
                    self.status_label.setText("No Thumbforge setup saved in this .kra.")
                return
            self.mappings = project["mappings"]
            self.columns = project["columns"] or ["episode"]
            self.rows = project["rows"]
            self.name_pattern_edit.setText(project["name_pattern"])
            self._set_png_settings(project["png_settings"])
            self._refresh_mapping_table()
            self._refresh_variables_table()
            self.status_label.setText("Loaded Thumbforge setup from this .kra.")
        except Exception as exc:
            if not silent:
                self._show_error(exc)

    def export_csv(self):
        self._sync_rows_from_table()
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "thumbforge.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            write_variable_csv(path, self.columns, self.rows)
            self.status_label.setText("Exported CSV.")
        except Exception as exc:
            self._show_error(exc)

    def preview_row(self):
        self._sync_rows_from_table()
        row = self.variables_table.currentRow()
        if row < 0 or row >= len(self.rows):
            self.status_label.setText("No row selected.")
            return
        try:
            output_path = os.path.join(tempfile.gettempdir(), "thumbforge_preview.png")
            self._exporter().export_job(self._active_template_path(), self.rows[row], output_path)
            self._show_preview_dialog(output_path)
            self.status_label.setText("Rendered preview for selected row.")
        except Exception as exc:
            self._show_error(exc)

    def export_current(self):
        self._sync_rows_from_table()
        row = self.variables_table.currentRow()
        if row < 0 or row >= len(self.rows):
            self.status_label.setText("No row selected.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Current",
            "thumbnail." + self._png_settings().file_format,
            "Images (*.png *.jpg *.webp)",
        )
        if not path:
            return
        path = ensure_export_path(path, self._png_settings())
        try:
            self._exporter().export_job(self._active_template_path(), self.rows[row], path)
            self.status_label.setText("Exported " + os.path.basename(path))
        except Exception as exc:
            self._show_error(exc)

    def export_all(self):
        self._sync_rows_from_table()
        if not self.rows:
            self.status_label.setText("No rows to export.")
            return
        self._export_rows(list(range(len(self.rows))))

    def export_selected(self):
        self._sync_rows_from_table()
        rows = sorted({index.row() for index in self.variables_table.selectedIndexes()})
        if not rows:
            self.status_label.setText("No rows selected.")
            return
        self._export_rows(rows)

    def _export_rows(self, row_indexes: list[int]):
        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not output_dir:
            return
        try:
            template_path = self._active_template_path()
            selected_rows = [self.rows[index] for index in row_indexes]
            issues = validate_export_plan(
                mappings=self.mappings,
                columns=self.columns,
                rows=selected_rows,
                output_dir=output_dir,
                name_pattern=self.name_pattern_edit.text().strip() or "thumb_{episode}",
                settings=self._png_settings(),
            )
            errors = [issue.message for issue in issues if issue.level == "error"]
            if errors:
                QMessageBox.warning(self, "Thumbforge", "\n".join(errors))
                return
            report = ExportReport(exported=[], failures=[])
            exporter = self._exporter()
            output_paths = build_output_paths(
                output_dir=output_dir,
                pattern=self.name_pattern_edit.text().strip() or "thumb_{episode}",
                rows=selected_rows,
                settings=self._png_settings(),
            )
            progress = QProgressDialog("Exporting thumbnails...", "Cancel", 0, len(row_indexes), self)
            progress.setWindowTitle("Thumbforge Export")
            progress.setMinimumDuration(0)
            for progress_index, row_index in enumerate(row_indexes, start=1):
                if progress.wasCanceled():
                    report.failures.append("Export canceled after " + str(progress_index - 1) + " row(s).")
                    break
                progress.setValue(progress_index - 1)
                progress.setLabelText(
                    "Exporting row " + str(row_index + 1) + " of " + str(len(self.rows))
                )
                QApplication.processEvents()
                variables = self.rows[row_index]
                output_path = output_paths[progress_index - 1]
                try:
                    exporter.export_job(template_path, variables, output_path)
                    report.exported.append(output_path)
                except Exception as exc:
                    report.failures.append("Row " + str(row_index + 1) + ": " + str(exc))
                self.status_label.setText(
                    "Exported " + str(progress_index) + "/" + str(len(row_indexes))
                )
                progress.setValue(progress_index)
                QApplication.processEvents()
            progress.setValue(len(row_indexes))
            QMessageBox.information(self, "Thumbforge", self._format_report(report))
        except Exception as exc:
            self._show_error(exc)

    def _exporter(self) -> KritaTemplateExporter:
        return KritaTemplateExporter(self.mappings, self._png_settings())

    def _png_settings(self) -> PngExportSettings:
        return PngExportSettings(
            file_format=self.format_combo.currentText(),
            compression=self.compression_spin.value(),
            quality=self.quality_spin.value(),
            alpha=self.alpha_check.isChecked(),
            force_srgb=self.force_srgb_check.isChecked(),
            save_icc=self.save_icc_check.isChecked(),
            interlaced=self.interlaced_check.isChecked(),
            target_width=self.target_width_spin.value(),
            target_height=self.target_height_spin.value(),
        )

    def _set_png_settings(self, settings: PngExportSettings):
        index = self.format_combo.findText(settings.file_format)
        if index >= 0:
            self.format_combo.setCurrentIndex(index)
        self.compression_spin.setValue(settings.compression)
        self.quality_spin.setValue(settings.quality)
        self.alpha_check.setChecked(settings.alpha)
        self.force_srgb_check.setChecked(settings.force_srgb)
        self.save_icc_check.setChecked(settings.save_icc)
        self.interlaced_check.setChecked(settings.interlaced)
        self.target_width_spin.setValue(settings.target_width)
        self.target_height_spin.setValue(settings.target_height)

    def _apply_export_preset(self, preset: str):
        if preset == "Small PNG":
            self._set_png_settings(
                PngExportSettings(
                    file_format="png",
                    compression=9,
                    quality=90,
                    alpha=False,
                    force_srgb=True,
                    save_icc=False,
                    interlaced=False,
                    target_width=1280,
                    target_height=720,
                )
            )
        elif preset == "Transparent PNG":
            self._set_png_settings(
                PngExportSettings(
                    file_format="png",
                    compression=6,
                    quality=90,
                    alpha=True,
                    force_srgb=True,
                    save_icc=True,
                    interlaced=False,
                    target_width=0,
                    target_height=0,
                )
            )
        else:
            self._set_png_settings(
                PngExportSettings(
                    file_format="png",
                    compression=6,
                    quality=90,
                    alpha=False,
                    force_srgb=True,
                    save_icc=True,
                    interlaced=False,
                    target_width=1280,
                    target_height=720,
                )
            )

    def _format_report(self, report: ExportReport) -> str:
        message = "Exported " + str(report.succeeded) + " thumbnail(s)."
        if report.failures:
            message += "\n\nFailed " + str(report.failed) + " row(s):\n"
            message += "\n".join(report.failures[:8])
        return message

    def _show_preview_dialog(self, image_path: str):
        dialog = QDialog(self)
        dialog.setWindowTitle("Thumbforge Preview")
        layout = QVBoxLayout(dialog)
        label = QLabel()
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            label.setPixmap(pixmap.scaledToWidth(720))
        layout.addWidget(label)
        dialog.resize(760, 520)
        dialog.exec_()

    def _show_error(self, exc: Exception):
        self.status_label.setText("Error: " + str(exc))
        QMessageBox.warning(self, "Thumbforge", str(exc))
