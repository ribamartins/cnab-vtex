"""Byte-exact assertions for each CNAB 240 record type.

Tests verify exact field positions per SISPAG v085 spec and RESEARCH.md field position tables.
Run with: PYTHONPATH=src python -m pytest tests/cnab/test_records.py -v
"""
from decimal import Decimal
from datetime import date, datetime

import pytest

from cnab.records import (
    header_arquivo, header_lote, segmento_a,
    segmento_b_pix, trailer_lote, trailer_arquivo,
)
from cnab.builder import CompanyConfig, PaymentInput


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


# ---------------------------------------------------------------------------
# header_arquivo tests
# ---------------------------------------------------------------------------

def test_header_arquivo_length(company_config):
    record = header_arquivo(company_config, datetime(2026, 3, 30, 10, 0, 0))
    assert len(record) == 240


def test_header_arquivo_bank_code(company_config):
    record = header_arquivo(company_config, datetime(2026, 3, 30, 10, 0, 0))
    assert record[0:3] == '341'


def test_header_arquivo_lote_zero(company_config):
    record = header_arquivo(company_config, datetime(2026, 3, 30, 10, 0, 0))
    assert record[3:7] == '0000'


def test_header_arquivo_tipo_reg(company_config):
    record = header_arquivo(company_config, datetime(2026, 3, 30, 10, 0, 0))
    assert record[7:8] == '0'


def test_header_arquivo_layout_version(company_config):
    record = header_arquivo(company_config, datetime(2026, 3, 30, 10, 0, 0))
    assert record[14:17] == '080'


def test_header_arquivo_inscricao_tipo_cnpj(company_config):
    record = header_arquivo(company_config, datetime(2026, 3, 30, 10, 0, 0))
    assert record[17:18] == '2'


def test_header_arquivo_arquivo_codigo_remessa(company_config):
    record = header_arquivo(company_config, datetime(2026, 3, 30, 10, 0, 0))
    assert record[142:143] == '1'


# ---------------------------------------------------------------------------
# header_lote tests
# ---------------------------------------------------------------------------

def test_header_lote_length(company_config):
    record = header_lote(company_config, lot_number=1)
    assert len(record) == 240


def test_header_lote_tipo_reg(company_config):
    record = header_lote(company_config, lot_number=1)
    assert record[7:8] == '1'


def test_header_lote_operacao_credito(company_config):
    record = header_lote(company_config, lot_number=1)
    assert record[8:9] == 'C'


def test_header_lote_tipo_pagamento_fornecedores(company_config):
    record = header_lote(company_config, lot_number=1)
    assert record[9:11] == '20'


def test_header_lote_forma_pagamento_pix(company_config):
    record = header_lote(company_config, lot_number=1)
    assert record[11:13] == '45'


def test_header_lote_layout_lote(company_config):
    record = header_lote(company_config, lot_number=1)
    assert record[13:16] == '040'


# ---------------------------------------------------------------------------
# segmento_a tests
# ---------------------------------------------------------------------------

def test_segmento_a_length(company_config, sample_payment):
    record = segmento_a(company_config, sample_payment, 1, date(2026, 3, 30))
    assert len(record) == 240


def test_segmento_a_tipo_reg(company_config, sample_payment):
    record = segmento_a(company_config, sample_payment, 1, date(2026, 3, 30))
    assert record[7:8] == '3'


def test_segmento_a_segmento_code(company_config, sample_payment):
    record = segmento_a(company_config, sample_payment, 1, date(2026, 3, 30))
    assert record[13:14] == 'A'


def test_segmento_a_camara_pix(company_config, sample_payment):
    """Nota 35: Para pagamento via PIX deve ser informado 009 (SPI)."""
    record = segmento_a(company_config, sample_payment, 1, date(2026, 3, 30))
    assert record[17:20] == '009'


def test_segmento_a_ident_transferencia_chave_pix(company_config, sample_payment):
    """Nota 36: 04 = Chave Pix."""
    record = segmento_a(company_config, sample_payment, 1, date(2026, 3, 30))
    assert record[112:114] == '04'


def test_segmento_a_valor_150_brl(company_config, sample_payment):
    """R$ 150.00 encodes as 000000000015000 — picture 9(13)V9(02), CNAB-08."""
    record = segmento_a(company_config, sample_payment, 1, date(2026, 3, 30))
    assert record[119:134] == '000000000015000'


# ---------------------------------------------------------------------------
# segmento_b_pix tests
# ---------------------------------------------------------------------------

def test_segmento_b_pix_length(company_config, sample_payment):
    record = segmento_b_pix(company_config, sample_payment, 1)
    assert len(record) == 240


def test_segmento_b_pix_tipo_reg(company_config, sample_payment):
    record = segmento_b_pix(company_config, sample_payment, 1)
    assert record[7:8] == '3'


def test_segmento_b_pix_segmento_code(company_config, sample_payment):
    record = segmento_b_pix(company_config, sample_payment, 1)
    assert record[13:14] == 'B'


def test_segmento_b_pix_key_type_code(company_config, sample_payment):
    """Positions 015-016 (0-indexed 14:16) contain the PIX key type code."""
    record = segmento_b_pix(company_config, sample_payment, 1)
    assert record[14:16] == sample_payment.pix_key_type


def test_segmento_b_pix_key_value_position(company_config, sample_payment):
    """CHAVE PIX at positions 128-227 (0-indexed 127:227), left-aligned space-padded."""
    record = segmento_b_pix(company_config, sample_payment, 1)
    expected_key = sample_payment.pix_key.ljust(100)[:100]
    assert record[127:227] == expected_key


def test_segmento_b_pix_num_reg_matches_seg_a(company_config, sample_payment):
    """Nota 9: Seg B NUM REG (positions 009-013, 0-indexed 8:13) must equal paired Seg A NUM REG."""
    seq = 3
    record_a = segmento_a(company_config, sample_payment, seq, date(2026, 3, 30))
    record_b = segmento_b_pix(company_config, sample_payment, seq)
    # Both must share the same NUM REG at positions 009-013 (0-indexed 8:13)
    assert record_a[8:13] == record_b[8:13]


# ---------------------------------------------------------------------------
# trailer_lote tests
# ---------------------------------------------------------------------------

def test_trailer_lote_length():
    record = trailer_lote(lot_number=1, record_count=8, total_value=Decimal('450.00'))
    assert len(record) == 240


def test_trailer_lote_tipo_reg():
    record = trailer_lote(lot_number=1, record_count=8, total_value=Decimal('450.00'))
    assert record[7:8] == '5'


def test_trailer_lote_record_count_3_payments():
    """For 3 payments: 2*3+2=8 records (header_lote + 6 segments + trailer_lote)."""
    record = trailer_lote(lot_number=1, record_count=8, total_value=Decimal('450.00'))
    assert record[17:23] == '000008'


def test_trailer_lote_value_sum(company_config, sample_payment):
    """Value sum field (pos 024-041, 0-indexed 23:41) is picture 9(16)V9(02) = 18 chars."""
    # 3 payments of R$ 150.00 = R$ 450.00 → 18-char string
    total = Decimal('450.00')
    record = trailer_lote(lot_number=1, record_count=8, total_value=total)
    # 450.00 * 100 = 45000, padded to 18 chars = '000000000000045000'
    assert record[23:41] == '000000000000045000'


# ---------------------------------------------------------------------------
# trailer_arquivo tests
# ---------------------------------------------------------------------------

def test_trailer_arquivo_length():
    record = trailer_arquivo(lot_count=1, total_records=10)
    assert len(record) == 240


def test_trailer_arquivo_lote_field():
    record = trailer_arquivo(lot_count=1, total_records=10)
    assert record[3:7] == '9999'


def test_trailer_arquivo_tipo_reg():
    record = trailer_arquivo(lot_count=1, total_records=10)
    assert record[7:8] == '9'


def test_trailer_arquivo_lot_count_3_payments():
    """For 3 payments: 1 lot."""
    record = trailer_arquivo(lot_count=1, total_records=10)
    assert record[17:23] == '000001'


def test_trailer_arquivo_total_records_3_payments():
    """For 3 payments: 2*3+4=10 total records."""
    record = trailer_arquivo(lot_count=1, total_records=10)
    assert record[23:29] == '000010'
