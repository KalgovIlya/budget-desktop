from datetime import date, timedelta

from src.application.dto import Expense
from src.application.period_series import build_period_series


def _exp(day: date, cents: int) -> Expense:
    return Expense(
        id=1,
        spent_on=day,
        amount_cents=cents,
        person_id=1,
        category_id=1,
        merchant_id=1,
        note="",
    )


def test_daily_series_starts_at_first_expense():
    start = date(2026, 7, 1)
    end = date(2026, 7, 10)
    items = [_exp(date(2026, 7, 8), 1000), _exp(date(2026, 7, 10), 2500)]
    series = build_period_series(items, start, end)
    assert series.grain == "day"
    assert series.points[0].bucket_start == date(2026, 7, 8)
    assert series.points[0].label == "08.07"
    assert len(series.points) == 3
    assert series.points[1].amount_cents == 0
    assert series.points[2].amount_cents == 2500


def test_daily_series_fills_gaps():
    start = date(2026, 7, 1)
    end = date(2026, 7, 3)
    items = [_exp(date(2026, 7, 1), 1000), _exp(date(2026, 7, 3), 2500)]
    series = build_period_series(items, start, end)
    assert series.grain == "day"
    assert len(series.points) == 3
    assert series.points[0].amount_cents == 1000
    assert series.points[1].amount_cents == 0
    assert series.points[2].amount_cents == 2500


def test_week_grain_for_long_span():
    start = date(2026, 1, 1)
    end = start + timedelta(days=60)
    items = [_exp(date(2026, 1, 5), 5000), _exp(date(2026, 1, 6), 1000)]
    series = build_period_series(items, start, end)
    assert series.grain == "week"
    assert len(series.points) >= 8
    assert sum(p.amount_cents for p in series.points) == 6000


def test_thin_axis_labels_keeps_slots():
    from src.ui.chart_theme import thin_axis_labels

    labs = [f"{i:02d}.07" for i in range(1, 32)]
    thinned = thin_axis_labels(labs, max_visible=7)
    assert len(thinned) == 31
    assert thinned[0] == "01.07"
    assert thinned[-1] == "31.07"
    assert " " in thinned
    assert "" not in thinned
