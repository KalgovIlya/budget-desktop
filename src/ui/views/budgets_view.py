from __future__ import annotations

from datetime import date
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.application.budget_service import BudgetService, month_label
from src.application.dto import CategoryBudgetStatus
from src.domain.errors import DomainError
from src.domain.money import Money
from src.i18n import money_label, t
from src.ui.table_style import apply_column_widths, style_data_table
from src.ui.theme import current_palette


def _limit_tip() -> str:
    return t("budgets.cell.tooltip")


def _fmt_cents(cents: int) -> str:
    return f"{(Decimal(cents) / Decimal(100)):.2f}"


class BudgetsView(QWidget):
    def __init__(self, budgets: BudgetService, parent=None) -> None:
        super().__init__(parent)
        self._budgets = budgets
        self._rows: list[int] = []

        self._title = QLabel()
        self._title.setObjectName("emptyTitle")
        self._period = QLabel()
        self._period.setObjectName("subtitle")
        self._hint = QLabel()
        self._hint.setObjectName("subtitle")
        self._hint.setWordWrap(True)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.setContentsMargins(0, 0, 0, 0)
        title_box.addWidget(self._title)
        title_box.addWidget(self._period)
        title_box.addWidget(self._hint)

        header = QHBoxLayout()
        header.setSpacing(10)
        header.addLayout(title_box, stretch=1)

        self._cards = QHBoxLayout()
        self._cards.setSpacing(10)
        self._cards.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget(0, 5)
        style_data_table(self._table)
        self._table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.EditKeyPressed
        )
        self._table.itemDoubleClicked.connect(self._prepare_limit_edit)
        self._table.itemChanged.connect(self._on_item_changed)

        self._empty = QLabel()
        self._empty.setObjectName("subtitle")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        layout.addLayout(header)
        layout.addLayout(self._cards)
        layout.addWidget(self._empty, stretch=1)
        layout.addWidget(self._table, stretch=1)
        self.retranslate()
        self.refresh()

    def retranslate(self) -> None:
        self._title.setText(t("budgets.title"))
        self._hint.setText(t("budgets.hint"))
        self._empty.setText(t("budgets.empty.no_categories"))
        self._table.setHorizontalHeaderLabels(
            [
                t("budgets.col.category"),
                t("budgets.col.limit"),
                t("budgets.col.fact"),
                t("budgets.col.remaining"),
                t("budgets.col.pct"),
            ]
        )
        tip = _limit_tip()
        limit_header = self._table.horizontalHeaderItem(1)
        if limit_header is not None:
            limit_header.setToolTip(tip)
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 1)
            if item is not None:
                item.setToolTip(tip)

    def refresh(self) -> None:
        today = date.today()
        self._period.setText(
            t("budgets.period.current_month", month=month_label(today))
        )
        statuses = self._budgets.list_status(today=today)
        has = bool(statuses)
        self._empty.setVisible(not has)
        self._table.setVisible(has)
        self._hint.setVisible(has)
        self._fill_summary(statuses)

        self._table.blockSignals(True)
        self._table.setRowCount(len(statuses))
        self._rows = []
        p = current_palette()
        warn = QColor(p.accent)
        danger = QColor("#C44B4B")
        ok = QColor(p.text)
        muted = QColor(p.muted)
        tip = _limit_tip()

        for row, status in enumerate(statuses):
            self._rows.append(status.category_id)
            name_item = QTableWidgetItem(status.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            if status.limit_cents:
                limit_item = QTableWidgetItem(
                    Money.from_cents(status.limit_cents).format_rub()
                )
                limit_item.setForeground(ok)
            else:
                limit_item = QTableWidgetItem("—")
                limit_item.setForeground(muted)
            limit_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            limit_item.setFlags(
                (limit_item.flags() | Qt.ItemFlag.ItemIsEditable)
                & ~Qt.ItemFlag.ItemIsUserCheckable
            )
            limit_item.setToolTip(tip)
            limit_item.setData(Qt.ItemDataRole.UserRole, status.limit_cents)

            spent_item = QTableWidgetItem(_fmt_cents(status.spent_cents))
            spent_item.setFlags(spent_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            spent_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )

            if status.remaining_cents is None:
                rem_text = "—"
                rem_color = muted
            else:
                rem_text = _fmt_cents(status.remaining_cents)
                rem_color = danger if status.remaining_cents < 0 else ok

            rem_item = QTableWidgetItem(rem_text)
            rem_item.setFlags(rem_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            rem_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            rem_item.setForeground(rem_color)

            if status.ratio is None:
                pct_text = "—"
                pct_color = muted
            else:
                pct_text = f"{status.ratio * 100:.0f}%"
                if status.ratio >= 1:
                    pct_color = danger
                elif status.ratio >= 0.8:
                    pct_color = warn
                else:
                    pct_color = ok

            pct_item = QTableWidgetItem(pct_text)
            pct_item.setFlags(pct_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            pct_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            pct_item.setForeground(pct_color)

            self._table.setItem(row, 0, name_item)
            self._table.setItem(row, 1, limit_item)
            self._table.setItem(row, 2, spent_item)
            self._table.setItem(row, 3, rem_item)
            self._table.setItem(row, 4, pct_item)

        self._table.blockSignals(False)
        apply_column_widths(
            self._table,
            fixed_cols=(1, 2, 3, 4),
            stretch_cols=(0,),
        )

    def _fill_summary(self, statuses: list[CategoryBudgetStatus]) -> None:
        while self._cards.count():
            item = self._cards.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not statuses:
            return

        budgeted = [s for s in statuses if s.limit_cents]
        limit_sum = sum(s.limit_cents or 0 for s in budgeted)
        spent_budgeted = sum(s.spent_cents for s in budgeted)
        remaining = limit_sum - spent_budgeted
        over = sum(1 for s in budgeted if (s.remaining_cents or 0) < 0)
        no_limit = len(statuses) - len(budgeted)

        self._cards.addWidget(
            self._card(
                t("budgets.card.limits"),
                money_label(_fmt_cents(limit_sum)) if budgeted else t("common.em_dash"),
            )
        )
        self._cards.addWidget(
            self._card(
                t("budgets.card.fact"),
                money_label(_fmt_cents(spent_budgeted))
                if budgeted
                else t("common.em_dash"),
            )
        )
        rem_label = (
            money_label(_fmt_cents(remaining)) if budgeted else t("common.em_dash")
        )
        self._cards.addWidget(
            self._card(
                t("budgets.card.remaining"),
                rem_label,
                danger=bool(budgeted and remaining < 0),
            )
        )

        if over:
            status_text = t("budgets.status.over_count", n=over)
        elif budgeted:
            status_text = t("budgets.status.ok")
        else:
            status_text = t("budgets.status.no_limits")
        self._cards.addWidget(
            self._card(t("budgets.card.over"), status_text, danger=over > 0)
        )

        if no_limit:
            self._cards.addWidget(
                self._card(
                    t("budgets.card.no_limit"),
                    t("budgets.status.over_count", n=no_limit),
                )
            )
        self._cards.addStretch(1)

    def _card(self, caption: str, value: str, *, danger: bool = False) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(4)
        name = QLabel(caption)
        name.setObjectName("subtitle")
        amount = QLabel(value)
        color = "color: #C44B4B;" if danger else ""
        amount.setStyleSheet(f"font-size: 16px; font-weight: 600; {color}")
        lay.addWidget(name)
        lay.addWidget(amount)
        return card

    def _prepare_limit_edit(self, item: QTableWidgetItem) -> None:
        if item.column() != 1:
            return
        if item.text().strip() in {"—", "-", "–"}:
            self._table.blockSignals(True)
            item.setText("")
            self._table.blockSignals(False)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() != 1:
            return
        row = item.row()
        if row < 0 or row >= len(self._rows):
            return
        category_id = self._rows[row]
        raw = item.text().strip()
        if raw in {"—", "-", "–"}:
            raw = ""
        try:
            self._budgets.set_limit_from_text(category_id, raw)
        except DomainError as exc:
            QMessageBox.warning(self, t("common.app_name"), str(exc))
        self.refresh()
