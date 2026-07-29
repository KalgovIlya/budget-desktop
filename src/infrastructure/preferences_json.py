from __future__ import annotations

import json
from pathlib import Path

from src.application.dto import UiPreferences

_VALID_LOCALES = frozenset({"ru", "en"})


class JsonPreferencesStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> UiPreferences:
        if not self._path.exists():
            return UiPreferences()
        data = json.loads(self._path.read_text(encoding="utf-8"))
        theme = data.get("theme", "light")
        if theme not in ("light", "dark"):
            theme = "light"
        locale = data.get("locale")
        if locale not in _VALID_LOCALES:
            locale = None
        return UiPreferences(
            last_person_id=data.get("last_person_id"),
            last_category_id=data.get("last_category_id"),
            theme=theme,
            locale=locale,
        )

    def save(self, prefs: UiPreferences) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "last_person_id": prefs.last_person_id,
            "last_category_id": prefs.last_category_id,
            "theme": prefs.theme,
            "locale": prefs.locale,
        }
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
