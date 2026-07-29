from datetime import date

from src.application.dto import ExpenseFilter
from src.domain.errors import ArchivedEntity
from src.domain.money import Money
import pytest


def test_repeat_fields_create_second_expense(world):
    catalogs, expenses, *_ = world
    person = catalogs.create_person("Я")
    cat = catalogs.create_category("Еда")
    first = expenses.add_expense(
        amount=Money.from_rubles_str("120.50"),
        spent_on=date(2026, 7, 1),
        person_id=person.id,
        category_id=cat.id,
        merchant_input="Лента",
        note="обед",
    )
    second = expenses.add_expense(
        amount=Money.from_cents(first.amount_cents),
        spent_on=date.today(),
        person_id=first.person_id,
        category_id=first.category_id,
        merchant_input=first.merchant_name,
        note=first.note,
    )
    assert second.id != first.id
    assert second.amount_cents == first.amount_cents
    assert second.person_id == first.person_id
    assert second.category_id == first.category_id
    assert second.merchant_id == first.merchant_id
    assert second.note == first.note
    assert second.spent_on == date.today()

    items = expenses.list_expenses(
        ExpenseFilter(date_from=date(2026, 1, 1), date_to=date.today())
    )
    assert len(items) == 2


def test_repeat_blocked_when_person_archived(world):
    catalogs, expenses, *_ = world
    person = catalogs.create_person("Я")
    cat = catalogs.create_category("Еда")
    expense = expenses.add_expense(
        amount=Money.from_rubles_str("10"),
        spent_on=date(2026, 7, 1),
        person_id=person.id,
        category_id=cat.id,
        merchant_input="Лента",
    )
    catalogs.archive_person(person.id)
    with pytest.raises(ArchivedEntity):
        expenses.add_expense(
            amount=Money.from_cents(expense.amount_cents),
            spent_on=date.today(),
            person_id=expense.person_id,
            category_id=expense.category_id,
            merchant_input=expense.merchant_name,
            note=expense.note,
        )


def test_recent_templates_unique_and_limit(world):
    catalogs, expenses, *_ = world
    person = catalogs.create_person("Я")
    cat = catalogs.create_category("Еда")
    expenses.add_expense(
        amount=Money.from_rubles_str("100"),
        spent_on=date(2026, 7, 1),
        person_id=person.id,
        category_id=cat.id,
        merchant_input="Лента",
    )
    expenses.add_expense(
        amount=Money.from_rubles_str("100"),
        spent_on=date(2026, 7, 2),
        person_id=person.id,
        category_id=cat.id,
        merchant_input="Лента",
        note="повтор",
    )
    expenses.add_expense(
        amount=Money.from_rubles_str("50"),
        spent_on=date(2026, 7, 3),
        person_id=person.id,
        category_id=cat.id,
        merchant_input="Магнит",
    )
    templates = expenses.list_recent_templates(limit=5)
    assert len(templates) == 2
    assert templates[0].merchant_name == "Магнит"
    assert templates[0].amount_cents == 5000
    assert templates[1].merchant_name == "Лента"
    assert templates[1].note == "повтор"


def test_recent_templates_skip_archived_merchant(world):
    catalogs, expenses, *_ = world
    person = catalogs.create_person("Я")
    cat = catalogs.create_category("Еда")
    expenses.add_expense(
        amount=Money.from_rubles_str("10"),
        spent_on=date(2026, 7, 1),
        person_id=person.id,
        category_id=cat.id,
        merchant_input="Старый",
    )
    merchant = catalogs.list_merchants(False)[0]
    catalogs.archive_merchant(merchant.id)
    expenses.add_expense(
        amount=Money.from_rubles_str("20"),
        spent_on=date(2026, 7, 2),
        person_id=person.id,
        category_id=cat.id,
        merchant_input="Новый",
    )
    templates = expenses.list_recent_templates(limit=5)
    assert len(templates) == 1
    assert templates[0].merchant_name == "Новый"
