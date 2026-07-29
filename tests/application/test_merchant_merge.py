from __future__ import annotations

from datetime import date

import pytest

from src.application.dto import ExpenseFilter
from src.domain.errors import NotFound, ValidationError
from src.domain.money import Money


def test_merge_merchants_reassigns_expenses(world):
    catalogs, expenses, prefs, export, tmp = world
    person = catalogs.create_person("Аня")
    food = catalogs.create_category("Еда")
    a = catalogs.create_merchant("Пятёрочка", food.id)
    b = catalogs.create_merchant("Пятерочка Dup", food.id)
    expenses.add_expense(
        amount=Money.from_rubles_str("100"),
        spent_on=date(2026, 7, 1),
        person_id=person.id,
        category_id=food.id,
        merchant_input="Пятёрочка",
        note="",
    )
    expenses.add_expense(
        amount=Money.from_rubles_str("50"),
        spent_on=date(2026, 7, 2),
        person_id=person.id,
        category_id=food.id,
        merchant_input="Пятерочка Dup",
        note="",
    )

    merged = catalogs.merge_merchants(
        survivor_id=a.id, source_ids=[b.id], display_name="Пятёрочка"
    )
    assert merged.id == a.id
    assert merged.display_name == "Пятёрочка"
    assert all(m.id != b.id for m in catalogs.list_merchants(True))
    items = expenses.list_expenses(
        ExpenseFilter(date_from=date(2026, 1, 1), date_to=date(2026, 12, 31))
    )
    assert len(items) == 2
    assert {i.merchant_id for i in items} == {a.id}
    assert all(i.merchant_name == "Пятёрочка" for i in items)


def test_merge_merchants_requires_same_category(world):
    catalogs, expenses, prefs, export, tmp = world
    food = catalogs.create_category("Еда")
    taxi = catalogs.create_category("Такси")
    a = catalogs.create_merchant("Магнит", food.id)
    b = catalogs.create_merchant("Яндекс", taxi.id)
    with pytest.raises(ValidationError):
        catalogs.merge_merchants(survivor_id=a.id, source_ids=[b.id])


def test_merge_merchants_needs_sources(world):
    catalogs, expenses, prefs, export, tmp = world
    food = catalogs.create_category("Еда")
    a = catalogs.create_merchant("Магнит", food.id)
    with pytest.raises(ValidationError):
        catalogs.merge_merchants(survivor_id=a.id, source_ids=[a.id])


def test_merge_unknown_merchant(world):
    catalogs, expenses, prefs, export, tmp = world
    food = catalogs.create_category("Еда")
    a = catalogs.create_merchant("Магнит", food.id)
    with pytest.raises(NotFound):
        catalogs.merge_merchants(survivor_id=a.id, source_ids=[99999])
