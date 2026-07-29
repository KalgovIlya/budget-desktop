from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.application.budget_service import BudgetService
from src.application.catalog_service import CatalogService
from src.application.dto import Expense, ExpenseFilter, UiPreferences
from src.application.expense_search import match_expense_query
from src.application.expense_service import ExpenseService, PreferencesService
from src.domain.errors import DomainError
from src.domain.money import Money
from src.i18n import money_label, t
from src.ui.table_style import apply_column_widths, style_data_table
from src.ui.views.expense_dialog import ExpenseDialog


class ExpensesView(QWidget):
    def __init__(
        self,
        expenses: ExpenseService,
        catalogs: CatalogService,
        prefs: PreferencesService,
        budgets: BudgetService | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._expenses = expenses
        self._catalogs = catalogs
        self._prefs = prefs
        self._budgets = budgets
        self._ids: list[int] = []
        self._all_items: list[Expense] = []

        self._title = QLabel(t("expenses.title"))
        self._title.setObjectName("emptyTitle")
        self._hint = QLabel(t("expenses.hint"))
        self._hint.setObjectName("subtitle")

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.setContentsMargins(0, 0, 0, 0)
        title_box.addWidget(self._title)
        title_box.addWidget(self._hint)

        self._search = QLineEdit()
        self._search.setPlaceholderText(t("expenses.search.placeholder"))
        self._search.setClearButtonEnabled(True)
        self._search.setMinimumWidth(280)
        self._search.setMaximumWidth(420)
        self._search.setToolTip(t("expenses.search.tooltip"))
        self._search.textChanged.connect(self._apply_search)

        self._add_btn = QPushButton(t("expenses.btn.add"))
        self._add_btn.setToolTip(t("expenses.btn.add.tooltip"))
        self._add_btn.clicked.connect(self.add_expense)

        header = QHBoxLayout()
        header.setSpacing(10)
        header.addLayout(title_box)
        header.addStretch(1)
        header.addWidget(self._search, 1)

        # Compact recent chips — no heavy section title
        self._recent_row = QHBoxLayout()
        self._recent_row.setSpacing(6)
        self._recent_row.setContentsMargins(0, 0, 0, 0)
        self._recent_wrap = QWidget()
        recent_layout = QHBoxLayout(self._recent_wrap)
        recent_layout.setContentsMargins(0, 0, 0, 0)
        recent_layout.setSpacing(8)
        self._recent_caption = QLabel(t("expenses.recent.caption"))
        self._recent_caption.setObjectName("subtitle")
        recent_layout.addWidget(self._recent_caption)
        recent_layout.addLayout(self._recent_row, stretch=1)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            [
                t("expenses.col.date"),
                t("expenses.col.amount"),
                t("expenses.col.person"),
                t("expenses.col.category"),
                t("expenses.col.merchant"),
                t("expenses.col.note"),
            ]
        )
        style_data_table(self._table)
        self._table.doubleClicked.connect(lambda _idx: self.edit_expense())
        self._table.itemSelectionChanged.connect(self._sync_row_actions)

        self._empty = QWidget()
        empty_layout = QVBoxLayout(self._empty)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_title = QLabel(t("expenses.empty.title"))
        self._empty_title.setObjectName("emptyTitle")
        self._empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_body = QLabel(t("expenses.empty.body_no_data"))
        self._empty_body.setObjectName("subtitle")
        self._empty_body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self._empty_title)
        empty_layout.addWidget(self._empty_body)

        self._repeat_btn = QPushButton(t("expenses.btn.repeat"))
        self._repeat_btn.setObjectName("secondary")
        self._repeat_btn.clicked.connect(self.repeat_expense)
        self._edit_btn = QPushButton(t("expenses.btn.edit"))
        self._edit_btn.setObjectName("secondary")
        self._edit_btn.clicked.connect(self.edit_expense)
        self._del_btn = QPushButton(t("expenses.btn.delete"))
        self._del_btn.setObjectName("danger")
        self._del_btn.clicked.connect(self.delete_expense)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        footer.addWidget(self._add_btn)
        footer.addWidget(self._repeat_btn)
        footer.addWidget(self._edit_btn)
        footer.addWidget(self._del_btn)
        footer.addStretch(1)

        self._list_host = QWidget()
        list_layout = QVBoxLayout(self._list_host)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)
        list_layout.addWidget(self._table, stretch=1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        layout.addLayout(header)
        layout.addWidget(self._recent_wrap)
        layout.addWidget(self._empty, stretch=1)
        layout.addWidget(self._list_host, stretch=1)
        layout.addLayout(footer)
        self.refresh()

    def retranslate(self) -> None:
        self._title.setText(t("expenses.title"))
        self._hint.setText(t("expenses.hint"))
        self._search.setPlaceholderText(t("expenses.search.placeholder"))
        self._search.setToolTip(t("expenses.search.tooltip"))
        self._add_btn.setText(t("expenses.btn.add"))
        self._add_btn.setToolTip(t("expenses.btn.add.tooltip"))
        self._recent_caption.setText(t("expenses.recent.caption"))
        self._table.setHorizontalHeaderLabels(
            [
                t("expenses.col.date"),
                t("expenses.col.amount"),
                t("expenses.col.person"),
                t("expenses.col.category"),
                t("expenses.col.merchant"),
                t("expenses.col.note"),
            ]
        )
        self._empty_title.setText(t("expenses.empty.title"))
        self._empty_body.setText(t("expenses.empty.body_no_data"))
        self._repeat_btn.setText(t("expenses.btn.repeat"))
        self._edit_btn.setText(t("expenses.btn.edit"))
        self._del_btn.setText(t("expenses.btn.delete"))

    def focus_search(self) -> None:
        self._search.setEnabled(True)
        self._search.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self._search.selectAll()

    def refresh(self) -> None:
        today = date.today()
        filt = ExpenseFilter(date_from=date(today.year - 2, 1, 1), date_to=today)
        self._all_items = self._expenses.list_expenses(filt)
        has_items = bool(self._all_items)
        self._search.setEnabled(True)
        self._apply_search()
        self._reload_recent()
        if not has_items:
            self._show_empty(
                t("expenses.empty.title"),
                t("expenses.empty.body_no_data"),
            )

    def _show_empty(self, title: str, body: str) -> None:
        self._empty_title.setText(title)
        self._empty_body.setText(body)
        self._empty.setVisible(True)
        self._list_host.setVisible(False)
        self._sync_row_actions()

    def _show_list(self) -> None:
        self._empty.setVisible(False)
        self._list_host.setVisible(True)

    def _sync_row_actions(self) -> None:
        row = self._table.currentRow()
        has = (
            self._list_host.isVisible()
            and row >= 0
            and row < len(self._ids)
        )
        self._repeat_btn.setEnabled(has)
        self._edit_btn.setEnabled(has)
        self._del_btn.setEnabled(has)

    def _apply_search(self) -> None:
        query = self._search.text()
        items = [e for e in self._all_items if match_expense_query(e, query)]
        if not self._all_items:
            return
        if not items:
            self._show_empty(
                t("expenses.empty.search_title"),
                t("expenses.empty.search_body"),
            )
            self._ids = []
            return

        self._show_list()
        self._table.setRowCount(len(items))
        self._ids = []
        for row, item in enumerate(items):
            self._ids.append(item.id)
            values = [
                item.spent_on.strftime("%d.%m.%Y"),
                Money.from_cents(item.amount_cents).format_rub(),
                item.person_name,
                item.category_name,
                item.merchant_name,
                item.note,
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if col == 1:
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self._table.setItem(row, col, cell)
        apply_column_widths(
            self._table,
            fixed_cols=(0, 1, 2),
            stretch_cols=(3, 4, 5),
        )
        if items:
            self._table.selectRow(0)
        self._sync_row_actions()

    def _reload_recent(self) -> None:
        while self._recent_row.count():
            item = self._recent_row.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        templates = self._expenses.list_recent_templates(limit=5)
        self._recent_wrap.setVisible(bool(templates))
        for expense in templates:
            amount = Money.from_cents(expense.amount_cents).format_rub()
            label = f"{expense.merchant_name} · {money_label(amount)}"
            btn = QPushButton(label)
            btn.setObjectName("secondary")
            btn.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
            btn.setToolTip(
                f"{expense.person_name} · {expense.category_name} · {expense.merchant_name}"
            )
            btn.clicked.connect(lambda _checked=False, e=expense: self._open_prefill(e))
            self._recent_row.addWidget(btn)
        self._recent_row.addStretch(1)

    def add_expense(self) -> None:
        dialog = ExpenseDialog(self._catalogs, self._prefs.get(), self)
        if dialog.exec():
            self._save_new(dialog.payload())

    def repeat_expense(self) -> None:
        expense = self._selected_expense()
        if expense is None:
            return
        self._open_prefill(expense)

    def _open_prefill(self, expense: Expense) -> None:
        if not self._can_repeat(expense):
            return
        dialog = ExpenseDialog(self._catalogs, self._prefs.get(), self, prefill=expense)
        if dialog.exec():
            self._save_new(dialog.payload())

    def _save_new(self, data: dict) -> None:
        try:
            expense = self._expenses.add_expense(**data)
            current = self._prefs.get()
            self._prefs.save(
                UiPreferences(
                    last_person_id=data["person_id"],
                    last_category_id=data["category_id"],
                    theme=current.theme,
                    locale=current.locale,
                )
            )
            self.refresh()
            self._maybe_budget_warning(expense.category_id, expense.spent_on)
        except DomainError as exc:
            QMessageBox.warning(self, t("common.app_name"), str(exc))

    def edit_expense(self) -> None:
        expense = self._selected_expense()
        if expense is None:
            return
        expense_id = expense.id
        dialog = ExpenseDialog(self._catalogs, self._prefs.get(), self, expense=expense)
        if dialog.exec():
            data = dialog.payload()
            try:
                updated = self._expenses.update_expense(expense_id, **data)
                current = self._prefs.get()
                self._prefs.save(
                    UiPreferences(
                        last_person_id=data["person_id"],
                        last_category_id=data["category_id"],
                        theme=current.theme,
                        locale=current.locale,
                    )
                )
                self.refresh()
                self._maybe_budget_warning(updated.category_id, updated.spent_on)
            except DomainError as exc:
                QMessageBox.warning(self, t("common.app_name"), str(exc))

    def delete_expense(self) -> None:
        row = self._table.currentRow()
        if row < 0 or not self._list_host.isVisible():
            QMessageBox.information(
                self, t("common.app_name"), t("expenses.msg.select_row")
            )
            return
        if (
            QMessageBox.question(
                self, t("common.app_name"), t("expenses.msg.confirm_delete")
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        try:
            self._expenses.delete_expense(self._ids[row])
            self.refresh()
        except DomainError as exc:
            QMessageBox.warning(self, t("common.app_name"), str(exc))

    def _selected_expense(self):
        if not self._list_host.isVisible():
            QMessageBox.information(
                self, t("common.app_name"), t("expenses.msg.select_row")
            )
            return None
        row = self._table.currentRow()
        if row < 0 or row >= len(self._ids):
            QMessageBox.information(
                self, t("common.app_name"), t("expenses.msg.select_row")
            )
            return None
        expense_id = self._ids[row]
        for item in self._all_items:
            if item.id == expense_id:
                return item
        return None

    def _can_repeat(self, expense) -> bool:
        people = {p.id: p for p in self._catalogs.list_people(True)}
        categories = {c.id: c for c in self._catalogs.list_categories(True)}
        merchants = {m.id: m for m in self._catalogs.list_merchants(True)}
        p = people.get(expense.person_id)
        c = categories.get(expense.category_id)
        m = merchants.get(expense.merchant_id)
        if p is None or p.is_archived:
            QMessageBox.warning(
                self, t("common.app_name"), t("expenses.msg.repeat_person_archived")
            )
            return False
        if c is None or c.is_archived:
            QMessageBox.warning(
                self, t("common.app_name"), t("expenses.msg.repeat_category_archived")
            )
            return False
        if m is None or m.is_archived:
            QMessageBox.warning(
                self, t("common.app_name"), t("expenses.msg.repeat_merchant_archived")
            )
            return False
        return True

    def _maybe_budget_warning(self, category_id: int, spent_on: date) -> None:
        if self._budgets is None:
            return
        message = self._budgets.warning_if_over(category_id, spent_on)
        if message:
            QMessageBox.warning(self, t("common.app_name"), message)
