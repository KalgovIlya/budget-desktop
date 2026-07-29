from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from src.application.budget_service import BudgetService
from src.application.catalog_service import CatalogService
from src.application.expense_service import ExpenseService, PreferencesService
from src.application.export_service import ExportService
from src.domain.clock import SystemClock
from src.infrastructure.db import connect, migrate
from src.infrastructure.paths import backups_dir, db_path, preferences_path
from src.infrastructure.preferences_json import JsonPreferencesStore
from src.infrastructure.resources import asset_path
from src.infrastructure.sqlite_repos import SqliteCatalogs, SqliteExpenses
from src.ui.main_window import MainWindow


def build_app(data_dir: Path | None = None) -> tuple[QApplication, MainWindow]:
    clock = SystemClock()
    database = db_path(data_dir)
    conn = connect(database)
    migrate(conn)

    catalogs_repo = SqliteCatalogs(conn)
    expenses_repo = SqliteExpenses(conn)
    catalog_service = CatalogService(catalogs_repo, clock)
    expense_service = ExpenseService(expenses_repo, catalogs_repo, catalog_service, clock)
    expense_service.purge_old_expenses()
    budget_service = BudgetService(catalogs_repo, expenses_repo)

    prefs = PreferencesService(JsonPreferencesStore(preferences_path(data_dir)), catalogs_repo)
    prefs.resolve_locale()
    export = ExportService(expense_service, catalog_service, database, backups_dir(data_dir))

    qt_app = QApplication.instance() or QApplication(sys.argv)
    from src.ui.theme import app_qss, set_theme_name

    set_theme_name(prefs.get().theme)
    qt_app.setStyle("Fusion")
    qt_app.setStyleSheet(app_qss())
    icon_file = asset_path("budget.ico")
    if not icon_file.exists():
        icon_file = asset_path("budget-icon.png")
    if icon_file.exists():
        qt_app.setWindowIcon(QIcon(str(icon_file)))
    window = MainWindow(catalog_service, expense_service, prefs, export, budget_service)
    return qt_app, window


def main() -> int:
    app, window = build_app()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
