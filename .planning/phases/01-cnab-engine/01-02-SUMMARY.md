---
phase: 01-cnab-engine
plan: 02
subsystem: payments
tags: [cnab, pix, validation, cpf, cnpj]

requires:
  - phase: 01-cnab-engine/01-01
    provides: PaymentInput dataclass, build_cnab, CNAB record functions

provides:
  - detect_pix_key_type: classifies raw PIX key as SISPAG Nota 37 type code (01/02/03/04)
  - validate_cpf / validate_cnpj: Receita Federal mod-11 check digit validation
  - validate_payments: consolidated per-row error list before CNAB generation (VALD-01..04)
  - ValidationError dataclass with row/field/message and human-readable __str__

affects: [excel-import, vtex-enrichment, ui-upload-flow]

tech-stack:
  added: []
  patterns:
    - "TDD red-green for pure validation logic — write all tests before any implementation"
    - "Consolidated error reporting: collect ALL errors before returning, never raise on first failure"
    - "PIX key detection order: UUID first to prevent false positives, then phone, email, CPF/CNPJ"
    - "all-same-digit rejection guard: len(set(digits)) == 1 check before mod-11 algorithm"

key-files:
  created:
    - src/cnab/pix_key.py
    - src/cnab/validator.py
    - tests/cnab/test_pix_key.py
    - tests/cnab/test_validator.py
  modified: []

key-decisions:
  - "PIX key detection uses UUID-first order to prevent ambiguity with all-digit UUIDs"
  - "validate_payments never raises — always returns full list so user sees ALL errors at once"
  - "Document validation distinguishes CPF (11 digits) vs CNPJ (14 digits) and names them in error messages"

patterns-established:
  - "Pattern 1: Import chain — validator imports from pix_key and builder, never circular"
  - "Pattern 2: make_payment() helper in tests — single valid default, override per test case"
  - "Pattern 3: per-field error collection via list.append inside a single row loop"

requirements-completed: [VALD-01, VALD-02, VALD-03, VALD-04]

duration: 15min
completed: 2026-03-30
---

# Phase 01 Plan 02: PIX Validator Summary

**PIX key type detector (4 types, SISPAG Nota 37) and pre-generation payment validator with consolidated per-row error reporting — the safety gate preventing invalid batches from reaching the bank.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-30T20:44:51Z
- **Completed:** 2026-03-30T20:59:00Z
- **Tasks:** 2 of 2
- **Files modified:** 4 created, 0 modified

## Accomplishments

### Task 1: PIX key type detector and CPF/CNPJ validation

Created `src/cnab/pix_key.py` with three public functions:

- `detect_pix_key_type(raw_key)`: strips whitespace, matches UUID/phone/email/CPF-CNPJ in that order, returns SISPAG code ('01'–'04'), raises ValueError for unrecognized formats.
- `validate_cpf(cpf)`: strips non-digits, checks length == 11, rejects all-same-digit, runs Receita Federal mod-11 on both check digits.
- `validate_cnpj(cnpj)`: strips non-digits, checks length == 14, rejects all-same-digit, runs Receita Federal mod-11 with standard weights [5,4,3,2,9,8,7,6,5,4,3,2] / [6,...].

25 tests covering all four key types, edge cases (whitespace stripping, ValueError for empty/invalid), and both document validators.

### Task 2: Pre-generation payment validator

Created `src/cnab/validator.py` with:

- `ValidationError` dataclass: row (int), field (str), message (str). `__str__` returns `"Row {row}: {field} - {message}"`.
- `validate_payments(payments)`: iterates all rows, collects ALL errors before returning. Checks name, document, pix_key presence, calls validate_cpf/validate_cnpj for check digits, calls detect_pix_key_type to verify PIX key format, rejects value <= 0.

14 tests validating every individual field error, correct row indices, multi-error rows, and the empty/valid-all-pass cases.

## Full Test Suite

96 tests across 5 files — all pass:

| File | Tests | Coverage |
|------|-------|----------|
| test_fields.py | 15 | cnab_alpha, cnab_numeric, cnab_value helpers |
| test_records.py | 29 | 6 record type functions |
| test_builder.py | 8 | build_cnab orchestration |
| test_pix_key.py | 25 | detect_pix_key_type, validate_cpf, validate_cnpj |
| test_validator.py | 14 + 5 = 14 | validate_payments, ValidationError |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all functions are fully implemented with real logic.

## Self-Check: PASSED

Files confirmed:
- FOUND: src/cnab/pix_key.py
- FOUND: src/cnab/validator.py
- FOUND: tests/cnab/test_pix_key.py
- FOUND: tests/cnab/test_validator.py

Commits confirmed:
- da14217 feat(01-cnab-engine-02): Task 1 — PIX key type detector and CPF/CNPJ validators
- fdb9b0a feat(01-cnab-engine-02): Task 2 — pre-generation payment validator
