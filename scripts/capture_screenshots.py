"""Capture README screenshots. Usage:
  python scripts/capture_screenshots.py en
  python scripts/capture_screenshots.py ru
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.i18n import set_locale
from src.main import build_app

LOCALE = (sys.argv[1] if len(sys.argv) > 1 else "en").lower()
if LOCALE not in ("en", "ru"):
    raise SystemExit("usage: capture_screenshots.py [en|ru]")

OUT = ROOT / "assets" / "screenshots" / LOCALE
SHOTS = (
    (0, "expenses.png"),
    (1, "stats.png"),
    (2, "budgets.png"),
)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    set_locale(LOCALE)
    app, window = build_app()
    window.resize(1180, 760)
    window.show()
    window.raise_()
    window.activateWindow()

    state = {"i": 0}

    def grab_next() -> None:
        i = state["i"]
        if i >= len(SHOTS):
            app.quit()
            return
        tab, name = SHOTS[i]
        window._switch(tab)
        app.processEvents()

        def save() -> None:
            pix = window.grab()
            path = OUT / name
            pix.save(str(path), "PNG")
            print("saved", path)
            state["i"] += 1
            QTimer.singleShot(400, grab_next)

        QTimer.singleShot(500, save)

    QTimer.singleShot(700, grab_next)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
