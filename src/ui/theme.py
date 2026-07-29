from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Palette:
    text: str
    muted: str
    window: str
    shell: str
    shell_border: str
    accent: str
    accent_hover: str
    accent_disabled: str
    accent_disabled_text: str
    surface: str
    surface_alt: str
    input_bg: str
    input_border: str
    secondary_bg: str
    secondary_hover: str
    danger_text: str
    danger_hover: str
    table_border: str
    table_row_line: str
    table_header: str
    tab_border: str
    tab_border_hover: str
    weekend: str
    on_accent: str
    chart_grid: str


LIGHT = Palette(
    text="#1c2430",
    muted="#667083",
    window="#ece8e1",
    shell="#fffdf8",
    shell_border="#d7d0c3",
    accent="#2f5d50",
    accent_hover="#3a7262",
    accent_disabled="#b7c2bc",
    accent_disabled_text="#eef2f0",
    surface="#f7f3ec",
    surface_alt="#f3eee6",
    input_bg="#ffffff",
    input_border="#cfc7b8",
    secondary_bg="#efe9df",
    secondary_hover="#e3dccf",
    danger_text="#8a3b32",
    danger_hover="#eadad6",
    table_border="#e0d9cc",
    table_row_line="#eee8de",
    table_header="#f3eee6",
    tab_border="#7a7266",
    tab_border_hover="#5c554c",
    weekend="#8a3b32",
    on_accent="#ffffff",
    chart_grid="#e5ddd0",
)

DARK = Palette(
    text="#e8e6e1",
    muted="#9aa3b0",
    window="#16191d",
    shell="#1e2228",
    shell_border="#343b45",
    accent="#4a8f7a",
    accent_hover="#5aa48c",
    accent_disabled="#3a4540",
    accent_disabled_text="#7a8580",
    surface="#262b33",
    surface_alt="#2c323c",
    input_bg="#262b33",
    input_border="#3d4450",
    secondary_bg="#2c323c",
    secondary_hover="#363d49",
    danger_text="#e09a90",
    danger_hover="#3a2c2a",
    table_border="#343b45",
    table_row_line="#2c323c",
    table_header="#262b33",
    tab_border="#6b7380",
    tab_border_hover="#8a93a0",
    weekend="#e09a90",
    on_accent="#ffffff",
    chart_grid="#262b32",
)

_theme_name: str = "light"


def current_theme_name() -> str:
    return _theme_name


def current_palette() -> Palette:
    return DARK if _theme_name == "dark" else LIGHT


def set_theme_name(name: str) -> None:
    global _theme_name
    _theme_name = "dark" if name == "dark" else "light"


def build_app_qss(p: Palette | None = None) -> str:
    p = p or current_palette()
    return f"""
QWidget {{
  font-family: "Segoe UI", sans-serif;
  font-size: 13px;
  color: {p.text};
}}
QMainWindow {{
  background: {p.window};
}}
QWidget#central {{
  background: {p.window};
}}
QFrame#shell {{
  background: {p.shell};
  border: 1px solid {p.shell_border};
  border-radius: 12px;
}}
QLabel#brand {{
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: {p.text};
}}
QLabel#subtitle {{
  color: {p.muted};
}}
QLabel#total {{
  font-size: 32px;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: {p.text};
}}
QLabel#emptyTitle {{
  font-size: 18px;
  font-weight: 600;
  color: {p.text};
}}
QLabel#sectionTitle {{
  font-size: 12px;
  font-weight: 600;
  color: {p.muted};
  text-transform: uppercase;
  letter-spacing: 0.04em;
}}
QPushButton {{
  background: {p.accent};
  color: {p.on_accent};
  border: none;
  padding: 10px 16px;
  border-radius: 8px;
  min-height: 22px;
}}
QPushButton:hover {{ background: {p.accent_hover}; }}
QPushButton:disabled {{ background: {p.accent_disabled}; color: {p.accent_disabled_text}; }}
QPushButton#secondary {{
  background: {p.secondary_bg};
  color: {p.text};
}}
QPushButton#secondary:hover {{ background: {p.secondary_hover}; }}
QPushButton#danger {{
  background: {p.secondary_bg};
  color: {p.danger_text};
}}
QPushButton#danger:hover {{ background: {p.danger_hover}; }}
QLineEdit, QComboBox, QDateEdit, QAbstractSpinBox, QTextEdit, QListWidget, QTableWidget {{
  background: {p.input_bg};
  border: 1px solid {p.input_border};
  border-radius: 8px;
  padding: 8px 10px;
  min-height: 18px;
  color: {p.text};
  selection-background-color: {p.accent};
  selection-color: {p.on_accent};
}}
QComboBox, QDateEdit {{
  padding-right: 28px;
}}
QComboBox::drop-down, QDateEdit::drop-down {{
  subcontrol-origin: padding;
  subcontrol-position: center right;
  width: 28px;
  border: none;
  background: transparent;
}}
QComboBox::down-arrow, QDateEdit::down-arrow {{
  width: 10px;
  height: 10px;
}}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
  width: 0;
  border: none;
  background: transparent;
}}
QComboBox QAbstractItemView {{
  background: {p.input_bg};
  border: 1px solid {p.input_border};
  border-radius: 6px;
  selection-background-color: {p.accent};
  selection-color: {p.on_accent};
  outline: 0;
  padding: 4px;
  color: {p.text};
}}
QListWidget, QTableWidget {{
  padding: 0;
}}
QTableWidget {{
  background: {p.input_bg};
  border: 1px solid {p.table_border};
  border-radius: 10px;
  gridline-color: transparent;
  outline: none;
  alternate-background-color: {p.surface};
  selection-background-color: {p.accent};
  selection-color: {p.on_accent};
}}
QTableWidget::item {{
  padding: 8px 12px;
  border: none;
  border-bottom: 1px solid {p.table_row_line};
}}
QTableWidget::item:selected {{
  background: {p.accent};
  color: {p.on_accent};
}}
QHeaderView::section {{
  background: {p.table_header};
  color: {p.muted};
  padding: 10px 12px;
  border: none;
  border-bottom: 1px solid {p.table_border};
  border-right: 1px solid {p.table_row_line};
  font-weight: 600;
  font-size: 12px;
}}
QHeaderView::section:last {{
  border-right: none;
}}
QTableCornerButton::section {{
  background: {p.table_header};
  border: none;
}}
QCheckBox {{
  spacing: 8px;
  padding: 4px 0;
  color: {p.text};
}}
QCheckBox::indicator {{
  width: 18px;
  height: 18px;
  border: 2px solid {p.tab_border};
  border-radius: 4px;
  background: {p.input_bg};
}}
QCheckBox::indicator:checked {{
  background-color: {p.accent};
  border: 2px solid {p.accent};
  width: 18px;
  height: 18px;
}}
QRadioButton {{
  spacing: 8px;
  padding: 4px 14px 4px 2px;
  color: {p.text};
  min-height: 22px;
}}
QRadioButton::indicator {{
  width: 16px;
  height: 16px;
  border: 2px solid {p.tab_border};
  border-radius: 9px;
  background: {p.input_bg};
}}
QRadioButton::indicator:hover {{
  border-color: {p.tab_border_hover};
}}
QRadioButton::indicator:checked {{
  width: 16px;
  height: 16px;
  border: 4px solid {p.accent};
  border-radius: 9px;
  background: {p.on_accent};
}}
QDialog {{
  background: {p.shell};
}}
QDialogButtonBox QPushButton {{
  min-width: 96px;
}}
QFrame#card {{
  background: {p.surface};
  border: 1px solid {p.table_border};
  border-radius: 10px;
}}
QFrame#filterPanel {{
  background: {p.surface};
  border-right: 1px solid {p.table_border};
}}
QScrollArea#filterScroll {{
  background: {p.surface};
  border: none;
}}
QScrollArea#filterScroll > QWidget > QWidget {{
  background: {p.surface};
}}
QListWidget#merchantFilterList {{
  min-height: 140px;
  max-height: 220px;
  outline: none;
}}
QFrame#tabBar {{
  background: transparent;
  border: none;
}}
QPushButton#tabBtn {{
  background: {p.shell};
  color: {p.text};
  padding: 8px 16px;
  border: 2px solid {p.tab_border};
  border-radius: 8px;
  font-weight: 600;
  min-height: 22px;
}}
QPushButton#tabBtn:hover {{
  background: {p.input_bg};
  color: {p.text};
  border: 2px solid {p.tab_border_hover};
}}
QPushButton#tabBtn:checked {{
  background: {p.shell};
  color: {p.accent};
  border: 2px solid {p.accent};
}}
QToolButton#themeCombo {{
  background: transparent;
  border: none;
  color: {p.text};
  font-size: 12px;
  font-weight: 600;
  padding: 8px 12px 8px 6px;
  min-height: 20px;
}}
QToolButton#themeCombo:hover {{
  color: {p.accent};
  background: transparent;
  border: none;
}}
QToolButton#themeCombo::menu-indicator {{
  image: none;
  width: 0;
}}
QMenu#themeMenu {{
  background: {p.input_bg};
  border: 1px solid {p.input_border};
  border-radius: 6px;
  padding: 4px;
  color: {p.text};
}}
QMenu#themeMenu::item {{
  padding: 6px 14px;
  border-radius: 4px;
}}
QMenu#themeMenu::item:selected {{
  background: {p.accent};
  color: {p.on_accent};
}}
QMessageBox {{
  background: {p.shell};
}}
QMessageBox QLabel {{
  color: {p.text};
}}
"""


# Back-compat for imports that still expect APP_QSS.
APP_QSS = build_app_qss(LIGHT)


def app_qss() -> str:
    return build_app_qss(current_palette())
