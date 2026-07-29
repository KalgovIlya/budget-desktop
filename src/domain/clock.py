from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Protocol


class Clock(Protocol):
    def today(self) -> date: ...

    def now_iso(self) -> str: ...


class SystemClock:
    def today(self) -> date:
        return date.today()

    def now_iso(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
