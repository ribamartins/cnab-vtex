"""PIX key type detection and CPF/CNPJ document validation.

Exports:
- detect_pix_key_type: classify raw PIX key as SISPAG Nota 37 type code
- validate_cpf: Receita Federal mod-11 check digit validation
- validate_cnpj: Receita Federal mod-11 check digit validation
"""
import re

_CPF_RE = re.compile(r'^\d{11}$')
_CNPJ_RE = re.compile(r'^\d{14}$')
_PHONE_RE = re.compile(r'^\+\d{10,13}$')
_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)


def detect_pix_key_type(raw_key: str) -> str:
    """Return SISPAG Nota 37 code for the PIX key type.

    '01' = phone (E.164 format, e.g. +5511999887766)
    '02' = email
    '03' = CPF (11 digits) or CNPJ (14 digits)
    '04' = random UUID (EVP)

    Detection order: UUID first (avoids false positive), then phone, email,
    CPF/CNPJ last (digits-only pattern is broadest).

    Raises ValueError if the key does not match any known format.
    """
    key = raw_key.strip()
    if not key:
        raise ValueError("Empty PIX key")
    if _UUID_RE.match(key):
        return '04'
    if _PHONE_RE.match(key):
        return '01'
    if _EMAIL_RE.match(key.lower()):
        return '02'
    if _CPF_RE.match(key) or _CNPJ_RE.match(key):
        return '03'
    raise ValueError(f"Cannot detect PIX key type for: {raw_key!r}")


def validate_cpf(cpf: str) -> bool:
    """Validate CPF check digits using Receita Federal mod-11 algorithm.

    Accepts raw digits or formatted string (e.g., '513.009.071-34').
    Strips all non-digit characters before validation.
    Rejects all-same-digit sequences (e.g., '11111111111').
    Returns True if CPF is valid, False otherwise.
    """
    digits = re.sub(r'\D', '', cpf)
    if len(digits) != 11:
        return False
    if len(set(digits)) == 1:
        return False

    # First check digit: weights 10..2 applied to first 9 digits
    weights = range(10, 1, -1)
    s = sum(int(d) * w for d, w in zip(digits[:9], weights))
    r = (s * 10) % 11
    if r == 10:
        r = 0
    if int(digits[9]) != r:
        return False

    # Second check digit: weights 11..2 applied to first 10 digits
    weights = range(11, 1, -1)
    s = sum(int(d) * w for d, w in zip(digits[:10], weights))
    r = (s * 10) % 11
    if r == 10:
        r = 0
    return int(digits[10]) == r


def validate_cnpj(cnpj: str) -> bool:
    """Validate CNPJ check digits using Receita Federal mod-11 algorithm.

    Accepts raw digits or formatted string (e.g., '11.222.333/0001-81').
    Strips all non-digit characters before validation.
    Rejects all-same-digit sequences (e.g., '11111111111111').
    Returns True if CNPJ is valid, False otherwise.
    """
    digits = re.sub(r'\D', '', cnpj)
    if len(digits) != 14:
        return False
    if len(set(digits)) == 1:
        return False

    # First check digit — weights: 5,4,3,2,9,8,7,6,5,4,3,2
    weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    s = sum(int(d) * w for d, w in zip(digits[:12], weights1))
    r = s % 11
    first = 0 if r < 2 else (11 - r)
    if int(digits[12]) != first:
        return False

    # Second check digit — weights: 6,5,4,3,2,9,8,7,6,5,4,3,2
    weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    s = sum(int(d) * w for d, w in zip(digits[:13], weights2))
    r = s % 11
    second = 0 if r < 2 else (11 - r)
    return int(digits[13]) == second
