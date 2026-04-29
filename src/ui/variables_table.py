"""Editable variables table for batch thumbnail generation."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.project import ThumbforgeProject


class VariablesTable(QWidget):
    """Table where each row is a set of variables for one thumbnail."""

    selectionChanged = Signal(dict)  # emits current row's variables

    def __init__(self, project: ThumbforgeProject, parent=None):
        super().__init__(parent)
        self.project = project

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Controls
        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("+ Add Row")
        self.btn_remove = QPushButton("- Remove Row")
        self.btn_add_col = QPushButton("+ Add Column")
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_remove)
        btn_row.addWidget(self.btn_add_col)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(len(project.variable_columns))
        self.table.setHorizontalHeaderLabels(project.variable_columns)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        self._load_rows()

        # Signals
        self.btn_add.clicked.connect(self._add_row)
        self.btn_remove.clicked.connect(self._remove_row)
        self.btn_add_col.clicked.connect(self._add_column)
        self.table.currentCellChanged.connect(self._on_selection)

    def _load_rows(self):
        for row_data in self.project.rows:
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
            for col_idx, col_name in enumerate(self.project.variable_columns):
                item = QTableWidgetItem(row_data.get(col_name, ""))
                self.table.setItem(row_idx, col_idx, item)

    def _add_row(self):
        row_idx = self.table.rowCount()
        self.table.insertRow(row_idx)
        # Pre-fill episode number
        if "episode" in self.project.variable_columns:
            col = self.project.variable_columns.index("episode")
            self.table.setItem(row_idx, col, QTableWidgetItem(str(row_idx + 1)))

    def _remove_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def _add_column(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Add Column", "Variable name:")
        if ok and name and name not in self.project.variable_columns:
            self.project.variable_columns.append(name)
            col_idx = self.table.columnCount()
            self.table.insertColumn(col_idx)
            self.table.setHorizontalHeaderItem(col_idx, QTableWidgetItem(name))

    def _on_selection(self, row, col, prev_row, prev_col):
        variables = self._row_to_dict(row)
        if variables is not None:
            self.selectionChanged.emit(variables)

    def _row_to_dict(self, row: int) -> dict[str, str] | None:
        if row < 0 or row >= self.table.rowCount():
            return None
        result: dict[str, str] = {}
        for col_idx, col_name in enumerate(self.project.variable_columns):
            item = self.table.item(row, col_idx)
            result[col_name] = item.text() if item else ""
        return result

    def current_variables(self) -> dict[str, str] | None:
        return self._row_to_dict(self.table.currentRow())

    def all_variables(self) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for row in range(self.table.rowCount()):
            d = self._row_to_dict(row)
            if d is not None:
                rows.append(d)
        return rows
