from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from src.domain.errors import ValidationError
from src.i18n import t


@dataclass(frozen=True, slots=True)
class Money:
    cents: int

    def __post_init__(self) -> None:
        if self.cents <= 0:
            raise ValidationError(t("money.err.positive"))

    @classmethod
    def from_rubles_str(cls, value: str) -> Money:
        text = value.strip().replace(" ", "").replace(",", ".")
        if not text:
            raise ValidationError(t("money.err.empty"))
        try:
            amount = Decimal(text)
        except InvalidOperation as exc:
            raise ValidationError(t("money.err.invalid")) from exc
        if amount <= 0:
            raise ValidationError(t("money.err.positive"))
        cents = int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        return cls(cents)

    @classmethod
    def from_cents(cls, cents: int) -> Money:
        return cls(cents)

    def format_rub(self) -> str:
        rubles = Decimal(self.cents) / Decimal(100)
        return f"{rubles:.2f}"
