from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget

from src.i18n import t


def ask_yes_no(parent: QWidget | None, text: str, *, title: str | None = None) -> bool:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(title if title is not None else t("common.app_name"))
    box.setText(text)
    box.setStandardButtons(
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    yes = box.button(QMessageBox.StandardButton.Yes)
    no = box.button(QMessageBox.StandardButton.No)
    if yes is not None:
        yes.setText(t("common.yes"))
    if no is not None:
        no.setText(t("common.no"))
    return box.exec() == QMessageBox.StandardButton.Yes
