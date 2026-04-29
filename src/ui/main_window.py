"""Main window for Thumbforge."""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.project import ThumbforgeProject
from core.renderer import TemplateConfig, TextOverlay, render_thumbnail
from ui.preview_widget import PreviewWidget
from ui.variables_table import VariablesTable

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Thumbforge")
        self.setMinimumSize(960, 600)

        self.project = ThumbforgeProject()

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
        self.btn_export = QPushButton("Export All")
        self.btn_export_one = QPushButton("Export Current")
        toolbar.addWidget(self.btn_open_bg)
        toolbar.addWidget(self.btn_open_kra)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_export_one)
        toolbar.addWidget(self.btn_export)
        root_layout.addLayout(toolbar)

        # Main splitter: preview | variables table
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.preview = PreviewWidget()
        splitter.addWidget(self.preview)

        self.variables_table = VariablesTable(self.project)
        splitter.addWidget(self.variables_table)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        root_layout.addWidget(splitter, stretch=1)

        # Status bar
        self.statusBar().showMessage("Ready")

    def _connect_signals(self):
        self.btn_open_bg.clicked.connect(self._open_background)
        self.btn_open_kra.clicked.connect(self._open_kra_template)
        self.btn_export.clicked.connect(self._export_all)
        self.btn_export_one.clicked.connect(self._export_current)
        self.variables_table.selectionChanged.connect(self._on_row_selected)

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
                from core.kra_parser import KraTemplate
                template = KraTemplate.load(path)
                self.project.template_config.width = template.width
                self.project.template_config.height = template.height
                if template.merged_preview:
                    self.preview.set_image(template.merged_preview)
                self.statusBar().showMessage(f"Template: {template.name} ({template.width}x{template.height})")
            except Exception as exc:
                logger.error("Failed to load .kra: %s", exc)
                QMessageBox.warning(self, "Error", f"Failed to load template:\n{exc}")

    def _on_row_selected(self, variables: dict[str, str]):
        self._refresh_preview(variables)

    def _refresh_preview(self, variables: dict[str, str] | None = None):
        variables = variables or {}
        try:
            image = render_thumbnail(self.project.template_config, variables)
            self.preview.set_image(image)
        except Exception as exc:
            logger.error("Preview render failed: %s", exc)

    def _export_current(self):
        row = self.variables_table.current_variables()
        if not row:
            self.statusBar().showMessage("No row selected.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Thumbnail", "thumbnail.png",
            "PNG (*.png);;JPEG (*.jpg)",
        )
        if path:
            from core.renderer import export_thumbnail
            image = render_thumbnail(self.project.template_config, row)
            export_thumbnail(image, path)
            self.statusBar().showMessage(f"Exported: {path}")

    def _export_all(self):
        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not output_dir:
            return
        from core.renderer import batch_export
        rows = self.variables_table.all_variables()
        if not rows:
            self.statusBar().showMessage("No rows to export.")
            return
        exported = batch_export(
            self.project.template_config,
            rows,
            output_dir,
            name_pattern=self.project.name_pattern,
        )
        self.statusBar().showMessage(f"Exported {len(exported)} thumbnail(s) to {output_dir}")
