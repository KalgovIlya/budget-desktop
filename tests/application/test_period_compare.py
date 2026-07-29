from datetime import date

from src.application.dto import NamedAmount, StatsDto
from src.application.period_compare import (
    build_compare_rows,
    format_delta_pct,
    format_total_delta,
    previous_period,
)


def test_previous_period_same_length():
    prev_from, prev_to = previous_period(date(2026, 7, 1), date(2026, 7, 30))
    assert prev_from == date(2026, 6, 1)
    assert prev_to == date(2026, 6, 30)
    assert (prev_to - prev_from).days == (date(2026, 7, 30) - date(2026, 7, 1)).days


def test_previous_period_rolling_30():
    prev_from, prev_to = previous_period(date(2026, 7, 1), date(2026, 7, 30))
    # 30 days: Jul 1..30 → Jun 1..30
    assert (date(2026, 7, 30) - date(2026, 7, 1)).days + 1 == 30
    assert (prev_to - prev_from).days + 1 == 30


def test_build_compare_rows_delta():
    prev = (NamedAmount(1, "Еда", 10000),)
    curr = (NamedAmount(1, "Еда", 15000), NamedAmount(2, "Такси", 2000))
    rows = build_compare_rows(prev, curr)
    by_id = {r.id: r for r in rows}
    assert by_id[1].delta_cents == 5000
    assert by_id[2].previous_cents == 0
    assert by_id[2].current_cents == 2000
    assert format_delta_pct(by_id[1]) == "+50%"
    assert format_delta_pct(by_id[2]) == "нов."


def test_format_total_delta():
    assert "Δ" in format_total_delta(10000, 15000)
    assert "+50%" in format_total_delta(10000, 15000)
