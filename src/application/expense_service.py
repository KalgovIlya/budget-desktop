from __future__ import annotations

from datetime import date

from src.application.catalog_service import CatalogService
from src.application.dto import Expense, ExpenseFilter, PeriodSeries, StatsDto, UiPreferences
from src.application.filter_policy import normalize_filter
from src.application.period_series import build_period_series
from src.domain.clock import Clock
from src.domain.errors import ArchivedEntity, NotFound, ValidationError
from src.domain.money import Money
from src.domain.retention import cutoff_date
from src.i18n import t
from src.infrastructure.sqlite_repos import SqliteCatalogs, SqliteExpenses


class ExpenseService:
    def __init__(
        self,
        expenses: SqliteExpenses,
        catalogs: SqliteCatalogs,
        catalog_service: CatalogService,
        clock: Clock,
    ) -> None:
        self._e = expenses
        self._c = catalogs
        self._catalogs = catalog_service
        self._clock = clock

    def list_expenses(self, filt: ExpenseFilter) -> list[Expense]:
        return self._e.list_filtered(self._normalized(filt))

    def list_recent_templates(self, *, limit: int = 5) -> list[Expense]:
        """Latest unique active drafts: person+category+merchant+amount (note from newest)."""
        if limit <= 0:
            return []
        today = date.today()
        items = self.list_expenses(
            ExpenseFilter(date_from=date(today.year - 2, 1, 1), date_to=today)
        )
        active_people = {p.id for p in self._c.list_people(False)}
        active_cats = {c.id for c in self._c.list_categories(False)}
        active_merchants = {m.id for m in self._c.list_merchants(False)}
        seen: set[tuple[int, int, int, int]] = set()
        out: list[Expense] = []
        for item in items:
            if item.person_id not in active_people:
                continue
            if item.category_id not in active_cats:
                continue
            if item.merchant_id not in active_merchants:
                continue
            key = (item.person_id, item.category_id, item.merchant_id, item.amount_cents)
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
            if len(out) >= limit:
                break
        return out

    def get_stats(self, filt: ExpenseFilter) -> StatsDto:
        return self._e.stats(self._normalized(filt))

    def get_period_series(self, filt: ExpenseFilter) -> PeriodSeries:
        normalized = self._normalized(filt)
        items = self._e.list_filtered(normalized)
        return build_period_series(items, normalized.date_from, normalized.date_to)

    def add_expense(
        self,
        *,
        amount: Money,
        spent_on: date,
        person_id: int,
        category_id: int,
        merchant_input: str,
        note: str = "",
    ) -> Expense:
        person, category = self._require_active_person_category(person_id, category_id)
        merchant = self._catalogs.resolve_merchant_for_expense(merchant_input, category.id)
        now = self._clock.now_iso()
        expense = self._e.add(
            spent_on=spent_on,
            amount_cents=amount.cents,
            person_id=person.id,
            category_id=category.id,
            merchant_id=merchant.id,
            note=note.strip(),
            created_at=now,
            updated_at=now,
        )
        self.purge_old_expenses()
        return expense

    def update_expense(
        self,
        expense_id: int,
        *,
        amount: Money,
        spent_on: date,
        person_id: int,
        category_id: int,
        merchant_input: str,
        note: str = "",
    ) -> Expense:
        if not self._e.get(expense_id):
            raise NotFound(t("err.expense_not_found"))
        person, category = self._require_active_person_category(person_id, category_id)
        merchant = self._catalogs.resolve_merchant_for_expense(merchant_input, category.id)
        expense = self._e.update(
            expense_id,
            spent_on=spent_on,
            amount_cents=amount.cents,
            person_id=person.id,
            category_id=category.id,
            merchant_id=merchant.id,
            note=note.strip(),
            updated_at=self._clock.now_iso(),
        )
        self.purge_old_expenses()
        return expense

    def delete_expense(self, expense_id: int) -> None:
        if not self._e.get(expense_id):
            raise NotFound(t("err.expense_not_found"))
        self._e.delete(expense_id)

    def purge_old_expenses(self) -> int:
        anchor = self._e.max_spent_on()
        if anchor is None:
            return 0
        return self._e.delete_before(cutoff_date(anchor))

    def _normalized(self, filt: ExpenseFilter) -> ExpenseFilter:
        include = filt.include_archived
        return normalize_filter(
            filt,
            scope_person_ids=[p.id for p in self._c.list_people(include)],
            scope_category_ids=[c.id for c in self._c.list_categories(include)],
            scope_merchant_ids=[m.id for m in self._c.list_merchants(include)],
        )

    def _require_active_person_category(self, person_id: int, category_id: int):
        person = self._c.get_person(person_id)
        if not person:
            raise NotFound(t("err.person_not_found"))
        if person.is_archived:
            raise ArchivedEntity(t("err.person_archived"))
        category = self._c.get_category(category_id)
        if not category:
            raise NotFound(t("err.category_not_found"))
        if category.is_archived:
            raise ArchivedEntity(t("err.category_archived"))
        return person, category


class PreferencesService:
    def __init__(self, store, catalogs: SqliteCatalogs) -> None:
        self._store = store
        self._c = catalogs

    def get(self) -> UiPreferences:
        prefs = self._store.load()
        return self._sanitize(prefs)

    def resolve_locale(self) -> UiPreferences:
        """Ensure locale is set (detect on first run) and apply it globally."""
        from src.i18n import detect_system_locale, set_locale

        prefs = self.get()
        if prefs.locale not in ("ru", "en"):
            prefs = self.save(
                UiPreferences(
                    last_person_id=prefs.last_person_id,
                    last_category_id=prefs.last_category_id,
                    theme=prefs.theme,
                    locale=detect_system_locale(),
                )
            )
        set_locale(prefs.locale or "en")
        return prefs

    def save(self, prefs: UiPreferences) -> UiPreferences:
        cleaned = self._sanitize(prefs)
        self._store.save(cleaned)
        return cleaned

    def _sanitize(self, prefs: UiPreferences) -> UiPreferences:
        person_id = prefs.last_person_id
        category_id = prefs.last_category_id
        if person_id is not None:
            person = self._c.get_person(person_id)
            if person is None or person.is_archived:
                person_id = None
        if category_id is not None:
            cat = self._c.get_category(category_id)
            if cat is None or cat.is_archived:
                category_id = None
        if person_id is None:
            people = self._c.list_people(False)
            person_id = people[0].id if people else None
        if category_id is None:
            cats = self._c.list_categories(False)
            category_id = cats[0].id if cats else None
        locale = prefs.locale if prefs.locale in ("ru", "en") else None
        return UiPreferences(
            last_person_id=person_id,
            last_category_id=category_id,
            theme=prefs.theme if prefs.theme in ("light", "dark") else "light",
            locale=locale,
        )
