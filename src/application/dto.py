from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol, Sequence


@dataclass(frozen=True, slots=True)
class Person:
    id: int
    name: str
    is_archived: bool


@dataclass(frozen=True, slots=True)
class Category:
    id: int
    name: str
    is_archived: bool


@dataclass(frozen=True, slots=True)
class Merchant:
    id: int
    canonical_key: str
    display_name: str
    category_id: int
    is_archived: bool
    category_name: str = ""


@dataclass(frozen=True, slots=True)
class Expense:
    id: int
    spent_on: date
    amount_cents: int
    person_id: int
    category_id: int
    merchant_id: int
    note: str
    person_name: str = ""
    category_name: str = ""
    merchant_name: str = ""


@dataclass(frozen=True, slots=True)
class ExpenseFilter:
    date_from: date
    date_to: date
    person_ids: tuple[int, ...] = ()
    category_ids: tuple[int, ...] = ()
    merchant_ids: tuple[int, ...] = ()
    merchant_query: str | None = None
    include_archived: bool = False


@dataclass(frozen=True, slots=True)
class NamedAmount:
    id: int | None
    name: str
    amount_cents: int


@dataclass(frozen=True, slots=True)
class CompareRow:
    id: int
    name: str
    previous_cents: int
    current_cents: int

    @property
    def delta_cents(self) -> int:
        return self.current_cents - self.previous_cents


@dataclass(frozen=True, slots=True)
class StatsDto:
    total_cents: int
    by_person: tuple[NamedAmount, ...]
    by_category: tuple[NamedAmount, ...]
    by_merchant: tuple[NamedAmount, ...]
    items: tuple[Expense, ...]


@dataclass(frozen=True, slots=True)
class UiPreferences:
    last_person_id: int | None = None
    last_category_id: int | None = None
    theme: str = "light"
    locale: str | None = None


@dataclass(frozen=True, slots=True)
class CsvImportResult:
    imported: int
    errors: tuple[tuple[int, str], ...]


@dataclass(frozen=True, slots=True)
class CategoryBudgetStatus:
    category_id: int
    name: str
    limit_cents: int | None
    spent_cents: int

    @property
    def remaining_cents(self) -> int | None:
        if self.limit_cents is None:
            return None
        return self.limit_cents - self.spent_cents

    @property
    def ratio(self) -> float | None:
        if self.limit_cents is None or self.limit_cents <= 0:
            return None
        return self.spent_cents / self.limit_cents


@dataclass(frozen=True, slots=True)
class SeriesPoint:
    label: str
    bucket_start: date
    amount_cents: int


@dataclass(frozen=True, slots=True)
class PeriodSeries:
    grain: str
    points: tuple[SeriesPoint, ...]


class PersonWriter(Protocol):
    def create(self, name: str, created_at: str) -> Person: ...
    def rename(self, person_id: int, name: str) -> Person: ...
    def set_archived(self, person_id: int, archived: bool) -> Person: ...
    def delete(self, person_id: int) -> None: ...
    def get(self, person_id: int) -> Person | None: ...
    def list_all(self, include_archived: bool = False) -> list[Person]: ...
    def find_by_name_folded(self, folded: str) -> Person | None: ...
    def expense_count(self, person_id: int) -> int: ...


class CategoryWriter(Protocol):
    def create(self, name: str, created_at: str) -> Category: ...
    def rename(self, category_id: int, name: str) -> Category: ...
    def set_archived(self, category_id: int, archived: bool) -> Category: ...
    def delete(self, category_id: int) -> None: ...
    def get(self, category_id: int) -> Category | None: ...
    def list_all(self, include_archived: bool = False) -> list[Category]: ...
    def find_by_name_folded(self, folded: str) -> Category | None: ...
    def expense_count(self, category_id: int) -> int: ...


class MerchantWriter(Protocol):
    def create(self, canonical_key: str, display_name: str, created_at: str) -> Merchant: ...
    def rename_display(self, merchant_id: int, display_name: str) -> Merchant: ...
    def set_archived(self, merchant_id: int, archived: bool) -> Merchant: ...
    def delete(self, merchant_id: int) -> None: ...
    def get(self, merchant_id: int) -> Merchant | None: ...
    def get_by_canonical(self, canonical_key: str) -> Merchant | None: ...
    def list_all(self, include_archived: bool = False) -> list[Merchant]: ...
    def expense_count(self, merchant_id: int) -> int: ...


class ExpenseWriter(Protocol):
    def add(
        self,
        *,
        spent_on: date,
        amount_cents: int,
        person_id: int,
        category_id: int,
        merchant_id: int,
        note: str,
        created_at: str,
        updated_at: str,
    ) -> Expense: ...

    def update(
        self,
        expense_id: int,
        *,
        spent_on: date,
        amount_cents: int,
        person_id: int,
        category_id: int,
        merchant_id: int,
        note: str,
        updated_at: str,
    ) -> Expense: ...

    def delete(self, expense_id: int) -> None: ...
    def get(self, expense_id: int) -> Expense | None: ...
    def max_spent_on(self) -> date | None: ...
    def delete_before(self, cutoff: date) -> int: ...


class ExpenseQuery(Protocol):
    def list_filtered(self, filt: ExpenseFilter) -> list[Expense]: ...
    def stats(self, filt: ExpenseFilter) -> StatsDto: ...
