from __future__ import annotations

import sqlite3
from datetime import date

from src.application.dto import (
    Category,
    Expense,
    ExpenseFilter,
    Merchant,
    NamedAmount,
    Person,
    StatsDto,
)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _person(row: sqlite3.Row) -> Person:
    return Person(id=row["id"], name=row["name"], is_archived=bool(row["is_archived"]))


def _category(row: sqlite3.Row) -> Category:
    return Category(id=row["id"], name=row["name"], is_archived=bool(row["is_archived"]))


def _merchant(row: sqlite3.Row) -> Merchant:
    keys = row.keys()
    return Merchant(
        id=row["id"],
        canonical_key=row["canonical_key"],
        display_name=row["display_name"],
        category_id=row["category_id"],
        is_archived=bool(row["is_archived"]),
        category_name=row["category_name"] if "category_name" in keys else "",
    )


def _expense(row: sqlite3.Row) -> Expense:
    keys = row.keys()
    return Expense(
        id=row["id"],
        spent_on=_parse_date(row["spent_on"]),
        amount_cents=row["amount_cents"],
        person_id=row["person_id"],
        category_id=row["category_id"],
        merchant_id=row["merchant_id"],
        note=row["note"] or "",
        person_name=row["person_name"] if "person_name" in keys else "",
        category_name=row["category_name"] if "category_name" in keys else "",
        merchant_name=row["merchant_name"] if "merchant_name" in keys else "",
    )


class SqliteCatalogs:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def clear_all_business_data(self) -> None:
        """Wipe expenses and catalogs (FK-safe order). Preferences file untouched."""
        self._conn.execute("DELETE FROM expenses")
        self._conn.execute("DELETE FROM category_budgets")
        self._conn.execute("DELETE FROM merchants")
        self._conn.execute("DELETE FROM categories")
        self._conn.execute("DELETE FROM people")
        self._conn.commit()

    # --- people ---
    def create_person(self, name: str, created_at: str) -> Person:
        cur = self._conn.execute(
            "INSERT INTO people (name, created_at) VALUES (?, ?)",
            (name, created_at),
        )
        self._conn.commit()
        return self.get_person(int(cur.lastrowid))  # type: ignore[arg-type]

    def rename_person(self, person_id: int, name: str) -> Person:
        self._conn.execute("UPDATE people SET name = ? WHERE id = ?", (name, person_id))
        self._conn.commit()
        return self.get_person(person_id)  # type: ignore[return-value]

    def set_person_archived(self, person_id: int, archived: bool) -> Person:
        self._conn.execute(
            "UPDATE people SET is_archived = ? WHERE id = ?",
            (1 if archived else 0, person_id),
        )
        self._conn.commit()
        return self.get_person(person_id)  # type: ignore[return-value]

    def delete_person(self, person_id: int) -> None:
        self._conn.execute("DELETE FROM people WHERE id = ?", (person_id,))
        self._conn.commit()

    def get_person(self, person_id: int) -> Person | None:
        row = self._conn.execute("SELECT * FROM people WHERE id = ?", (person_id,)).fetchone()
        return _person(row) if row else None

    def list_people(self, include_archived: bool = False) -> list[Person]:
        sql = "SELECT * FROM people"
        if not include_archived:
            sql += " WHERE is_archived = 0"
        sql += " ORDER BY name COLLATE NOCASE"
        return [_person(r) for r in self._conn.execute(sql)]

    def find_person_by_name_folded(self, folded: str) -> Person | None:
        for p in self.list_people(include_archived=True):
            if p.name.strip().casefold() == folded:
                return p
        return None

    def person_expense_count(self, person_id: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM expenses WHERE person_id = ?", (person_id,)
        ).fetchone()
        return int(row["c"])

    # --- categories ---
    def create_category(self, name: str, created_at: str) -> Category:
        cur = self._conn.execute(
            "INSERT INTO categories (name, created_at) VALUES (?, ?)",
            (name, created_at),
        )
        self._conn.commit()
        return self.get_category(int(cur.lastrowid))  # type: ignore[arg-type]

    def rename_category(self, category_id: int, name: str) -> Category:
        self._conn.execute("UPDATE categories SET name = ? WHERE id = ?", (name, category_id))
        self._conn.commit()
        return self.get_category(category_id)  # type: ignore[return-value]

    def set_category_archived(self, category_id: int, archived: bool) -> Category:
        self._conn.execute(
            "UPDATE categories SET is_archived = ? WHERE id = ?",
            (1 if archived else 0, category_id),
        )
        self._conn.commit()
        return self.get_category(category_id)  # type: ignore[return-value]

    def delete_category(self, category_id: int) -> None:
        self._conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        self._conn.commit()

    def get_category(self, category_id: int) -> Category | None:
        row = self._conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
        return _category(row) if row else None

    def list_categories(self, include_archived: bool = False) -> list[Category]:
        sql = "SELECT * FROM categories"
        if not include_archived:
            sql += " WHERE is_archived = 0"
        sql += " ORDER BY name COLLATE NOCASE"
        return [_category(r) for r in self._conn.execute(sql)]

    def find_category_by_name_folded(self, folded: str) -> Category | None:
        for c in self.list_categories(include_archived=True):
            if c.name.strip().casefold() == folded:
                return c
        return None

    def category_expense_count(self, category_id: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM expenses WHERE category_id = ?", (category_id,)
        ).fetchone()
        return int(row["c"])

    # --- merchants ---
    def create_merchant(
        self, canonical_key: str, display_name: str, category_id: int, created_at: str
    ) -> Merchant:
        cur = self._conn.execute(
            """
            INSERT INTO merchants (canonical_key, display_name, category_id, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (canonical_key, display_name, category_id, created_at),
        )
        self._conn.commit()
        return self.get_merchant(int(cur.lastrowid))  # type: ignore[arg-type]

    def rename_merchant_display(self, merchant_id: int, display_name: str) -> Merchant:
        self._conn.execute(
            "UPDATE merchants SET display_name = ? WHERE id = ?",
            (display_name, merchant_id),
        )
        self._conn.commit()
        return self.get_merchant(merchant_id)  # type: ignore[return-value]

    def set_merchant_archived(self, merchant_id: int, archived: bool) -> Merchant:
        self._conn.execute(
            "UPDATE merchants SET is_archived = ? WHERE id = ?",
            (1 if archived else 0, merchant_id),
        )
        self._conn.commit()
        return self.get_merchant(merchant_id)  # type: ignore[return-value]

    def delete_merchant(self, merchant_id: int) -> None:
        self._conn.execute("DELETE FROM merchants WHERE id = ?", (merchant_id,))
        self._conn.commit()

    def reassign_expenses_merchant(self, from_id: int, to_id: int) -> None:
        self._conn.execute(
            "UPDATE expenses SET merchant_id = ? WHERE merchant_id = ?",
            (to_id, from_id),
        )
        self._conn.commit()

    def get_merchant(self, merchant_id: int) -> Merchant | None:
        row = self._conn.execute(
            """
            SELECT m.*, c.name AS category_name
            FROM merchants m
            JOIN categories c ON c.id = m.category_id
            WHERE m.id = ?
            """,
            (merchant_id,),
        ).fetchone()
        return _merchant(row) if row else None

    def get_merchant_by_canonical(self, canonical_key: str) -> Merchant | None:
        row = self._conn.execute(
            """
            SELECT m.*, c.name AS category_name
            FROM merchants m
            JOIN categories c ON c.id = m.category_id
            WHERE m.canonical_key = ?
            """,
            (canonical_key,),
        ).fetchone()
        return _merchant(row) if row else None

    def list_merchants(
        self, include_archived: bool = False, category_id: int | None = None
    ) -> list[Merchant]:
        sql = """
            SELECT m.*, c.name AS category_name
            FROM merchants m
            JOIN categories c ON c.id = m.category_id
            WHERE 1=1
        """
        params: list[object] = []
        if not include_archived:
            sql += " AND m.is_archived = 0"
        if category_id is not None:
            sql += " AND m.category_id = ?"
            params.append(category_id)
        sql += " ORDER BY m.display_name COLLATE NOCASE"
        return [_merchant(r) for r in self._conn.execute(sql, params)]

    def merchant_expense_count(self, merchant_id: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM expenses WHERE merchant_id = ?", (merchant_id,)
        ).fetchone()
        return int(row["c"])

    def category_merchant_count(self, category_id: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM merchants WHERE category_id = ?", (category_id,)
        ).fetchone()
        return int(row["c"])

    def get_category_budget_cents(self, category_id: int) -> int | None:
        row = self._conn.execute(
            "SELECT limit_cents FROM category_budgets WHERE category_id = ?",
            (category_id,),
        ).fetchone()
        return int(row["limit_cents"]) if row else None

    def list_category_budget_cents(self) -> dict[int, int]:
        rows = self._conn.execute(
            "SELECT category_id, limit_cents FROM category_budgets"
        ).fetchall()
        return {int(r["category_id"]): int(r["limit_cents"]) for r in rows}

    def upsert_category_budget(self, category_id: int, limit_cents: int) -> None:
        self._conn.execute(
            """
            INSERT INTO category_budgets (category_id, limit_cents) VALUES (?, ?)
            ON CONFLICT(category_id) DO UPDATE SET limit_cents = excluded.limit_cents
            """,
            (category_id, limit_cents),
        )
        self._conn.commit()

    def delete_category_budget(self, category_id: int) -> None:
        self._conn.execute(
            "DELETE FROM category_budgets WHERE category_id = ?", (category_id,)
        )
        self._conn.commit()


class SqliteExpenses:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

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
    ) -> Expense:
        cur = self._conn.execute(
            """
            INSERT INTO expenses (
              spent_on, amount_cents, person_id, category_id, merchant_id, note, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                spent_on.isoformat(),
                amount_cents,
                person_id,
                category_id,
                merchant_id,
                note,
                created_at,
                updated_at,
            ),
        )
        self._conn.commit()
        return self.get(int(cur.lastrowid))  # type: ignore[arg-type]

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
    ) -> Expense:
        self._conn.execute(
            """
            UPDATE expenses SET
              spent_on = ?, amount_cents = ?, person_id = ?, category_id = ?,
              merchant_id = ?, note = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                spent_on.isoformat(),
                amount_cents,
                person_id,
                category_id,
                merchant_id,
                note,
                updated_at,
                expense_id,
            ),
        )
        self._conn.commit()
        return self.get(expense_id)  # type: ignore[return-value]

    def delete(self, expense_id: int) -> None:
        self._conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        self._conn.commit()

    def get(self, expense_id: int) -> Expense | None:
        row = self._conn.execute(
            """
            SELECT e.*, p.name AS person_name, c.name AS category_name, m.display_name AS merchant_name
            FROM expenses e
            JOIN people p ON p.id = e.person_id
            JOIN categories c ON c.id = e.category_id
            JOIN merchants m ON m.id = e.merchant_id
            WHERE e.id = ?
            """,
            (expense_id,),
        ).fetchone()
        return _expense(row) if row else None

    def max_spent_on(self) -> date | None:
        row = self._conn.execute("SELECT MAX(spent_on) AS m FROM expenses").fetchone()
        if not row or row["m"] is None:
            return None
        return _parse_date(row["m"])

    def delete_before(self, cutoff: date) -> int:
        cur = self._conn.execute(
            "DELETE FROM expenses WHERE spent_on < ?",
            (cutoff.isoformat(),),
        )
        self._conn.commit()
        return int(cur.rowcount)

    def _where(self, filt: ExpenseFilter) -> tuple[str, list[object]]:
        clauses = ["e.spent_on >= ?", "e.spent_on <= ?"]
        params: list[object] = [filt.date_from.isoformat(), filt.date_to.isoformat()]
        include_archived = filt.include_archived

        if filt.person_ids:
            placeholders = ",".join("?" * len(filt.person_ids))
            clauses.append(f"e.person_id IN ({placeholders})")
            params.extend(filt.person_ids)
        elif not include_archived:
            clauses.append("p.is_archived = 0")

        if filt.category_ids:
            placeholders = ",".join("?" * len(filt.category_ids))
            clauses.append(f"e.category_id IN ({placeholders})")
            params.extend(filt.category_ids)
        elif not include_archived:
            clauses.append("c.is_archived = 0")

        if filt.merchant_query:
            clauses.append("m.display_name LIKE ? COLLATE NOCASE")
            params.append(f"%{filt.merchant_query.strip()}%")
            if not include_archived:
                clauses.append("m.is_archived = 0")
        elif filt.merchant_ids:
            placeholders = ",".join("?" * len(filt.merchant_ids))
            clauses.append(f"e.merchant_id IN ({placeholders})")
            params.extend(filt.merchant_ids)
        elif not include_archived:
            clauses.append("m.is_archived = 0")

        return " AND ".join(clauses), params

    def list_filtered(self, filt: ExpenseFilter) -> list[Expense]:
        where, params = self._where(filt)
        rows = self._conn.execute(
            f"""
            SELECT e.*, p.name AS person_name, c.name AS category_name, m.display_name AS merchant_name
            FROM expenses e
            JOIN people p ON p.id = e.person_id
            JOIN categories c ON c.id = e.category_id
            JOIN merchants m ON m.id = e.merchant_id
            WHERE {where}
            ORDER BY e.spent_on DESC, e.id DESC
            """,
            params,
        ).fetchall()
        return [_expense(r) for r in rows]

    def stats(self, filt: ExpenseFilter) -> StatsDto:
        items = self.list_filtered(filt)
        total = sum(i.amount_cents for i in items)

        def group(attr_id: str, attr_name: str) -> tuple[NamedAmount, ...]:
            buckets: dict[int, list] = {}
            for item in items:
                key = getattr(item, attr_id)
                buckets.setdefault(key, []).append(item)
            out: list[NamedAmount] = []
            for key, group_items in buckets.items():
                name = getattr(group_items[0], attr_name)
                out.append(
                    NamedAmount(
                        id=key,
                        name=name,
                        amount_cents=sum(g.amount_cents for g in group_items),
                    )
                )
            out.sort(key=lambda x: (-x.amount_cents, x.name.casefold()))
            return tuple(out)

        return StatsDto(
            total_cents=total,
            by_person=group("person_id", "person_name"),
            by_category=group("category_id", "category_name"),
            by_merchant=group("merchant_id", "merchant_name"),
            items=tuple(items),
        )

    def sum_category_spent(
        self, category_id: int, date_from: date, date_to: date
    ) -> int:
        row = self._conn.execute(
            """
            SELECT COALESCE(SUM(amount_cents), 0) AS total
            FROM expenses
            WHERE category_id = ? AND spent_on >= ? AND spent_on <= ?
            """,
            (category_id, date_from.isoformat(), date_to.isoformat()),
        ).fetchone()
        return int(row["total"])
