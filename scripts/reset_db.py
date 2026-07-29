from datetime import datetime, timezone
from pathlib import Path
import shutil

from src.infrastructure.db import connect, migrate, reset_database, _columns
from src.infrastructure.paths import backups_dir, db_path
from src.main import build_app

db = db_path()
print("resetting", db)
if db.exists():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    bak = backups_dir() / f"pre-reset-{stamp}.db"
    shutil.copy2(db, bak)
    print("backed up to", bak)

reset_database(db)
conn = connect(db)
print("tables", [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")])
print("merchants cols", sorted(_columns(conn, "merchants")))
conn.close()

app, window = build_app()
print("boot ok")
