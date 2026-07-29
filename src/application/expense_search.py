from __future__ import annotations

from src.application.dto import Expense
from src.domain.money import Money


def match_expense_query(expense: Expense, query: str) -> bool:
    needle = query.strip().casefold()
    if not needle:
        return True
    amount = Money.from_cents(expense.amount_cents)
    haystacks = (
        expense.person_name,
        expense.category_name,
        expense.merchant_name,
        expense.note,
        amount.format_rub(),
        f"{amount.cents / 100:.0f}" if amount.cents % 100 == 0 else "",
        str(amount.cents),
    )
    return any(needle in value.casefold() for value in haystacks if value)
