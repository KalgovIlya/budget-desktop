from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from src.application.dto import ExpenseFilter
from src.domain.errors import ValidationError
from src.domain.money import Money


def test_csv_import_replaces_database(world):
    catalogs, expenses, prefs, export, tmp = world
    p = catalogs.create_person("Аня")
    c = catalogs.create_category("Еда")
    expenses.add_expense(
        amount=Money.from_rubles_str("10.50"),
        spent_on=date(2026, 7, 1),
        person_id=p.id,
        category_id=c.id,
        merchant_input="Самокат",
        note="тест",
    )
    target = tmp / "out.csv"
    export.export_csv(
        ExpenseFilter(date_from=date(2026, 7, 1), date_to=date(2026, 7, 31)),
        target,
    )

    # Add extra local data that must disappear after import.
    catalogs.create_person("Лишний")
    result = export.import_csv(target)
    assert result.imported == 1
    assert result.errors == ()
    assert {p.name for p in catalogs.list_people(False)} == {"Аня"}
    items = expenses.list_expenses(
        ExpenseFilter(date_from=date(2026, 1, 1), date_to=date(2026, 12, 31))
    )
    assert len(items) == 1

    # Second import of the same file does not duplicate.
    result2 = export.import_csv(target)
    assert result2.imported == 1
    items2 = expenses.list_expenses(
        ExpenseFilter(date_from=date(2026, 1, 1), date_to=date(2026, 12, 31))
    )
    assert len(items2) == 1


def test_csv_import_creates_from_empty(world):
    catalogs, expenses, prefs, export, tmp = world
    path = tmp / "in.csv"
    path.write_text(
        "spent_on;amount_rub;person;category;merchant;note\n"
        "2026-07-02;99.00;Боря;Такси;Яндекс;поездка\n",
        encoding="utf-8-sig",
    )
    result = export.import_csv(path)
    assert result.imported == 1
    assert result.errors == ()
    assert {p.name for p in catalogs.list_people(False)} == {"Боря"}
    assert {c.name for c in catalogs.list_categories(False)} == {"Такси"}
    assert {m.display_name for m in catalogs.list_merchants(False)} == {"Яндекс"}


def test_csv_import_bad_row_after_wipe(world):
    catalogs, expenses, prefs, export, tmp = world
    p = catalogs.create_person("Старый")
    c = catalogs.create_category("Старое")
    expenses.add_expense(
        amount=Money.from_rubles_str("1"),
        spent_on=date(2026, 1, 1),
        person_id=p.id,
        category_id=c.id,
        merchant_input="Старое место",
        note="",
    )
    path = tmp / "mixed.csv"
    path.write_text(
        "spent_on;amount_rub;person;category;merchant;note\n"
        "2026-07-02;not-a-sum;Аня;Еда;Магнит;\n"
        "2026-07-03;50.00;Аня;Еда;Магнит;ok\n",
        encoding="utf-8-sig",
    )
    result = export.import_csv(path)
    assert result.imported == 1
    assert len(result.errors) == 1
    assert result.errors[0][0] == 2
    # Old data wiped even though one row failed.
    assert {p.name for p in catalogs.list_people(False)} == {"Аня"}
    assert len(
        expenses.list_expenses(
            ExpenseFilter(date_from=date(2026, 1, 1), date_to=date(2026, 12, 31))
        )
    ) == 1


def test_csv_import_bad_header_keeps_data(world):
    catalogs, expenses, prefs, export, tmp = world
    p = catalogs.create_person("Аня")
    c = catalogs.create_category("Еда")
    expenses.add_expense(
        amount=Money.from_rubles_str("10"),
        spent_on=date(2026, 7, 1),
        person_id=p.id,
        category_id=c.id,
        merchant_input="Магнит",
        note="",
    )
    path = tmp / "bad.csv"
    path.write_text("a;b;c\n1;2;3\n", encoding="utf-8-sig")
    with pytest.raises(ValidationError):
        export.import_csv(path)
    assert len(catalogs.list_people(False)) == 1
    assert len(
        expenses.list_expenses(
            ExpenseFilter(date_from=date(2026, 1, 1), date_to=date(2026, 12, 31))
        )
    ) == 1
