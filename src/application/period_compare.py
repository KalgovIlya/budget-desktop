from __future__ import annotations

from datetime import date, timedelta

from src.application.dto import CompareRow, NamedAmount, StatsDto


def previous_period(date_from: date, date_to: date) -> tuple[date, date]:
    if date_from > date_to:
        raise ValueError("date_from > date_to")
    length = (date_to - date_from).days + 1
    prev_to = date_from - timedelta(days=1)
    prev_from = prev_to - timedelta(days=length - 1)
    return prev_from, prev_to


def _index(rows: tuple[NamedAmount, ...]) -> dict[int, NamedAmount]:
    out: dict[int, NamedAmount] = {}
    for row in rows:
        if row.id is not None:
            out[row.id] = row
    return out


def build_compare_rows(
    previous: tuple[NamedAmount, ...],
    current: tuple[NamedAmount, ...],
) -> tuple[CompareRow, ...]:
    prev_map = _index(previous)
    curr_map = _index(current)
    ids = set(prev_map) | set(curr_map)
    rows: list[CompareRow] = []
    for entity_id in ids:
        prev = prev_map.get(entity_id)
        curr = curr_map.get(entity_id)
        name = (curr or prev).name  # type: ignore[union-attr]
        rows.append(
            CompareRow(
                id=entity_id,
                name=name,
                previous_cents=prev.amount_cents if prev else 0,
                current_cents=curr.amount_cents if curr else 0,
            )
        )
    rows.sort(key=lambda r: (-abs(r.delta_cents), r.name.casefold()))
    return tuple(rows)


def format_delta_pct(row: CompareRow) -> str:
    from src.i18n import t

    if row.previous_cents == 0:
        if row.current_cents == 0:
            return t("common.em_dash")
        return t("compare.pct.new")
    pct = row.delta_cents / row.previous_cents * 100
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.0f}%"


def format_total_delta(previous_cents: int, current_cents: int) -> str:
    from src.i18n import t

    delta = current_cents - previous_cents
    money = _fmt(abs(delta))
    sign = "+" if delta > 0 else "−" if delta < 0 else ""
    if previous_cents == 0:
        pct = t("compare.pct.new") if current_cents else t("common.em_dash")
    else:
        ratio = delta / previous_cents * 100
        pct_sign = "+" if ratio > 0 else ""
        pct = f"{pct_sign}{ratio:.0f}%"
    if delta == 0:
        return t("compare.total_delta_zero")
    return t("compare.total_delta", sign=sign, money=money, pct=pct)


def _fmt(cents: int) -> str:
    from decimal import Decimal

    return f"{(Decimal(cents) / Decimal(100)):.2f}"


def compare_stats(previous: StatsDto, current: StatsDto) -> tuple[tuple[CompareRow, ...], tuple[CompareRow, ...]]:
    return (
        build_compare_rows(previous.by_category, current.by_category),
        build_compare_rows(previous.by_person, current.by_person),
    )
