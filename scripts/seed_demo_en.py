"""Reset local Budget DB and seed English demo data (for screenshots / trial)."""

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

    alex = catalogs.create_person("Alex")
    sam = catalogs.create_person("Sam")

    groceries = catalogs.create_category("Groceries")
    transport = catalogs.create_category("Transport")
    dining = catalogs.create_category("Dining")
    home = catalogs.create_category("Home")

    today = date.today()
    month_start = today.replace(day=1)

    samples = [
        (alex, groceries, "Whole Foods", "125.40", 2, "Weekly run"),
        (sam, groceries, "Trader Joe's", "67.80", 5, ""),
        (alex, transport, "Uber", "18.50", 1, "Airport"),
        (sam, transport, "Metro Card", "33.00", 8, ""),
        (alex, dining, "Blue Bottle", "12.50", 0, "Coffee"),
        (sam, dining, "Pizza Place", "42.00", 3, "Friday night"),
        (alex, dining, "Sushi Bar", "78.20", 10, ""),
        (sam, home, "IKEA", "156.00", 12, "Shelves"),
        (alex, home, "Amazon", "29.99", 6, "Batteries"),
        (sam, groceries, "Whole Foods", "54.10", 14, ""),
        (alex, transport, "Uber", "9.75", 4, ""),
        (sam, dining, "Blue Bottle", "6.25", 7, ""),
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

    budgets.set_limit(groceries.id, Money.from_rubles_str("400.00").cents)
    budgets.set_limit(dining.id, Money.from_rubles_str("200.00").cents)
    budgets.set_limit(transport.id, Money.from_rubles_str("150.00").cents)

    prefs.save(
        UiPreferences(
            last_person_id=alex.id,
            last_category_id=groceries.id,
            theme="light",
            locale="en",
        )
    )
    print("seeded", db)
    return db


if __name__ == "__main__":
    seed()
