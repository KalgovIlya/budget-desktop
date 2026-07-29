from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from src.application.dto import Merchant
from src.domain.errors import DomainError
from src.i18n import t
from src.ui.styles import app_qss
from src.ui.themed_combo import ThemedComboBox


class MerchantMergeDialog(QDialog):
    def __init__(self, merchants: list[Merchant], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("merchant_merge.title"))
        self.setStyleSheet(app_qss())
        self.setMinimumWidth(420)
        self._merchants = merchants
        self._result: tuple[int, list[int], str] | None = None

        self.survivor_combo = ThemedComboBox()
        for m in merchants:
            label = f"{m.display_name} · {m.category_name}"
            self.survivor_combo.addItem(label, m.id)

        self.name_edit = QLineEdit()
        self.survivor_combo.currentIndexChanged.connect(self._on_survivor_changed)
        self._on_survivor_changed()

        form = QFormLayout()
        form.addRow(t("merchant_merge.field.survivor"), self.survivor_combo)
        form.addRow(t("merchant_merge.field.display_name"), self.name_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(t("merchant_merge.btn.merge"))
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

    def _on_survivor_changed(self) -> None:
        sid = self.survivor_combo.currentData()
        for m in self._merchants:
            if m.id == sid:
                self.name_edit.setText(m.display_name)
                break

    def _accept(self) -> None:
        try:
            survivor_id = self.survivor_combo.currentData()
            if survivor_id is None:
                raise DomainError(t("merchant_merge.err.need_survivor"))
            name = self.name_edit.text().strip()
            if not name:
                raise DomainError(t("merchant_merge.err.need_name"))
            source_ids = [m.id for m in self._merchants]
            self._result = (int(survivor_id), source_ids, name)
            self.accept()
        except DomainError as exc:
            QMessageBox.warning(self, t("common.app_name"), str(exc))

    def payload(self) -> tuple[int, list[int], str]:
        assert self._result is not None
        return self._result
