"""Thumbforge docker for Krita."""

from __future__ import annotations

import os
import tempfile

from krita import DockWidget, Krita
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QBrush, QColor, QDesktopServices, QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QInputDialog,
    QMessageBox,
    QApplication,
    QDialog,
    QProgressDialog,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .csv_io import read_variable_csv, write_variable_csv
from .exporter import KritaTemplateExporter
from .models import ExportReport, PngExportSettings, TextMapping, ensure_export_path
from .logging_utils import log, log_exception, log_path
from .project_store import load_project_from_document, save_project_to_document
from .text_replace import plain_text
from .validation import build_output_paths, validate_export_plan
from .version import BUILD, VERSION


class ThumbforgeDocker(DockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Thumbforge")
        self.mappings: list[TextMapping] = []
        self.columns: list[str] = ["episode"]
        self.rows: list[dict[str, str]] = []
        self.last_output_dir = ""
        self._build_ui()
        self._connect_signals()
        self._check_krita_compatibility()

    def canvasChanged(self, canvas):
        self.load_setup(silent=True)

    def _build_ui(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        tabs = QTabWidget()
        layout.addWidget(tabs, stretch=1)

        template_tab = QWidget()
        template_layout = QVBoxLayout(template_tab)
        template_layout.setContentsMargins(6, 6, 6, 6)

        project_row = QHBoxLayout()
        self.load_setup_button = QPushButton("Load Setup")
        self.save_setup_button = QPushButton("Save Setup")
        project_row.addWidget(self.load_setup_button)
        project_row.addWidget(self.save_setup_button)
        project_row.addStretch()
        template_layout.addLayout(project_row)

        self.annotation_label = QLabel("Setup storage: .kra annotation")
        template_layout.addWidget(self.annotation_label)

        filename_form = QFormLayout()
        self.name_pattern_edit = QLineEdit("thumb_{episode}")
        filename_form.addRow("Filename", self.name_pattern_edit)
        template_layout.addLayout(filename_form)

        mapping_group = QGroupBox("Text Layer Mappings")
        mapping_layout = QVBoxLayout(mapping_group)
        mapping_toolbar = QHBoxLayout()
        self.detect_button = QPushButton("Detect Text")
        self.refresh_button = QPushButton("Refresh Text")
        mapping_toolbar.addWidget(self.detect_button)
        mapping_toolbar.addWidget(self.refresh_button)
        mapping_toolbar.addStretch()
        mapping_layout.addLayout(mapping_toolbar)
        self.mapping_table = QTableWidget(0, 4)
        self.mapping_table.setHorizontalHeaderLabels(["Layer", "Shape", "Source Text", "Variable"])
        self.mapping_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.mapping_table.setAlternatingRowColors(True)
        self.mapping_table.verticalHeader().setDefaultSectionSize(24)
        self.mapping_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.mapping_table.horizontalHeader().setStretchLastSection(True)
        self.mapping_table.setColumnWidth(0, 180)
        self.mapping_table.setColumnWidth(1, 110)
        self.mapping_table.setColumnWidth(2, 220)
        mapping_layout.addWidget(self.mapping_table)
        template_layout.addWidget(mapping_group, stretch=1)
        tabs.addTab(template_tab, "Template")

        data_tab = QWidget()
        data_layout = QVBoxLayout(data_tab)
        data_layout.setContentsMargins(6, 6, 6, 6)

        data_import_row = QHBoxLayout()
        self.import_button = QPushButton("Import CSV")
        self.import_names_button = QPushButton("Import Filenames")
        self.export_csv_button = QPushButton("Export CSV")
        data_import_row.addWidget(self.import_button)
        data_import_row.addWidget(self.import_names_button)
        data_import_row.addWidget(self.export_csv_button)
        data_import_row.addStretch()
        data_layout.addLayout(data_import_row)

        data_edit_row = QHBoxLayout()
        self.add_row_button = QPushButton("+ Row")
        self.remove_row_button = QPushButton("- Row")
        self.duplicate_row_button = QPushButton("Duplicate Row")
        self.move_row_up_button = QPushButton("Move Up")
        self.move_row_down_button = QPushButton("Move Down")
        self.add_column_button = QPushButton("+ Column")
        self.remove_column_button = QPushButton("- Column")
        self.generate_rows_button = QPushButton("Generate Rows")
        self.validate_rows_button = QPushButton("Validate Rows")
        self.paste_rows_button = QPushButton("Paste Rows")
        data_edit_row.addWidget(self.add_row_button)
        data_edit_row.addWidget(self.remove_row_button)
        data_edit_row.addWidget(self.duplicate_row_button)
        data_edit_row.addWidget(self.move_row_up_button)
        data_edit_row.addWidget(self.move_row_down_button)
        data_edit_row.addWidget(self.add_column_button)
        data_edit_row.addWidget(self.remove_column_button)
        data_edit_row.addWidget(self.generate_rows_button)
        data_edit_row.addWidget(self.validate_rows_button)
        data_edit_row.addWidget(self.paste_rows_button)
        data_edit_row.addStretch()
        data_layout.addLayout(data_edit_row)

        self.variables_table = QTableWidget(0, len(self.columns))
        self.variables_table.setHorizontalHeaderLabels(self.columns)
        self.variables_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.variables_table.setAlternatingRowColors(True)
        self.variables_table.verticalHeader().setDefaultSectionSize(24)
        self.variables_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.variables_table.horizontalHeader().setStretchLastSection(True)
        data_layout.addWidget(self.variables_table, stretch=1)
        tabs.addTab(data_tab, "Data")

        export_tab = QWidget()
        export_layout = QVBoxLayout(export_tab)
        export_layout.setContentsMargins(6, 6, 6, 6)

        export_group = QGroupBox("Export Settings")
        settings_grid = QGridLayout(export_group)
        settings_grid.addWidget(QLabel("Format"), 0, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["png", "jpg", "webp"])
        settings_grid.addWidget(self.format_combo, 0, 1)
        settings_grid.addWidget(QLabel("Preset"), 0, 2)
        self.export_preset_combo = QComboBox()
        self.export_preset_combo.addItems(["YouTube PNG", "Small PNG", "Transparent PNG"])
        settings_grid.addWidget(self.export_preset_combo, 0, 3, 1, 2)
        settings_grid.addWidget(QLabel("Compression"), 1, 0)
        self.compression_spin = QSpinBox()
        self.compression_spin.setRange(0, 9)
        self.compression_spin.setValue(6)
        settings_grid.addWidget(self.compression_spin, 1, 1)
        settings_grid.addWidget(QLabel("Quality"), 1, 2)
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(90)
        settings_grid.addWidget(self.quality_spin, 1, 3)
        self.alpha_check = QCheckBox("Alpha")
        self.alpha_check.setChecked(True)
        self.force_srgb_check = QCheckBox("sRGB")
        self.force_srgb_check.setChecked(True)
        self.save_icc_check = QCheckBox("ICC")
        self.save_icc_check.setChecked(True)
        self.interlaced_check = QCheckBox("Interlaced")
        settings_grid.addWidget(self.alpha_check, 2, 0)
        settings_grid.addWidget(self.force_srgb_check, 2, 1)
        settings_grid.addWidget(self.save_icc_check, 2, 2)
        settings_grid.addWidget(self.interlaced_check, 2, 3)
        export_layout.addWidget(export_group)

        resize_group = QGroupBox("Resize")
        resize_grid = QGridLayout(resize_group)
        self.target_width_spin = QSpinBox()
        self.target_width_spin.setRange(0, 10000)
        self.target_width_spin.setValue(0)
        self.target_width_spin.setSpecialValueText("Original")
        self.target_height_spin = QSpinBox()
        self.target_height_spin.setRange(0, 10000)
        self.target_height_spin.setValue(0)
        self.target_height_spin.setSpecialValueText("Original")
        resize_grid.addWidget(QLabel("Width"), 0, 0)
        resize_grid.addWidget(self.target_width_spin, 0, 1)
        resize_grid.addWidget(QLabel("Height"), 0, 2)
        resize_grid.addWidget(self.target_height_spin, 0, 3)
        export_layout.addWidget(resize_group)

        export_actions = QHBoxLayout()
        self.preview_row_button = QPushButton("Preview Row")
        self.export_current_button = QPushButton("Export Current")
        self.export_selected_button = QPushButton("Export Selected")
        self.export_all_button = QPushButton("Export All")
        self.open_output_button = QPushButton("Open Output Folder")
        self.open_output_button.setEnabled(False)
        export_actions.addWidget(self.preview_row_button)
        export_actions.addWidget(self.export_current_button)
        export_actions.addWidget(self.export_selected_button)
        export_actions.addWidget(self.export_all_button)
        export_actions.addWidget(self.open_output_button)
        export_actions.addStretch()
        export_layout.addLayout(export_actions)
        export_layout.addStretch()
        tabs.addTab(export_tab, "Export")

        self.status_label = QLabel("Open a saved .kra template, then detect text layers.")
        layout.addWidget(self.status_label)
        self.version_label = QLabel("Thumbforge " + VERSION + " (" + BUILD + ")")
        layout.addWidget(self.version_label)
        self.log_label = QLabel("Log: " + log_path())
        layout.addWidget(self.log_label)

        self._set_tooltips()
        self.setWidget(root)

    def _set_tooltips(self):
        self.load_setup_button.setToolTip("Load Thumbforge mappings, rows, filename pattern, and export settings from this .kra annotation.")
        self.save_setup_button.setToolTip("Save the current Thumbforge setup into this .kra as a Krita annotation.")
        self.annotation_label.setToolTip("Thumbforge stores setup data inside the .kra file, not in a separate sidecar file.")
        self.name_pattern_edit.setToolTip("Output filename pattern. Use variables like {episode}, {title}, or subfolders like {series}/thumb_{episode}.")

        self.detect_button.setToolTip("Scan the active Krita document and create mappings for detected vector text shapes.")
        self.refresh_button.setToolTip("Re-scan text shapes while preserving existing variable names when possible.")
        self.mapping_table.setToolTip("Map each Krita vector text shape to a variable column used by the data rows.")

        self.import_button.setToolTip("Import variable rows from a CSV file.")
        self.import_names_button.setToolTip("Create rows from selected filenames, filling filename, title, and episode columns.")
        self.export_csv_button.setToolTip("Export the current variable table to CSV.")
        self.add_row_button.setToolTip("Add an empty variable row.")
        self.remove_row_button.setToolTip("Remove the selected variable row.")
        self.duplicate_row_button.setToolTip("Duplicate the selected variable row below the original.")
        self.move_row_up_button.setToolTip("Move the selected variable row one position up.")
        self.move_row_down_button.setToolTip("Move the selected variable row one position down.")
        self.add_column_button.setToolTip("Add a new variable column.")
        self.remove_column_button.setToolTip("Remove the selected variable column.")
        self.generate_rows_button.setToolTip("Generate numbered rows and fill text_* columns with #1, #2, and so on.")
        self.validate_rows_button.setToolTip("Highlight missing values for variables used by text mappings.")
        self.paste_rows_button.setToolTip("Paste rows from the clipboard, such as copied Excel or Google Sheets cells.")
        self.variables_table.setToolTip("One row equals one exported thumbnail. Columns are variables used by mappings and filename patterns.")

        self.format_combo.setToolTip("Choose the exported image format.")
        self.export_preset_combo.setToolTip("Apply common export settings for YouTube, smaller PNGs, or transparent PNG output.")
        self.compression_spin.setToolTip("PNG compression level. Higher values are smaller but may export slower.")
        self.quality_spin.setToolTip("JPEG/WebP quality. Higher values keep more detail and create larger files.")
        self.alpha_check.setToolTip("Preserve transparency when the selected format supports it.")
        self.force_srgb_check.setToolTip("Ask Krita to convert/export using sRGB color behavior.")
        self.save_icc_check.setToolTip("Include the sRGB/ICC color profile when Krita supports it for the selected format.")
        self.interlaced_check.setToolTip("Enable interlaced/progressive PNG-style output when supported.")
        self.target_width_spin.setToolTip("Export width. Use Original to keep the document width.")
        self.target_height_spin.setToolTip("Export height. Use Original to keep the document height.")

        self.preview_row_button.setToolTip("Render the selected row to a temporary image and show a preview.")
        self.export_current_button.setToolTip("Export the selected row to a chosen file.")
        self.export_selected_button.setToolTip("Export all selected table rows to a folder.")
        self.export_all_button.setToolTip("Export every row in the variable table to a folder.")
        self.open_output_button.setToolTip("Open the folder used by the latest successful export.")
        self.status_label.setToolTip("Shows the latest Thumbforge status or validation message.")
        self.log_label.setToolTip("Detailed activity and error log written by the plugin.")

    def _connect_signals(self):
        self.detect_button.clicked.connect(self.detect_text_layers)
        self.refresh_button.clicked.connect(self.refresh_text_layers)
        self.load_setup_button.clicked.connect(self.load_setup)
        self.save_setup_button.clicked.connect(self.save_setup)
        self.import_button.clicked.connect(self.import_csv)
        self.import_names_button.clicked.connect(self.import_filenames)
        self.export_csv_button.clicked.connect(self.export_csv)
        self.add_row_button.clicked.connect(self.add_row)
        self.remove_row_button.clicked.connect(self.remove_selected_row)
        self.duplicate_row_button.clicked.connect(self.duplicate_selected_row)
        self.move_row_up_button.clicked.connect(self.move_selected_row_up)
        self.move_row_down_button.clicked.connect(self.move_selected_row_down)
        self.add_column_button.clicked.connect(self.add_column)
        self.remove_column_button.clicked.connect(self.remove_selected_column)
        self.generate_rows_button.clicked.connect(self.generate_rows)
        self.validate_rows_button.clicked.connect(self.validate_rows)
        self.paste_rows_button.clicked.connect(self.paste_rows)
        self.preview_row_button.clicked.connect(self.preview_row)
        self.export_current_button.clicked.connect(self.export_current)
        self.export_selected_button.clicked.connect(self.export_selected)
        self.export_all_button.clicked.connect(self.export_all)
        self.open_output_button.clicked.connect(self.open_output_folder)
        self.mapping_table.itemChanged.connect(self._mapping_changed)
        self.variables_table.itemChanged.connect(self._variables_changed)
        self.export_preset_combo.currentTextChanged.connect(self._apply_export_preset)

    def _check_krita_compatibility(self):
        try:
            version = Krita.instance().version()
        except Exception:
            version = ""
        if not version:
            return
        log("Krita version: " + version)
        major = self._parse_major_version(version)
        if major is not None and major < 5:
            self.status_label.setText("Thumbforge expects Krita 5.x or newer.")

    def _parse_major_version(self, version: str) -> int | None:
        try:
            return int(version.split(".", 1)[0])
        except Exception:
            return None

    def _active_template_path(self) -> str:
        doc = Krita.instance().activeDocument()
        if doc is None:
            raise RuntimeError("No active Krita document.")
        path = doc.fileName()
        if not path:
            raise RuntimeError("Save the .kra template before exporting.")
        if self._document_is_modified(doc):
            answer = QMessageBox.question(
                self,
                "Thumbforge",
                "The active .kra has unsaved changes. Save before exporting?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes,
            )
            if answer == QMessageBox.Cancel:
                raise RuntimeError("Export canceled.")
            if answer == QMessageBox.Yes:
                doc.save()
                doc.waitForDone()
        return path

    def _document_is_modified(self, doc) -> bool:
        try:
            return bool(doc.modified())
        except Exception:
            return False

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

    def validate_rows(self):
        self._sync_rows_from_table()
        required = [mapping.variable_name for mapping in self.mappings if mapping.variable_name]
        issues = 0
        self._clear_variable_highlights()
        for row_index, row in enumerate(self.rows):
            for variable in required:
                if not row.get(variable, "").strip():
                    issues += 1
                    self._highlight_cell(row_index, variable)
        if issues:
            self.status_label.setText("Found " + str(issues) + " missing mapped value(s).")
        else:
            self.status_label.setText("Rows look valid.")

    def _clear_variable_highlights(self):
        for row_index in range(self.variables_table.rowCount()):
            for column_index in range(self.variables_table.columnCount()):
                item = self.variables_table.item(row_index, column_index)
                if item is not None:
                    item.setBackground(QBrush())

    def _highlight_cell(self, row_index: int, variable: str):
        if variable not in self.columns:
            return
        column_index = self.columns.index(variable)
        item = self.variables_table.item(row_index, column_index)
        if item is None:
            item = QTableWidgetItem("")
            self.variables_table.setItem(row_index, column_index, item)
        item.setBackground(QBrush(QColor("#ffd6d6")))

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
            if self.rows:
                self.variables_table.selectRow(min(selected, len(self.rows) - 1))

    def duplicate_selected_row(self):
        selected = self.variables_table.currentRow()
        if selected < 0:
            self.status_label.setText("No row selected.")
            return
        self._sync_rows_from_table()
        if selected >= len(self.rows):
            return
        self.rows.insert(selected + 1, dict(self.rows[selected]))
        self._refresh_variables_table()
        self.variables_table.selectRow(selected + 1)
        self.status_label.setText("Duplicated row " + str(selected + 1) + ".")

    def move_selected_row_up(self):
        self._move_selected_row(-1)

    def move_selected_row_down(self):
        self._move_selected_row(1)

    def _move_selected_row(self, offset: int):
        selected = self.variables_table.currentRow()
        if selected < 0:
            self.status_label.setText("No row selected.")
            return
        target = selected + offset
        self._sync_rows_from_table()
        if target < 0 or target >= len(self.rows):
            return
        self.rows[selected], self.rows[target] = self.rows[target], self.rows[selected]
        self._refresh_variables_table()
        self.variables_table.selectRow(target)

    def add_column(self):
        name, accepted = QInputDialog.getText(self, "Add Column", "Column name")
        name = name.strip()
        if not accepted or not name:
            return
        if name in self.columns:
            self.status_label.setText("Column already exists: " + name)
            return
        self._sync_rows_from_table()
        self.columns.append(name)
        for row in self.rows:
            row[name] = ""
        self._refresh_variables_table()

    def remove_selected_column(self):
        column = self.variables_table.currentColumn()
        if column < 0 or column >= len(self.columns):
            return
        name = self.columns[column]
        if name == "episode":
            self.status_label.setText("The episode column cannot be removed.")
            return
        self._sync_rows_from_table()
        self.columns.pop(column)
        for row in self.rows:
            row.pop(name, None)
        self._refresh_variables_table()

    def generate_rows(self):
        count, accepted = QInputDialog.getInt(self, "Generate Rows", "Rows", 10, 1, 10000)
        if not accepted:
            return
        self.rows = []
        for index in range(1, count + 1):
            row = {column: "" for column in self.columns}
            if "episode" in self.columns:
                row["episode"] = str(index)
            for column in self.columns:
                if column.startswith("text_"):
                    row[column] = "#" + str(index)
            self.rows.append(row)
        self._refresh_variables_table()
        self.status_label.setText("Generated " + str(count) + " row(s).")

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

    def import_filenames(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Import Filenames", "", "All Files (*)")
        if not paths:
            return
        for column in ["filename", "title"]:
            if column not in self.columns:
                self.columns.append(column)
        self._sync_rows_from_table()
        start = len(self.rows) + 1
        for offset, path in enumerate(paths):
            stem = os.path.splitext(os.path.basename(path))[0]
            row = {column: "" for column in self.columns}
            if "episode" in self.columns:
                row["episode"] = str(start + offset)
            row["filename"] = stem
            row["title"] = stem
            self.rows.append(row)
        self._refresh_variables_table()
        self.status_label.setText("Imported " + str(len(paths)) + " filename row(s).")

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
            self._set_last_output_dir(os.path.dirname(path))
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
            self._set_last_output_dir(output_dir)
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

    def _set_last_output_dir(self, output_dir: str):
        self.last_output_dir = output_dir
        self.open_output_button.setEnabled(bool(output_dir and os.path.isdir(output_dir)))

    def open_output_folder(self):
        if not self.last_output_dir or not os.path.isdir(self.last_output_dir):
            self.status_label.setText("No export folder available yet.")
            self.open_output_button.setEnabled(False)
            return
        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_output_dir))
        if opened:
            self.status_label.setText("Opened output folder.")
        else:
            self.status_label.setText("Could not open output folder.")

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
        log_exception("Thumbforge error", exc)
        self.status_label.setText("Error: " + str(exc))
        QMessageBox.warning(self, "Thumbforge", str(exc))
