from __future__ import annotations

from PySide6.QtCore import QEvent, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPalette
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QListView,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionViewItem,
)

from src.ui.theme import current_palette

_ROW_HEIGHT = 30


class _ComboItemDelegate(QStyledItemDelegate):
    """Paint selection ourselves — Windows Fusion ignores QSS on combo popup."""

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:  # noqa: N802
        size = super().sizeHint(option, index)
        return QSize(size.width(), max(size.height(), _ROW_HEIGHT))

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        p = current_palette()
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        selected = bool(opt.state & QStyle.StateFlag.State_Selected)
        hovered = bool(opt.state & QStyle.StateFlag.State_MouseOver)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if selected:
            painter.fillRect(opt.rect.adjusted(2, 1, -2, -1), QColor(p.accent))
            painter.setPen(QColor(p.on_accent))
        elif hovered:
            painter.fillRect(opt.rect.adjusted(2, 1, -2, -1), QColor(p.surface))
            painter.setPen(QColor(p.text))
        else:
            painter.setPen(QColor(p.text))
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        painter.drawText(
            opt.rect.adjusted(10, 0, -10, 0),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            str(text),
        )
        painter.restore()


def apply_combo_theme(combo: QComboBox) -> None:
    p = current_palette()
    if not isinstance(combo.view(), QListView):
        combo.setView(QListView())
    view = combo.view()
    view.setItemDelegate(_ComboItemDelegate(view))
    view.setMouseTracking(True)
    view.setUniformItemSizes(True)
    view.setStyleSheet(
        f"QListView {{ background:{p.input_bg}; border:1px solid {p.input_border};"
        f" border-radius:6px; padding:4px; outline:0; color:{p.text}; }}"
    )
    pal = view.palette()
    pal.setColor(QPalette.ColorRole.Base, QColor(p.input_bg))
    pal.setColor(QPalette.ColorRole.Text, QColor(p.text))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(p.accent))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(p.on_accent))
    view.setPalette(pal)
    popup = view.window()
    if popup is not None:
        popup.setStyleSheet(view.styleSheet())
        popup.setPalette(pal)
    completer = combo.completer()
    if completer is not None and completer.popup() is not None:
        popup_view = completer.popup()
        popup_view.setItemDelegate(_ComboItemDelegate(popup_view))
        popup_view.setMouseTracking(True)
        popup_view.setUniformItemSizes(True)
        popup_view.setStyleSheet(view.styleSheet())
        popup_view.setPalette(pal)


class ThemedComboBox(QComboBox):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        apply_combo_theme(self)

    def showPopup(self) -> None:  # noqa: N802
        apply_combo_theme(self)
        super().showPopup()
        apply_combo_theme(self)


class SearchableComboBox(ThemedComboBox):
    """Dropdown of known values + type-to-filter / free text for new names.

    Click field → completer popup (empty text: all items; else contains-filter).
    Typing keeps the same completer behavior; free text for new names allowed.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setMaxVisibleItems(12)
        completer = QCompleter(self.model(), self)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setMaxVisibleItems(12)
        self.setCompleter(completer)
        line = self.lineEdit()
        if line is not None:
            line.installEventFilter(self)
            line.textEdited.connect(lambda _text: QTimer.singleShot(0, self._fit_completer_popup))
        apply_combo_theme(self)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        line = self.lineEdit()
        if (
            line is not None
            and obj is line
            and isinstance(event, QMouseEvent)
            and event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
        ):
            # After focus/selection settle, open suggestions for this click.
            QTimer.singleShot(0, self._open_on_click)
        return super().eventFilter(obj, event)

    def _open_on_click(self) -> None:
        if not self.isVisible() or not self.isEnabled():
            return
        completer = self.completer()
        if completer is None:
            return
        # Empty prefix → full list; non-empty → contains-filter (same as typing).
        completer.setCompletionPrefix(self.currentText().strip())
        apply_combo_theme(self)
        completer.complete()
        self._fit_completer_popup()

    def _fit_completer_popup(self) -> None:
        completer = self.completer()
        if completer is None:
            return
        popup = completer.popup()
        if popup is None or not popup.isVisible():
            return
        visible = min(max(completer.completionCount(), 1), completer.maxVisibleItems())
        frame = popup.frameWidth() * 2
        height = visible * _ROW_HEIGHT + frame + 8
        popup.setMinimumHeight(height)
        popup.resize(max(popup.width(), self.width()), height)

    def set_items(self, names: list[str], current: str | None = None) -> None:
        previous = self.currentText() if current is None else current
        self.blockSignals(True)
        self.clear()
        self.addItems(names)
        self.setEditText(previous)
        self.blockSignals(False)
        apply_combo_theme(self)

    def setPlaceholderText(self, text: str) -> None:  # noqa: N802
        line = self.lineEdit()
        if line is not None:
            line.setPlaceholderText(text)
        else:
            super().setPlaceholderText(text)

    def text(self) -> str:
        return self.currentText().strip()
