from datetime import date

from src.application.budget_service import BudgetService, month_bounds
from src.domain.money import Money


def test_budget_limit_and_status(world):
    catalogs, expenses, *_ = world
    catalogs_repo = expenses._c
    budgets = BudgetService(catalogs_repo, expenses._e)
    person = catalogs.create_person("Я")
    food = catalogs.create_category("Еда")
    taxi = catalogs.create_category("Такси")
    budgets.set_limit(food.id, 10_000)
    expenses.add_expense(
        amount=Money.from_rubles_str("40"),
        spent_on=date.today().replace(day=1),
        person_id=person.id,
        category_id=food.id,
        merchant_input="Лента",
    )
    statuses = {s.category_id: s for s in budgets.list_status(today=date.today())}
    assert statuses[food.id].limit_cents == 10_000
    assert statuses[food.id].spent_cents == 4000
    assert statuses[food.id].remaining_cents == 6000
    assert statuses[taxi.id].limit_cents is None


def test_clear_limit(world):
    catalogs, expenses, *_ = world
    budgets = BudgetService(expenses._c, expenses._e)
    food = catalogs.create_category("Еда")
    budgets.set_limit(food.id, 5000)
    budgets.set_limit(food.id, None)
    assert budgets.list_status()[0].limit_cents is None


def test_warning_when_over_current_month(world):
    catalogs, expenses, *_ = world
    budgets = BudgetService(expenses._c, expenses._e)
    person = catalogs.create_person("Я")
    food = catalogs.create_category("Еда")
    budgets.set_limit(food.id, 5000)
    today = date.today()
    expenses.add_expense(
        amount=Money.from_rubles_str("60"),
        spent_on=today,
        person_id=person.id,
        category_id=food.id,
        merchant_input="Лента",
    )
    msg = budgets.warning_if_over(food.id, today, today=today)
    assert msg is not None
    assert "превышен" in msg


def test_no_warning_outside_month(world):
    catalogs, expenses, *_ = world
    budgets = BudgetService(expenses._c, expenses._e)
    person = catalogs.create_person("Я")
    food = catalogs.create_category("Еда")
    budgets.set_limit(food.id, 1000)
    start, _ = month_bounds(date.today())
    if start.month == 1:
        old = date(start.year - 1, 12, 15)
    else:
        old = date(start.year, start.month - 1, 15)
    expenses.add_expense(
        amount=Money.from_rubles_str("50"),
        spent_on=old,
        person_id=person.id,
        category_id=food.id,
        merchant_input="Лента",
    )
    assert budgets.warning_if_over(food.id, old) is None
