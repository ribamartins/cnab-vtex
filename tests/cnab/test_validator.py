"""Tests for the pre-generation payment validator.

Covers:
- ValidationError dataclass structure and __str__ representation
- validate_payments: all mandatory field checks, document validation,
  PIX key type detection, consolidated per-row error reporting
"""
from decimal import Decimal

import pytest

from cnab.builder import PaymentInput
from cnab.validator import ValidationError, validate_payments


def make_payment(**overrides) -> PaymentInput:
    """Return a valid PaymentInput with sensible defaults.

    Any keyword argument overrides the corresponding field.
    Default values represent a known-valid PIX CPF payment.
    """
    defaults = {
        'name': 'JOAO DA SILVA',
        'document': '51300907134',      # Valid CPF
        'pix_key': '51300907134',       # CPF as PIX key
        'pix_key_type': '03',
        'value': Decimal('150.00'),
        'reference_id': 'REF001',
    }
    defaults.update(overrides)
    return PaymentInput(**defaults)


class TestValidationErrorStructure:
    """Tests for ValidationError dataclass and __str__."""

    def test_validation_error_str(self):
        err = ValidationError(row=2, field='pix_key', message='PIX key is required')
        assert str(err) == 'Row 2: pix_key - PIX key is required'

    def test_validation_error_fields(self):
        err = ValidationError(row=0, field='name', message='Beneficiary name is required')
        assert err.row == 0
        assert err.field == 'name'
        assert err.message == 'Beneficiary name is required'


class TestValidatePayments:
    """Tests for validate_payments function."""

    def test_empty_list_returns_no_errors(self):
        errors = validate_payments([])
        assert errors == []

    def test_valid_payment_returns_no_errors(self):
        errors = validate_payments([make_payment()])
        assert errors == []

    def test_missing_pix_key(self):
        errors = validate_payments([make_payment(pix_key='')])
        assert len(errors) >= 1
        pix_errors = [e for e in errors if e.field == 'pix_key']
        assert len(pix_errors) == 1
        assert pix_errors[0].row == 0
        msg = pix_errors[0].message.lower()
        assert 'missing' in msg or 'required' in msg

    def test_missing_document(self):
        errors = validate_payments([make_payment(document='')])
        doc_errors = [e for e in errors if e.field == 'document']
        assert len(doc_errors) >= 1
        assert doc_errors[0].row == 0

    def test_missing_name(self):
        errors = validate_payments([make_payment(name='')])
        name_errors = [e for e in errors if e.field == 'name']
        assert len(name_errors) == 1
        assert name_errors[0].row == 0

    def test_zero_value(self):
        errors = validate_payments([make_payment(value=Decimal('0'))])
        value_errors = [e for e in errors if e.field == 'value']
        assert len(value_errors) == 1
        assert value_errors[0].row == 0
        msg = value_errors[0].message.lower()
        assert 'zero' in msg or 'positive' in msg

    def test_negative_value(self):
        errors = validate_payments([make_payment(value=Decimal('-1'))])
        value_errors = [e for e in errors if e.field == 'value']
        assert len(value_errors) == 1
        assert value_errors[0].row == 0

    def test_invalid_cpf_check_digit(self):
        errors = validate_payments([make_payment(document='51300907135')])
        doc_errors = [e for e in errors if e.field == 'document']
        assert len(doc_errors) == 1
        assert doc_errors[0].row == 0
        msg = doc_errors[0].message
        assert 'CPF' in msg
        assert 'invalid' in msg.lower()

    def test_invalid_cnpj_check_digit(self):
        errors = validate_payments([make_payment(document='11222333000182')])
        doc_errors = [e for e in errors if e.field == 'document']
        assert len(doc_errors) == 1
        assert doc_errors[0].row == 0
        msg = doc_errors[0].message
        assert 'CNPJ' in msg
        assert 'invalid' in msg.lower()

    def test_undetectable_pix_key(self):
        errors = validate_payments([make_payment(pix_key='invalid-key-format')])
        pix_errors = [e for e in errors if e.field == 'pix_key']
        assert len(pix_errors) == 1
        assert pix_errors[0].row == 0

    def test_correct_row_indices(self):
        """Errors in row 0 and row 2 must carry correct row numbers."""
        payments = [
            make_payment(name=''),                  # row 0 — invalid
            make_payment(),                         # row 1 — valid
            make_payment(value=Decimal('0')),       # row 2 — invalid
        ]
        errors = validate_payments(payments)
        rows_with_errors = {e.row for e in errors}
        assert 0 in rows_with_errors
        assert 1 not in rows_with_errors
        assert 2 in rows_with_errors

    def test_multiple_errors_per_row(self):
        """A single row with both empty name and zero value must produce two errors."""
        errors = validate_payments([make_payment(name='', value=Decimal('0'))])
        fields_with_errors = {e.field for e in errors}
        assert 'name' in fields_with_errors
        assert 'value' in fields_with_errors
        assert len(errors) >= 2
