from __future__ import annotations

import os
import sys
from pathlib import Path


def app_data_dir(override: Path | None = None) -> Path:
    if override is not None:
        override.mkdir(parents=True, exist_ok=True)
        return override
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    root = base / "Budget"
    root.mkdir(parents=True, exist_ok=True)
    (root / "backups").mkdir(parents=True, exist_ok=True)
    return root


def db_path(override_dir: Path | None = None) -> Path:
    return app_data_dir(override_dir) / "budget.db"


def preferences_path(override_dir: Path | None = None) -> Path:
    return app_data_dir(override_dir) / "preferences.json"


def backups_dir(override_dir: Path | None = None) -> Path:
    path = app_data_dir(override_dir) / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path
