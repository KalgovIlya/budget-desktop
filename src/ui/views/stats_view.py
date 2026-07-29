from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QChart,
    QChartView,
    QLineSeries,
    QPieSeries,
    QValueAxis,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QBrush, QColor, QPainter
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDateEdit,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.application.catalog_service import CatalogService
from src.application.dto import CompareRow, ExpenseFilter, StatsDto
from src.application.expense_service import ExpenseService
from src.application.export_service import ExportService
from src.application.period_compare import (
    compare_stats,
    format_delta_pct,
    format_total_delta,
    previous_period,
)
from src.domain.errors import DomainError
from src.domain.money import Money
from src.i18n import money_label, t
from src.ui.calendar_theme import theme_date_edit
from src.ui.chart_theme import style_axis, style_chart, thin_axis_labels
from src.ui.message_box import ask_yes_no
from src.ui.table_style import apply_column_widths, style_data_table
from src.ui.theme import current_palette
from src.ui.themed_combo import ThemedComboBox


def _rub(cents: int) -> str:
    if cents <= 0:
        return "0.00"
    return Money.from_cents(cents).format_rub()


class StatsView(QWidget):
    def __init__(
        self,
        expenses: ExpenseService,
        catalogs: CatalogService,
        export: ExportService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._expenses = expenses
        self._catalogs = catalogs
        self._export = export

        self._from = QDateEdit()
        self._to = QDateEdit()
        for w in (self._from, self._to):
            w.setDisplayFormat("dd.MM.yyyy")
            w.setMinimumWidth(120)
            theme_date_edit(w)
        self._set_this_month()

        self._preset = ThemedComboBox()
        self._preset.addItem(t("stats.period.this_month"), "this")
        self._preset.addItem(t("stats.period.prev_month"), "prev")
        self._preset.addItem(t("stats.period.last_30_days"), "30")
        self._preset.addItem(t("stats.period.custom"), "custom")
        self._preset.currentIndexChanged.connect(self._on_preset)

        self._people_box = QVBoxLayout()
        self._people_box.setSpacing(2)
        self._categories_box = QVBoxLayout()
        self._categories_box.setSpacing(2)
        self._merchant_list = QListWidget()
        self._merchant_list.setObjectName("merchantFilterList")
        self._merchant_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self._merchant_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._merchant_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._merchant_list.setMinimumHeight(140)
        self._merchant_list.setMaximumHeight(220)
        self._merchant_query = QLineEdit()
        self._merchant_query.setPlaceholderText(t("stats.merchant_search.placeholder"))
        self._merchant_query.textChanged.connect(self._on_merchant_query)
        self._include_archived = QCheckBox(t("stats.include_archived"))
        self._include_archived.toggled.connect(self._on_include_archived)
        self._compare = QCheckBox(t("stats.compare"))
        self._compare.toggled.connect(self.refresh)

        self._mode_list = QRadioButton(t("stats.mode.list"))
        self._mode_chart = QRadioButton(t("stats.mode.chart"))
        self._mode_merchants = QRadioButton(t("stats.mode.merchants"))
        self._mode_dynamics = QRadioButton(t("stats.mode.dynamics"))
        self._mode_list.setChecked(True)
        modes = QButtonGroup(self)
        for btn in (self._mode_list, self._mode_chart, self._mode_merchants, self._mode_dynamics):
            modes.addButton(btn)
            btn.toggled.connect(self.refresh)

        self._total = QLabel(money_label("0.00"))
        self._total.setObjectName("total")
        self._meta = QLabel(t("stats.meta.records", count=0))
        self._meta.setObjectName("subtitle")
        self._cards = QHBoxLayout()
        self._stack = QStackedWidget()
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            [
                t("stats.col.date"),
                t("stats.col.amount"),
                t("stats.col.person"),
                t("stats.col.category"),
                t("stats.col.merchant"),
            ]
        )
        style_data_table(self._table)
        self._chart_view = QChartView()
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._merchant_table = QTableWidget(0, 2)
        self._merchant_table.setHorizontalHeaderLabels(
            [t("stats.col.merchant"), t("stats.col.amount")]
        )
        style_data_table(self._merchant_table)
        self._compare_table = QTableWidget(0, 5)
        self._compare_table.setHorizontalHeaderLabels(
            [
                t("stats.compare.col.name"),
                t("stats.compare.col.was"),
                t("stats.compare.col.became"),
                t("stats.compare.col.delta_money"),
                t("stats.compare.col.delta_pct"),
            ]
        )
        style_data_table(self._compare_table)
        self._stack.addWidget(self._table)
        self._stack.addWidget(self._chart_view)
        self._stack.addWidget(self._merchant_table)
        self._stack.addWidget(self._compare_table)

        self._apply_btn = QPushButton(t("stats.btn.apply"))
        self._apply_btn.clicked.connect(self.refresh)
        self._reset_btn = QPushButton(t("stats.btn.reset_filters"))
        self._reset_btn.setObjectName("secondary")
        self._reset_btn.clicked.connect(self._reset)
        self._csv_btn = QPushButton(t("stats.btn.export_csv"))
        self._csv_btn.setObjectName("secondary")
        self._csv_btn.clicked.connect(self._export_csv)
        self._import_btn = QPushButton(t("stats.btn.import_csv"))
        self._import_btn.setObjectName("secondary")
        self._import_btn.clicked.connect(self._import_csv)
        self._bak_btn = QPushButton(t("stats.btn.backup"))
        self._bak_btn.setObjectName("secondary")
        self._bak_btn.clicked.connect(self._backup)

        filter_panel = QFrame()
        filter_panel.setObjectName("filterPanel")
        left = QVBoxLayout(filter_panel)
        left.setContentsMargins(12, 12, 12, 12)
        left.setSpacing(10)

        def section(text: str) -> QLabel:
            lab = QLabel(text)
            lab.setObjectName("sectionTitle")
            return lab

        self._section_period = section(t("stats.section.period"))
        left.addWidget(self._section_period)
        left.addWidget(self._preset)
        dates = QHBoxLayout()
        dates.addWidget(self._from)
        dates.addWidget(self._to)
        left.addLayout(dates)
        left.addWidget(self._include_archived)
        left.addWidget(self._compare)
        self._section_people = section(t("stats.section.people"))
        left.addWidget(self._section_people)
        left.addLayout(self._people_box)
        self._section_categories = section(t("stats.section.categories"))
        left.addWidget(self._section_categories)
        left.addLayout(self._categories_box)
        self._section_merchants = section(t("stats.section.merchants"))
        left.addWidget(self._section_merchants)
        left.addWidget(self._merchant_list)
        left.addWidget(self._merchant_query)
        left.addWidget(self._apply_btn)
        left.addWidget(self._reset_btn)
        left.addStretch(1)
        self._section_service = section(t("stats.section.service"))
        left.addWidget(self._section_service)
        left.addWidget(self._csv_btn)
        left.addWidget(self._import_btn)
        left.addWidget(self._bak_btn)

        for btn in (
            self._apply_btn,
            self._reset_btn,
            self._csv_btn,
            self._import_btn,
            self._bak_btn,
        ):
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        filter_scroll = QScrollArea()
        filter_scroll.setObjectName("filterScroll")
        filter_scroll.setWidgetResizable(True)
        filter_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        filter_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        filter_scroll.setFixedWidth(360)
        filter_scroll.setWidget(filter_panel)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(12)
        mode_row.setContentsMargins(0, 0, 0, 0)
        for btn in (
            self._mode_list,
            self._mode_chart,
            self._mode_merchants,
            self._mode_dynamics,
        ):
            btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            btn.setMinimumWidth(btn.sizeHint().width() + 8)
            mode_row.addWidget(btn, 0)
        mode_row.addStretch(1)

        summary = QVBoxLayout()
        summary.setSpacing(2)
        summary.setContentsMargins(0, 0, 0, 0)
        summary.addWidget(self._total)
        summary.addWidget(self._meta)

        right = QVBoxLayout()
        right.setContentsMargins(16, 8, 8, 8)
        right.setSpacing(10)
        right.addLayout(summary)
        right.addLayout(mode_row)
        right.addLayout(self._cards)
        right.addWidget(self._stack, stretch=1)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(filter_scroll)
        root.addLayout(right, stretch=1)

        self._people_checks: list[QCheckBox] = []
        self._category_checks: list[QCheckBox] = []
        self._archived_people: set[int] = set()
        self._archived_categories: set[int] = set()
        self._archived_merchants: set[int] = set()
        self.reload_filters()
        self.refresh()

    def retranslate(self) -> None:
        idx = self._preset.currentIndex()
        self._preset.blockSignals(True)
        self._preset.clear()
        self._preset.addItem(t("stats.period.this_month"), "this")
        self._preset.addItem(t("stats.period.prev_month"), "prev")
        self._preset.addItem(t("stats.period.last_30_days"), "30")
        self._preset.addItem(t("stats.period.custom"), "custom")
        self._preset.blockSignals(False)
        self._preset.setCurrentIndex(idx)

        self._include_archived.setText(t("stats.include_archived"))
        self._compare.setText(t("stats.compare"))
        self._mode_list.setText(t("stats.mode.list"))
        self._mode_chart.setText(t("stats.mode.chart"))
        self._mode_merchants.setText(t("stats.mode.merchants"))
        self._mode_dynamics.setText(t("stats.mode.dynamics"))
        self._section_period.setText(t("stats.section.period"))
        self._section_people.setText(t("stats.section.people"))
        self._section_categories.setText(t("stats.section.categories"))
        self._section_merchants.setText(t("stats.section.merchants"))
        self._section_service.setText(t("stats.section.service"))
        self._apply_btn.setText(t("stats.btn.apply"))
        self._reset_btn.setText(t("stats.btn.reset_filters"))
        self._csv_btn.setText(t("stats.btn.export_csv"))
        self._import_btn.setText(t("stats.btn.import_csv"))
        self._bak_btn.setText(t("stats.btn.backup"))
        self._table.setHorizontalHeaderLabels(
            [
                t("stats.col.date"),
                t("stats.col.amount"),
                t("stats.col.person"),
                t("stats.col.category"),
                t("stats.col.merchant"),
            ]
        )
        self._merchant_table.setHorizontalHeaderLabels(
            [t("stats.col.merchant"), t("stats.col.amount")]
        )
        self._compare_table.setHorizontalHeaderLabels(
            [
                t("stats.compare.col.name"),
                t("stats.compare.col.was"),
                t("stats.compare.col.became"),
                t("stats.compare.col.delta_money"),
                t("stats.compare.col.delta_pct"),
            ]
        )
        self._merchant_query.setPlaceholderText(t("stats.merchant_search.placeholder"))

    def _on_include_archived(self, _checked: bool) -> None:
        self.reload_filters()
        self.refresh()

    def reload_filters(self) -> None:
        self._clear_layout(self._people_box)
        self._clear_layout(self._categories_box)
        self._people_checks = []
        self._category_checks = []
        include = self._include_archived.isChecked()
        people = self._catalogs.list_people(include)
        cats = self._catalogs.list_categories(include)
        self._archived_people = {p.id for p in people if p.is_archived}
        self._archived_categories = {c.id for c in cats if c.is_archived}
        if not people:
            self._people_box.addWidget(QLabel(t("stats.empty.no_people")))
        for p in people:
            label = p.name + t("stats.suffix.archived") if p.is_archived else p.name
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setProperty("entity_id", p.id)
            self._people_checks.append(cb)
            self._people_box.addWidget(cb)
        if not cats:
            self._categories_box.addWidget(QLabel(t("stats.empty.no_categories")))
        for c in cats:
            label = c.name + t("stats.suffix.archived") if c.is_archived else c.name
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setProperty("entity_id", c.id)
            self._category_checks.append(cb)
            self._categories_box.addWidget(cb)
        for cb in self._category_checks:
            cb.stateChanged.connect(self._reload_merchants_only)
        self._reload_merchants_only()

    def _reload_merchants_only(self) -> None:
        self._merchant_list.clear()
        selected_cats = [
            int(cb.property("entity_id")) for cb in self._category_checks if cb.isChecked()
        ]
        include = self._include_archived.isChecked()
        merchants = self._catalogs.list_merchants(include)
        self._archived_merchants = {m.id for m in merchants if m.is_archived}
        if self._category_checks and selected_cats and len(selected_cats) < len(self._category_checks):
            merchants = [m for m in merchants if m.category_id in selected_cats]
        elif self._category_checks and not selected_cats:
            merchants = []
        for m in merchants:
            mark = t("stats.suffix.archived") if m.is_archived else ""
            item = QListWidgetItem(f"{m.display_name} · {m.category_name}{mark}")
            item.setData(Qt.ItemDataRole.UserRole, m.id)
            self._merchant_list.addItem(item)

    def _archive_suffix(self, entity_id: int | None, archived_ids: set[int]) -> str:
        if entity_id is not None and entity_id in archived_ids:
            return t("stats.suffix.archived")
        return ""

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()

    def _on_preset(self) -> None:
        key = self._preset.currentData()
        if key == "this":
            self._set_this_month()
        elif key == "prev":
            self._set_prev_month()
        elif key == "30":
            self._set_30_days()
        custom = key == "custom"
        self._from.setEnabled(custom or True)
        self._to.setEnabled(custom or True)

    def _on_merchant_query(self, text: str) -> None:
        if text.strip():
            self._merchant_list.clearSelection()

    def _filter(self) -> ExpenseFilter:
        qd1, qd2 = self._from.date(), self._to.date()
        person_ids = tuple(
            int(cb.property("entity_id")) for cb in self._people_checks if cb.isChecked()
        )
        if len(person_ids) == len(self._people_checks):
            person_ids = ()
        category_ids = tuple(
            int(cb.property("entity_id")) for cb in self._category_checks if cb.isChecked()
        )
        if len(category_ids) == len(self._category_checks):
            category_ids = ()
        query = self._merchant_query.text().strip()
        selected = self._merchant_list.selectedItems()
        merchant_ids = tuple(int(i.data(Qt.ItemDataRole.UserRole)) for i in selected)
        if query:
            merchant_ids = ()
        return ExpenseFilter(
            date_from=date(qd1.year(), qd1.month(), qd1.day()),
            date_to=date(qd2.year(), qd2.month(), qd2.day()),
            person_ids=person_ids,
            category_ids=category_ids,
            merchant_ids=merchant_ids,
            merchant_query=query or None,
            include_archived=self._include_archived.isChecked(),
        )

    def refresh(self) -> None:
        theme_date_edit(self._from)
        theme_date_edit(self._to)
        if self._people_checks and not any(cb.isChecked() for cb in self._people_checks):
            self._render_stats(StatsDto(0, (), (), (), ()), previous=None)
            return
        if self._category_checks and not any(cb.isChecked() for cb in self._category_checks):
            self._render_stats(StatsDto(0, (), (), (), ()), previous=None)
            return
        try:
            filt = self._filter()
            stats = self._expenses.get_stats(filt)
            previous = None
            if self._compare.isChecked():
                prev_from, prev_to = previous_period(filt.date_from, filt.date_to)
                previous = self._expenses.get_stats(
                    ExpenseFilter(
                        date_from=prev_from,
                        date_to=prev_to,
                        person_ids=filt.person_ids,
                        category_ids=filt.category_ids,
                        merchant_ids=filt.merchant_ids,
                        merchant_query=filt.merchant_query,
                        include_archived=filt.include_archived,
                    )
                )
        except DomainError as exc:
            QMessageBox.warning(self, t("common.app_name"), str(exc))
            return
        self._render_stats(stats, previous=previous)

    def _render_stats(self, stats: StatsDto, *, previous: StatsDto | None) -> None:
        self._total.setText(
            money_label(Money.from_cents(stats.total_cents).format_rub())
            if stats.total_cents
            else money_label("0.00")
        )
        if previous is None:
            self._meta.setText(t("stats.meta.records", count=len(stats.items)))
        else:
            prev_from, prev_to = previous_period(
                self._filter().date_from, self._filter().date_to
            )
            was = (
                Money.from_cents(previous.total_cents).format_rub()
                if previous.total_cents
                else "0.00"
            )
            delta = format_total_delta(previous.total_cents, stats.total_cents)
            self._meta.setText(
                t(
                    "stats.meta.records_compare",
                    count=len(stats.items),
                    was=was,
                    date_from=prev_from.strftime("%d.%m"),
                    date_to=prev_to.strftime("%d.%m"),
                    delta=delta,
                )
            )

        while self._cards.count():
            item = self._cards.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for named in stats.by_person:
            card = QFrame()
            card.setObjectName("card")
            lay = QVBoxLayout(card)
            lay.setContentsMargins(12, 10, 12, 10)
            label = named.name + self._archive_suffix(named.id, self._archived_people)
            name = QLabel(label)
            name.setObjectName("subtitle")
            amount = QLabel(money_label(Money.from_cents(named.amount_cents).format_rub()))
            amount.setStyleSheet("font-size: 16px; font-weight: 600;")
            lay.addWidget(name)
            lay.addWidget(amount)
            self._cards.addWidget(card)
        self._cards.addStretch()

        if previous is not None and self._mode_list.isChecked():
            self._stack.setCurrentIndex(3)
            self._fill_compare_table(previous, stats)
            return

        if self._mode_list.isChecked():
            self._stack.setCurrentIndex(0)
            self._table.setRowCount(len(stats.items))
            for row, item in enumerate(stats.items):
                vals = [
                    item.spent_on.strftime("%d.%m.%Y"),
                    Money.from_cents(item.amount_cents).format_rub(),
                    item.person_name
                    + self._archive_suffix(item.person_id, self._archived_people),
                    item.category_name
                    + self._archive_suffix(item.category_id, self._archived_categories),
                    item.merchant_name
                    + self._archive_suffix(item.merchant_id, self._archived_merchants),
                ]
                for col, val in enumerate(vals):
                    cell = QTableWidgetItem(val)
                    if col == 1:
                        cell.setTextAlignment(
                            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                        )
                    self._table.setItem(row, col, cell)
            apply_column_widths(
                self._table,
                fixed_cols=(0, 1, 2),
                stretch_cols=(3, 4),
            )
            return
        elif self._mode_chart.isChecked():
            self._stack.setCurrentIndex(1)
            series = QPieSeries()
            for named in stats.by_category:
                if named.amount_cents > 0:
                    label = named.name + self._archive_suffix(named.id, self._archived_categories)
                    series.append(label, named.amount_cents / 100)
            # Slice callouts duplicate the legend and often vanish on dark theme.
            for pie_slice in series.slices():
                pie_slice.setLabelVisible(False)
            chart = QChart()
            chart.addSeries(series)
            chart.setTitle(t("stats.chart.by_category"))
            style_chart(chart)
            legend = chart.legend()
            legend.setVisible(True)
            legend.setAlignment(Qt.AlignmentFlag.AlignRight)
            p = current_palette()
            legend.setLabelColor(QColor(p.text))
            legend.setBackgroundVisible(False)
            self._chart_view.setBackgroundBrush(QBrush(QColor(p.shell)))
            self._chart_view.setChart(chart)
        elif self._mode_dynamics.isChecked():
            self._stack.setCurrentIndex(1)
            self._render_dynamics()
        else:
            self._stack.setCurrentIndex(2)
            self._merchant_table.setRowCount(len(stats.by_merchant))
            for row, named in enumerate(stats.by_merchant):
                label = named.name + self._archive_suffix(named.id, self._archived_merchants)
                self._merchant_table.setItem(row, 0, QTableWidgetItem(label))
                amount_cell = QTableWidgetItem(
                    Money.from_cents(named.amount_cents).format_rub()
                )
                amount_cell.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                self._merchant_table.setItem(row, 1, amount_cell)
            apply_column_widths(
                self._merchant_table,
                fixed_cols=(1,),
                stretch_cols=(0,),
            )

    def _fill_compare_table(self, previous: StatsDto, current: StatsDto) -> None:
        cats, people = compare_stats(previous, current)
        self._compare_table.clearSpans()
        self._compare_table.setRowCount(0)
        p = current_palette()
        danger = QColor("#C44B4B")
        ok = QColor(p.accent)
        muted = QColor(p.muted)

        def add_section(title: str) -> None:
            row = self._compare_table.rowCount()
            self._compare_table.insertRow(row)
            item = QTableWidgetItem(title)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            item.setForeground(muted)
            self._compare_table.setItem(row, 0, item)
            self._compare_table.setSpan(row, 0, 1, 5)

        def add_row(entry: CompareRow) -> None:
            row = self._compare_table.rowCount()
            self._compare_table.insertRow(row)
            delta = entry.delta_cents
            if delta > 0:
                delta_text = f"+{_rub(delta)}"
                color = danger
            elif delta < 0:
                delta_text = f"−{_rub(abs(delta))}"
                color = ok
            else:
                delta_text = "0.00"
                color = muted
            values = [
                entry.name,
                _rub(entry.previous_cents),
                _rub(entry.current_cents),
                delta_text,
                format_delta_pct(entry),
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col >= 1:
                    cell.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                if col >= 3:
                    cell.setForeground(color)
                self._compare_table.setItem(row, col, cell)

        add_section(t("stats.section.categories"))
        for entry in cats:
            add_row(entry)
        add_section(t("stats.section.people"))
        for entry in people:
            add_row(entry)
        apply_column_widths(
            self._compare_table,
            fixed_cols=(1, 2, 3, 4),
            stretch_cols=(0,),
        )

    def _render_dynamics(self) -> None:
        try:
            series_data = self._expenses.get_period_series(self._filter())
        except DomainError as exc:
            QMessageBox.warning(self, t("common.app_name"), str(exc))
            return
        line = QLineSeries()
        line.setPointsVisible(len(series_data.points) <= 62)
        raw_labels: list[str] = []
        max_rub = 0.0
        for idx, point in enumerate(series_data.points):
            rub = point.amount_cents / 100.0
            max_rub = max(max_rub, rub)
            line.append(float(idx), rub)
            raw_labels.append(point.label)
        categories = thin_axis_labels(raw_labels, max_visible=7)
        chart = QChart()
        chart.addSeries(line)
        grain = (
            t("stats.chart.grain_weeks")
            if series_data.grain == "week"
            else t("stats.chart.grain_days")
        )
        chart.setTitle(t("stats.chart.by_grain", grain=grain))
        chart.legend().setVisible(False)
        axis_x = QBarCategoryAxis()
        if categories:
            axis_x.append(categories)
        else:
            axis_x.append(["—"])
            line.append(0.0, 0.0)
        axis_y = QValueAxis()
        axis_y.setLabelFormat("%.0f")
        axis_y.setRange(0.0, max(max_rub * 1.15, 1.0))
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        line.attachAxis(axis_x)
        line.attachAxis(axis_y)
        style_chart(chart)
        style_axis(axis_x, show_grid=False)
        style_axis(axis_y, show_grid=True)
        p = current_palette()
        pen = line.pen()
        pen.setColor(QColor(p.accent))
        pen.setWidth(2)
        line.setPen(pen)
        self._chart_view.setBackgroundBrush(QBrush(QColor(p.shell)))
        self._chart_view.setChart(chart)

    def _reset(self) -> None:
        self._preset.setCurrentIndex(0)
        self._set_this_month()
        self._merchant_query.clear()
        self._include_archived.blockSignals(True)
        self._include_archived.setChecked(False)
        self._include_archived.blockSignals(False)
        self._compare.blockSignals(True)
        self._compare.setChecked(False)
        self._compare.blockSignals(False)
        self.reload_filters()
        self.refresh()

    def _set_this_month(self) -> None:
        today = date.today()
        self._from.setDate(QDate(today.year, today.month, 1))
        self._to.setDate(QDate(today.year, today.month, today.day))

    def _set_prev_month(self) -> None:
        today = date.today()
        first_this = date(today.year, today.month, 1)
        last_prev = first_this - timedelta(days=1)
        self._from.setDate(QDate(last_prev.year, last_prev.month, 1))
        self._to.setDate(QDate(last_prev.year, last_prev.month, last_prev.day))

    def _set_30_days(self) -> None:
        today = date.today()
        start = today - timedelta(days=29)
        self._from.setDate(QDate(start.year, start.month, start.day))
        self._to.setDate(QDate(today.year, today.month, today.day))

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, t("stats.dialog.export_title"), "budget.csv", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            self._export.export_csv(self._filter(), Path(path))
            QMessageBox.information(
                self, t("common.app_name"), t("stats.msg.saved", path=path)
            )
        except (DomainError, OSError) as exc:
            QMessageBox.warning(self, t("common.app_name"), str(exc))

    def _import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("stats.dialog.import_title"), "", "CSV (*.csv)"
        )
        if not path:
            return
        if not ask_yes_no(self, t("stats.msg.import_confirm")):
            return
        try:
            result = self._export.import_csv(Path(path))
        except (DomainError, OSError) as exc:
            QMessageBox.warning(self, t("common.app_name"), str(exc))
            return
        lines = [t("stats.msg.imported_rows", count=result.imported)]
        if result.errors:
            lines.append(t("stats.msg.error_count", count=len(result.errors)))
            preview = result.errors[:8]
            for row_no, message in preview:
                lines.append(t("stats.msg.error_row", row=row_no, message=message))
            if len(result.errors) > 8:
                lines.append(t("stats.msg.error_more", count=len(result.errors) - 8))
        QMessageBox.information(self, t("common.app_name"), "\n".join(lines))
        self.reload_filters()
        self.refresh()

    def _backup(self) -> None:
        try:
            path = self._export.backup_database()
            QMessageBox.information(
                self, t("common.app_name"), t("stats.msg.backup_done", path=path)
            )
        except OSError as exc:
            QMessageBox.warning(self, t("common.app_name"), str(exc))
