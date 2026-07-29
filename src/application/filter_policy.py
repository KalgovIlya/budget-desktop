from __future__ import annotations

from src.application.dto import ExpenseFilter
from src.domain.errors import ValidationError
from src.i18n import t


def normalize_filter(
    filt: ExpenseFilter,
    *,
    scope_person_ids: list[int],
    scope_category_ids: list[int],
    scope_merchant_ids: list[int],
) -> ExpenseFilter:
    if filt.date_from > filt.date_to:
        raise ValidationError(t("filter.err.date_range"))

    mq = (filt.merchant_query or "").strip() or None
    mids = tuple(filt.merchant_ids)
    if mq and mids:
        raise ValidationError(t("filter.err.merchant_xor"))

    person_ids = tuple(filt.person_ids) if filt.person_ids else tuple(scope_person_ids)
    category_ids = tuple(filt.category_ids) if filt.category_ids else tuple(scope_category_ids)

    if mq:
        merchant_ids: tuple[int, ...] = ()
    elif mids:
        merchant_ids = mids
    else:
        merchant_ids = tuple(scope_merchant_ids)

    return ExpenseFilter(
        date_from=filt.date_from,
        date_to=filt.date_to,
        person_ids=person_ids,
        category_ids=category_ids,
        merchant_ids=merchant_ids,
        merchant_query=mq,
        include_archived=filt.include_archived,
    )
