from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from src.application.catalog_service import CatalogService
from src.application.dto import Expense, UiPreferences
from src.domain.errors import DomainError
from src.domain.money import Money
from src.i18n import t
from src.ui.calendar_theme import theme_date_edit
from src.ui.theme import app_qss
from src.ui.themed_combo import SearchableComboBox, ThemedComboBox


class ExpenseDialog(QDialog):
    def __init__(
        self,
        catalogs: CatalogService,
        prefs: UiPreferences,
        parent=None,
        expense: Expense | None = None,
        *,
        prefill: Expense | None = None,
    ) -> None:
        super().__init__(parent)
        if expense is not None and prefill is not None:
            raise ValueError("Передайте либо expense, либо prefill")
        if expense is not None:
            title = t("expense_dialog.title.edit")
        elif prefill is not None:
            title = t("expense_dialog.title.repeat")
        else:
            title = t("expense_dialog.title.new")
        self.setWindowTitle(title)
        self.setStyleSheet(app_qss())
        self.setMinimumWidth(420)
        self._catalogs = catalogs
        self._expense = expense
        self.amount_edit = QLineEdit()
        self.date_edit = QDateEdit()
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setDate(QDate.currentDate())
        theme_date_edit(self.date_edit)
        self.person_combo = ThemedComboBox()
        self.category_combo = ThemedComboBox()
        self.merchant_combo = SearchableComboBox()
        self.merchant_combo.setPlaceholderText(t("expense_dialog.merchant.placeholder"))
        self.note_edit = QLineEdit()

        form = QFormLayout()
        form.addRow(t("expense_dialog.field.amount"), self.amount_edit)
        form.addRow(t("expense_dialog.field.date"), self.date_edit)
        form.addRow(t("expense_dialog.field.person"), self.person_combo)
        form.addRow(t("expense_dialog.field.category"), self.category_combo)
        form.addRow(t("expense_dialog.field.merchant"), self.merchant_combo)
        form.addRow(t("expense_dialog.field.note"), self.note_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText(t("expense_dialog.btn.save"))
        ok_btn.setDefault(True)
        ok_btn.setAutoDefault(True)
        cancel = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        cancel.setText(t("common.cancel"))
        cancel.setObjectName("secondary")
        cancel.setAutoDefault(False)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self._accept)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self.category_combo.currentIndexChanged.connect(lambda _idx: self._reload_merchants())
        self._load_combos(prefs)
        source = expense if expense is not None else prefill
        if source is not None:
            self.amount_edit.setText(Money.from_cents(source.amount_cents).format_rub())
            if expense is not None:
                self.date_edit.setDate(
                    QDate(expense.spent_on.year, expense.spent_on.month, expense.spent_on.day)
                )
            self._select_combo(self.person_combo, source.person_id)
            self._select_combo(self.category_combo, source.category_id)
            self.note_edit.setText(source.note)
            self._reload_merchants(preserve=source.merchant_name)
        else:
            self._reload_merchants()
        self._result: dict | None = None

    def _load_combos(self, prefs: UiPreferences) -> None:
        self.person_combo.clear()
        for p in self._catalogs.list_people(False):
            self.person_combo.addItem(p.name, p.id)
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        for c in self._catalogs.list_categories(False):
            self.category_combo.addItem(c.name, c.id)
        self.category_combo.blockSignals(False)
        if prefs.last_person_id is not None:
            self._select_combo(self.person_combo, prefs.last_person_id)
        if prefs.last_category_id is not None:
            self._select_combo(self.category_combo, prefs.last_category_id)

    def _reload_merchants(self, *, preserve: str | None = None) -> None:
        category_id = self.category_combo.currentData()
        current = preserve if preserve is not None else self.merchant_combo.text()
        if category_id is None:
            self.merchant_combo.set_items([], current)
            return
        names = [m.display_name for m in self._catalogs.list_merchants(False, int(category_id))]
        self.merchant_combo.set_items(names, current)

    def _select_combo(self, combo: ThemedComboBox, value: int) -> None:
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _accept(self) -> None:
        try:
            if self.person_combo.currentData() is None or self.category_combo.currentData() is None:
                raise DomainError(t("expense_dialog.err.need_person_category"))
            amount = Money.from_rubles_str(self.amount_edit.text())
            qd = self.date_edit.date()
            spent_on = date(qd.year(), qd.month(), qd.day())
            category_id = int(self.category_combo.currentData())
            merchant_input = self.merchant_combo.text()
            self._catalogs.resolve_merchant_for_expense(merchant_input, category_id)
            self._result = {
                "amount": amount,
                "spent_on": spent_on,
                "person_id": int(self.person_combo.currentData()),
                "category_id": category_id,
                "merchant_input": merchant_input,
                "note": self.note_edit.text(),
            }
            self.accept()
        except DomainError as exc:
            QMessageBox.warning(self, t("common.app_name"), str(exc))

    def payload(self) -> dict:
        assert self._result is not None
        return self._result
