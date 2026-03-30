"""End-to-end integration tests for build_cnab orchestrator.

Tests verify:
- Output type (bytes)
- LATIN-1 encoding
- Every line is exactly 240 bytes
- LF separators, no CRLF
- Correct line count for N payments
- Correct value encoding in output

Run with: PYTHONPATH=src python -m pytest tests/cnab/test_builder.py -v
"""
from decimal import Decimal
from datetime import date

import pytest

from cnab.builder import build_cnab, CompanyConfig, PaymentInput


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def company_config() -> CompanyConfig:
    return CompanyConfig(
        cnpj='12345678000195',
        agency='1234',
        account='123456789012',
        dac='1',
        name='PRETTYNEW LTDA',
        address='RUA TESTE',
        address_number='100',
        complement='SALA 1',
        city='SAO PAULO',
        cep='01000000',
        state='SP',
    )


@pytest.fixture
def sample_payment() -> PaymentInput:
    return PaymentInput(
        name='JOAO DA SILVA',
        document='51300907134',
        pix_key='51300907134',
        pix_key_type='03',
        value=Decimal('150.00'),
        reference_id='REF001',
    )


@pytest.fixture
def three_payments() -> list[PaymentInput]:
    return [
        PaymentInput(
            name='JOAO DA SILVA',
            document='51300907134',
            pix_key='51300907134',
            pix_key_type='03',
            value=Decimal('150.00'),
            reference_id='REF001',
        ),
        PaymentInput(
            name='MARIA SOUZA',
            document='12345678901',
            pix_key='maria@email.com',
            pix_key_type='02',
            value=Decimal('200.50'),
            reference_id='REF002',
        ),
        PaymentInput(
            name='PEDRO ALVES',
            document='98765432100',
            pix_key='+5511987654321',
            pix_key_type='01',
            value=Decimal('75.25'),
            reference_id='REF003',
        ),
    ]


# ---------------------------------------------------------------------------
# build_cnab tests
# ---------------------------------------------------------------------------

def test_build_cnab_returns_bytes(company_config, sample_payment):
    result = build_cnab([sample_payment], company_config, date(2026, 3, 30))
    assert isinstance(result, bytes)


def test_build_cnab_latin1_decodable(company_config, sample_payment):
    """Output must be LATIN-1 encoded — decodable without errors (CNAB-07)."""
    result = build_cnab([sample_payment], company_config, date(2026, 3, 30))
    decoded = result.decode('latin-1')  # Must not raise
    assert isinstance(decoded, str)


def test_build_cnab_all_lines_240_bytes(company_config, sample_payment):
    """Every line in output must be exactly 240 bytes (CNAB-07)."""
    result = build_cnab([sample_payment], company_config, date(2026, 3, 30))
    lines = result.rstrip(b'\n').split(b'\n')
    assert all(len(line) == 240 for line in lines), (
        f"Line lengths: {[len(l) for l in lines]}"
    )


def test_build_cnab_no_crlf(company_config, sample_payment):
    """No carriage return bytes anywhere — CRLF suppressed (Pitfall 1)."""
    result = build_cnab([sample_payment], company_config, date(2026, 3, 30))
    assert b'\r' not in result


def test_build_cnab_1_payment_has_6_lines(company_config, sample_payment):
    """1 payment = header_arq + header_lote + segA + segB + trailer_lote + trailer_arq = 6 lines."""
    result = build_cnab([sample_payment], company_config, date(2026, 3, 30))
    lines = result.rstrip(b'\n').split(b'\n')
    assert len(lines) == 6


def test_build_cnab_3_payments_has_10_lines(company_config, three_payments):
    """3 payments = 1+1+6+1+1 = 10 lines."""
    result = build_cnab(three_payments, company_config, date(2026, 3, 30))
    lines = result.rstrip(b'\n').split(b'\n')
    assert len(lines) == 10


def test_build_cnab_0_payments_has_4_lines(company_config):
    """0 payments = header_arq + header_lote + trailer_lote + trailer_arq = 4 lines."""
    result = build_cnab([], company_config, date(2026, 3, 30))
    lines = result.rstrip(b'\n').split(b'\n')
    assert len(lines) == 4


def test_build_cnab_value_150_in_output(company_config, sample_payment):
    """R$ 150.00 encodes as 000000000015000 in Seg A of the output (CNAB-08)."""
    result = build_cnab([sample_payment], company_config, date(2026, 3, 30))
    # Decode and find the value string in the output
    decoded = result.decode('latin-1')
    assert '000000000015000' in decoded
