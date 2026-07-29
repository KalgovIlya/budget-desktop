from datetime import date

import pytest

from src.application.filter_policy import normalize_filter
from src.application.dto import ExpenseFilter
from src.domain.errors import ValidationError


def test_xor_merchants():
    filt = ExpenseFilter(
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
        merchant_ids=(1,),
        merchant_query="ozon",
    )
    with pytest.raises(ValidationError):
        normalize_filter(
            filt,
            scope_person_ids=[1],
            scope_category_ids=[1],
            scope_merchant_ids=[1, 2],
        )


def test_empty_expands_to_scope():
    filt = ExpenseFilter(date_from=date(2026, 1, 1), date_to=date(2026, 1, 31))
    out = normalize_filter(
        filt,
        scope_person_ids=[10, 11],
        scope_category_ids=[20],
        scope_merchant_ids=[30, 31],
    )
    assert out.person_ids == (10, 11)
    assert out.category_ids == (20,)
    assert out.merchant_ids == (30, 31)
    assert out.include_archived is False


def test_preserves_include_archived():
    filt = ExpenseFilter(
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
        include_archived=True,
    )
    out = normalize_filter(
        filt,
        scope_person_ids=[1, 2],
        scope_category_ids=[3],
        scope_merchant_ids=[4],
    )
    assert out.include_archived is True
    assert out.person_ids == (1, 2)
