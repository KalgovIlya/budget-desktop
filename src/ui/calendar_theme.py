from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette, QTextCharFormat
from PySide6.QtWidgets import QCalendarWidget, QDateEdit, QToolButton, QWidget

from src.ui.theme import current_palette


def _calendar_qss() -> str:
    p = current_palette()
    return f"""
QCalendarWidget {{
  background: {p.shell};
  border: 1px solid {p.input_border};
}}
QCalendarWidget QWidget#qt_calendar_navigationbar {{
  background: {p.surface_alt};
  border: none;
  min-height: 40px;
}}
QCalendarWidget QToolButton {{
  background: transparent;
  color: {p.text};
  border: none;
  border-radius: 6px;
  padding: 6px 10px;
  margin: 4px;
  font-weight: 600;
}}
QCalendarWidget QToolButton:hover {{
  background: {p.secondary_hover};
}}
QCalendarWidget QToolButton::menu-indicator {{
  image: none;
  width: 0;
}}
QCalendarWidget QSpinBox {{
  background: {p.input_bg};
  border: 1px solid {p.input_border};
  border-radius: 6px;
  padding: 2px 6px;
  color: {p.text};
  selection-background-color: {p.accent};
  selection-color: {p.on_accent};
}}
QCalendarWidget QSpinBox::up-button,
QCalendarWidget QSpinBox::down-button {{
  width: 14px;
  border: none;
  background: transparent;
}}
QCalendarWidget QMenu {{
  background: {p.input_bg};
  border: 1px solid {p.input_border};
  color: {p.text};
}}
QCalendarWidget QMenu::item:selected {{
  background: {p.accent};
  color: {p.on_accent};
}}
QCalendarWidget QAbstractItemView:enabled {{
  background: {p.input_bg};
  color: {p.text};
  selection-background-color: {p.accent};
  selection-color: {p.on_accent};
  outline: none;
  font-size: 13px;
}}
QCalendarWidget QAbstractItemView:disabled {{
  color: {p.muted};
}}
"""


def theme_calendar(calendar: QCalendarWidget) -> None:
    p = current_palette()
    calendar.setStyleSheet(_calendar_qss())
    calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
    calendar.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.ShortDayNames)
    calendar.setGridVisible(False)
    calendar.setAutoFillBackground(True)

    weekday = QTextCharFormat()
    weekday.setForeground(QColor(p.text))
    weekend = QTextCharFormat()
    weekend.setForeground(QColor(p.weekend))
    for day in (
        Qt.DayOfWeek.Monday,
        Qt.DayOfWeek.Tuesday,
        Qt.DayOfWeek.Wednesday,
        Qt.DayOfWeek.Thursday,
        Qt.DayOfWeek.Friday,
    ):
        calendar.setWeekdayTextFormat(day, weekday)
    calendar.setWeekdayTextFormat(Qt.DayOfWeek.Saturday, weekend)
    calendar.setWeekdayTextFormat(Qt.DayOfWeek.Sunday, weekend)

    for child in calendar.findChildren(QWidget):
        name = child.objectName()
        if name == "qt_calendar_navigationbar":
            child.setAutoFillBackground(True)
            child.setStyleSheet(
                f"background:{p.surface_alt}; color:{p.text}; border:none; min-height:40px;"
            )
        elif isinstance(child, QToolButton):
            child.setAutoFillBackground(False)
            child.setStyleSheet(
                f"QToolButton {{ background:transparent; color:{p.text}; border:none;"
                f" border-radius:6px; padding:6px 10px; margin:4px; font-weight:600; }}"
                f"QToolButton:hover {{ background:{p.secondary_hover}; }}"
                "QToolButton::menu-indicator { image:none; width:0; }"
            )

    pal = calendar.palette()
    pal.setColor(QPalette.ColorRole.Window, QColor(p.shell))
    pal.setColor(QPalette.ColorRole.Base, QColor(p.input_bg))
    pal.setColor(QPalette.ColorRole.Text, QColor(p.text))
    pal.setColor(QPalette.ColorRole.Button, QColor(p.surface_alt))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(p.text))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(p.accent))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(p.on_accent))
    calendar.setPalette(pal)

    host = calendar.parentWidget()
    for widget in (calendar, host, calendar.window()):
        if widget is None:
            continue
        widget.setAutoFillBackground(True)
        wpal = widget.palette()
        wpal.setColor(QPalette.ColorRole.Window, QColor(p.shell))
        wpal.setColor(QPalette.ColorRole.Base, QColor(p.input_bg))
        widget.setPalette(wpal)


def theme_date_edit(edit: QDateEdit) -> None:
    edit.setCalendarPopup(True)
    cal = edit.calendarWidget()
    if cal is None:
        return
    theme_calendar(cal)

    def _retheme(*_args) -> None:
        current = edit.calendarWidget()
        if current is not None:
            theme_calendar(current)

    if not getattr(edit, "_budget_calendar_themed", False):
        cal.currentPageChanged.connect(_retheme)
        setattr(edit, "_budget_calendar_themed", True)
