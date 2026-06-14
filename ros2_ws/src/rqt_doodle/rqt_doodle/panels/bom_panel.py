"""Bill of Materials panel — editable table with CSV export."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from python_qt_binding.QtCore import Qt, pyqtSignal as Signal
from python_qt_binding.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


_COLUMNS = ["Component", "Category", "Qty", "Supplier", "Part #", "Unit Price (£)", "Notes"]
_COL_IDX = {name: i for i, name in enumerate(_COLUMNS)}


class BOMPanel(QWidget):
    """Displays and manages the Bill of Materials."""

    bom_changed = Signal(list)  # emits updated BOM list of dicts

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Toolbar ────────────────────────────────────────────────────────
        toolbar = QWidget()
        toolbar.setObjectName("ViewerToolbar")
        bar = QHBoxLayout(toolbar)
        bar.setContentsMargins(8, 4, 8, 4)
        bar.setSpacing(6)

        self._total_label = QLabel("0 components  |  Total: £0.00")
        self._total_label.setStyleSheet("color: #9d9d9d; font-size: 11px;")
        bar.addWidget(self._total_label)
        bar.addStretch()

        add_btn = QPushButton("+ Add row")
        add_btn.setProperty("secondary", True)
        add_btn.clicked.connect(self._add_empty_row)
        bar.addWidget(add_btn)

        del_btn = QPushButton("Remove selected")
        del_btn.setProperty("secondary", True)
        del_btn.clicked.connect(self._remove_selected)
        bar.addWidget(del_btn)

        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self._export_csv)
        bar.addWidget(export_btn)

        layout.addWidget(toolbar)

        # ── Table ──────────────────────────────────────────────────────────
        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)

        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(_COL_IDX["Component"], QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(_COL_IDX["Notes"], QHeaderView.ResizeMode.Stretch)
        for col in ("Category", "Qty", "Part #", "Unit Price (£)"):
            hh.setSectionResizeMode(_COL_IDX[col], QHeaderView.ResizeMode.ResizeToContents)

        self._table.itemChanged.connect(self._on_cell_changed)
        layout.addWidget(self._table)

    # ── Public API ──────────────────────────────────────────────────────────

    def set_bom(self, items: list[dict[str, Any]]) -> None:
        self._table.blockSignals(True)
        self._table.setRowCount(0)
        for item in items:
            self._append_row(item)
        self._table.blockSignals(False)
        self._refresh_totals()

    def get_bom(self) -> list[dict[str, Any]]:
        rows = []
        for r in range(self._table.rowCount()):
            row: dict[str, Any] = {}
            for col_name, col_idx in _COL_IDX.items():
                cell = self._table.item(r, col_idx)
                row[col_name.lower().replace(" ", "_").replace("(£)", "").strip("_")] = (
                    cell.text() if cell else ""
                )
            rows.append(row)
        return rows

    # ── Internal ────────────────────────────────────────────────────────────

    def _append_row(self, item: dict[str, Any]) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        mapping = {
            "Component": item.get("name", item.get("component", "")),
            "Category": item.get("category", ""),
            "Qty": str(item.get("qty", item.get("quantity", 1))),
            "Supplier": item.get("supplier", ""),
            "Part #": item.get("part_number", item.get("part_#", "")),
            "Unit Price (£)": str(item.get("unit_price", item.get("unit_price_£", ""))),
            "Notes": item.get("notes", ""),
        }
        for col_name, value in mapping.items():
            cell = QTableWidgetItem(value)
            if col_name == "Qty":
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, _COL_IDX[col_name], cell)

    def _add_empty_row(self) -> None:
        self._append_row({})
        self._table.scrollToBottom()

    def _remove_selected(self) -> None:
        rows = sorted(
            {idx.row() for idx in self._table.selectedIndexes()}, reverse=True
        )
        for row in rows:
            self._table.removeRow(row)
        self._refresh_totals()
        self.bom_changed.emit(self.get_bom())

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export BOM as CSV", "bom.csv", "CSV files (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(_COLUMNS)
            for r in range(self._table.rowCount()):
                writer.writerow(
                    (self._table.item(r, c).text() if self._table.item(r, c) else "")
                    for c in range(len(_COLUMNS))
                )

    def _on_cell_changed(self) -> None:
        self._refresh_totals()
        self.bom_changed.emit(self.get_bom())

    def _refresh_totals(self) -> None:
        n = self._table.rowCount()
        total = 0.0
        qty_col = _COL_IDX["Qty"]
        price_col = _COL_IDX["Unit Price (£)"]
        for r in range(n):
            try:
                qty = int(self._table.item(r, qty_col).text())
                price = float(self._table.item(r, price_col).text())
                total += qty * price
            except (AttributeError, ValueError):
                pass
        self._total_label.setText(
            f"{n} component{'s' if n != 1 else ''}  |  Total: £{total:.2f}"
        )
