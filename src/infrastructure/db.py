from __future__ import annotations

import sqlite3
from pathlib import Path

CORE_SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  is_archived INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  is_archived INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
"""

MERCHANTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS merchants (
  id INTEGER PRIMARY KEY,
  canonical_key TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
  is_archived INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
"""

EXPENSES_SCHEMA = """
CREATE TABLE IF NOT EXISTS expenses (
  id INTEGER PRIMARY KEY,
  spent_on TEXT NOT NULL,
  amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
  person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE RESTRICT,
  category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
  merchant_id INTEGER NOT NULL REFERENCES merchants(id) ON DELETE RESTRICT,
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
"""

INDEXES = """
CREATE INDEX IF NOT EXISTS idx_expenses_spent_on ON expenses(spent_on);
CREATE INDEX IF NOT EXISTS idx_expenses_person ON expenses(person_id);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category_id);
CREATE INDEX IF NOT EXISTS idx_expenses_merchant ON expenses(merchant_id);
CREATE INDEX IF NOT EXISTS idx_merchants_category ON merchants(category_id);
"""

CATEGORY_BUDGETS_SCHEMA = """
CREATE TABLE IF NOT EXISTS category_budgets (
  category_id INTEGER PRIMARY KEY REFERENCES categories(id) ON DELETE CASCADE,
  limit_cents INTEGER NOT NULL CHECK (limit_cents > 0)
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def migrate(conn: sqlite3.Connection) -> None:
    conn.executescript(CORE_SCHEMA)

    needs_merchants_rebuild = False
    if _table_exists(conn, "merchants"):
        cols = _columns(conn, "merchants")
        if "category_id" not in cols:
            needs_merchants_rebuild = True
    else:
        conn.executescript(MERCHANTS_SCHEMA)

    if needs_merchants_rebuild:
        # Old schema without category link — wipe dependent data and recreate.
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DROP TABLE IF EXISTS expenses")
        conn.execute("DROP TABLE IF EXISTS merchants")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(MERCHANTS_SCHEMA)

    if not _table_exists(conn, "expenses"):
        conn.executescript(EXPENSES_SCHEMA)
    else:
        # Ensure expenses still exists after rebuild.
        conn.executescript(EXPENSES_SCHEMA)

    conn.executescript(INDEXES)
    conn.executescript(CATEGORY_BUDGETS_SCHEMA)
    conn.commit()


def reset_database(path: Path) -> None:
    """Delete DB file and recreate empty schema."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = connect(path)
    migrate(conn)
    conn.close()
