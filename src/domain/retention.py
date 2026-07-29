from __future__ import annotations

from datetime import date


def cutoff_date(anchor: date) -> date:
    """Two calendar years before anchor (spent_on retention window start)."""
    try:
        return date(anchor.year - 2, anchor.month, anchor.day)
    except ValueError:
        # Feb 29 → Feb 28
        return date(anchor.year - 2, anchor.month, 28)
