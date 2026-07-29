from pathlib import Path

from src.infrastructure.db import connect, migrate


def test_migrate_creates_tables(tmp_path: Path):
    conn = connect(tmp_path / "x.db")
    migrate(conn)
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert {"people", "categories", "merchants", "expenses"} <= tables
