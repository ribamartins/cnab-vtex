# Phase 3: Data Pipeline - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers the data intake pipeline: Excel file import with structure validation, VTEX MasterData API enrichment (retrieving beneficiary PIX data per row), and a consolidated validation report with per-row error detail. The user can review results and decide to proceed with valid rows or abort. No CNAB file generation — that's Phase 4. No dashboard or audit — that's Phase 4.

</domain>

<decisions>
## Implementation Decisions

### Excel Format & Validation (IMPT-01, IMPT-02)
- **D-01:** Column names must match exactly: "Nome do Beneficiário", "Código", "Valor". Case-sensitive, no fuzzy matching. Clear error naming the missing/wrong column.
- **D-02:** Header row is always row 1. No auto-detection of header position.
- **D-03:** "Valor" column is text in Brazilian currency format (e.g., "R$ 1.500,50"). Parser must strip "R$", replace "." (thousands) and "," (decimal) to produce Decimal. Never float.
- **D-04:** Blank/empty rows in the middle of the spreadsheet are silently skipped. Only rows with data are processed.

### Import Preview Screen (IMPT-03)
- **D-05:** After file selection, show: filename, row count, total value (R$), and first 5-10 rows as a preview table. User confirms before any VTEX call.
- **D-06:** File selection via "Importar Planilha" button that opens native QFileDialog. No drag-and-drop.
- **D-07:** Next step button labeled "Continuar" (not "Consultar VTEX" or "Enriquecer Dados").

### VTEX Enrichment Flow (VTEX-01, VTEX-02)
- **D-08:** Sequential API calls with 200-500ms delay between requests. No parallel/concurrent calls. Simple progress tracking.
- **D-09:** When VTEX returns no results for a referenceId, mark the row as error ("Não encontrado na VTEX") and continue processing remaining rows.
- **D-10:** Typical batch size is 50-200 rows. Progress indicator required (progress bar or row counter).
- **D-11:** Cancel button discards ALL results (enriched + pending). Clean slate, user starts over.
- **D-12:** VTEX credentials retrieved from Company model (encrypted columns, decrypted via Fernet — established in Phase 2 D-03/D-04).

### Validation Report UX (VTEX-03, VALD-01 through VALD-04)
- **D-13:** Summary bar at top: X rows ready, Y rows with errors, Z total rows, R$ total value of valid rows. Below: table showing ONLY error rows with error reason per row.
- **D-14:** Two buttons only: "Gerar CNAB" (enabled when at least 1 valid row) and "Cancelar".
- **D-15:** User can proceed with partial data — valid rows generate CNAB, error rows are excluded. Clear message showing excluded count.
- **D-16:** Validation uses existing `validate_payments()` from `src/cnab/validator.py` plus VTEX-specific errors (not found, timeout, missing pixKey). Combined into one consolidated report.

### Claude's Discretion
- VTEX API timeout value and retry policy (if any)
- Exact delay between sequential VTEX calls (200-500ms range)
- Progress bar vs text counter for enrichment progress
- Number of sample rows in preview (5-10 range)
- Error message wording and formatting in validation report
- Internal data structures for holding enrichment results before validation
- Whether to use QThread or QRunnable for background VTEX calls

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### CNAB Engine (Phase 1 — data contracts)
- `src/cnab/builder.py` — `PaymentInput` dataclass (target shape for enriched data) and `CompanyConfig` dataclass
- `src/cnab/validator.py` — `validate_payments()` function and `ValidationError` dataclass (reuse for validation report)
- `src/cnab/pix_key.py` — `detect_pix_key_type()` function (maps raw pixKey to SISPAG code)

### Database Models (Phase 2 — data layer)
- `src/app/models.py` — `Company` model (VTEX credentials in encrypted columns), `Payment` model, `CnabFile` model
- `src/app/crypto.py` — Fernet encryption/decryption for VTEX credentials
- `src/app/database.py` — Session management and engine setup

### UI Patterns (Phase 2 — established patterns)
- `src/ui/settings_window.py` — QDialog pattern, tab layout, form fields (reference for new screens)
- `src/ui/styles.py` — Shared stylesheet constants
- `src/ui/login_dialog.py` — Dialog pattern with session parameter

### External Documentation
- `Documents/Vtex API Info.txt` — VTEX MasterData API endpoint, auth headers, response schema
- `Documents/sispag_cnab.md` — CNAB 240 SISPAG Itau v085 spec

### Stack
- `CLAUDE.md` — Technology stack (openpyxl for Excel, httpx for HTTP, PySide6 for UI)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/cnab/validator.py:validate_payments()` — Takes `list[PaymentInput]`, returns `list[ValidationError]` with per-row errors. Reuse directly after VTEX enrichment maps data to PaymentInput objects.
- `src/cnab/pix_key.py:detect_pix_key_type()` — Classifies raw pixKey strings. Use during VTEX-to-PaymentInput mapping.
- `src/cnab/pix_key.py:validate_cpf()` / `validate_cnpj()` — Already used by validator. No duplication needed.
- `src/app/crypto.py` — Fernet encrypt/decrypt functions for retrieving stored VTEX credentials.
- `src/ui/styles.py` — Shared Qt stylesheet for consistent UI appearance.

### Established Patterns
- Screen-as-QDialog: all screens receive `session` as constructor param (Phase 2 pattern)
- SQLAlchemy 2.0 `Mapped[T]` + `mapped_column()` for all models
- Dataclass-based data contracts (PaymentInput, CompanyConfig) — enrichment service should produce PaymentInput objects

### Integration Points
- New import/enrichment screens connect to MainWindow (src/ui/main_window.py)
- VTEX credentials read from Company model via session query + crypto decrypt
- Enriched data maps to PaymentInput for validation, then to Payment model for DB storage (Phase 4)
- Excel parser is a new pure-Python module (no UI dependency) — testable independently

</code_context>

<specifics>
## Specific Ideas

- Valor parsing must handle "R$ 1.500,50" text format → Decimal("1500.50"). Strip currency symbol, replace dots, replace comma with dot.
- VTEX API endpoint: `GET /api/dataentities/VV/search?_fields=_all&_where=referenceId={id}` with headers X-VTEX-API-AppKey and X-VTEX-API-AppToken.
- VTEX response fields needed: `pixKey`, `document`, `firstName`, `lastName`, `email`, `homePhone` — map to PaymentInput fields.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-data-pipeline*
*Context gathered: 2026-03-30*
