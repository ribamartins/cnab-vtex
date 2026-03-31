---
phase: 03-data-pipeline
plan: 01
subsystem: data-pipeline
tags: [excel-parser, vtex-enrichment, tdd, decimal, httpx]
dependency_graph:
  requires:
    - 01-cnab-engine (PaymentInput, detect_pix_key_type)
    - 02-foundation (app package structure)
  provides:
    - src/app/excel_parser.py (parse_excel, ParseResult, ParsedRow, ExcelParseError)
    - src/vtex/enrichment.py (enrich_payments, EnrichmentResult)
  affects:
    - 03-02 (UI screens consume parse_excel and enrich_payments)
tech_stack:
  added:
    - openpyxl (already in requirements — first use in production code)
    - httpx (already in requirements — first use in production code)
  patterns:
    - TDD Red-Green for both modules
    - Decimal-only arithmetic (no float) per D-03 and CNAB-08
    - Duck-typed rows param to avoid circular imports between app and vtex packages
key_files:
  created:
    - src/app/excel_parser.py
    - src/vtex/__init__.py
    - src/vtex/enrichment.py
    - tests/app/test_excel_parser.py
    - tests/vtex/__init__.py
    - tests/vtex/test_enrichment.py
  modified: []
decisions:
  - "Excel column names case-sensitive and exact: Nome do Beneficiario, Codigo, Valor (D-01)"
  - "VTEX throttle set to 300ms — within the D-08 range of 200-500ms"
  - "rows param typed loosely with duck typing to avoid circular import between app.excel_parser and vtex.enrichment"
metrics:
  duration_minutes: 3
  completed_date: "2026-03-31"
  tasks_completed: 2
  files_created: 6
  files_modified: 0
  tests_added: 25
  tests_total: 167
---

# Phase 3 Plan 1: Excel Parser and VTEX Enrichment Service Summary

**One-liner:** Pure-Python Excel parser converting Brazilian currency text to Decimal plus sequential VTEX MasterData enrichment service mapping referenceId rows to PaymentInput objects.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Excel parser tests | deb4f2c | tests/app/test_excel_parser.py |
| 1 (GREEN) | Excel parser implementation | 20049b3 | src/app/excel_parser.py |
| 2 (RED) | VTEX enrichment tests | af2d6ea | tests/vtex/__init__.py, tests/vtex/test_enrichment.py |
| 2 (GREEN) | VTEX enrichment implementation | f4e432c | src/vtex/__init__.py, src/vtex/enrichment.py |

## What Was Built

### `src/app/excel_parser.py`

- `REQUIRED_COLUMNS = ["Nome do Beneficiario", "Codigo", "Valor"]` — exact match, case-sensitive (D-01)
- `parse_excel(path: Path) -> ParseResult` — opens .xlsx read-only, validates headers row 1 (D-02), skips blank rows (D-04)
- `_parse_valor(raw: str) -> Decimal` — strips "R$", replaces thousands dot, converts comma to dot, returns Decimal never float (D-03, CNAB-08)
- `ExcelParseError` — names missing column or invalid value
- `ParsedRow` dataclass — nome, codigo, valor (Decimal), original_valor (raw string)
- `ParseResult` dataclass — rows, total_value (sum of Decimals), filename

### `src/vtex/enrichment.py`

- `enrich_payments(rows, app_key, app_token, on_progress, cancel_flag)` — sequential calls with 300ms throttle (D-08), progress callback (D-10), cancellation via threading.Event (D-11)
- `_fetch_one()` — GET VTEX MasterData with params `_fields=_all&_where=referenceId={codigo}`, handles timeout/HTTP errors/empty list per row (D-09)
- `_map_to_payment()` — detects PIX key type via `detect_pix_key_type()`, maps firstName+lastName with receiverName fallback, document with cpf fallback (Pitfall 7)
- `EnrichmentResult` dataclass — row_index, reference_id, payment (Optional[PaymentInput]), error (Optional[str])

## Test Coverage

- `tests/app/test_excel_parser.py` — 16 tests: row count/total/filename, Decimal types, original_valor preservation, missing column errors, blank row skipping, all _parse_valor variants
- `tests/vtex/test_enrichment.py` — 9 tests: success path with field mapping, not-found/timeout/HTTP-500/missing-pixKey errors, progress callback verification, cancel_flag early stop, document/cpf fallback
- Full suite: 167 tests, 0 failures

## Key Design Notes

The `rows` parameter in `enrich_payments()` accepts duck-typed objects (`.codigo`, `.valor`, `.nome`) rather than importing `ParsedRow` directly. This avoids a circular import where `vtex.enrichment` would import from `app.excel_parser` while Plan 03-02 UI screens will import both. The contract is documented in the function signature via comment.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — both modules are fully wired with real logic. No placeholder data flows to consumers.

## Self-Check: PASSED

Files verified present:
- src/app/excel_parser.py — FOUND
- src/vtex/__init__.py — FOUND
- src/vtex/enrichment.py — FOUND
- tests/app/test_excel_parser.py — FOUND
- tests/vtex/__init__.py — FOUND
- tests/vtex/test_enrichment.py — FOUND

Commits verified:
- deb4f2c — FOUND
- 20049b3 — FOUND
- af2d6ea — FOUND
- f4e432c — FOUND
