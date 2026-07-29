"""Reset local Budget DB and seed Russian demo data (for RU README screenshots)."""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.application.budget_service import BudgetService
from src.application.catalog_service import CatalogService
from src.application.dto import UiPreferences
from src.application.expense_service import ExpenseService, PreferencesService
from src.domain.clock import SystemClock
from src.domain.money import Money
from src.infrastructure.db import connect, migrate, reset_database
from src.infrastructure.paths import backups_dir, db_path, preferences_path
from src.infrastructure.preferences_json import JsonPreferencesStore
from src.infrastructure.sqlite_repos import SqliteCatalogs, SqliteExpenses


def seed() -> Path:
    db = db_path()
    if db.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        bak = backups_dir() / f"pre-seed-{stamp}.db"
        shutil.copy2(db, bak)
        print("backed up to", bak)

    reset_database(db)
    conn = connect(db)
    migrate(conn)
    clock = SystemClock()
    catalogs_repo = SqliteCatalogs(conn)
    expenses_repo = SqliteExpenses(conn)
    catalogs = CatalogService(catalogs_repo, clock)
    expenses = ExpenseService(expenses_repo, catalogs_repo, catalogs, clock)
    budgets = BudgetService(catalogs_repo, expenses_repo)
    prefs = PreferencesService(JsonPreferencesStore(preferences_path()), catalogs_repo)

    anna = catalogs.create_person("Анна")
    ivan = catalogs.create_person("Иван")

    groceries = catalogs.create_category("Продукты")
    transport = catalogs.create_category("Транспорт")
    dining = catalogs.create_category("Кафе")
    home = catalogs.create_category("Дом")

    today = date.today()
    month_start = today.replace(day=1)

    samples = [
        (anna, groceries, "Пятёрочка", "1254.00", 2, "Недельные покупки"),
        (ivan, groceries, "Магнит", "678.50", 5, ""),
        (anna, transport, "Яндекс Go", "350.00", 1, "В аэропорт"),
        (ivan, transport, "Метро", "87.00", 8, ""),
        (anna, dining, "Кофемания", "420.00", 0, "Кофе"),
        (ivan, dining, "Додо Пицца", "890.00", 3, "Пятница"),
        (anna, dining, "СушиWok", "1450.00", 10, ""),
        (ivan, home, "Леруа Мерлен", "3200.00", 12, "Полки"),
        (anna, home, "Ozon", "599.00", 6, "Батарейки"),
        (ivan, groceries, "Пятёрочка", "540.20", 14, ""),
        (anna, transport, "Яндекс Go", "280.00", 4, ""),
        (ivan, dining, "Кофемания", "290.00", 7, ""),
    ]
    for person, category, merchant, amount, days_ago, note in samples:
        spent = today - timedelta(days=days_ago)
        if spent < month_start:
            spent = month_start
        expenses.add_expense(
            amount=Money.from_rubles_str(amount),
            spent_on=spent,
            person_id=person.id,
            category_id=category.id,
            merchant_input=merchant,
            note=note,
        )

    budgets.set_limit(groceries.id, Money.from_rubles_str("8000.00").cents)
    budgets.set_limit(dining.id, Money.from_rubles_str("5000.00").cents)
    budgets.set_limit(transport.id, Money.from_rubles_str("3000.00").cents)

    prefs.save(
        UiPreferences(
            last_person_id=anna.id,
            last_category_id=groceries.id,
            theme="light",
            locale="ru",
        )
    )
    print("seeded", db)
    return db


if __name__ == "__main__":
    seed()
