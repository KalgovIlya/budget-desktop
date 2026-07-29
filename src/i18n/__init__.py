from __future__ import annotations

import locale as py_locale
from typing import Any

from src.i18n.catalog import EN, RU

_LOCALES = {"en": EN, "ru": RU}
_current: str = "en"


def detect_system_locale() -> str:
    """Return 'ru' if the OS language is Russian, otherwise 'en'."""
    candidates: list[str] = []
    try:
        lang, _ = py_locale.getlocale()
        if lang:
            candidates.append(lang)
    except Exception:
        pass
    try:
        lang, _ = py_locale.getdefaultlocale()  # type: ignore[deprecated]
        if lang:
            candidates.append(lang)
    except Exception:
        pass
    for raw in candidates:
        code = raw.replace("-", "_").split("_", 1)[0].lower()
        if code == "ru":
            return "ru"
    return "en"


def get_locale() -> str:
    return _current


def set_locale(code: str) -> str:
    global _current
    _current = code if code in _LOCALES else "en"
    return _current


def t(key: str, **kwargs: Any) -> str:
    catalog = _LOCALES.get(_current, EN)
    text = catalog.get(key) or EN.get(key) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text


def locale_display_name(code: str | None = None) -> str:
    code = code or _current
    if code == "ru":
        return "Русский"
    return "English"


def money_label(amount: str) -> str:
    """Return amount as-is (no currency symbol — language ≠ currency)."""
    return amount
