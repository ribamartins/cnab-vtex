---
phase: 01-cnab-engine
plan: 01
subsystem: cnab-engine
tags: [cnab, pix, records, builder, tdd, byte-exact]
dependency_graph:
  requires: []
  provides:
    - cnab.fields (cnab_alpha, cnab_numeric, cnab_value)
    - cnab.records (header_arquivo, header_lote, segmento_a, segmento_b_pix, trailer_lote, trailer_arquivo)
    - cnab.builder (build_cnab, PaymentInput, CompanyConfig)
  affects:
    - Phase 02 (Flask app imports cnab.builder.build_cnab)
    - Phase 03 (VTEX enrichment populates PaymentInput fields)
    - Phase 04 (PySide6 UI calls build_cnab and saves output bytes)
tech_stack:
  added:
    - pytest==9.0.2 (test runner, requirements-dev.txt)
  patterns:
    - TDD: RED (failing import) → GREEN (implement) → verify for both tasks
    - Field helpers: cnab_alpha/cnab_numeric/cnab_value as pure formatting functions
    - Record functions: one per record type, each asserts len == 240
    - Builder: orchestrates records, accumulates Decimal totals, encodes LATIN-1 with LF
key_files:
  created:
    - src/cnab/__init__.py (package marker)
    - src/cnab/fields.py (3 field helper functions)
    - src/cnab/records.py (6 record type functions)
    - src/cnab/builder.py (PaymentInput + CompanyConfig dataclasses + build_cnab)
    - tests/__init__.py (package marker)
    - tests/cnab/__init__.py (package marker)
    - tests/cnab/test_fields.py (15 unit tests for field helpers)
    - tests/cnab/test_records.py (34 byte-position assertions for all 6 record types)
    - tests/cnab/test_builder.py (8 integration tests for build_cnab)
    - requirements-dev.txt (pytest==9.0.2)
  modified: []
decisions:
  - "Segmento A AGENCIA/CONTA FAVORECIDO filled with 20 zeros (key-based PIX, spec Nota 11 optional)"
  - "Segmento B INFO ENTRE USUARIOS filled with 65 zeros (numeric picture 9(65), per open question 3)"
  - "PaymentInput.value uses Decimal — float is explicitly prohibited per CNAB-08"
  - "build_cnab encodes LATIN-1 with LF-only separators — CRLF suppressed by join/encode pattern"
metrics:
  duration_seconds: 245
  completed_date: "2026-03-30"
  tasks_completed: 2
  tasks_total: 2
  files_created: 10
  files_modified: 0
  tests_added: 57
  tests_passing: 57
---

# Phase 01 Plan 01: CNAB Engine — Core Records and Builder Summary

**One-liner:** Pure-Python CNAB 240 engine with six byte-exact PIX Transferencia record functions (SISPAG Itau v085), Decimal arithmetic, and LATIN-1/LF encoding — 57 tests all passing.

## What Was Built

Complete CNAB 240 byte-exact file generator for PIX Transferencia payments, implementing all six mandatory record types as specified in Itau SISPAG v085.

### Module Structure

```
src/cnab/
├── __init__.py        — package marker
├── fields.py          — cnab_alpha, cnab_numeric, cnab_value helpers
├── records.py         — 6 record functions (each asserts len == 240)
└── builder.py         — PaymentInput/CompanyConfig dataclasses + build_cnab
tests/cnab/
├── test_fields.py     — 15 unit tests: all field helper behaviors
├── test_records.py    — 34 byte-position tests: all 6 record types
└── test_builder.py    — 8 integration tests: encoding, line count, CRLF
```

### Key Constraints Met

| Constraint | Implementation |
|------------|----------------|
| Every record exactly 240 chars | `assert len(r) == 240` in every record function |
| LATIN-1 encoding | `content.encode('latin-1')` in build_cnab |
| LF separators, no CRLF | `'\n'.join(records)` — explicit LF, no text-mode Windows translation |
| Decimal arithmetic only | `PaymentInput.value: Decimal`, `total_value = Decimal('0')`, `cnab_value` uses only Decimal ops |
| R$ 150.00 = `000000000015000` | Verified by `test_cnab_value_150_brl` and `test_segmento_a_valor_150_brl` |
| Trailer Lote = 2N+2 records | `lote_record_count = 2 * len(payments) + 2` in builder |
| Trailer Arquivo = 2N+4 records | `total_record_count = 2 * len(payments) + 4` in builder |
| Seg B NUM REG = same as Seg A | Both receive `seq` (same variable) — verified by `test_segmento_b_pix_num_reg_matches_seg_a` |
| Trailer Lote value: 9(16)V9(02) = 18 chars | `cnab_value(total_value, 16, 2)` — distinct from Seg A's 15-char field |

### Field Position Verification (0-based Python slicing)

| Field | 0-based slice | Expected | Test |
|-------|--------------|----------|------|
| Header Arquivo bank | [0:3] | `341` | PASS |
| Header Arquivo layout | [14:17] | `080` | PASS |
| Header Arquivo remessa | [142:143] | `1` | PASS |
| Header Lote operation | [8:9] | `C` | PASS |
| Header Lote tipo pag | [9:11] | `20` | PASS |
| Header Lote forma pag PIX | [11:13] | `45` | PASS |
| Header Lote layout lote | [13:16] | `040` | PASS |
| Segmento A camara SPI | [17:20] | `009` | PASS |
| Segmento A ident transf | [112:114] | `04` | PASS |
| Segmento A valor R$150 | [119:134] | `000000000015000` | PASS |
| Segmento B tipo chave | [14:16] | pix_key_type | PASS |
| Segmento B chave pix | [127:227] | pix_key padded | PASS |
| Trailer Lote tipo reg | [7:8] | `5` | PASS |
| Trailer Arquivo lote | [3:7] | `9999` | PASS |
| Trailer Arquivo tipo reg | [7:8] | `9` | PASS |

## Test Results

```
57 passed in 0.09s
PYTHONPATH=src python -m pytest tests/cnab/ -v
```

## Verification Output

```
Lines: 6, All 240: True, No CRLF: True
```
(1 payment = header_arq + header_lote + segA + segB + trailer_lote + trailer_arq = 6 lines)

## Deviations from Plan

None — plan executed exactly as written. All TDD phases (RED/GREEN) completed in order. All field positions, formulas, and encoding rules implemented per RESEARCH.md tables.

## Known Stubs

None. All six record functions produce complete, bank-submittable output. The build_cnab orchestrator generates a valid CNAB file for any list of PaymentInput records.

## Self-Check: PASSED

All files exist on disk. Both commits (d75c089, 2a3292f) verified in git log. All 57 tests passing.
