from datetime import date

from src.application.dto import ExpenseFilter
from src.domain.money import Money


def test_stats_excludes_archived_by_default(world):
    catalogs, expenses, *_ = world
    active = catalogs.create_person("Я")
    archived = catalogs.create_person("Бывший")
    cat = catalogs.create_category("Еда")
    expenses.add_expense(
        amount=Money.from_rubles_str("100"),
        spent_on=date(2026, 7, 1),
        person_id=active.id,
        category_id=cat.id,
        merchant_input="Лента",
    )
    expenses.add_expense(
        amount=Money.from_rubles_str("40"),
        spent_on=date(2026, 7, 2),
        person_id=archived.id,
        category_id=cat.id,
        merchant_input="Магнит",
    )
    catalogs.archive_person(archived.id)

    filt = ExpenseFilter(date_from=date(2026, 7, 1), date_to=date(2026, 7, 31))
    stats = expenses.get_stats(filt)
    assert stats.total_cents == 10000
    assert len(stats.items) == 1

    with_archive = expenses.get_stats(
        ExpenseFilter(
            date_from=date(2026, 7, 1),
            date_to=date(2026, 7, 31),
            include_archived=True,
        )
    )
    assert with_archive.total_cents == 14000
    assert len(with_archive.items) == 2


def test_stats_include_archived_merchant(world):
    catalogs, expenses, *_ = world
    person = catalogs.create_person("Я")
    cat = catalogs.create_category("Еда")
    expenses.add_expense(
        amount=Money.from_rubles_str("10"),
        spent_on=date(2026, 7, 1),
        person_id=person.id,
        category_id=cat.id,
        merchant_input="Старый магазин",
    )
    merchant = catalogs.list_merchants(False)[0]
    catalogs.archive_merchant(merchant.id)

    off = expenses.get_stats(
        ExpenseFilter(date_from=date(2026, 7, 1), date_to=date(2026, 7, 31))
    )
    assert off.total_cents == 0

    on = expenses.get_stats(
        ExpenseFilter(
            date_from=date(2026, 7, 1),
            date_to=date(2026, 7, 31),
            include_archived=True,
        )
    )
    assert on.total_cents == 1000


def test_merchant_query_respects_include_archived(world):
    catalogs, expenses, *_ = world
    person = catalogs.create_person("Я")
    cat = catalogs.create_category("Еда")
    expenses.add_expense(
        amount=Money.from_rubles_str("25"),
        spent_on=date(2026, 7, 1),
        person_id=person.id,
        category_id=cat.id,
        merchant_input="АрхивКафе",
    )
    merchant = catalogs.list_merchants(False)[0]
    catalogs.archive_merchant(merchant.id)

    off = expenses.get_stats(
        ExpenseFilter(
            date_from=date(2026, 7, 1),
            date_to=date(2026, 7, 31),
            merchant_query="Кафе",
        )
    )
    assert off.total_cents == 0

    on = expenses.get_stats(
        ExpenseFilter(
            date_from=date(2026, 7, 1),
            date_to=date(2026, 7, 31),
            merchant_query="Кафе",
            include_archived=True,
        )
    )
    assert on.total_cents == 2500
