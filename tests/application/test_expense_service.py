from datetime import date
from pathlib import Path

import pytest

from src.application.dto import ExpenseFilter
from src.domain.errors import AlreadyExists, ArchivedEntity, InUse, ValidationError
from src.domain.money import Money


def test_merchant_bound_to_category(world):
    catalogs, expenses, *_ = world
    food = catalogs.create_category("Еда")
    taxi = catalogs.create_category("Такси")
    m = catalogs.create_merchant("Пятёрочка", food.id)
    assert m.category_id == food.id
    with pytest.raises(AlreadyExists):
        catalogs.create_merchant("пятерочка", food.id)
    with pytest.raises(ValidationError):
        catalogs.resolve_merchant_for_expense("Пятёрочка", taxi.id)
    resolved = catalogs.resolve_merchant_for_expense(" Пятёрочка ", food.id)
    assert resolved.id == m.id


def test_archived_merchant_resolve(world):
    catalogs, expenses, *_ = world
    food = catalogs.create_category("Еда")
    m = catalogs.create_merchant("Ozon", food.id)
    catalogs.archive_merchant(m.id)
    with pytest.raises(ArchivedEntity):
        catalogs.resolve_merchant_for_expense("ozon", food.id)


def test_delete_in_use(world):
    catalogs, expenses, *_ = world
    p = catalogs.create_person("Я")
    c = catalogs.create_category("Еда")
    expenses.add_expense(
        amount=Money.from_rubles_str("100"),
        spent_on=date(2026, 7, 1),
        person_id=p.id,
        category_id=c.id,
        merchant_input="Лента",
    )
    with pytest.raises(InUse):
        catalogs.delete_person(p.id)
    catalogs.archive_person(p.id)


def test_stats_and_purge(world):
    catalogs, expenses, *_ = world
    p = catalogs.create_person("Я")
    c = catalogs.create_category("Еда")
    expenses.add_expense(
        amount=Money.from_rubles_str("100"),
        spent_on=date(2026, 7, 28),
        person_id=p.id,
        category_id=c.id,
        merchant_input="Лента",
    )
    expenses.add_expense(
        amount=Money.from_rubles_str("50"),
        spent_on=date(2023, 1, 1),
        person_id=p.id,
        category_id=c.id,
        merchant_input="Лента",
    )
    stats = expenses.get_stats(
        ExpenseFilter(date_from=date(2020, 1, 1), date_to=date(2026, 12, 31))
    )
    assert stats.total_cents == 10000
    assert len(stats.items) == 1


def test_csv_export(world):
    catalogs, expenses, prefs, export, tmp = world
    p = catalogs.create_person("Я")
    c = catalogs.create_category("Еда")
    expenses.add_expense(
        amount=Money.from_rubles_str("10.5"),
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
    text = target.read_text(encoding="utf-8-sig")
    assert "spent_on;amount_rub;person;category;merchant;note" in text
    assert "10.50" in text
