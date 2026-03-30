"""Pre-generation payment validator for CNAB PIX.

Validates all payments before CNAB file generation. Returns a consolidated
per-row error list so the user can fix ALL issues before any file is generated.

Exports:
- ValidationError: dataclass describing a single field-level validation failure
- validate_payments: check all payments, return list[ValidationError]
"""
import re
from dataclasses import dataclass
from decimal import Decimal

from cnab.pix_key import validate_cpf, validate_cnpj, detect_pix_key_type
from cnab.builder import PaymentInput


@dataclass
class ValidationError:
    """Describes a single validation failure for one payment row.

    Attributes:
        row:     0-based row index in the payment list.
        field:   Name of the field that failed ('name', 'document', 'pix_key', 'value').
        message: Human-readable description of the problem.
    """
    row: int
    field: str
    message: str

    def __str__(self) -> str:
        return f"Row {self.row}: {self.field} - {self.message}"


def validate_payments(payments: list[PaymentInput]) -> list[ValidationError]:
    """Validate all payments before CNAB generation.

    Checks every payment for:
    - VALD-03: mandatory fields (name, document, pix_key, value > 0)
    - VALD-02: CPF/CNPJ check digit validity for 11- or 14-digit documents
    - VALD-01: PIX key type detectability

    Returns a list of ALL validation errors across ALL rows.
    An empty return list means all payments are valid and generation can proceed.
    This is the pre-generation safety gate (VALD-04).
    """
    errors: list[ValidationError] = []

    for i, payment in enumerate(payments):
        # --- Mandatory: name ---
        if not payment.name or not payment.name.strip():
            errors.append(ValidationError(
                row=i, field='name',
                message='Beneficiary name is required'
            ))

        # --- Mandatory: document ---
        if not payment.document or not payment.document.strip():
            errors.append(ValidationError(
                row=i, field='document',
                message='Document (CPF/CNPJ) is required'
            ))
        else:
            # VALD-02: validate CPF or CNPJ check digits
            digits = re.sub(r'\D', '', payment.document)
            if len(digits) == 11:
                if not validate_cpf(digits):
                    errors.append(ValidationError(
                        row=i, field='document',
                        message=f'CPF is invalid (check digits failed): {payment.document}'
                    ))
            elif len(digits) == 14:
                if not validate_cnpj(digits):
                    errors.append(ValidationError(
                        row=i, field='document',
                        message=f'CNPJ is invalid (check digits failed): {payment.document}'
                    ))
            else:
                errors.append(ValidationError(
                    row=i, field='document',
                    message=(
                        f'Document must be 11 digits (CPF) or 14 digits (CNPJ), '
                        f'got {len(digits)} digits'
                    )
                ))

        # --- Mandatory: pix_key ---
        if not payment.pix_key or not payment.pix_key.strip():
            errors.append(ValidationError(
                row=i, field='pix_key',
                message='PIX key is required (missing or empty)'
            ))
        else:
            # VALD-01: verify key type is detectable
            try:
                detect_pix_key_type(payment.pix_key)
            except ValueError:
                errors.append(ValidationError(
                    row=i, field='pix_key',
                    message=f'Cannot detect PIX key type: {payment.pix_key!r}'
                ))

        # --- Mandatory: value > 0 ---
        if payment.value is None or payment.value <= Decimal('0'):
            errors.append(ValidationError(
                row=i, field='value',
                message=(
                    f'Payment value must be positive (greater than zero), '
                    f'got {payment.value}'
                )
            ))

    return errors
