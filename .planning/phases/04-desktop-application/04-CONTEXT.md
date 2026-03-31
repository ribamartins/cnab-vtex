# Phase 4: Desktop Application - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers the full payment workflow GUI: CNAB file generation from validated data (wiring ValidationReportDialog -> CNAB builder -> DB + file download), file management (download, mock transmission), a dashboard with file list and filters, file detail drill-down with payment rows, and an audit log viewer. No return file processing — that's v2. No real Itau API — mock transmitter only.

</domain>

<decisions>
## Implementation Decisions

### CNAB Generation Flow (FILE-01, FILE-02)
- **D-01:** After "Gerar CNAB" click in ValidationReportDialog, the system generates the CNAB file, saves to DB with status "Criado", and immediately opens a native Save As dialog for the user to download the .txt file. One-click flow: generate + auto-download.
- **D-02:** Filename convention: `CNAB_YYYYMMDD_NNN.txt` where NNN is a zero-padded sequential number per day (e.g., CNAB_20260331_001.txt).
- **D-03:** Users can re-download any previously generated file from the dashboard file detail dialog at any time.

### Dashboard Layout (DASH-01, DASH-02, DASH-03)
- **D-04:** MainWindow central widget replaced with a file list table as the main dashboard. Columns: Data, Arquivo, Status, Pagamentos, Valor. "Importar Planilha" button prominent at top.
- **D-05:** Filters above the table: status dropdown (Todos, Criado, Transmitido, Erro) + date range pickers (De/Ate). Filters apply immediately on change.
- **D-06:** File detail via QDialog: click a row to open a detail dialog showing file info + table of individual payments with status. Dialog includes [Baixar .txt], [Transmitir] (when status=Criado), [Fechar] buttons.

### Mock Transmission (FILE-03, FILE-04)
- **D-07:** Transmission triggered from the file detail dialog only. "Transmitir" button visible only for files with status "Criado".
- **D-08:** Confirmation dialog before transmission: shows payment count and total value. User confirms or cancels.
- **D-09:** Mock transmitter always succeeds (status -> "Transmitido"). Error flow tested manually in dev. Real API replaces mock in v2.

### Audit Log (AUDT-01, AUDT-02)
- **D-10:** Audit log accessed via menu: Arquivo > "Log de Auditoria" opens a separate QDialog.
- **D-11:** Audit log table columns: Data/Hora, Usuario, Acao, Detalhes. Filters: action type dropdown + date range pickers.
- **D-12:** Core actions only: file generation, file download, transmission attempt (success/error), status changes. Login/logout and settings changes are NOT logged.

### Claude's Discretion
- Save As dialog default folder behavior (remember last folder, Documents fallback, etc.)
- Brief spinner/progress indicator during CNAB generation
- Exact table column widths, sort order (default: newest first)
- Success message wording and display duration
- Audit log detail text format
- File detail dialog layout and sizing
- Date picker widget choice (QDateEdit or similar)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### CNAB Engine (Phase 1 — generation pipeline)
- `src/cnab/builder.py` — `build_cnab()` function, `PaymentInput` and `CompanyConfig` dataclasses
- `src/cnab/validator.py` — `validate_payments()` function (already wired into ValidationReportDialog)

### Database Models (Phase 2 — all tables exist)
- `src/app/models.py` — `CnabFile` (status, file_content, row_count, total_value_cents, error_details, transmitted_at), `Payment` (per-row data), `AuditLog` (action, details, target_type, target_id), `Company.to_company_config()`
- `src/app/database.py` — Session management and engine setup
- `src/app/crypto.py` — Fernet decryption for VTEX credentials

### UI Layer (Phases 2-3 — established patterns)
- `src/ui/main_window.py` — Current shell with placeholder central widget, `_open_import()` already stores `valid_payments` for Phase 4 integration
- `src/ui/validation_report_dialog.py` — "Gerar CNAB" button and `valid_payments()` method — Phase 4 wires the generation pipeline here
- `src/ui/import_preview_dialog.py` — Import flow that feeds into validation report
- `src/ui/settings_window.py` — QDialog pattern reference (tabs, forms, session param)
- `src/ui/login_dialog.py` — Dialog pattern reference
- `src/ui/styles.py` — Shared stylesheet constants

### External Documentation
- `Documents/sispag_cnab.md` — CNAB 240 SISPAG Itau v085 spec
- `Documents/Vtex API Info.txt` — VTEX API reference

### Stack
- `CLAUDE.md` — Technology stack (PySide6, SQLAlchemy 2.0, openpyxl, httpx)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MainWindow._open_import()` already calls `ImportPreviewDialog`, gets `valid_payments()` on accept — Phase 4 chains CNAB generation after this
- `Company.to_company_config()` converts DB model to `CompanyConfig` dataclass for `build_cnab()`
- `CnabFile` model has `file_content` (LargeBinary) for storing raw CNAB bytes and `total_value_cents` (Integer) for value storage
- `AuditLog` model ready with `action`, `details`, `target_type`, `target_id` fields
- `Payment` model maps 1:1 to `PaymentInput` fields with `value_cents` integer storage
- `src/ui/styles.py` stylesheet constants for consistent UI

### Established Patterns
- Screen-as-QDialog: all screens receive `session` as constructor param (Phase 2 pattern)
- SQLAlchemy 2.0 `Mapped[T]` + `mapped_column()` for all models
- Dataclass-based data contracts (`PaymentInput`, `CompanyConfig`)
- Import flow: QFileDialog for file selection, QThread for background work (Phase 3 pattern)

### Integration Points
- `ValidationReportDialog` "Gerar CNAB" button → needs to trigger generation pipeline (currently no-op)
- `MainWindow._build_central_widget()` → replace placeholder with dashboard table
- `MainWindow._build_menu()` → add "Log de Auditoria" menu action
- `CnabFile.payments` relationship → file detail dialog loads payments via relationship

</code_context>

<specifics>
## Specific Ideas

- File detail dialog shows [Baixar .txt] [Transmitir] [Fechar] buttons as shown in the mockup
- Dashboard table is the first thing users see after login — must be fast and clear
- Audit log dialog accessible from Arquivo menu, not cluttering the main dashboard

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-desktop-application*
*Context gathered: 2026-03-31*
