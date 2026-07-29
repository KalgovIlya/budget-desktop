from src.application.dto import Expense
from src.application.expense_search import match_expense_query
from datetime import date


def _expense(**kwargs) -> Expense:
    base = dict(
        id=1,
        spent_on=date(2026, 7, 1),
        amount_cents=10050,
        person_id=1,
        category_id=1,
        merchant_id=1,
        note="обед",
        person_name="Я",
        category_name="Еда",
        merchant_name="Лента",
    )
    base.update(kwargs)
    return Expense(**base)


def test_empty_query_matches_all():
    assert match_expense_query(_expense(), "")
    assert match_expense_query(_expense(), "  ")


def test_matches_merchant_casefold():
    assert match_expense_query(_expense(), "лента")
    assert not match_expense_query(_expense(), "магнит")


def test_matches_note_person_category():
    assert match_expense_query(_expense(), "обед")
    assert match_expense_query(_expense(), "я")
    assert match_expense_query(_expense(), "еда")


def test_matches_amount_formats():
    assert match_expense_query(_expense(), "100.50")
    assert match_expense_query(_expense(amount_cents=10000), "100")
    assert match_expense_query(_expense(), "10050")
