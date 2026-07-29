from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.application.budget_service import BudgetService
from src.application.catalog_service import CatalogService
from src.application.dto import UiPreferences
from src.application.expense_service import ExpenseService, PreferencesService
from src.application.export_service import ExportService
from src.i18n import get_locale, locale_display_name, set_locale, t
from src.ui.theme import app_qss, current_theme_name, set_theme_name
from src.ui.views.budgets_view import BudgetsView
from src.ui.views.catalogs_view import CatalogsView
from src.ui.views.expenses_view import ExpensesView
from src.ui.views.stats_view import StatsView

_TAB_KEYS = (
    "main.tab.expenses",
    "main.tab.stats",
    "main.tab.budgets",
    "main.tab.catalogs",
)


class MainWindow(QMainWindow):
    def __init__(
        self,
        catalogs: CatalogService,
        expenses: ExpenseService,
        prefs: PreferencesService,
        export: ExportService,
        budgets: BudgetService,
    ) -> None:
        super().__init__()
        self._prefs = prefs
        self.setWindowTitle(t("common.app_name"))
        self.resize(1180, 760)
        self.setMinimumSize(960, 640)
        self.setStyleSheet(app_qss())

        self._expenses_view = ExpensesView(expenses, catalogs, prefs, budgets)
        self._stats_view = StatsView(expenses, catalogs, export)
        self._budgets_view = BudgetsView(budgets)
        self._catalogs_view = CatalogsView(catalogs)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._expenses_view)
        self._stack.addWidget(self._stats_view)
        self._stack.addWidget(self._budgets_view)
        self._stack.addWidget(self._catalogs_view)

        self._brand = QLabel(t("common.app_name"))
        self._brand.setObjectName("brand")
        self._subtitle = QLabel(t("main.subtitle"))
        self._subtitle.setObjectName("subtitle")

        brand_box = QVBoxLayout()
        brand_box.setSpacing(0)
        brand_box.addWidget(self._brand)
        brand_box.addWidget(self._subtitle)

        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)
        tabs_row = QHBoxLayout()
        tabs_row.setContentsMargins(4, 4, 4, 4)
        tabs_row.setSpacing(4)
        self._tab_buttons: list[QPushButton] = []
        for index, key in enumerate(_TAB_KEYS):
            btn = QPushButton(t(key))
            btn.setObjectName("tabBtn")
            btn.setCheckable(True)
            btn.setChecked(index == 0)
            btn.clicked.connect(lambda checked=False, i=index: self._switch(i))
            self._tab_group.addButton(btn, index)
            self._tab_buttons.append(btn)
            tabs_row.addWidget(btn)

        tab_bar = QFrame()
        tab_bar.setObjectName("tabBar")
        tab_bar.setLayout(tabs_row)

        chrome_font = QFont()
        chrome_font.setPointSize(12)
        chrome_font.setWeight(QFont.Weight.DemiBold)

        self._theme_btn = QToolButton()
        self._theme_btn.setObjectName("themeCombo")
        self._theme_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._theme_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self._theme_btn.setAutoRaise(True)
        self._theme_btn.setFont(chrome_font)
        self._theme_menu = QMenu(self._theme_btn)
        self._theme_menu.setObjectName("themeMenu")
        self._theme_btn.setMenu(self._theme_menu)

        self._lang_btn = QToolButton()
        self._lang_btn.setObjectName("themeCombo")
        self._lang_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._lang_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self._lang_btn.setAutoRaise(True)
        self._lang_btn.setFont(chrome_font)
        self._lang_menu = QMenu(self._lang_btn)
        self._lang_menu.setObjectName("themeMenu")
        self._lang_btn.setMenu(self._lang_menu)

        self._rebuild_theme_menu()
        self._rebuild_lang_menu()
        self._sync_theme_label()
        self._sync_lang_label()

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(12)
        header.addLayout(brand_box)
        header.addWidget(tab_bar)
        header.addStretch(1)
        header.addWidget(
            self._lang_btn, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        header.addWidget(
            self._theme_btn, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        shell = QFrame()
        shell.setObjectName("shell")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(16, 16, 16, 16)
        shell_layout.setSpacing(12)
        shell_layout.addLayout(header)
        shell_layout.addWidget(self._stack, stretch=1)

        central = QWidget()
        central.setObjectName("central")
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.addWidget(shell)
        self.setCentralWidget(central)

        QShortcut(QKeySequence("Ctrl+N"), self, activated=self._hotkey_new_expense)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._hotkey_focus_search)

    def _hotkey_new_expense(self) -> None:
        self._switch(0)
        self._expenses_view.add_expense()

    def _hotkey_focus_search(self) -> None:
        self._switch(0)
        self._expenses_view.focus_search()

    def _rebuild_theme_menu(self) -> None:
        self._theme_menu.clear()
        act_light = self._theme_menu.addAction(t("main.theme.light"))
        act_dark = self._theme_menu.addAction(t("main.theme.dark"))
        act_light.triggered.connect(lambda: self._apply_theme("light"))
        act_dark.triggered.connect(lambda: self._apply_theme("dark"))

    def _rebuild_lang_menu(self) -> None:
        self._lang_menu.clear()
        act_en = self._lang_menu.addAction(t("main.lang.en"))
        act_ru = self._lang_menu.addAction(t("main.lang.ru"))
        act_en.triggered.connect(lambda: self._apply_locale("en"))
        act_ru.triggered.connect(lambda: self._apply_locale("ru"))

    def _fit_tool_button(self, btn: QToolButton, text: str) -> None:
        btn.setText(text)
        metrics = btn.fontMetrics()
        btn.setMinimumWidth(metrics.horizontalAdvance(text) + 28)
        btn.setMinimumHeight(metrics.height() + 18)
        btn.adjustSize()

    def _sync_theme_label(self) -> None:
        name = (
            t("main.theme.dark")
            if current_theme_name() == "dark"
            else t("main.theme.light")
        )
        self._fit_tool_button(self._theme_btn, t("main.theme.label", name=name))

    def _sync_lang_label(self) -> None:
        self._fit_tool_button(
            self._lang_btn,
            t("main.lang.label", name=locale_display_name()),
        )

    def _copy_prefs(self, **overrides) -> UiPreferences:
        current = self._prefs.get()
        return UiPreferences(
            last_person_id=overrides.get("last_person_id", current.last_person_id),
            last_category_id=overrides.get(
                "last_category_id", current.last_category_id
            ),
            theme=overrides.get("theme", current.theme),
            locale=overrides.get("locale", current.locale),
        )

    def _apply_theme(self, next_theme: str) -> None:
        if next_theme not in ("light", "dark") or next_theme == current_theme_name():
            return
        set_theme_name(next_theme)
        sheet = app_qss()
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(sheet)
        self.setStyleSheet(sheet)
        self._prefs.save(self._copy_prefs(theme=next_theme))
        self._sync_theme_label()
        self._switch(self._stack.currentIndex())

    def _apply_locale(self, next_locale: str) -> None:
        if next_locale not in ("ru", "en") or next_locale == get_locale():
            return
        set_locale(next_locale)
        self._prefs.save(self._copy_prefs(locale=next_locale))
        self._retranslate()
        self._switch(self._stack.currentIndex())

    def _retranslate(self) -> None:
        self.setWindowTitle(t("common.app_name"))
        self._brand.setText(t("common.app_name"))
        self._subtitle.setText(t("main.subtitle"))
        for btn, key in zip(self._tab_buttons, _TAB_KEYS):
            btn.setText(t(key))
        self._rebuild_theme_menu()
        self._rebuild_lang_menu()
        self._sync_theme_label()
        self._sync_lang_label()
        self._expenses_view.retranslate()
        self._stats_view.retranslate()
        self._budgets_view.retranslate()
        self._catalogs_view.retranslate()

    def _switch(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        btn = self._tab_group.button(index)
        if btn:
            btn.setChecked(True)
        if index == 0:
            self._expenses_view.refresh()
        elif index == 1:
            self._stats_view.reload_filters()
            self._stats_view.refresh()
        elif index == 2:
            self._budgets_view.refresh()
        else:
            self._catalogs_view.refresh()
