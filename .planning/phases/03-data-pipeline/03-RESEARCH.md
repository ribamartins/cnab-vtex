# Phase 3: Data Pipeline - Research

**Researched:** 2026-03-30
**Domain:** Excel parsing (openpyxl), VTEX MasterData API (httpx), PySide6 background threading, validation report UI
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Excel Format & Validation (IMPT-01, IMPT-02)**
- D-01: Column names must match exactly: "Nome do Beneficiario", "Codigo", "Valor". Case-sensitive, no fuzzy matching. Clear error naming the missing/wrong column.
- D-02: Header row is always row 1. No auto-detection of header position.
- D-03: "Valor" column is text in Brazilian currency format (e.g., "R$ 1.500,50"). Parser must strip "R$", replace "." (thousands) and "," (decimal) to produce Decimal. Never float.
- D-04: Blank/empty rows in the middle of the spreadsheet are silently skipped. Only rows with data are processed.

**Import Preview Screen (IMPT-03)**
- D-05: After file selection, show: filename, row count, total value (R$), and first 5-10 rows as a preview table. User confirms before any VTEX call.
- D-06: File selection via "Importar Planilha" button that opens native QFileDialog. No drag-and-drop.
- D-07: Next step button labeled "Continuar" (not "Consultar VTEX" or "Enriquecer Dados").

**VTEX Enrichment Flow (VTEX-01, VTEX-02)**
- D-08: Sequential API calls with 200-500ms delay between requests. No parallel/concurrent calls. Simple progress tracking.
- D-09: When VTEX returns no results for a referenceId, mark the row as error ("Nao encontrado na VTEX") and continue processing remaining rows.
- D-10: Typical batch size is 50-200 rows. Progress indicator required (progress bar or row counter).
- D-11: Cancel button discards ALL results (enriched + pending). Clean slate, user starts over.
- D-12: VTEX credentials retrieved from Company model (encrypted columns, decrypted via Fernet — established in Phase 2 D-03/D-04).

**Validation Report UX (VTEX-03, VALD-01 through VALD-04)**
- D-13: Summary bar at top: X rows ready, Y rows with errors, Z total rows, R$ total value of valid rows. Below: table showing ONLY error rows with error reason per row.
- D-14: Two buttons only: "Gerar CNAB" (enabled when at least 1 valid row) and "Cancelar".
- D-15: User can proceed with partial data — valid rows generate CNAB, error rows are excluded. Clear message showing excluded count.
- D-16: Validation uses existing `validate_payments()` from `src/cnab/validator.py` plus VTEX-specific errors (not found, timeout, missing pixKey). Combined into one consolidated report.

### Claude's Discretion
- VTEX API timeout value and retry policy (if any)
- Exact delay between sequential VTEX calls (200-500ms range)
- Progress bar vs text counter for enrichment progress
- Number of sample rows in preview (5-10 range)
- Error message wording and formatting in validation report
- Internal data structures for holding enrichment results before validation
- Whether to use QThread or QRunnable for background VTEX calls

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| IMPT-01 | User can import Excel file (.xlsx) with columns: Nome do Beneficiario, Codigo (referenceId), Valor | openpyxl row iteration, column name matching, QFileDialog integration |
| IMPT-02 | System validates Excel structure before processing (required columns, data types) | Column presence check before first API call; Valor currency string parsing with Decimal |
| IMPT-03 | System displays import preview with row count and total value before proceeding | QDialog with QTableWidget preview (5-10 rows), QLabel summary, "Continuar" button |
| VTEX-01 | System queries VTEX MasterData API for each referenceId and retrieves beneficiary data (pixKey, document, name, email, phone) | httpx GET /api/dataentities/VV/search, sequential with throttle, response field mapping to PaymentInput |
| VTEX-02 | System handles VTEX API errors gracefully (timeout, not found, rate limit) with per-row error reporting | httpx timeout config, HTTPStatusError, empty result list = not found; QThread for background run |
| VTEX-03 | System displays enrichment results with success/failure status per row before CNAB generation | ValidationReportDialog with summary bar, error-rows-only table, "Gerar CNAB" / "Cancelar" buttons |
</phase_requirements>

---

## Summary

Phase 3 adds the data intake pipeline for the CNAB PIX system: Excel import, VTEX MasterData enrichment, and a consolidated validation report. All three constituent libraries are already pinned in `requirements.txt` — openpyxl 3.1.5 for Excel, httpx 0.27.0 for VTEX calls, and PySide6 6.10.1 for UI. No new dependencies are needed.

The phase is well-scoped. The Excel parser is a pure-Python module with no UI dependency — it is independently testable. The VTEX enrichment service runs sequentially (by decision D-08), making QThread the appropriate threading primitive: a single worker thread runs the loop, emits signals per row for live progress, and the main thread updates the UI. QRunnable is unnecessary (it is a fire-and-forget primitive without per-row signal support that QThread provides natively).

The critical integration point is the `PaymentInput` dataclass from Phase 1 (`src/cnab/builder.py`). After VTEX enrichment maps VTEX response fields to PaymentInput objects, the existing `validate_payments()` from Phase 1 runs directly on the result list. VTEX-specific errors (not found, timeout, missing pixKey) are represented as additional entries using the existing `ValidationError` dataclass — no new error type is needed.

**Primary recommendation:** Build the Excel parser as a pure module first (no Qt dependency), test it in isolation, then build the two UI dialogs (ImportPreviewDialog, ValidationReportDialog) against the established QDialog + session constructor pattern from Phase 2.

---

## Project Constraints (from CLAUDE.md)

All directives from CLAUDE.md that constrain this phase:

- Stack: Python + PySide6 (Qt) — no Flask, no web, no SPA
- Excel: openpyxl — not pandas
- HTTP: httpx — not requests
- Decimal arithmetic for all payment values — never float
- SQLite local DB; SQLAlchemy 2.0 Mapped[T] / mapped_column() style
- Credentials in Fernet-encrypted DB columns, never hardcoded
- VTEX credentials from Company model via `src/app/crypto.py` decrypt_value()
- pathlib.Path exclusively — no os.path.join
- pytest for tests

---

## Standard Stack

### Core (already installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openpyxl | 3.1.5 | Read .xlsx files | Project constraint; no pandas overhead for row iteration |
| httpx | 0.27.0 | VTEX MasterData HTTP GET | Project constraint; sync mode sufficient; better timeout control than requests |
| PySide6 | 6.10.1 | Qt UI — QFileDialog, QDialog, QTableWidget, QThread | Project constraint; Python 3.14 requires >=6.10.1 |
| decimal (stdlib) | — | Currency arithmetic | CNAB-08: float prohibited for all payment values |
| time (stdlib) | — | Inter-request throttle (time.sleep) | Simple sequential delay, no scheduler needed |

### Supporting (already installed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| cryptography (Fernet) | 43.0.3 | Decrypt VTEX credentials | Retrieve app_key/app_token from Company model |
| SQLAlchemy | 2.0.48 | Read Company model from DB | Fetch credentials for enrichment service |
| pytest | 9.0.2 | Test runner | Excel parser and enrichment service unit tests |

### No New Dependencies

All libraries are present in `requirements.txt`. No `pip install` step is needed for this phase.

---

## Architecture Patterns

### Recommended Module Structure

```
src/
├── app/
│   └── excel_parser.py      # NEW: Pure-Python Excel parser (no Qt)
├── vtex/
│   └── enrichment.py        # NEW: VTEX enrichment service (httpx, no Qt)
└── ui/
    ├── import_preview_dialog.py   # NEW: QDialog — file select + preview
    └── validation_report_dialog.py # NEW: QDialog — enrichment results + CNAB gate
```

The `src/vtex/` subdirectory isolates the VTEX concern. Alternatively, `src/app/vtex_client.py` is acceptable if the team prefers fewer subdirectories — this is Claude's discretion.

### Pattern 1: Excel Parser Module

**What:** Pure function — accepts a file path, returns a typed result. No UI imports.
**When to use:** Called by ImportPreviewDialog after user selects a file.

```python
# src/app/excel_parser.py
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import NamedTuple

import openpyxl


REQUIRED_COLUMNS = ["Nome do Benefici\u00e1rio", "C\u00f3digo", "Valor"]


@dataclass
class ParsedRow:
    nome: str
    codigo: str
    valor: Decimal
    original_valor: str   # keep raw string for preview table display


@dataclass
class ParseResult:
    rows: list[ParsedRow]
    total_value: Decimal
    filename: str


class ExcelParseError(Exception):
    """Raised for structural problems (missing column, unparseable value)."""
    pass


def parse_excel(path: Path) -> ParseResult:
    """Parse Excel .xlsx file and return validated rows.

    Raises ExcelParseError if structure is invalid.
    Silently skips blank rows (D-04).
    """
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active

    # Row 1 is always header (D-02)
    headers = [str(cell.value).strip() if cell.value is not None else ""
               for cell in next(ws.iter_rows(min_row=1, max_row=1))]

    for col in REQUIRED_COLUMNS:
        if col not in headers:
            raise ExcelParseError(
                f"Coluna obrigat\u00f3ria ausente: '{col}'"
            )

    col_idx = {col: headers.index(col) for col in REQUIRED_COLUMNS}

    rows: list[ParsedRow] = []
    for excel_row in ws.iter_rows(min_row=2, values_only=True):
        nome_val = excel_row[col_idx["Nome do Benefici\u00e1rio"]]
        cod_val = excel_row[col_idx["C\u00f3digo"]]
        val_val = excel_row[col_idx["Valor"]]

        # D-04: skip fully blank rows
        if nome_val is None and cod_val is None and val_val is None:
            continue

        nome = str(nome_val).strip() if nome_val is not None else ""
        codigo = str(cod_val).strip() if cod_val is not None else ""
        original_valor = str(val_val).strip() if val_val is not None else ""
        valor = _parse_valor(original_valor)

        rows.append(ParsedRow(
            nome=nome, codigo=codigo, valor=valor,
            original_valor=original_valor
        ))

    wb.close()
    total = sum((r.valor for r in rows), Decimal("0"))
    return ParseResult(rows=rows, total_value=total, filename=path.name)


def _parse_valor(raw: str) -> Decimal:
    """Convert Brazilian currency string to Decimal (D-03).

    "R$ 1.500,50" -> Decimal("1500.50")
    Raises ExcelParseError if not parseable.
    """
    cleaned = raw.replace("R$", "").strip()
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        raise ExcelParseError(
            f"Valor inv\u00e1lido: '{raw}' (esperado formato 'R$ 1.500,50')"
        )
```

### Pattern 2: VTEX Enrichment Service

**What:** Stateless function that takes a list of ParsedRows and credentials, returns enriched PaymentInput list plus per-row error map.
**When to use:** Called from QThread worker after user confirms import preview.

```python
# src/vtex/enrichment.py
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Optional

import httpx

from cnab.builder import PaymentInput
from cnab.pix_key import detect_pix_key_type


VTEX_BASE_URL = "https://prettynew.myvtex.com"
VTEX_SEARCH_PATH = "/api/dataentities/VV/search"
REQUEST_TIMEOUT = 10.0          # seconds (Claude's discretion)
THROTTLE_DELAY = 0.3            # 300ms between calls (Claude's discretion, within 200-500ms)


@dataclass
class EnrichmentResult:
    """Outcome for a single row after VTEX lookup."""
    row_index: int
    reference_id: str
    payment: Optional[PaymentInput]   # None if error
    error: Optional[str]              # Error message if payment is None


def enrich_payments(
    rows,          # list[ParsedRow]
    app_key: str,
    app_token: str,
    on_progress: Optional[Callable[[int, int], None]] = None,
    cancel_flag=None,   # threading.Event or similar
) -> list[EnrichmentResult]:
    """Query VTEX MasterData for each row, return EnrichmentResult per row.

    Sequential calls with THROTTLE_DELAY between requests (D-08).
    on_progress(current, total) called after each row.
    cancel_flag.is_set() checked before each call (D-11).
    """
    headers = {
        "X-VTEX-API-AppKey": app_key,
        "X-VTEX-API-AppToken": app_token,
        "Accept": "application/json",
    }
    results: list[EnrichmentResult] = []
    total = len(rows)

    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        for idx, row in enumerate(rows):
            if cancel_flag and cancel_flag.is_set():
                break

            result = _fetch_one(client, headers, idx, row)
            results.append(result)

            if on_progress:
                on_progress(idx + 1, total)

            if idx < total - 1:
                time.sleep(THROTTLE_DELAY)

    return results


def _fetch_one(client, headers, idx, row) -> EnrichmentResult:
    ref_id = row.codigo
    try:
        resp = client.get(
            VTEX_BASE_URL + VTEX_SEARCH_PATH,
            params={"_fields": "_all", "_where": f"referenceId={ref_id}"},
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

        if not data:
            return EnrichmentResult(
                row_index=idx, reference_id=ref_id,
                payment=None,
                error="N\u00e3o encontrado na VTEX"   # D-09
            )

        record = data[0]
        return _map_to_payment(idx, ref_id, record, row.valor)

    except httpx.TimeoutException:
        return EnrichmentResult(
            row_index=idx, reference_id=ref_id,
            payment=None, error="Timeout ao consultar VTEX"
        )
    except httpx.HTTPStatusError as exc:
        return EnrichmentResult(
            row_index=idx, reference_id=ref_id,
            payment=None,
            error=f"Erro HTTP {exc.response.status_code}"
        )
    except Exception as exc:
        return EnrichmentResult(
            row_index=idx, reference_id=ref_id,
            payment=None, error=f"Erro inesperado: {exc}"
        )


def _map_to_payment(idx, ref_id, record, valor) -> EnrichmentResult:
    pix_key = record.get("pixKey") or ""
    if not pix_key:
        return EnrichmentResult(
            row_index=idx, reference_id=ref_id,
            payment=None, error="pixKey ausente no registro VTEX"
        )

    try:
        pix_key_type = detect_pix_key_type(pix_key)
    except ValueError:
        return EnrichmentResult(
            row_index=idx, reference_id=ref_id,
            payment=None,
            error=f"Tipo de chave PIX n\u00e3o detectado: {pix_key!r}"
        )

    first = record.get("firstName") or ""
    last = record.get("lastName") or ""
    name = f"{first} {last}".strip() or record.get("receiverName") or ""
    document = record.get("document") or record.get("cpf") or ""

    payment = PaymentInput(
        name=name,
        document=document,
        pix_key=pix_key,
        pix_key_type=pix_key_type,
        value=valor,
        reference_id=ref_id,
    )
    return EnrichmentResult(
        row_index=idx, reference_id=ref_id,
        payment=payment, error=None
    )
```

### Pattern 3: QThread Worker for Enrichment

**What:** Thin QThread subclass that calls `enrich_payments()` and emits Qt signals for live progress updates. Runs enrichment off the main thread so the UI stays responsive.
**When to use:** ImportPreviewDialog starts this thread when user clicks "Continuar".

```python
# Inside import_preview_dialog.py or a dedicated worker module
import threading
from PySide6.QtCore import QThread, Signal

from vtex.enrichment import enrich_payments


class EnrichmentWorker(QThread):
    progress = Signal(int, int)           # current, total
    finished = Signal(list)               # list[EnrichmentResult]

    def __init__(self, rows, app_key, app_token, parent=None):
        super().__init__(parent)
        self._rows = rows
        self._app_key = app_key
        self._app_token = app_token
        self._cancel = threading.Event()

    def cancel(self):
        """Signal cancellation (D-11). Thread checks flag before each row."""
        self._cancel.set()

    def run(self):
        results = enrich_payments(
            self._rows, self._app_key, self._app_token,
            on_progress=lambda cur, tot: self.progress.emit(cur, tot),
            cancel_flag=self._cancel,
        )
        self.finished.emit(results)
```

**Why QThread over QRunnable:** QRunnable has no built-in signal support (signals require a QObject, and QRunnable is not a QObject). QThread subclass is the idiomatic PySide6 pattern for a long-running task with progress reporting. The Qt documentation recommends "use QThread for tasks with signals/slots; use QRunnable for fire-and-forget worker pool tasks."

### Pattern 4: ImportPreviewDialog

**What:** QDialog that handles file selection, parses Excel, shows preview table and summary, then launches EnrichmentWorker.
**When to use:** Triggered from MainWindow "Importar Planilha" action (to be added to menu/central widget in Phase 3).

Key structure:
```
ImportPreviewDialog(session, current_user, parent=None)
├── _build_ui()
│   ├── "Importar Planilha" button -> QFileDialog.getOpenFileName()
│   ├── preview QLabel (filename, row count, total value)
│   ├── QTableWidget (5-10 rows preview)
│   └── "Continuar" button (disabled until file loaded)
├── _on_import_clicked() -> opens QFileDialog, calls parse_excel()
├── _on_continue_clicked() -> reads Company VTEX creds, starts EnrichmentWorker
└── _on_enrichment_done(results) -> opens ValidationReportDialog
```

### Pattern 5: ValidationReportDialog

**What:** QDialog showing consolidated validation results. Runs `validate_payments()` on enriched rows, merges VTEX errors, presents summary and error table.
**When to use:** Opened by ImportPreviewDialog after EnrichmentWorker completes.

Key structure:
```
ValidationReportDialog(results: list[EnrichmentResult], session, parent=None)
├── _build_ui()
│   ├── Summary bar QLabel: "X prontos / Y com erros / Z total / R$ valor total"
│   ├── QTableWidget — error rows only (row index, referenceId, error reason)
│   └── "Gerar CNAB" button (objectName="primary", enabled if >=1 valid row)
│       "Cancelar" button
└── _collect_valid_payments() -> list[PaymentInput] for Phase 4 handoff
```

### Validation Merge Strategy

VTEX errors and PaymentInput validation errors are combined into a single report:

```python
# 1. Separate successful enrichments from VTEX errors
vtex_errors = [r for r in results if r.payment is None]
enriched = [r.payment for r in results if r.payment is not None]

# 2. Run existing validate_payments() on successfully enriched rows
from cnab.validator import validate_payments, ValidationError
validation_errors = validate_payments(enriched)

# 3. Present unified error table (VTEX errors + validation errors)
# Valid rows = enriched rows whose index has NO ValidationError
```

### Anti-Patterns to Avoid

- **Running httpx calls on the main thread:** Blocks the Qt event loop, making the UI freeze. Always run in QThread.
- **Using float for currency:** Decimal("1500.50") not 1500.50 — CNAB-08 is non-negotiable.
- **Calling `openpyxl.load_workbook` without `read_only=True`:** Memory-wastes for read-only import; `read_only=True` streams rows without loading full workbook into memory.
- **Accessing QWidget from QThread.run():** Qt forbids GUI calls from non-main threads. Use `Signal.emit()` only, let the main thread update widgets in a slot.
- **String comparison for column headers without stripping whitespace:** Excel headers may have leading/trailing spaces. Always `.strip()` before comparison.
- **Using `os.path.join` for file paths:** Project convention is `pathlib.Path` exclusively.
- **Calling `ws.iter_rows()` after `wb.close()`:** Read all data before closing workbook.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Background threading with Qt | Custom thread wrapper | QThread subclass with Signals | QThread integrates with Qt event loop, signal/slot across threads is safe |
| Excel row iteration | Manual xlrd/xml parsing | openpyxl `iter_rows(values_only=True)` | openpyxl handles merged cells, number formats, and encoding |
| HTTP timeout / connection pooling | Manual socket code | httpx.Client context manager | httpx handles keep-alive, timeout tiers, connection pooling |
| CPF/CNPJ validation | New validator code | `cnab.pix_key.validate_cpf()` / `validate_cnpj()` | Already implemented and tested in Phase 1 |
| PIX key type detection | New regex logic | `cnab.pix_key.detect_pix_key_type()` | Already implemented, UUID-first order prevents ambiguity |
| Payment field validation | Duplicate checks | `cnab.validator.validate_payments()` | Already implements VALD-01 through VALD-04 |
| Fernet decryption | New crypto code | `app.crypto.decrypt_value()` | Already implemented in Phase 2 |

**Key insight:** Phase 1 and Phase 2 already delivered the validation and crypto infrastructure. Phase 3 is an integration layer, not a foundation layer.

---

## Common Pitfalls

### Pitfall 1: VTEX Response is a List, Not a Dict

**What goes wrong:** Code tries `response.json()["pixKey"]` and gets a `TypeError: list indices must be integers`.
**Why it happens:** VTEX MasterData /search returns a JSON array even for a single match. The real response is `[{...record...}]`.
**How to avoid:** Always do `data = resp.json(); record = data[0] if data else None`.
**Warning signs:** `TypeError` on first VTEX call in tests with mock responses.

### Pitfall 2: Empty VTEX Response vs "Not Found"

**What goes wrong:** An empty `[]` response raises an IndexError when code blindly does `data[0]`.
**Why it happens:** VTEX returns `[]` (empty list) when referenceId does not match any record — it does not return 404.
**How to avoid:** `if not data: return EnrichmentResult(..., error="Nao encontrado na VTEX")` before indexing.
**Warning signs:** IndexError in enrichment service for any referenceId that doesn't exist.

### Pitfall 3: Brazilian Decimal Parsing Edge Cases

**What goes wrong:** "1.000" is parsed as 1.0 instead of 1000. "R$50" (no spaces, no cents) raises InvalidOperation.
**Why it happens:** The replace chain `replace(".", "").replace(",", ".")` must happen after stripping "R$" and whitespace. "1.000" with no comma also needs to be handled (it is 1000, not 1.0).
**How to avoid:** Strip currency symbol and whitespace first, then apply the replace chain. Add a test case for round values like "R$ 100" (no decimal comma).
**Warning signs:** Decimal values off by factor of 1000 in test output.

### Pitfall 4: QThread Signal Emitted After Dialog Closed

**What goes wrong:** User cancels the enrichment dialog, dialog is destroyed, worker emits `finished` signal, crash or silent error.
**Why it happens:** QThread finishes asynchronously; if the parent QDialog is already closed/deleted, the slot is called on a dead object.
**How to avoid:** Call `worker.cancel()` then `worker.wait()` in the dialog's `reject()` / `closeEvent()` before returning. This blocks briefly but ensures the thread is stopped before the dialog dies.
**Warning signs:** Occasional crash or "wrapped C/C++ object has been deleted" Qt error.

### Pitfall 5: openpyxl read_only and Merged Cells

**What goes wrong:** Merged cell reads return `None` for non-anchor cells in read_only mode.
**Why it happens:** `read_only=True` does not expand merged cell values to all covered cells.
**How to avoid:** For this use case (three specific columns, row-by-row import), merged cells in the data range are user error. The parser should treat `None` in a data column as a blank value (already covered by D-04 skip logic for fully-blank rows, but partial-blank rows still need explicit handling per column).
**Warning signs:** Unexpected None values in name/codigo columns for rows that appear populated in Excel.

### Pitfall 6: VTEX Rate Limiting

**What goes wrong:** Rapid sequential requests trigger VTEX's rate limiter, returning 429 errors.
**Why it happens:** VTEX MasterData has documented rate limits (exact limits vary by plan). 200-500ms delay (D-08) is a reasonable mitigation, but the exact safe rate is not documented in the project's VTEX API Info.txt.
**How to avoid:** Use 300ms delay (recommended, within the 200-500ms window). If 429 is received, treat it as an error for that row (do not auto-retry — D-08 specifies no retry policy). Log the HTTP status code clearly.
**Warning signs:** Multiple consecutive rows with "Erro HTTP 429" in the validation report.

### Pitfall 7: VTEX document Field vs cpf Field

**What goes wrong:** Mapping code reads `record["document"]` but the field is empty; the CPF is actually in `record["cpf"]` for some records.
**Why it happens:** The VTEX response shows both `"document": "51300907134"` and `"cpf": null`. For some record types, CPF may appear in `cpf` instead of `document`.
**How to avoid:** Use fallback: `document = record.get("document") or record.get("cpf") or ""`. If still empty after fallback, validate_payments() will catch it as a ValidationError.
**Warning signs:** validation report showing document-missing errors for rows that clearly have a CPF visible in VTEX.

---

## Code Examples

### VTEX Response Field Mapping (Verified against Documents/Vtex API Info.txt)

```python
# Actual VTEX response structure (from Vtex API Info.txt — HIGH confidence)
# GET /api/dataentities/VV/search?_fields=_all&_where=referenceId=802586
# Returns: list[dict] — always a list, even for single result
{
    "firstName": "Fabio",
    "lastName": "Michels",
    "document": "51300907134",   # PRIMARY: use this for CPF/CNPJ
    "cpf": null,                  # FALLBACK: some records use this
    "pixKey": "51300907134",     # PIX key value
    "email": "fabmichels@gmail.com",
    "homePhone": "5561999810561",
    "receiverName": "fabio michels",  # FALLBACK for name if firstName/lastName empty
    "referenceId": "802586"
}
# Note: response is a JSON array: [{...}], not {...}
```

### PaymentInput Construction from VTEX Record

```python
# After _map_to_payment() — integrates with Phase 1 contracts
from cnab.builder import PaymentInput
from cnab.pix_key import detect_pix_key_type

pix_key = record.get("pixKey") or ""
pix_key_type = detect_pix_key_type(pix_key)  # raises ValueError if undetectable

first = record.get("firstName") or ""
last = record.get("lastName") or ""
name = f"{first} {last}".strip() or record.get("receiverName") or ""

payment = PaymentInput(
    name=name,
    document=record.get("document") or record.get("cpf") or "",
    pix_key=pix_key,
    pix_key_type=pix_key_type,
    value=row.valor,           # Decimal from ExcelParser — never float
    reference_id=row.codigo,
)
```

### QFileDialog Usage (PySide6)

```python
from PySide6.QtWidgets import QFileDialog
from pathlib import Path

def _on_import_clicked(self):
    path_str, _ = QFileDialog.getOpenFileName(
        self,
        "Selecionar Planilha",
        "",
        "Arquivos Excel (*.xlsx)"
    )
    if not path_str:
        return  # user cancelled
    path = Path(path_str)
    # call parse_excel(path) and update preview
```

### Reading VTEX Credentials from Company Model

```python
from app.models import Company
from app.crypto import decrypt_value

company = self._session.query(Company).first()
if company is None or not company.vtex_app_key_encrypted:
    # Show error: credentials not configured
    return

app_key = decrypt_value(company.vtex_app_key_encrypted)
app_token = decrypt_value(company.vtex_app_token_encrypted)
```

### Valor Parsing Edge Cases

```python
# D-03 compliance — all must produce correct Decimal
_parse_valor("R$ 1.500,50")  # -> Decimal("1500.50")
_parse_valor("R$ 100")        # -> Decimal("100")  -- no decimal comma
_parse_valor("R$50,00")       # -> Decimal("50.00") -- no spaces
_parse_valor("1.000,00")      # -> Decimal("1000.00") -- no currency symbol
_parse_valor("0,50")          # -> Decimal("0.50")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `QThread.run()` with manual mutex | QThread + Qt Signals/Slots for cross-thread communication | Qt 4.x → Qt 5.x | Signals emitted from worker thread are queued automatically to the main thread — no manual locking needed |
| `requests` for HTTP | `httpx` for HTTP | ~2021 | httpx has identical sync API, better timeout control, and active maintenance |
| `xlrd` for Excel | `openpyxl` for .xlsx | xlrd dropped .xlsx support in 2.0 (2020) | openpyxl is now the standard for .xlsx; xlrd only supports .xls |

**Deprecated/outdated:**
- `xlrd` for .xlsx: dropped in xlrd 2.0.0. openpyxl is the replacement.
- `QThread.exec()` / event loop in thread: not needed here — worker thread does sequential work and emits signals, no event loop required.

---

## Open Questions

1. **VTEX Rate Limit Exact Threshold**
   - What we know: D-08 specifies 200-500ms delay; 300ms is recommended
   - What's unclear: Exact rate limit (requests/minute) for the prettynew.myvtex.com account is not documented in the project files
   - Recommendation: Use 300ms delay and treat 429 as a row error (no auto-retry). If the live API reveals a stricter limit, the delay constant can be tuned without structural changes.

2. **VTEX Token Expiry**
   - What we know: VTEX API credentials (AppKey/AppToken) are stored in the Company model
   - What's unclear: Whether AppTokens expire and require rotation
   - Recommendation: Out of scope for Phase 3. If 401 is returned, surface it as an error row. Credential management is Phase 2 / Settings concern.

3. **homePhone Format in VTEX Response**
   - What we know: The sample shows `"homePhone": "5561999810561"` (digits only, country code, no +)
   - What's unclear: Whether pixKey for phone numbers appears in E.164 format (`+5561999810561`) or digits-only (`5561999810561`)
   - Recommendation: `detect_pix_key_type()` requires E.164 (`+` prefix) for phone detection. If VTEX returns digits-only, the phone key will fall through to CPF/CNPJ detection and likely fail. The sample `pixKey` is `"51300907134"` (a CPF), so this edge case may not arise often. If it does, validate_payments() will surface it as a ValidationError.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| openpyxl | Excel parsing | Yes | 3.1.5 | — |
| httpx | VTEX API calls | Yes | 0.27.0 | — |
| PySide6 | Qt UI | Yes | 6.10.1 | — |
| cryptography (Fernet) | VTEX credential decrypt | Yes | 43.0.3 | — |
| pytest | Test runner | Yes | 9.0.2 | — |
| Python | Runtime | Yes | 3.14.3 | — |

No missing dependencies. All required libraries are installed.

---

## Sources

### Primary (HIGH confidence)
- `Documents/Vtex API Info.txt` — Actual VTEX response schema, endpoint URL, field names
- `src/cnab/builder.py` — PaymentInput dataclass field names and types
- `src/cnab/validator.py` — validate_payments() signature and ValidationError dataclass
- `src/cnab/pix_key.py` — detect_pix_key_type() signature and detection rules
- `src/app/models.py` — Company model encrypted credential fields, relationship structure
- `src/app/crypto.py` — decrypt_value() function signature
- `src/ui/styles.py` — Color constants and spacing constants (COLOR_ACCENT, SPACING_MD, etc.)
- `src/ui/main_window.py` — QMainWindow session pattern for integration
- `requirements.txt` — Installed package versions (ground truth)
- `.planning/phases/03-data-pipeline/03-CONTEXT.md` — All user decisions (D-01 through D-16)

### Secondary (MEDIUM confidence)
- PySide6 QThread / Signal documentation — training knowledge, consistent with Qt 6.x patterns
- openpyxl `read_only=True` + `iter_rows(values_only=True)` — training knowledge, stable API since openpyxl 2.x
- httpx sync client usage — training knowledge, verified against installed 0.27.0

### Tertiary (LOW confidence — flag for validation if critical)
- VTEX rate limiting thresholds — not documented in project files; 300ms delay is a reasonable default
- homePhone / pixKey phone format edge case — single sample data point, not a full dataset

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and pinned in requirements.txt
- Architecture: HIGH — patterns derived from existing Phase 1/2 code and Qt documentation
- VTEX API mapping: HIGH — actual response schema in Documents/Vtex API Info.txt
- Pitfalls: HIGH for structural pitfalls (list vs dict, empty list); MEDIUM for rate limiting (no documented threshold)

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (openpyxl/httpx/PySide6 APIs are stable; VTEX MasterData endpoint is project-specific and unlikely to change)
