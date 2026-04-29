"""Main window for Thumbforge."""
from __future__ import annotations

import logging
from copy import deepcopy
from pathlib import Path
import tempfile

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.project import ThumbforgeProject
from core.renderer import TextOverlay, parse_font_size, render_thumbnail
from ui.preview_widget import PreviewWidget
from ui.variables_table import VariablesTable

logger = logging.getLogger(__name__)


class ExportWorker(QObject):
    """Runs thumbnail exports outside the UI thread."""

    completed = Signal(str, str)
    failed = Signal(str)

    def __init__(
        self,
        *,
        mode: str,
        template_config,
        kra_template_path: str,
        text_layer_mappings: list,
        variables: dict[str, str] | None = None,
        rows: list[dict[str, str]] | None = None,
        output_path: str = "",
        output_dir: str = "",
        name_pattern: str = "thumb_{episode}",
    ):
        super().__init__()
        self.mode = mode
        self.template_config = template_config
        self.kra_template_path = kra_template_path
        self.text_layer_mappings = text_layer_mappings
        self.variables = variables or {}
        self.rows = rows or []
        self.output_path = output_path
        self.output_dir = output_dir
        self.name_pattern = name_pattern

    def run(self):
        try:
            if self.mode == "current":
                message = self._export_current()
                self.completed.emit("Export Complete", message)
            else:
                message = self._export_batch()
                self.completed.emit("Batch Export Complete", message)
        except Exception as exc:
            logger.error("Export failed: %s", exc)
            self.failed.emit(str(exc))

    def _export_current(self) -> str:
        if self.kra_template_path and self.text_layer_mappings:
            import tempfile

            from core.kra_writer import write_variable_kra
            from core.krita_exporter import export_kra_to_image

            with tempfile.TemporaryDirectory(prefix="thumbforge_kra_") as tmp:
                kra_path = Path(tmp) / "current.kra"
                write_variable_kra(
                    self.kra_template_path,
                    kra_path,
                    self.text_layer_mappings,
                    self.variables,
                )
                export_kra_to_image(kra_path, self.output_path)
            return f"Exported: {self.output_path}"

        from core.renderer import export_thumbnail, render_thumbnail

        image = render_thumbnail(self.template_config, self.variables)
        export_thumbnail(image, self.output_path)
        return f"Exported: {self.output_path}"

    def _export_batch(self) -> str:
        if self.kra_template_path and self.text_layer_mappings:
            from core.krita_exporter import batch_export_kra_report

            report = batch_export_kra_report(
                self.kra_template_path,
                self.text_layer_mappings,
                self.rows,
                self.output_dir,
                name_pattern=self.name_pattern,
            )
            message = f"Exported {report.succeeded} thumbnail(s) to {self.output_dir}"
            if report.failures:
                message += f"\n\nFailed {report.failed} row(s):\n" + "\n".join(report.failures[:5])
            return message

        from core.renderer import batch_export

        exported = batch_export(
            self.template_config,
            self.rows,
            self.output_dir,
            name_pattern=self.name_pattern,
        )
        return f"Exported {len(exported)} thumbnail(s) to {self.output_dir}"


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Thumbforge")
        self.setMinimumSize(960, 600)

        self.project = ThumbforgeProject()
        self.project_path: str = ""
        self._loading_mappings = False
        self._export_thread: QThread | None = None
        self._export_worker: ExportWorker | None = None

        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 8)

        # Toolbar row
        toolbar = QHBoxLayout()
        self.btn_open_bg = QPushButton("Open Background")
        self.btn_open_kra = QPushButton("Open .kra Template")
        self.btn_open_project = QPushButton("Open Project")
        self.btn_save_project = QPushButton("Save Project")
        self.btn_export = QPushButton("Export All")
        self.btn_export_one = QPushButton("Export Current")
        toolbar.addWidget(self.btn_open_project)
        toolbar.addWidget(self.btn_save_project)
        toolbar.addWidget(self.btn_open_bg)
        toolbar.addWidget(self.btn_open_kra)
        toolbar.addWidget(QLabel("Filename"))
        self.name_pattern_edit = QLineEdit(self.project.name_pattern)
        self.name_pattern_edit.setMinimumWidth(180)
        toolbar.addWidget(self.name_pattern_edit)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_export_one)
        toolbar.addWidget(self.btn_export)
        root_layout.addLayout(toolbar)

        # Main splitter: preview | variables table
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.preview = PreviewWidget()
        splitter.addWidget(self.preview)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        mapping_group = QGroupBox("Text Layer Mappings")
        mapping_layout = QVBoxLayout(mapping_group)
        self.mapping_table = QTableWidget(0, 3)
        self.mapping_table.setHorizontalHeaderLabels(["Layer", "Source Text", "Variable"])
        self.mapping_table.horizontalHeader().setStretchLastSection(True)
        mapping_layout.addWidget(self.mapping_table)
        right_layout.addWidget(mapping_group, stretch=1)

        self.variables_table = VariablesTable(self.project)
        right_layout.addWidget(self.variables_table, stretch=3)
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        root_layout.addWidget(splitter, stretch=1)

        # Status bar
        self.statusBar().showMessage("Ready")

    def _connect_signals(self):
        self.btn_open_bg.clicked.connect(self._open_background)
        self.btn_open_kra.clicked.connect(self._open_kra_template)
        self.btn_open_project.clicked.connect(self._open_project)
        self.btn_save_project.clicked.connect(self._save_project)
        self.btn_export.clicked.connect(self._export_all)
        self.btn_export_one.clicked.connect(self._export_current)
        self.variables_table.selectionChanged.connect(self._on_row_selected)
        self.variables_table.variablesEdited.connect(self._on_row_selected)
        self.mapping_table.itemChanged.connect(self._on_mapping_changed)
        self.name_pattern_edit.editingFinished.connect(self._on_name_pattern_changed)

    def _open_background(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Background Image", "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*)",
        )
        if path:
            self.project.template_config.background_path = path
            self._refresh_preview()
            self.statusBar().showMessage(f"Background: {Path(path).name}")

    def _open_kra_template(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Krita Template", "",
            "Krita Files (*.kra);;All Files (*)",
        )
        if path:
            try:
                from core.kra_parser import KraTemplate, list_text_layer_details
                template = KraTemplate.load(path)
                self.project.kra_template_path = path
                self.project.template_config.width = template.width
                self.project.template_config.height = template.height
                self.project.text_layer_mappings.clear()
                self.project.template_config.overlays.clear()
                if template.merged_preview:
                    preview_path = self._save_template_preview(template.merged_preview, path)
                    self.project.kra_preview_path = preview_path
                    self.project.template_config.background_path = preview_path
                details = list_text_layer_details(template)
                for index, detail in enumerate(details, start=1):
                    variable_name = f"text_{index}"
                    if variable_name not in self.project.variable_columns:
                        self.project.variable_columns.append(variable_name)
                    self.project.upsert_text_layer_mapping(
                        layer_name=detail.layer.name,
                        variable_name=variable_name,
                        svg_path=detail.svg_path,
                        source_text=detail.text,
                    )
                    self.project.template_config.overlays.append(
                        TextOverlay(
                            text=f"{{{variable_name}}}",
                            x=int(detail.x or detail.layer.x),
                            y=int(detail.y or detail.layer.y),
                            font_size=parse_font_size(detail.font_size),
                            color=detail.fill or "#ffffff",
                        )
                    )
                self._refresh_mapping_table()
                self.variables_table.refresh_from_project()
                if template.merged_preview:
                    self.preview.set_image(template.merged_preview)
                from core.validation import validate_youtube_template
                warnings = validate_youtube_template(
                    template.width,
                    template.height,
                    self.project.text_layer_mappings,
                )
                suffix = f" - {warnings[0]}" if warnings else ""
                self.statusBar().showMessage(
                    f"Template: {template.name} ({template.width}x{template.height}){suffix}"
                )
            except Exception as exc:
                logger.error("Failed to load .kra: %s", exc)
                QMessageBox.warning(self, "Error", f"Failed to load template:\n{exc}")

    def _save_template_preview(self, image, template_path: str) -> str:
        cache_dir = Path(tempfile.gettempdir()) / "thumbforge"
        cache_dir.mkdir(parents=True, exist_ok=True)
        output_path = cache_dir / f"{Path(template_path).stem}_merged.png"
        image.save(output_path, format="PNG")
        return str(output_path)

    def _on_row_selected(self, variables: dict[str, str]):
        self._refresh_preview(variables)

    def _refresh_preview(self, variables: dict[str, str] | None = None):
        variables = variables or {}
        try:
            image = render_thumbnail(self.project.template_config, variables)
            self.preview.set_image(image)
        except Exception as exc:
            logger.error("Preview render failed: %s", exc)

    def _refresh_mapping_table(self):
        self._loading_mappings = True
        try:
            self.mapping_table.setRowCount(0)
            for mapping in self.project.text_layer_mappings:
                row = self.mapping_table.rowCount()
                self.mapping_table.insertRow(row)
                layer_item = QTableWidgetItem(mapping.layer_name)
                layer_item.setFlags(layer_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                source_item = QTableWidgetItem(mapping.source_text)
                source_item.setFlags(source_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                variable_item = QTableWidgetItem(mapping.variable_name)
                self.mapping_table.setItem(row, 0, layer_item)
                self.mapping_table.setItem(row, 1, source_item)
                self.mapping_table.setItem(row, 2, variable_item)
        finally:
            self._loading_mappings = False

    def _on_mapping_changed(self, item: QTableWidgetItem):
        if self._loading_mappings or item.column() != 2:
            return
        row = item.row()
        if 0 <= row < len(self.project.text_layer_mappings):
            variable_name = item.text().strip()
            if not variable_name:
                return
            self.project.text_layer_mappings[row].variable_name = variable_name
            if row < len(self.project.template_config.overlays):
                self.project.template_config.overlays[row].text = f"{{{variable_name}}}"
            if variable_name not in self.project.variable_columns:
                self.project.variable_columns.append(variable_name)
                self.variables_table.refresh_from_project()

    def _on_name_pattern_changed(self):
        pattern = self.name_pattern_edit.text().strip()
        self.project.name_pattern = pattern or "thumb_{episode}"
        if not pattern:
            self.name_pattern_edit.setText(self.project.name_pattern)

    def _sync_project_from_ui(self):
        self.project.rows = self.variables_table.all_variables()
        self._on_name_pattern_changed()

    def _open_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Thumbforge Project",
            "",
            "Thumbforge Projects (*.tfproj *.json);;All Files (*)",
        )
        if not path:
            return
        try:
            self.project = ThumbforgeProject.load(path)
            self.project_path = path
            self.variables_table.project = self.project
            self.variables_table.refresh_from_project()
            self.name_pattern_edit.setText(self.project.name_pattern)
            self._refresh_mapping_table()
            self._refresh_preview(self.variables_table.current_variables() or {})
            self.statusBar().showMessage(f"Project loaded: {Path(path).name}")
        except Exception as exc:
            logger.error("Failed to open project: %s", exc)
            QMessageBox.warning(self, "Error", f"Failed to open project:\n{exc}")

    def _save_project(self):
        self._sync_project_from_ui()
        path = self.project_path
        if not path:
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Thumbforge Project",
                "thumbnail.tfproj",
                "Thumbforge Projects (*.tfproj);;All Files (*)",
            )
            if not path:
                return
            self.project_path = path
        try:
            self.project.save(path)
            self.statusBar().showMessage(f"Project saved: {Path(path).name}")
        except Exception as exc:
            logger.error("Failed to save project: %s", exc)
            QMessageBox.warning(self, "Error", f"Failed to save project:\n{exc}")

    def _export_current(self):
        self._sync_project_from_ui()
        row = self.variables_table.current_variables()
        if not row:
            self.statusBar().showMessage("No row selected.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Thumbnail", "thumbnail.png",
            "PNG (*.png);;JPEG (*.jpg)",
        )
        if path:
            worker = ExportWorker(
                mode="current",
                template_config=deepcopy(self.project.template_config),
                kra_template_path=self.project.kra_template_path,
                text_layer_mappings=deepcopy(self.project.text_layer_mappings),
                variables=deepcopy(row),
                output_path=path,
                name_pattern=self.project.name_pattern,
            )
            self._start_export(worker)

    def _export_all(self):
        self._sync_project_from_ui()
        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not output_dir:
            return
        rows = self.variables_table.all_variables()
        if not rows:
            self.statusBar().showMessage("No rows to export.")
            return
        worker = ExportWorker(
            mode="batch",
            template_config=deepcopy(self.project.template_config),
            kra_template_path=self.project.kra_template_path,
            text_layer_mappings=deepcopy(self.project.text_layer_mappings),
            rows=deepcopy(rows),
            output_dir=output_dir,
            name_pattern=self.project.name_pattern,
        )
        self._start_export(worker)

    def _start_export(self, worker: ExportWorker):
        if self._export_thread is not None:
            self.statusBar().showMessage("Export already running.")
            return

        self.btn_export.setEnabled(False)
        self.btn_export_one.setEnabled(False)
        self.statusBar().showMessage("Export running...")

        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.completed.connect(self._on_export_completed)
        worker.failed.connect(self._on_export_failed)
        worker.completed.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.completed.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_export_worker)

        self._export_thread = thread
        self._export_worker = worker
        thread.start()

    def _on_export_completed(self, title: str, message: str):
        QMessageBox.information(self, title, message)
        self.statusBar().showMessage(message.splitlines()[0])

    def _on_export_failed(self, message: str):
        QMessageBox.warning(self, "Export Failed", message)
        self.statusBar().showMessage("Export failed.")

    def _clear_export_worker(self):
        self._export_thread = None
        self._export_worker = None
        self.btn_export.setEnabled(True)
        self.btn_export_one.setEnabled(True)
