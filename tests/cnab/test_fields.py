"""Unit tests for CNAB field helpers — cnab_alpha, cnab_numeric, cnab_value.

Each test function corresponds to exactly one behavior bullet from the plan spec.
Run with: PYTHONPATH=src python -m pytest tests/cnab/test_fields.py -v
"""
from decimal import Decimal

from cnab.fields import cnab_alpha, cnab_numeric, cnab_value


# ---------------------------------------------------------------------------
# cnab_alpha tests
# ---------------------------------------------------------------------------

def test_cnab_alpha_left_aligned_space_padded():
    assert cnab_alpha('JOAO', 10) == 'JOAO      '


def test_cnab_alpha_truncated_to_length():
    assert cnab_alpha('ABCDEFGHIJK', 10) == 'ABCDEFGHIJ'


def test_cnab_alpha_empty_becomes_spaces():
    assert cnab_alpha('', 5) == '     '


def test_cnab_alpha_uppercased():
    assert cnab_alpha('joao', 10) == 'JOAO      '


def test_cnab_alpha_none_becomes_spaces():
    assert cnab_alpha(None, 5) == '     '


# ---------------------------------------------------------------------------
# cnab_numeric tests
# ---------------------------------------------------------------------------

def test_cnab_numeric_exact_fit():
    assert cnab_numeric(341, 3) == '341'


def test_cnab_numeric_zero_padded_left():
    assert cnab_numeric(0, 4) == '0000'


def test_cnab_numeric_left_padded_single():
    assert cnab_numeric(1, 7) == '0000001'


def test_cnab_numeric_truncated_from_right():
    assert cnab_numeric(99999999999, 5) == '99999'


def test_cnab_numeric_empty_becomes_zeros():
    assert cnab_numeric('', 3) == '000'


def test_cnab_numeric_none_becomes_zeros():
    assert cnab_numeric(None, 3) == '000'


# ---------------------------------------------------------------------------
# cnab_value tests
# ---------------------------------------------------------------------------

def test_cnab_value_150_brl():
    assert cnab_value(Decimal('150.00'), 13, 2) == '000000000015000'


def test_cnab_value_1_cent():
    assert cnab_value(Decimal('0.01'), 13, 2) == '000000000000001'


def test_cnab_value_max_15chars():
    assert cnab_value(Decimal('9999999999999.99'), 13, 2) == '999999999999999'


def test_cnab_value_trailer_18chars():
    assert cnab_value(Decimal('1234.56'), 16, 2) == '000000000000123456'
