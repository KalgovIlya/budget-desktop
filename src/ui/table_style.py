from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView, QTableWidget


def style_data_table(table: QTableWidget) -> None:
    """Unified look for expenses / stats tables."""
    table.setShowGrid(False)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    table.setWordWrap(False)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(38)
    header = table.horizontalHeader()
    header.setHighlightSections(False)
    header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    header.setStretchLastSection(False)
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)


def apply_column_widths(
    table: QTableWidget,
    *,
    fixed_cols: tuple[int, ...] = (),
    stretch_cols: tuple[int, ...] = (),
) -> None:
    """Size fixed columns by content; share leftover across stretch columns."""
    header = table.horizontalHeader()
    table.resizeColumnsToContents()
    for col in range(table.columnCount()):
        if col in stretch_cols:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        elif col in fixed_cols:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        else:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
