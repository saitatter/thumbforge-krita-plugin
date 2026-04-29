"""Live preview widget for rendered thumbnails."""
from __future__ import annotations

from io import BytesIO

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PreviewWidget(QWidget):
    """Shows a scaled preview of the current thumbnail."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel("No preview")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setMinimumSize(640, 360)
        self.label.setStyleSheet("background-color: #1e1e1e; color: #888;")
        layout.addWidget(self.label)

        self._pixmap: QPixmap | None = None

    def set_image(self, pil_image) -> None:
        """Update the preview from a PIL Image."""
        buf = BytesIO()
        pil_image.save(buf, format="PNG")
        buf.seek(0)

        qimg = QImage()
        qimg.loadFromData(buf.read())
        self._pixmap = QPixmap.fromImage(qimg)
        self._update_display()

    def _update_display(self):
        if self._pixmap is None:
            return
        scaled = self._pixmap.scaled(
            self.label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_display()
