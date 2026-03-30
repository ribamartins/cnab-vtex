"""CNAB 240 record type functions for SISPAG Itau v085 PIX Transferencia.

Each function takes typed parameters and returns a 240-character string.
Every function asserts len(result) == 240 before returning.

Field positions use 1-based indexing per spec; implementation builds records
left-to-right by concatenation. Python 0-based slice = pos - 1.

Source: Itau SISPAG v085 spec (./Documents/sispag_cnab.md) and
        RESEARCH.md confirmed field position tables.
"""
from datetime import date, datetime
from decimal import Decimal

from cnab.fields import cnab_alpha, cnab_numeric, cnab_value


def header_arquivo(company, generation_dt: datetime) -> str:
    """Header de Arquivo (Tipo Registro = 0).

    Contains company identification and file metadata.
    Positions per RESEARCH.md 'Header de Arquivo — Confirmed Field Positions' table.
    """
    r = ''
    r += cnab_numeric(341, 3)                    # 001-003 BANCO = 341
    r += cnab_numeric(0, 4)                      # 004-007 LOTE = 0000
    r += cnab_numeric(0, 1)                      # 008     TIPO REG = 0
    r += cnab_alpha('', 6)                       # 009-014 BRANCOS
    r += cnab_numeric(80, 3)                     # 015-017 LAYOUT ARQUIVO = 080
    r += cnab_numeric(2, 1)                      # 018     EMPRESA INSCRICAO TIPO = 2 (CNPJ)
    r += cnab_numeric(company.cnpj, 14)          # 019-032 CNPJ (14 digits)
    r += cnab_alpha('', 20)                      # 033-052 BRANCOS
    r += cnab_numeric(company.agency, 5)         # 053-057 AGENCIA
    r += cnab_alpha(' ', 1)                      # 058     BRANCO
    r += cnab_numeric(company.account, 12)       # 059-070 CONTA
    r += cnab_alpha(' ', 1)                      # 071     BRANCO
    r += cnab_numeric(company.dac, 1)            # 072     DAC
    r += cnab_alpha(company.name, 30)            # 073-102 NOME EMPRESA
    r += cnab_alpha('ITAU UNIBANCO S.A.', 30)    # 103-132 NOME BANCO
    r += cnab_alpha('', 10)                      # 133-142 BRANCOS
    r += cnab_numeric(1, 1)                      # 143     ARQUIVO CODIGO = 1 (REMESSA)
    r += generation_dt.strftime('%d%m%Y')        # 144-151 DATA GERACAO DDMMAAAA
    r += generation_dt.strftime('%H%M%S')        # 152-157 HORA GERACAO HHMMSS
    r += cnab_numeric(0, 9)                      # 158-166 ZEROS
    r += cnab_numeric(0, 5)                      # 167-171 DENSIDADE = 00000 (teleprocessamento)
    r += cnab_alpha('', 69)                      # 172-240 BRANCOS
    assert len(r) == 240, f"header_arquivo: got {len(r)}"
    return r


def header_lote(company, lot_number: int) -> str:
    """Header de Lote (Tipo Registro = 1) for PIX Transferencia.

    Contains lot identification and company address.
    Positions per RESEARCH.md 'Header de Lote (PIX Transferencia)' table.
    """
    r = ''
    r += cnab_numeric(341, 3)                    # 001-003 BANCO = 341
    r += cnab_numeric(lot_number, 4)             # 004-007 LOTE
    r += cnab_numeric(1, 1)                      # 008     TIPO REG = 1
    r += 'C'                                     # 009     TIPO OPERACAO = C (credito)
    r += cnab_numeric(company.tipo_pagamento, 2) # 010-011 TIPO PAGAMENTO (Nota 4, default 20)
    r += cnab_numeric(45, 2)                     # 012-013 FORMA PAGAMENTO = 45 (PIX Transferencia)
    r += cnab_numeric(40, 3)                     # 014-016 LAYOUT LOTE = 040
    r += cnab_alpha(' ', 1)                      # 017     BRANCO
    r += cnab_numeric(2, 1)                      # 018     INSCRICAO TIPO = 2 (CNPJ)
    r += cnab_numeric(company.cnpj, 14)          # 019-032 CNPJ
    r += cnab_alpha('', 4)                       # 033-036 IDENT LANCAMENTO (Nota 13: brancos)
    r += cnab_alpha('', 16)                      # 037-052 BRANCOS
    r += cnab_numeric(company.agency, 5)         # 053-057 AGENCIA
    r += cnab_alpha(' ', 1)                      # 058     BRANCO
    r += cnab_numeric(company.account, 12)       # 059-070 CONTA
    r += cnab_alpha(' ', 1)                      # 071     BRANCO
    r += cnab_numeric(company.dac, 1)            # 072     DAC
    r += cnab_alpha(company.name, 30)            # 073-102 NOME EMPRESA
    r += cnab_alpha('', 30)                      # 103-132 FINALIDADE LOTE (Nota 6: brancos)
    r += cnab_alpha('', 10)                      # 133-142 HISTORICO C/C (Nota 7: brancos)
    r += cnab_alpha(company.address, 30)         # 143-172 ENDERECO
    r += cnab_numeric(company.address_number, 5) # 173-177 NUMERO
    r += cnab_alpha(company.complement, 15)      # 178-192 COMPLEMENTO
    r += cnab_alpha(company.city, 20)            # 193-212 CIDADE
    r += cnab_numeric(company.cep, 8)            # 213-220 CEP
    r += cnab_alpha(company.state, 2)            # 221-222 ESTADO
    r += cnab_alpha('', 8)                       # 223-230 BRANCOS
    r += cnab_alpha('', 10)                      # 231-240 OCORRENCIAS (remessa: brancos)
    assert len(r) == 240, f"header_lote: got {len(r)}"
    return r


def segmento_a(company, payment, seq_number: int, payment_date: date) -> str:
    """Segmento A (Tipo Registro = 3) for PIX Chave.

    Mandatory detail record for PIX Transferencia payments.
    Positions per RESEARCH.md 'Segmento A (PIX Chave) — Complete Field Map' table.
    """
    r = ''
    r += cnab_numeric(341, 3)                        # 001-003 BANCO = 341
    r += cnab_numeric(1, 4)                          # 004-007 LOTE = 0001
    r += cnab_numeric(3, 1)                          # 008     TIPO REG = 3
    r += cnab_numeric(seq_number, 5)                 # 009-013 NUM REG (sequential within lot)
    r += 'A'                                         # 014     SEGMENTO = A
    r += cnab_numeric(0, 3)                          # 015-017 TIPO MOVIMENTO = 000 (inclusao)
    r += cnab_numeric(9, 3)                          # 018-020 CAMARA = 009 (SPI/PIX, Nota 35)
    r += cnab_numeric(0, 3)                          # 021-023 BANCO FAVORECIDO = 000 (key-based)
    r += cnab_alpha('0' * 20, 20)                    # 024-043 AGENCIA/CONTA FAVORECIDO = zeros
    r += cnab_alpha(payment.name, 30)                # 044-073 NOME FAVORECIDO
    r += cnab_alpha(payment.reference_id, 20)        # 074-093 SEU NUMERO
    r += payment_date.strftime('%d%m%Y')             # 094-101 DATA PAGTO DDMMAAAA
    r += 'BRL'                                       # 102-104 MOEDA TIPO = BRL
    r += cnab_numeric(0, 8)                          # 105-112 CODIGO ISPB = 00000000 (Nota 35)
    r += '04'                                        # 113-114 IDENT TRANSFERENCIA = 04 (Chave Pix)
    r += cnab_numeric(0, 5)                          # 115-119 ZEROS
    r += cnab_value(payment.value, 13, 2)            # 120-134 VALOR DO PAGTO 9(13)V9(02)
    r += cnab_alpha('', 15)                          # 135-149 NOSSO NUMERO (remessa: spaces)
    r += cnab_alpha('', 5)                           # 150-154 BRANCOS (Nota 42)
    r += cnab_numeric(0, 8)                          # 155-162 DATA EFETIVA = 00000000 (remessa)
    r += cnab_numeric(0, 15)                         # 163-177 VALOR EFETIVO = zeros (remessa)
    r += cnab_alpha('', 20)                          # 178-197 FINALIDADE DETALHE (Nota 13)
    r += cnab_numeric(0, 6)                          # 198-203 N DO DOCUMENTO = zeros (remessa)
    r += cnab_numeric(payment.document, 14)          # 204-217 N DE INSCRICAO = CPF/CNPJ 14 digits
    r += cnab_alpha('', 2)                           # 218-219 FINALIDADE DOC/STATUS (spaces)
    r += cnab_alpha('', 5)                           # 220-224 FINALIDADE TED (spaces)
    r += cnab_alpha('', 5)                           # 225-229 BRANCOS
    r += '0'                                         # 230     AVISO = 0 (no notice, Nota 16)
    r += cnab_alpha('', 10)                          # 231-240 OCORRENCIAS (remessa: spaces)
    assert len(r) == 240, f"segmento_a: got {len(r)}"
    return r


def segmento_b_pix(company, payment, seq_number: int) -> str:
    """Segmento B PIX (Tipo Registro = 3, Segmento = B) for PIX key-based payments.

    Distinct from generic Segmento B (DOC/TED). Contains PIX key type and key value.
    Positions per RESEARCH.md 'Pattern 4: Segmento B PIX' table (spec pos 700-721).

    CRITICAL: NUM REG (pos 009-013) is the SAME as the paired Segmento A (Nota 9).
    """
    # Determine inscricao tipo: 1=CPF (11 digits), 2=CNPJ (14 digits)
    digits_only = ''.join(c for c in payment.document if c.isdigit())
    inscricao_tipo = '1' if len(digits_only) == 11 else '2'

    r = ''
    r += cnab_numeric(341, 3)                        # 001-003 BANCO = 341
    r += cnab_numeric(1, 4)                          # 004-007 LOTE = 0001
    r += cnab_numeric(3, 1)                          # 008     TIPO REG = 3
    r += cnab_numeric(seq_number, 5)                 # 009-013 NUM REG = SAME as paired Seg A
    r += 'B'                                         # 014     SEGMENTO = B
    r += cnab_alpha(payment.pix_key_type, 2)         # 015-016 TIPO CHAVE (Nota 37)
    r += cnab_alpha(' ', 1)                          # 017     BRANCO
    r += inscricao_tipo                              # 018     INSCRICAO TIPO (1=CPF, 2=CNPJ)
    r += cnab_numeric(payment.document, 14)          # 019-032 INSCRICAO NUM (CPF/CNPJ, 14 digits)
    r += cnab_alpha('', 30)                          # 033-062 BRANCOS
    r += cnab_numeric(0, 65)                         # 063-127 INFO ENTRE USUARIOS (9(65), zeros)
    r += cnab_alpha(payment.pix_key, 100)            # 128-227 CHAVE PIX (left-aligned, space-pad)
    r += cnab_alpha('', 3)                           # 228-230 BRANCOS
    r += cnab_alpha('', 10)                          # 231-240 OCORRENCIAS (remessa: spaces)
    assert len(r) == 240, f"segmento_b_pix: got {len(r)}"
    return r


def trailer_lote(lot_number: int, record_count: int, total_value: Decimal) -> str:
    """Trailer de Lote (Tipo Registro = 5).

    Contains total record count and value sum for the lot.
    Positions per RESEARCH.md 'Trailer de Lote' table.

    IMPORTANT: total_value uses picture 9(16)V9(02) = 18 chars (Pitfall 7, NOT 15).
    """
    r = ''
    r += cnab_numeric(341, 3)                        # 001-003 BANCO = 341
    r += cnab_numeric(lot_number, 4)                 # 004-007 LOTE
    r += cnab_numeric(5, 1)                          # 008     TIPO REG = 5
    r += cnab_alpha('', 9)                           # 009-017 BRANCOS
    r += cnab_numeric(record_count, 6)               # 018-023 TOTAL QTDE REG (2N+2)
    r += cnab_value(total_value, 16, 2)              # 024-041 TOTAL VALOR PAGTOS 9(16)V9(02) = 18 chars
    r += cnab_numeric(0, 18)                         # 042-059 ZEROS
    r += cnab_alpha('', 171)                         # 060-230 BRANCOS
    r += cnab_alpha('', 10)                          # 231-240 OCORRENCIAS (remessa: spaces)
    assert len(r) == 240, f"trailer_lote: got {len(r)}"
    return r


def trailer_arquivo(lot_count: int, total_records: int) -> str:
    """Trailer de Arquivo (Tipo Registro = 9).

    Contains lot count and total record count for the entire file.
    Positions per RESEARCH.md 'Trailer de Arquivo' table.
    """
    r = ''
    r += cnab_numeric(341, 3)                        # 001-003 BANCO = 341
    r += cnab_numeric(9999, 4)                       # 004-007 LOTE = 9999
    r += cnab_numeric(9, 1)                          # 008     TIPO REG = 9
    r += cnab_alpha('', 9)                           # 009-017 BRANCOS
    r += cnab_numeric(lot_count, 6)                  # 018-023 TOTAL QTDE LOTES
    r += cnab_numeric(total_records, 6)              # 024-029 TOTAL QTDE REGISTROS (2N+4)
    r += cnab_alpha('', 211)                         # 030-240 BRANCOS
    assert len(r) == 240, f"trailer_arquivo: got {len(r)}"
    return r
