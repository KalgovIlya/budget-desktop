from datetime import date

from src.domain.retention import cutoff_date


def test_cutoff_two_years_before_anchor():
    assert cutoff_date(date(2026, 7, 28)) == date(2024, 7, 28)


def test_cutoff_leap_day():
    assert cutoff_date(date(2024, 2, 29)) == date(2022, 2, 28)
