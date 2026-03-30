# Phase 3: Data Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-30
**Phase:** 03-data-pipeline
**Areas discussed:** Excel format & validation, VTEX enrichment flow, Validation report UX, Import preview screen

---

## Excel Format & Validation

| Option | Description | Selected |
|--------|-------------|----------|
| Exact match | Columns must be exactly 'Nome do Beneficiário', 'Código', 'Valor'. Clear error if different. | ✓ |
| Case-insensitive match | Accept 'CODIGO', 'codigo', 'Código' etc. More forgiving. | |
| Positional (column A/B/C) | Ignore header names, use column position. | |

**User's choice:** Exact match
**Notes:** Simple, no ambiguity.

| Option | Description | Selected |
|--------|-------------|----------|
| Always row 1 | First row is always the header. | ✓ |
| Auto-detect | Scan first 5 rows looking for column names. | |

**User's choice:** Always row 1

| Option | Description | Selected |
|--------|-------------|----------|
| Number cell (1500.50) | Excel stores as numeric type. | |
| Text with comma (R$ 1.500,50) | Brazilian currency format as text. Needs string parsing. | ✓ |
| Support both | Try numeric first, fall back to text parsing. | |

**User's choice:** Text with comma (R$ 1.500,50)
**Notes:** Team's Excel files use Brazilian currency text format.

| Option | Description | Selected |
|--------|-------------|----------|
| Skip silently | Ignore blank rows, only process rows with data. | ✓ |
| Treat as error | Any blank row triggers a warning. | |

**User's choice:** Skip silently

---

## VTEX Enrichment Flow

| Option | Description | Selected |
|--------|-------------|----------|
| Sequential with delay | One request at a time with 200-500ms delay. | ✓ |
| Parallel with limit | Up to 3-5 concurrent requests. | |
| Batch query | Single VTEX query returning multiple results. | |

**User's choice:** Sequential with delay

| Option | Description | Selected |
|--------|-------------|----------|
| Mark row as error, continue | Row gets error, other rows proceed normally. | ✓ |
| Mark and offer retry | Same plus 'Retry failed rows' button. | |
| Stop entire batch | Halt all processing on first failure. | |

**User's choice:** Mark row as error, continue

| Option | Description | Selected |
|--------|-------------|----------|
| Small (10-50 rows) | Quick processing. | |
| Medium (50-200 rows) | Needs progress indicator. | ✓ |
| Large (200+ rows) | May need parallel strategy. | |

**User's choice:** Medium (50-200 rows)

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, with partial results | Cancel stops remaining, keeps enriched rows. | |
| Yes, discard all | Cancel discards everything. Clean slate. | ✓ |
| No cancel needed | Batches small enough. | |

**User's choice:** Yes, discard all

---

## Validation Report UX

| Option | Description | Selected |
|--------|-------------|----------|
| Summary + error table | Top: summary bar. Below: only error rows. | ✓ |
| Full table with status column | ALL rows with status column. | |
| Two separate tables | One for ready, one for errors. | |

**User's choice:** Summary + error table

| Option | Description | Selected |
|--------|-------------|----------|
| Proceed / Cancel only | 'Gerar CNAB' and 'Cancelar'. Simple. | ✓ |
| Proceed / Remove errors / Cancel | Add button to remove error rows. | |
| Proceed / Export report / Cancel | Add export-to-Excel of report. | |

**User's choice:** Proceed / Cancel only

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, if at least 1 valid row | Generate with valid rows only. | ✓ |
| No, all or nothing | Must fix all errors first. | |

**User's choice:** Yes, if at least 1 valid row

---

## Import Preview Screen

| Option | Description | Selected |
|--------|-------------|----------|
| Stats + sample rows | Filename, row count, total value, first 5-10 rows. | ✓ |
| Stats only | Filename, row count, total value. No row preview. | |
| Full table | Show all rows from Excel. | |

**User's choice:** Stats + sample rows

| Option | Description | Selected |
|--------|-------------|----------|
| Button opens file dialog | 'Importar Planilha' opens native QFileDialog. | ✓ |
| Drag and drop | Drop zone area. | |
| Both | Drag-and-drop + Browse button. | |

**User's choice:** Button opens file dialog

| Option | Description | Selected |
|--------|-------------|----------|
| Consultar VTEX | Clear action about API calls. | |
| Continuar | Generic 'Continue' button. | ✓ |
| Enriquecer Dados | Descriptive of enrichment. | |

**User's choice:** Continuar

---

## Claude's Discretion

- VTEX API timeout value and retry policy
- Exact delay between sequential VTEX calls (200-500ms range)
- Progress indicator style (bar vs text counter)
- Number of sample rows in preview (5-10)
- Error message wording
- Internal data structures for enrichment results
- QThread vs QRunnable for background VTEX calls

## Deferred Ideas

None — discussion stayed within phase scope.
