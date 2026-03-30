"""CNAB field formatting helpers.

Provides three pure functions for formatting values into fixed-width CNAB fields:
- cnab_alpha: alfanumerico (left-aligned, space-padded right, uppercase)
- cnab_numeric: numerico (right-aligned, zero-padded left)
- cnab_value: picture 9(n)V9(d) — Decimal amount as fixed-width integer string

Source: SISPAG v085 spec section 2.2 field format rules.
"""
from decimal import Decimal


def cnab_alpha(value: str | None, length: int) -> str:
    """Alfanumerico: uppercase, left-aligned, space-padded right, truncated to length."""
    return str(value or '').upper().ljust(length)[:length]


def cnab_numeric(value: int | str | None, length: int) -> str:
    """Numerico: right-aligned, zero-padded left, truncated to length from right."""
    return str(int(value or 0)).zfill(length)[-length:]


def cnab_value(amount: Decimal, integer_digits: int, decimal_digits: int) -> str:
    """Picture 9(n)V9(d): Decimal amount as fixed-width integer string.

    R$ 150,00 with picture 9(13)V9(02) -> '000000000015000' (15 chars total)
    Trailer Lote with picture 9(16)V9(02) -> 18 chars total

    Uses Decimal arithmetic exclusively — never float.
    """
    total_width = integer_digits + decimal_digits
    factor = Decimal(10) ** decimal_digits
    cents = int(amount * factor)
    return str(cents).zfill(total_width)[-total_width:]
