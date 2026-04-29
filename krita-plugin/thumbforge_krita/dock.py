"""Thumbforge docker for Krita."""

from __future__ import annotations

import os

from krita import DockWidget, Krita
from PyQt5.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .csv_io import read_variable_csv, write_variable_csv
from .exporter import KritaTemplateExporter
from .models import PngExportSettings, TextMapping, ensure_png_path, substitute
from .project_store import load_project_from_document, save_project_to_document
from .text_replace import plain_text


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
        self.load_setup_button = QPushButton("Load Setup")
        self.save_setup_button = QPushButton("Save Setup")
        self.import_button = QPushButton("Import CSV")
        self.export_csv_button = QPushButton("Export CSV")
        toolbar.addWidget(self.detect_button)
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

        export_group = QGroupBox("PNG Export Settings")
        export_layout = QHBoxLayout(export_group)
        export_layout.addWidget(QLabel("Compression"))
        self.compression_spin = QSpinBox()
        self.compression_spin.setRange(0, 9)
        self.compression_spin.setValue(6)
        export_layout.addWidget(self.compression_spin)
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

        mapping_group = QGroupBox("Text Layer Mappings")
        mapping_layout = QVBoxLayout(mapping_group)
        self.mapping_table = QTableWidget(0, 3)
        self.mapping_table.setHorizontalHeaderLabels(["Layer", "Source Text", "Variable"])
        self.mapping_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        mapping_layout.addWidget(self.mapping_table)
        layout.addWidget(mapping_group)

        row_toolbar = QHBoxLayout()
        self.add_row_button = QPushButton("+ Row")
        self.remove_row_button = QPushButton("- Row")
        self.export_current_button = QPushButton("Export Current")
        self.export_all_button = QPushButton("Export All")
        row_toolbar.addWidget(self.add_row_button)
        row_toolbar.addWidget(self.remove_row_button)
        row_toolbar.addStretch()
        row_toolbar.addWidget(self.export_current_button)
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
        self.load_setup_button.clicked.connect(self.load_setup)
        self.save_setup_button.clicked.connect(self.save_setup)
        self.import_button.clicked.connect(self.import_csv)
        self.export_csv_button.clicked.connect(self.export_csv)
        self.add_row_button.clicked.connect(self.add_row)
        self.remove_row_button.clicked.connect(self.remove_selected_row)
        self.export_current_button.clicked.connect(self.export_current)
        self.export_all_button.clicked.connect(self.export_all)
        self.mapping_table.itemChanged.connect(self._mapping_changed)
        self.variables_table.itemChanged.connect(self._variables_changed)

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
            self.mappings = []
            for node in self._walk_nodes(doc.rootNode()):
                if str(node.type()).lower() != "vectorlayer":
                    continue
                for shape in list(node.shapes()):
                    svg = shape.toSvg()
                    text = self._first_text(svg)
                    if text is None:
                        continue
                    variable_name = "text_" + str(len(self.mappings) + 1)
                    self.mappings.append(TextMapping(node.name(), text, variable_name))
                    if variable_name not in self.columns:
                        self.columns.append(variable_name)
            self._refresh_mapping_table()
            self._refresh_variables_table()
            self.status_label.setText("Detected " + str(len(self.mappings)) + " text mapping(s).")
        except Exception as exc:
            self._show_error(exc)

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
                self.mapping_table.setItem(row, 1, QTableWidgetItem(mapping.source_text))
                self.mapping_table.setItem(row, 2, QTableWidgetItem(mapping.variable_name))
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
        mapping.layer_name = self.mapping_table.item(row, 0).text().strip()
        mapping.source_text = self.mapping_table.item(row, 1).text()
        mapping.variable_name = self.mapping_table.item(row, 2).text().strip()
        if mapping.variable_name and mapping.variable_name not in self.columns:
            self.columns.append(mapping.variable_name)
            self._refresh_variables_table()

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

    def export_current(self):
        self._sync_rows_from_table()
        row = self.variables_table.currentRow()
        if row < 0 or row >= len(self.rows):
            self.status_label.setText("No row selected.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Current", "thumbnail.png", "PNG (*.png)")
        if not path:
            return
        path = ensure_png_path(path)
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
        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not output_dir:
            return
        try:
            template_path = self._active_template_path()
            for index, variables in enumerate(self.rows, start=1):
                name = substitute(self.name_pattern_edit.text().strip() or "thumb_{episode}", variables)
                output_path = ensure_png_path(os.path.join(output_dir, name))
                self._exporter().export_job(template_path, variables, output_path)
                self.status_label.setText("Exported " + str(index) + "/" + str(len(self.rows)))
            QMessageBox.information(self, "Thumbforge", "Exported " + str(len(self.rows)) + " thumbnail(s).")
        except Exception as exc:
            self._show_error(exc)

    def _exporter(self) -> KritaTemplateExporter:
        return KritaTemplateExporter(self.mappings, self._png_settings())

    def _png_settings(self) -> PngExportSettings:
        return PngExportSettings(
            compression=self.compression_spin.value(),
            alpha=self.alpha_check.isChecked(),
            force_srgb=self.force_srgb_check.isChecked(),
            save_icc=self.save_icc_check.isChecked(),
            interlaced=self.interlaced_check.isChecked(),
        )

    def _set_png_settings(self, settings: PngExportSettings):
        self.compression_spin.setValue(settings.compression)
        self.alpha_check.setChecked(settings.alpha)
        self.force_srgb_check.setChecked(settings.force_srgb)
        self.save_icc_check.setChecked(settings.save_icc)
        self.interlaced_check.setChecked(settings.interlaced)

    def _show_error(self, exc: Exception):
        self.status_label.setText("Error: " + str(exc))
        QMessageBox.warning(self, "Thumbforge", str(exc))
