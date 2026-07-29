import pytest

from src.domain.errors import ValidationError
from src.domain.merchant import canonical_key, levenshtein, suggest_keys


def test_canonical_strips_spaces_and_case():
    assert canonical_key(" Пятерочка ") == "пятерочка"
    assert canonical_key("Пере кресток") == "перекресток"
    assert canonical_key("Пятёрочка") == "пятерочка"


def test_empty_canonical_raises():
    with pytest.raises(ValidationError):
        canonical_key("???")


def test_levenshtein_basic():
    assert levenshtein("пятерочка", "пятирочка") == 1


def test_suggest_includes_fuzzy():
    cands = [("пятерочка", "Пятёрочка"), ("лента", "Лента")]
    # query key without ё
    out = suggest_keys("пятерочка", cands)
    assert any(k == "пятерочка" for k, _ in out)
