"""CNAB 240 file builder — orchestrates record functions into a complete file.

Exports:
- PaymentInput: dataclass for per-payment beneficiary data
- CompanyConfig: dataclass for the debit company configuration
- build_cnab: assembles all records and returns LATIN-1 encoded bytes
"""
from dataclasses import dataclass
from decimal import Decimal
from datetime import date, datetime


@dataclass
class PaymentInput:
    """Per-payment beneficiary data for CNAB PIX Transferencia."""
    name: str             # Beneficiary name (max 30 chars in CNAB)
    document: str         # CPF (11 digits) or CNPJ (14 digits), digits only
    pix_key: str          # Raw PIX key value
    pix_key_type: str     # SISPAG Nota 37 code: '01' phone, '02' email, '03' CPF/CNPJ, '04' UUID
    value: Decimal        # Payment amount (must be Decimal, never float — CNAB-08)
    reference_id: str     # VTEX referenceId / company document reference


@dataclass
class CompanyConfig:
    """Debit company configuration for CNAB header and lote records."""
    cnpj: str             # 14 digits, no punctuation
    agency: str           # Up to 5 digits
    account: str          # Up to 12 digits
    dac: str              # 1 digit (DAC Itau)
    name: str             # Company name (max 30 chars)
    address: str          # Street address (max 30 chars)
    address_number: str   # Number (max 5 digits)
    complement: str       # Address complement (max 15 chars)
    city: str             # City name (max 20 chars)
    cep: str              # 8 digits, no hyphen
    state: str            # 2-char state abbreviation (e.g., 'SP')
    tipo_pagamento: int = 20  # Nota 4: 20=Fornecedores (default), 98=Diversos


def build_cnab(payments: list[PaymentInput], config: CompanyConfig,
                payment_date: date) -> bytes:
    """Build complete CNAB 240 file as LATIN-1 encoded bytes.

    Returns bytes with LF line separators (no CRLF).
    Each record line is exactly 240 bytes when encoded.
    """
    from cnab.records import (
        header_arquivo, header_lote, segmento_a,
        segmento_b_pix, trailer_lote, trailer_arquivo
    )

    records: list[str] = []
    records.append(header_arquivo(config, datetime.now()))
    records.append(header_lote(config, lot_number=1))

    total_value = Decimal('0')
    for seq, payment in enumerate(payments, start=1):
        records.append(segmento_a(config, payment, seq, payment_date))
        records.append(segmento_b_pix(config, payment, seq))  # SAME seq as Seg A (Nota 9)
        total_value += payment.value

    # record_count for trailer_lote = header_lote + 2*N segments + trailer_lote = 2N+2
    lote_record_count = 2 * len(payments) + 2
    records.append(trailer_lote(lot_number=1, record_count=lote_record_count,
                                 total_value=total_value))

    # total_records for trailer_arquivo = header_arq + lote_records + trailer_arq = 1 + (2N+2) + 1 = 2N+4
    total_record_count = 2 * len(payments) + 4
    records.append(trailer_arquivo(lot_count=1, total_records=total_record_count))

    # Validate all records are 240 chars
    for i, r in enumerate(records):
        assert len(r) == 240, f"Record {i} is {len(r)} chars, expected 240"

    # Encode to LATIN-1 bytes, join with LF (not CRLF — Pitfall 1)
    content = '\n'.join(records) + '\n'
    return content.encode('latin-1')
