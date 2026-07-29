from src.domain.money import Money


def test_from_rubles_string():
    assert Money.from_rubles_str("2140.50").cents == 214050


def test_from_rubles_comma():
    assert Money.from_rubles_str("1 200,5").cents == 120050


def test_rejects_non_positive():
    import pytest
    from src.domain.errors import ValidationError

    with pytest.raises(ValidationError):
        Money(0)
