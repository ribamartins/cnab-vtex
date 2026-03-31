---
phase: 03-data-pipeline
plan: 02
subsystem: ui
tags: [pyside6, qthread, excel, vtex, cnab, validation, dialog]

requires:
  - phase: 03-data-pipeline/03-01
    provides: parse_excel, enrich_payments, EnrichmentResult, ExcelParseError
  - phase: 02-foundation
    provides: MainWindow, SettingsWindow QDialog pattern, session param, get_app_stylesheet

provides:
  - ImportPreviewDialog: QDialog with Excel file selection, parse preview, and VTEX enrichment orchestration
  - EnrichmentWorker: QThread that runs enrich_payments() with live progress signals and cancel support
  - ValidationReportDialog: QDialog showing merged VTEX+CNAB validation report with Gerar CNAB gate
  - MainWindow updated with "Importar Planilha" menu action wired to ImportPreviewDialog

affects:
  - 03-data-pipeline
  - 04-dashboard (will call valid_payments from MainWindow._last_valid_payments)

tech-stack:
  added: []
  patterns:
    - QThread worker pattern with Signal(int, int) progress and Signal(list) finished_signal
    - cancel() + wait() on reject/closeEvent (Pitfall 4 prevention)
    - Validation merge pattern: VTEX errors + validate_payments() errors unified in one table
    - _format_brl() Decimal -> Brazilian currency string helper

key-files:
  created:
    - src/ui/import_preview_dialog.py
    - src/ui/validation_report_dialog.py
  modified:
    - src/ui/main_window.py

key-decisions:
  - "ImportPreviewDialog always calls worker.cancel() + worker.wait() in both _on_cancel_clicked and reject() override to prevent dangling QThread on dialog close (Pitfall 4)"
  - "ValidationReportDialog uses 0-based validation_error_indices set to map enriched list index back to original row_index for display (D-16 merge pattern)"
  - "Gerar CNAB button enabled iff valid_count >= 1, reflecting D-14 gate"
  - "MainWindow stores _last_valid_payments for Phase 4 CNAB generation hook"

patterns-established:
  - "EnrichmentWorker pattern: QThread subclass with threading.Event cancel_flag, Signal(int,int) progress, Signal(list) finished_signal"
  - "Dialog cleanup pattern: override reject() to cancel+wait any running worker before super().reject()"

requirements-completed:
  - IMPT-03
  - VTEX-03

duration: 4min
completed: 2026-03-31
---

# Phase 03 Plan 02: Import UI Dialogs Summary

**Two PySide6 QDialogs connecting the pure-Python data pipeline to the UI: Excel import with live preview, VTEX enrichment progress in QThread, and a consolidated validation report gating CNAB generation**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-31T09:32:45Z
- **Completed:** 2026-03-31T09:33:57Z
- **Tasks:** 2 of 3 (Task 3 is human verification checkpoint)
- **Files modified:** 3

## Accomplishments

- ImportPreviewDialog: file selection via QFileDialog, Excel parse + preview (first 10 rows, filename, row count, total value in R$ format), VTEX enrichment launch with live QProgressBar updates
- EnrichmentWorker QThread with threading.Event cancel_flag, progress signals, finished_signal — clean shutdown via cancel()+wait() on dialog reject
- ValidationReportDialog: merged VTEX errors + validate_payments() CNAB validation errors in single error table; summary bar with valid/error/total counts and valid value; Gerar CNAB gate (enabled when >= 1 valid row)
- MainWindow wired with "Importar Planilha" menu action (before Configuracoes separator) and _last_valid_payments storage for Phase 4

## Task Commits

1. **Task 1: ImportPreviewDialog and ValidationReportDialog** - `a7b48d2` (feat)
2. **Task 2: Wire ImportPreviewDialog into MainWindow** - `421a360` (feat)
3. **Task 3: Human verification checkpoint** - pending human approval

**Plan metadata:** (pending final commit)

## Files Created/Modified

- `src/ui/import_preview_dialog.py` - EnrichmentWorker (QThread) + ImportPreviewDialog (file selection, preview, enrichment orchestration)
- `src/ui/validation_report_dialog.py` - ValidationReportDialog (merged VTEX+CNAB error report, Gerar CNAB gate)
- `src/ui/main_window.py` - Added "Importar Planilha" menu action, _open_import() handler, QDialog import

## Decisions Made

- cancel()+wait() called in both _on_cancel_clicked() and reject() override to handle all close paths safely (Pitfall 4)
- ValidationReportDialog uses a set of 0-based enriched-list indices (validation_error_indices) to identify valid rows, then maps back to original row_index for display
- _format_brl() helper duplicated in both files (kept self-contained per plan design; could be extracted to utils in future)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Pre-existing: pytest collection fails without `PYTHONPATH=src` because there is no `conftest.py` or `pyproject.toml` configuring the source path. All 167 existing tests pass with `PYTHONPATH=src python -m pytest`. This is out of scope for this plan.

## Known Stubs

- `MainWindow._last_valid_payments`: set after successful ImportPreviewDialog acceptance, but no Phase 3 consumer yet — Phase 4 (dashboard/CNAB generation) will use this list to call build_cnab().

## Next Phase Readiness

- ImportPreviewDialog and ValidationReportDialog are complete and wired
- MainWindow stores valid_payments list ready for Phase 4 CNAB generation
- Human verification (Task 3 checkpoint) pending — app must be launched to confirm visual flow

---
*Phase: 03-data-pipeline*
*Completed: 2026-03-31*

## Self-Check: PASSED

Files exist:
- FOUND: src/ui/import_preview_dialog.py
- FOUND: src/ui/validation_report_dialog.py
- FOUND: src/ui/main_window.py

Commits exist:
- FOUND: a7b48d2 (Task 1)
- FOUND: 421a360 (Task 2)
