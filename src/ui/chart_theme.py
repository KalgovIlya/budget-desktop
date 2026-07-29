from __future__ import annotations

from PySide6.QtCharts import QAbstractAxis, QChart
from PySide6.QtGui import QBrush, QColor, QPen

from src.ui.theme import current_palette


def style_chart(chart: QChart) -> None:
    p = current_palette()
    chart.setBackgroundBrush(QBrush(QColor(p.shell)))
    chart.setPlotAreaBackgroundVisible(True)
    chart.setPlotAreaBackgroundBrush(QBrush(QColor(p.shell)))
    chart.setTitleBrush(QBrush(QColor(p.text)))
    chart.setBackgroundRoundness(0)
    if chart.legend() is not None:
        chart.legend().setLabelColor(QColor(p.text))


def style_axis(axis: QAbstractAxis, *, show_grid: bool = True) -> None:
    p = current_palette()
    axis.setLabelsColor(QColor(p.muted))
    axis.setLinePen(QPen(QColor(p.table_border)))
    if show_grid:
        grid = QPen(QColor(p.chart_grid))
        grid.setWidth(1)
        axis.setGridLinePen(grid)
        axis.setGridLineVisible(True)
    else:
        axis.setGridLineVisible(False)
    if hasattr(axis, "setMinorGridLineVisible"):
        axis.setMinorGridLineVisible(False)  # type: ignore[attr-defined]
    if hasattr(axis, "setTitleBrush"):
        axis.setTitleBrush(QBrush(QColor(p.muted)))  # type: ignore[attr-defined]


def thin_axis_labels(labels: list[str], *, max_visible: int = 8) -> list[str]:
    """Keep chart readable: hide most category labels when there are too many.

    Uses a space (not "") so QBarCategoryAxis keeps stable category slots.
    """
    n = len(labels)
    if n <= max_visible:
        return labels
    step = max(1, (n - 1) // (max_visible - 1))
    out = [" "] * n
    for i in range(0, n, step):
        out[i] = labels[i]
    out[-1] = labels[-1]
    return out
