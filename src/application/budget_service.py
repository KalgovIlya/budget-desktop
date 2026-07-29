from __future__ import annotations

from calendar import monthrange
from datetime import date

from src.application.dto import CategoryBudgetStatus
from src.domain.errors import NotFound, ValidationError
from src.domain.money import Money
from src.i18n import t
from src.infrastructure.sqlite_repos import SqliteCatalogs, SqliteExpenses


def month_bounds(day: date) -> tuple[date, date]:
    last = monthrange(day.year, day.month)[1]
    return date(day.year, day.month, 1), date(day.year, day.month, last)


def month_label(day: date) -> str:
    return t("month.label", month=t(f"month.{day.month}"), year=day.year)


class BudgetService:
    def __init__(self, catalogs: SqliteCatalogs, expenses: SqliteExpenses) -> None:
        self._c = catalogs
        self._e = expenses

    def list_status(self, *, today: date | None = None) -> list[CategoryBudgetStatus]:
        today = today or date.today()
        start, end = month_bounds(today)
        limits = self._c.list_category_budget_cents()
        out: list[CategoryBudgetStatus] = []
        for cat in self._c.list_categories(False):
            spent = self._e.sum_category_spent(cat.id, start, end)
            out.append(
                CategoryBudgetStatus(
                    category_id=cat.id,
                    name=cat.name,
                    limit_cents=limits.get(cat.id),
                    spent_cents=spent,
                )
            )
        out.sort(key=lambda s: s.name.casefold())
        return out

    def set_limit(self, category_id: int, limit_cents: int | None) -> None:
        cat = self._c.get_category(category_id)
        if cat is None:
            raise NotFound(t("err.category_not_found"))
        if cat.is_archived:
            raise ValidationError(t("budget.err.archived_limit"))
        if limit_cents is None:
            self._c.delete_category_budget(category_id)
            return
        if limit_cents <= 0:
            raise ValidationError(t("budget.err.limit_positive"))
        self._c.upsert_category_budget(category_id, limit_cents)

    def set_limit_from_text(self, category_id: int, text: str) -> None:
        cleaned = text.strip().replace(" ", "").replace(",", ".")
        if not cleaned:
            self.set_limit(category_id, None)
            return
        money = Money.from_rubles_str(cleaned)
        self.set_limit(category_id, money.cents)

    def warning_if_over(
        self, category_id: int, spent_on: date, *, today: date | None = None
    ) -> str | None:
        today = today or date.today()
        start, end = month_bounds(today)
        if not (start <= spent_on <= end):
            return None
        limit = self._c.get_category_budget_cents(category_id)
        if limit is None:
            return None
        spent = self._e.sum_category_spent(category_id, start, end)
        if spent <= limit:
            return None
        cat = self._c.get_category(category_id)
        name = cat.name if cat else t("budget.fallback_category_name")
        over = Money.from_cents(spent - limit).format_rub()
        lim = Money.from_cents(limit).format_rub()
        fact = Money.from_cents(spent).format_rub()
        return t(
            "budget.warn.over_limit",
            name=name,
            lim=lim,
            month=month_label(today),
            fact=fact,
            over=over,
        )
