from __future__ import annotations

from src.application.dto import UiPreferences
from src.i18n import detect_system_locale, get_locale, set_locale, t
from src.infrastructure.preferences_json import JsonPreferencesStore


def test_t_switches_with_locale():
    set_locale("en")
    assert t("main.tab.expenses") == "Expenses"
    set_locale("ru")
    assert t("main.tab.expenses") == "Траты"


def test_t_fallback_to_english_key():
    set_locale("ru")
    # Unknown key falls back to key itself if missing in both
    assert t("no.such.key") == "no.such.key"


def test_t_format_kwargs():
    set_locale("en")
    assert t("stats.meta.records", count=3) == "Records: 3"


def test_detect_system_locale_russian(monkeypatch):
    monkeypatch.setattr(
        "src.i18n.py_locale.getlocale", lambda: ("ru_RU", "UTF-8")
    )
    monkeypatch.setattr(
        "src.i18n.py_locale.getdefaultlocale", lambda: ("ru_RU", "UTF-8")
    )
    assert detect_system_locale() == "ru"


def test_detect_system_locale_english(monkeypatch):
    monkeypatch.setattr(
        "src.i18n.py_locale.getlocale", lambda: ("en_US", "UTF-8")
    )
    monkeypatch.setattr(
        "src.i18n.py_locale.getdefaultlocale", lambda: ("en_US", "UTF-8")
    )
    assert detect_system_locale() == "en"


def test_preferences_locale_roundtrip(tmp_path):
    store = JsonPreferencesStore(tmp_path / "preferences.json")
    store.save(
        UiPreferences(
            last_person_id=None,
            last_category_id=None,
            theme="dark",
            locale="en",
        )
    )
    loaded = store.load()
    assert loaded.locale == "en"
    assert loaded.theme == "dark"


def test_resolve_locale_persists_on_first_run(world, monkeypatch):
    catalog_svc, expense_svc, prefs, export, tmp_path = world
    monkeypatch.setattr(
        "src.i18n.detect_system_locale", lambda: "en"
    )
    # Empty prefs file → locale None
    resolved = prefs.resolve_locale()
    assert resolved.locale == "en"
    assert get_locale() == "en"
    assert prefs.get().locale == "en"
