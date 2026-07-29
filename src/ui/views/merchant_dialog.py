from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from src.application.dto import Category
from src.domain.errors import DomainError
from src.i18n import t
from src.ui.styles import app_qss
from src.ui.themed_combo import ThemedComboBox


class MerchantDialog(QDialog):
    """Единое окно: категория + название места."""

    def __init__(
        self,
        categories: list[Category],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("merchant_dialog.title"))
        self.setStyleSheet(app_qss())
        self.setMinimumWidth(400)
        self._result: tuple[str, int] | None = None

        self.category_combo = ThemedComboBox(self)
        for cat in categories:
            self.category_combo.addItem(cat.name, cat.id)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(t("merchant_dialog.name.placeholder"))

        form = QFormLayout()
        form.addRow(t("merchant_dialog.field.category"), self.category_combo)
        form.addRow(t("merchant_dialog.field.name"), self.name_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(t("merchant_dialog.btn.add"))
        cancel = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        cancel.setText(t("common.cancel"))
        cancel.setObjectName("secondary")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.name_edit.setFocus()

    def _accept(self) -> None:
        try:
            if self.category_combo.currentData() is None:
                raise DomainError(t("merchant_dialog.err.need_category"))
            name = self.name_edit.text().strip()
            if not name:
                raise DomainError(t("merchant_dialog.err.need_name"))
            self._result = (name, int(self.category_combo.currentData()))
            self.accept()
        except DomainError as exc:
            QMessageBox.warning(self, t("common.app_name"), str(exc))

    def payload(self) -> tuple[str, int]:
        assert self._result is not None
        return self._result
