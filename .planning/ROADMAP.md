# Roadmap: CNAB PIX Payment System

## Overview

A four-phase journey that builds the riskiest parts first. Phase 1 hardens the CNAB engine as pure, tested Python — no UI, no database, no network calls — because a single wrong byte causes the bank to reject the entire batch. Phase 2 lays the foundation: SQLite schema, authentication, and settings (company CNPJ/agency/account/DAC that every CNAB header requires). Phase 3 wires up the data intake pipeline: Excel import, VTEX enrichment, and per-row validation. Phase 4 assembles the desktop application in PySide6, connecting all working services through a thin GUI layer, and delivers the dashboard, audit log, and file management the finance team operates day-to-day.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: CNAB Engine** - Pure CNAB 240 byte-exact generation and validation library — no UI, no database
- [x] **Phase 2: Foundation** - SQLite schema, authentication, and settings screen — prerequisites for file generation (completed 2026-03-30)
- [x] **Phase 3: Data Pipeline** - Excel import, VTEX enrichment, and pre-generation validation with per-row error reporting (completed 2026-03-31)
- [ ] **Phase 4: Desktop Application** - PySide6 GUI connecting all services: login, upload flow, file management, dashboard, and audit log

## Phase Details

### Phase 1: CNAB Engine
**Goal**: A tested, byte-exact CNAB 240 generator and validator exists as pure Python with no external dependencies
**Depends on**: Nothing (first phase)
**Requirements**: CNAB-01, CNAB-02, CNAB-03, CNAB-04, CNAB-05, CNAB-06, CNAB-07, CNAB-08, VALD-01, VALD-02, VALD-03, VALD-04
**Success Criteria** (what must be TRUE):
  1. Given a list of Python payment objects and company config, the builder returns a bytes object where every record is exactly 240 bytes encoded in LATIN-1 (assert passes for all six record types: Header Arquivo, Header Lote, Segmento A, Segmento B PIX, Trailer Lote, Trailer Arquivo)
  2. A payment value of R$ 150,00 is encoded as `000000000015000` (Decimal arithmetic, no float noise) and verified by unit test with known-good byte sequence
  3. PIX key type detector correctly classifies all four types (CPF/CNPJ → 03, phone → 01, email → 02, UUID → 04) from raw VTEX pixKey strings with no human input
  4. Validator returns per-row errors for missing pixKey, missing document, zero value, and invalid CPF/CNPJ check digits before any CNAB generation is attempted
  5. A pytest run with known-good inputs asserts exact byte sequences for Segmento A + Segmento B pairs, and Trailer counts match 2N+2 formula for N payments
**Plans**: 2 plans

Plans:
- [x] 01-01: CNAB 240 builder — all six record types, 240-byte enforcement, LATIN-1 encoding
- [x] 01-02: PIX key detector and pre-generation validator with unit test suite

### Phase 2: Foundation
**Goal**: Users can authenticate into the application and admins can configure the company data required by every CNAB header
**Depends on**: Phase 1
**Requirements**: AUTH-01, AUTH-02, AUTH-03, CONF-01, CONF-02, CONF-03
**Success Criteria** (what must be TRUE):
  1. A user can log in with username and password; incorrect credentials are rejected with a clear message
  2. An admin can create, edit, and deactivate user accounts without editing any file or database directly
  3. The application remembers the logged-in user across restarts (session persistence)
  4. An admin can enter and save company CNPJ, agency, account, DAC, VTEX AppKey, and AppToken; the values survive application restart and are never stored in plaintext source code
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Database models (5 tables), Alembic baseline, Fernet encryption, auth service with user CRUD
- [x] 02-02-PLAN.md — PySide6 login dialog, first-run setup wizard, settings window (company/users/credentials tabs)

### Phase 3: Data Pipeline
**Goal**: Users can import an Excel file, retrieve beneficiary PIX data from VTEX, and see a clear per-row validation report before deciding whether to generate a CNAB file
**Depends on**: Phase 2
**Requirements**: IMPT-01, IMPT-02, IMPT-03, VTEX-01, VTEX-02, VTEX-03
**Success Criteria** (what must be TRUE):
  1. User can select an Excel file; the system validates its structure (required columns, data types) and shows a preview with row count and total value before any API call is made
  2. After import preview is accepted, the system queries VTEX MasterData for each referenceId and displays enrichment results showing success or failure per row (not found, timeout, missing pixKey)
  3. A consolidated validation report shows all rows with errors (missing field, invalid CPF/CNPJ, undetectable key type) and all rows that are ready, allowing the user to decide whether to proceed or abort
  4. An Excel file with invalid structure (missing required column) is rejected before VTEX queries begin, with a human-readable error naming the missing column
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — Excel parser module (openpyxl) and VTEX enrichment service (httpx) with test suites
- [x] 03-02-PLAN.md — ImportPreviewDialog, ValidationReportDialog, and MainWindow integration

### Phase 4: Desktop Application
**Goal**: The finance team can operate the full payment workflow end-to-end from a desktop application: import, generate, download, track, and audit CNAB files
**Depends on**: Phase 3
**Requirements**: FILE-01, FILE-02, FILE-03, FILE-04, DASH-01, DASH-02, DASH-03, AUDT-01, AUDT-02
**Success Criteria** (what must be TRUE):
  1. After validation passes, user can generate a CNAB file; the file is saved to the database with status "Criado" and the user can immediately download it as a .txt file for manual upload to Itau Empresas
  2. User can trigger mock transmission; status moves to "Transmitido" on success or "Erro" on failure, with error details saved and visible in the file record
  3. Dashboard shows all generated CNAB files with status, date, total value, and row count; user can filter by status and date range without writing any query
  4. User can drill into any file record and see individual payment rows with their status
  5. Audit log captures every significant action (generation, transmission attempt, status change) with actor and timestamp; user can view and filter the log by date and action type
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md — CNAB generation service, dashboard table with filters, generation pipeline wiring from ValidationReportDialog
- [ ] 04-02-PLAN.md — File detail dialog (download + mock transmission), transmission confirmation, and audit log viewer
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. CNAB Engine | 2/2 | Complete |  |
| 2. Foundation | 2/2 | Complete   | 2026-03-30 |
| 3. Data Pipeline | 2/2 | Complete   | 2026-03-31 |
| 4. Desktop Application | 1/2 | In Progress|  |
