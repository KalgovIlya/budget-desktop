from __future__ import annotations

from pathlib import Path

import pytest

from src.application.catalog_service import CatalogService
from src.application.expense_service import ExpenseService, PreferencesService
from src.application.export_service import ExportService
from src.domain.clock import SystemClock
from src.i18n import set_locale
from src.infrastructure.db import connect, migrate
from src.infrastructure.preferences_json import JsonPreferencesStore
from src.infrastructure.sqlite_repos import SqliteCatalogs, SqliteExpenses


@pytest.fixture(autouse=True)
def _force_ru_locale():
    set_locale("ru")
    yield
    set_locale("ru")


@pytest.fixture
def world(tmp_path: Path):
    db = tmp_path / "t.db"
    conn = connect(db)
    migrate(conn)
    clock = SystemClock()
    catalogs = SqliteCatalogs(conn)
    expenses = SqliteExpenses(conn)
    catalog_svc = CatalogService(catalogs, clock)
    expense_svc = ExpenseService(expenses, catalogs, catalog_svc, clock)
    prefs = PreferencesService(JsonPreferencesStore(tmp_path / "preferences.json"), catalogs)
    export = ExportService(expense_svc, catalog_svc, db, tmp_path / "backups")
    return catalog_svc, expense_svc, prefs, export, tmp_path
