from __future__ import annotations

from datetime import date, timedelta

from src.application.dto import Expense, PeriodSeries, SeriesPoint

WEEK_THRESHOLD_DAYS = 45


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def build_period_series(
    items: list[Expense],
    date_from: date,
    date_to: date,
    *,
    week_threshold: int = WEEK_THRESHOLD_DAYS,
) -> PeriodSeries:
    """Aggregate amounts by day/week.

    X-axis starts at the first expense in range (not empty leading days from
    period start like 01.07), and runs through date_to so trailing days stay.
    """
    if date_from > date_to:
        return PeriodSeries(grain="day", points=())

    in_range = [i for i in items if date_from <= i.spent_on <= date_to]
    span = (date_to - date_from).days + 1
    use_weeks = span > week_threshold
    grain = "week" if use_weeks else "day"

    if not in_range:
        return PeriodSeries(grain=grain, points=())

    first_spent = min(i.spent_on for i in in_range)
    buckets: dict[date, int] = {}

    if use_weeks:
        cursor = _week_start(first_spent)
        last = _week_start(date_to)
        while cursor <= last:
            buckets[cursor] = 0
            cursor += timedelta(days=7)
        for item in in_range:
            key = _week_start(item.spent_on)
            buckets[key] = buckets.get(key, 0) + item.amount_cents
    else:
        cursor = first_spent
        while cursor <= date_to:
            buckets[cursor] = 0
            cursor += timedelta(days=1)
        for item in in_range:
            buckets[item.spent_on] = buckets.get(item.spent_on, 0) + item.amount_cents

    points = tuple(
        SeriesPoint(
            label=start.strftime("%d.%m"),
            bucket_start=start,
            amount_cents=amount,
        )
        for start, amount in sorted(buckets.items())
    )
    return PeriodSeries(grain=grain, points=points)
