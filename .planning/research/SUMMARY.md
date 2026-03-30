# Project Research Summary

**Project:** CNAB PIX Payment File Generation — PrettyNew / Itaú SISPAG
**Domain:** Brazilian banking payment file generation, VTEX enrichment, Itaú SISPAG transmission
**Researched:** 2026-03-30
**Confidence:** HIGH

> **Stack change note:** Research was conducted assuming a Flask web application. The project has since been updated to a **desktop standalone application using Python + PySide6 (Qt6) + SQLite**. All findings related to CNAB generation, VTEX API integration, PIX key handling, byte encoding, and Itaú transmission remain fully valid. References to Flask, Jinja2, Flask-Login, Gunicorn, and web routing in the original research files should be replaced with PySide6 equivalents. This SUMMARY reflects the corrected desktop architecture.

---

## Executive Summary

This project is a desktop tool for a small finance team (1–5 people) that takes an Excel spreadsheet of beneficiaries, enriches each row with PIX key data from VTEX MasterData, generates a spec-compliant CNAB 240 remessa file targeting Itaú SISPAG v085, and transmits it to the bank. The domain is narrow but precise: the SISPAG specification is tightly controlled by Itaú and has zero tolerance for deviation — every record must be exactly 240 bytes, encoded in LATIN-1, with specific field positions holding hard-coded constants (câmara 009 for PIX, forma de pagamento 45, layout version 080). Expert implementation treats CNAB generation as a pure, isolated, exhaustively-tested function that receives Python domain objects and returns bytes.

The recommended approach is a layered pipeline: Excel Parser → VTEX Enrichment → PIX Key Detector → Validator → CNAB 240 Builder → File Store → Bank Transmitter → Status Tracker → Return Processor. Each layer has one responsibility and communicates only through explicit inputs and outputs. The desktop GUI (PySide6) is a thin layer on top of these service components; the same service classes would work equally in a CLI or web context. SQLite is the correct database choice — a 1–5 user single-machine tool will never stress it, and it requires no infrastructure. Bank transmission should be implemented behind a pluggable interface from day one, with a mock transmitter in place until Itaú credentials are confirmed.

The dominant risks are all in Phase 1: a 1-byte error in any CNAB record causes the bank to reject the entire batch with no partial processing. The five highest-risk failure modes are: (1) records not exactly 240 bytes, (2) UTF-8 instead of LATIN-1 encoding with accented names, (3) missing or incorrectly structured Segmento B PIX (mandatory for PIX via chave, though the summary table misleadingly calls it optional), (4) wrong implicit decimal encoding for payment values (Picture V format), and (5) wrong PIX key type code in Segmento B. All five must be resolved with unit tests asserting exact byte sequences before any integration work begins.

---

## Key Findings

### Recommended Stack

The original research recommended Flask + Jinja2, which has been superseded by PySide6 (Qt6). The core data and logic stack is unchanged. Python 3.12 is the runtime. SQLite via SQLAlchemy 2.x (with the modern `Mapped[T]` API) is the persistence layer; Alembic handles migrations even for SQLite so schema changes are manageable. openpyxl 3.x reads Excel uploads without pandas overhead. httpx handles VTEX and Itaú HTTP calls with better timeout semantics than requests. All CNAB byte work is done with Python stdlib (`str.ljust`, `str.zfill`, `codecs`/`.encode('latin-1')`) — no third-party CNAB library should be trusted because community libraries target generic FEBRABAN while Itaú SISPAG v085 has bank-specific layout deviations.

**Core technologies:**
- Python 3.12: Runtime — best performance and typing support in current stable line
- PySide6 (Qt6): Desktop GUI — replaces Flask; signals/slots drive the same pipeline components
- SQLite + SQLAlchemy 2.x: Persistence — zero-ops, file-portable, swap to PostgreSQL by changing one connection string
- Alembic: Migrations — start from day one even for SQLite to avoid painful manual schema updates
- openpyxl 3.x: Excel import — lightweight, no pandas dependency for a 3-column row iterator
- httpx 0.27.x: HTTP client — VTEX enrichment and Itaú transmission; sync mode is sufficient
- python-dotenv: Secrets — VTEX_APP_KEY, VTEX_APP_TOKEN, future Itaú credentials never in code
- pytest 8.x: Testing — critical for CNAB byte-level unit tests

**Version note:** All version numbers in STACK.md are from training knowledge (cutoff August 2025) and must be verified with `pip index versions <package>` before pinning in requirements.txt.

### Expected Features

The MVP is a tightly scoped, internally consistent set of 12 features. The feature dependency chain is strict: settings (company CNPJ/agency/account) must exist before any file can be generated; authentication gates everything; Excel upload flows through VTEX enrichment → PIX detection → validation → generation → storage in a single pipeline. Return file processing is also v1 scope because Itaú will send return files regardless and the team needs to confirm payment outcomes.

**Must have (table stakes — v1):**
- Authentication (user/password gate for the entire app)
- Settings page (company CNPJ, agência, conta, DAC — required in every CNAB header)
- Excel upload with beneficiary rows (Nome, Código/referenceId, Valor)
- VTEX MasterData enrichment per row (pixKey, document, firstName, lastName)
- PIX key type auto-detection (CPF/CNPJ/phone/email/UUID → codes 01-04)
- Pre-generation validation with per-row error report
- CNAB 240 file generation — Segmentos A + B, all 240-byte records, LATIN-1
- File download (manual submission fallback while API credentials are unavailable)
- File storage with status tracking (Criado, Transmitido, Erro)
- Dashboard — list of files with status, date, payment count
- Bank transmission via mock stub (complete the UI flow; real API when credentials arrive)
- Return file processing (parse arquivo retorno, update payment statuses by ocorrência code)
- Audit log (who generated, when transmitted, any errors)

**Should have (differentiators — v1 or early v2):**
- Validation error report table (row N: field X is missing — not just "file has errors")
- VTEX lookup failure report (list of referenceIds not found or missing pixKey)
- Human-readable rejection code mapping (SISPAG 2-char codes → plain Portuguese)
- File naming convention (`PIX_YYYYMMDD_HHMMSS_N_pagamentos.rem`)
- Duplicate payment detection (same referenceId + valor in same session)

**Defer (v2+):**
- Row-level error isolation / partial file generation (valid rows only)
- Transmission response storage (full Itaú HTTP response)
- Scheduled/automatic transmission
- Multi-bank or multi-company support (explicitly out of scope)

### Architecture Approach

The architecture is a strict forward-flowing pipeline where each layer has one responsibility and no layer reaches backward. The CNAB 240 Builder is a pure function (zero side effects, returns bytes, trivially unit-testable). The Bank Transmitter is a pluggable interface with a Mock implementation for all pre-credential phases. Validation always precedes file generation and surfaces all errors at once. The desktop GUI (PySide6 signals/slots) replaces the web routing layer but connects to the same service components in the same order.

**Major components:**
1. Excel Parser — reads .xlsx, produces `PaymentRow[]` (name, referenceId, amount)
2. VTEX Enrichment Service — GET `/api/dataentities/VV/search?_where=referenceId={id}`, returns `EnrichedPayment[]`
3. PIX Key Detector — pure function, classifies pixKey string into type code 01-04 and normalizes format
4. Validator — pre-flight checks (pixKey present, document present, amount > 0, company config complete), returns per-row `ValidationError[]`
5. CNAB 240 Builder — pure function, returns exact bytes: Header Arquivo + Header Lote + N×(Segmento A + Segmento B PIX) + Trailer Lote + Trailer Arquivo
6. File Store — writes bytes to disk (`/files/YYYYMMDD/{uuid}.rem`) + inserts DB metadata row
7. Bank Transmitter — pluggable: MockTransmitter now, ItauTransmitter when credentials arrive
8. Status Tracker / Audit Logger — DB writes only; records lifecycle events with actor and timestamp
9. Return Processor — parses Itaú arquivo retorno, maps ocorrência codes, updates payment rows in DB
10. Settings — stores/retrieves company config (CNPJ, agência, conta, DAC) from DB

**Database schema (minimum viable):** `companies`, `users`, `cnab_files`, `payments` (per-row within a file), `audit_logs`

### Critical Pitfalls

1. **Record not exactly 240 bytes** — Assert `len(record.encode('latin-1')) == 240` for every record during build. Open file with `newline='\n'` explicitly (Windows CRLF adds 1 byte per record and silently breaks the entire file). Build fields with enforced-width helpers, never raw string concatenation.

2. **UTF-8 encoding instead of LATIN-1** — Python 3 defaults to UTF-8. Accented characters (ã, é, ç) are multi-byte in UTF-8, silently expanding records beyond 240 bytes. Always `open(path, 'w', encoding='latin-1', newline='\n')`. Sanitize beneficiary names: `unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii').upper()` before placing in any CNAB field.

3. **Segmento B PIX treated as optional** — The CNAB summary table says "Segmento B — Opcional" but an explicit note states it is mandatory for PIX Transferência via chave. Every Segmento A for PIX must be immediately followed by a Segmento B. Trailer de Lote total count = 2N + 2 (N×A + N×B + 1 header + 1 trailer).

4. **Implicit decimal (Picture V) encoding** — A value of R$ 150.00 must be encoded as `000000000015000` (15 digits, no decimal point). Using `float` arithmetic with `* 100` produces float noise. Use `decimal.Decimal` throughout; parse Brazilian locale Excel values (comma separator, `R$` prefix) explicitly before encoding.

5. **Wrong PIX key type code in Segmento B** — The VTEX `pixKey` field is a raw string with no type metadata. Wrong type code causes rejection `BI`. Detection rules: 11 digits = CPF (03), 14 digits = CNPJ (03), starts with `+` = phone (01), contains `@` = email (02), UUID pattern = chave aleatória (04). Normalize keys (strip CPF/CNPJ punctuation, prefix `+` to phone keys missing it) as part of detection.

6. **Sequence number shared between Segmento A and B** — Per SISPAG Note 9, Segmento B carries the same NÚMERO DO REGISTRO as its paired Segmento A. Maintain two counters: `payment_seq` (shared by A+B pair) and `record_count` (increments for every record written).

7. **Trailer counts include header/trailer records** — Trailer de Lote TOTAL QTDE REGISTROS counts type 1 + type 3 + type 5 (not just type 3 detalhe records). For N payments: total = 2N + 2. Trailer de Arquivo includes type 0 + all lote records + type 9.

---

## Implications for Roadmap

Based on combined research, a 5-phase structure is strongly suggested. The ordering is driven by hard dependencies (settings must exist before file generation; pure logic must be tested before integration) and the risk-mitigation principle that the highest-risk area (CNAB byte precision) must be hardened before any UI or external service work begins.

### Phase 1: Core CNAB Engine (Pure Logic, No UI)
**Rationale:** The CNAB 240 Builder, PIX Key Detector, Validator, and value encoding are pure Python functions with zero external dependencies. They carry the highest rejection risk and must be hardened with unit tests before any other work builds on top of them. Starting here means problems are caught in isolation, not discovered during integration.
**Delivers:** A tested, byte-exact CNAB 240 file generator and validation library. Known-good output bytes for all record types.
**Addresses:** CNAB 240 file generation, PIX key detection, pre-generation validation, value encoding
**Avoids:** Pitfalls 1 (byte count), 2 (encoding), 3 (PIX key type), 4 (Picture V decimal), 5 (Segmento B mandatory), 6 (sequence numbers), 7 (trailer counts), 8 (forma 45), 14 (layout version), 16 (date format DDMMAAAA)
**Test requirement:** Assert `len(record.encode('latin-1')) == 240` for every record type. Assert exact byte sequences for known-good inputs. Assert value encoding against Brazilian locale test cases.

### Phase 2: Persistence and Settings
**Rationale:** The database schema and settings screen must exist before the GUI pipeline can store results. Settings (company CNPJ, agência, conta, DAC) are required fields in every generated CNAB header — the builder cannot run without them.
**Delivers:** SQLite DB with full schema (companies, users, cnab_files, payments, audit_logs), settings screen, Alembic migration baseline
**Addresses:** File storage with status tracking, settings page, audit log, authentication
**Uses:** SQLAlchemy 2.x, Alembic, PySide6 forms
**Avoids:** Pitfall 23 (company name consistency in headers), late-discovered schema problems

### Phase 3: Excel Import and VTEX Integration
**Rationale:** With the core engine and persistence in place, the data intake pipeline can be built. openpyxl reads Excel; the VTEX enrichment service fetches beneficiary data. Validation error reporting and null-field handling are built here.
**Delivers:** Full data intake flow — upload Excel → VTEX enrichment → per-row validation report with actionable errors
**Addresses:** Excel upload, VTEX lookup, PIX key enrichment, validation error report, VTEX lookup failure report
**Avoids:** Pitfall 10 (null pixKey), 11 (key normalization), 12 (VTEX rate limiting — add throttle here), 21 (Brazilian locale decimal in Excel), 22 (null VTEX fields)
**Research flag:** VTEX rate limiting strategy (batch query vs. sequential with throttle) should be confirmed against the live API before implementation.

### Phase 4: Desktop GUI Pipeline (PySide6)
**Rationale:** With all service components ready and tested, the desktop GUI is wired together. This is intentionally late — the GUI should be a thin layer on already-working services, not built in parallel with the logic.
**Delivers:** Complete PySide6 desktop application: login screen, settings, Excel upload flow, validation error table, file generation, dashboard, file download
**Addresses:** Authentication, dashboard (file list with status/date), file download, mock bank transmission trigger
**Uses:** PySide6 signals/slots connecting Excel Parser → VTEX Enrichment → Validator → CNAB Builder → File Store
**Avoids:** Building GUI before logic is tested (makes debugging much harder); premature UI investment

### Phase 5: Return File Processing and Real Bank Transmission
**Rationale:** Return file processing completes the payment lifecycle; the real Itaú transmitter replaces the mock when credentials become available. These are deferred because they depend on external parties (Itaú providing credentials and return files).
**Delivers:** Return file upload and parsing UI, ocorrência code → Portuguese description mapping, payment status updates (Agendado/Efetivado/Rejeitado), ItauTransmitter replacing MockTransmitter
**Addresses:** Return file processing, human-readable rejection code mapping, full payment lifecycle status, audit log viewer
**Avoids:** Pitfall 19 (treating BD "Agendado" as success), Pitfall 20 (wrong TLS certificate for Itaú API), Pitfall 25 (duplicate file submission)
**Research flag:** Itaú API authentication method (mTLS with ICP-Brasil certificate vs. OAuth 2.0 client_credentials) must be confirmed with the Itaú account manager before implementing ItauTransmitter. This is unknowable without credentials.

### Phase Ordering Rationale

- Phase 1 first because CNAB byte precision is the highest-risk area and is a pure logic problem with no dependencies. Failure here fails everything downstream.
- Phase 2 before Phase 3 because settings/company data is a required input to the CNAB builder and must exist before the full pipeline can run.
- Phase 3 before Phase 4 because the GUI should wrap already-working services, not be built alongside unproven logic.
- Phase 5 last because it depends on external parties (Itaú credentials, return file samples) and can be developed independently of the main pipeline.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 5 (Itaú transmission):** Authentication method is unknown until credentials are provided. Research the specific API contract (mTLS vs. OAuth, endpoint URL, file format for multipart POST) with the Itaú account manager. Do not build the real transmitter until this is confirmed.
- **Phase 3 (VTEX rate limiting):** The VTEX MasterData API rate limit for the project's AppKey should be verified before choosing sequential-with-throttle vs. batch `_where` query approach.

Phases with standard, well-documented patterns (research-phase likely not needed):
- **Phase 1 (CNAB engine):** Fully specified in SISPAG v085 documentation. All rules are documented. Implementation is a direct translation of spec to code.
- **Phase 2 (persistence):** SQLAlchemy 2.x + Alembic + SQLite is a canonical, well-documented pattern. No research needed.
- **Phase 4 (PySide6 GUI):** PySide6 Qt6 has extensive documentation. The architecture is straightforward signal/slot wiring of existing services.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Core data/logic stack (Python, SQLAlchemy, openpyxl, httpx) is HIGH confidence. PySide6 replaces Flask — this change was made after research, so Flask-specific stack findings should be discarded. PySide6 is a mature, well-documented framework; the substitution is straightforward. Package versions need pip verification before pinning. |
| Features | HIGH | Derived from official SISPAG v085 documentation and PROJECT.md. Feature list is complete and dependency-ordered. The only unknowns are Itaú API transmission details (no credentials). |
| Architecture | HIGH | Pipeline architecture derived from the SISPAG spec structure itself — the segment types and their required ordering define the component graph. The adaptation from Flask web layer to PySide6 desktop layer does not change any of the service components; only the outermost layer changes. |
| Pitfalls | HIGH | Every critical pitfall (1-15) is sourced from specific SISPAG documentation notes with exact field positions and occurrence codes. These are not hypothetical risks — they are documented rejection conditions. |

**Overall confidence:** HIGH for domain knowledge (CNAB spec, VTEX API). MEDIUM for desktop GUI implementation details (PySide6 specifics were not the focus of research).

### Gaps to Address

- **Itaú API authentication:** The transmission mechanism (mTLS certificate type, OAuth variant, endpoint URL) cannot be determined without credentials. The mock transmitter is the correct mitigation. Resolve during Phase 5 planning by engaging the Itaú account manager.
- **PySide6 stack specifics:** STACK.md documented a Flask stack. The PySide6 equivalents for auth (no session management needed for a desktop app — OS-level user or simple app-level login dialog), file upload (QFileDialog instead of HTTP multipart), and routing (signals/slots instead of Flask routes) are standard Qt patterns but were not researched in depth. These are low-risk gaps given PySide6's documentation quality.
- **VTEX rate limits:** The exact rate limit for the project's AppKey needs verification against the live API. Implement throttle conservatively (25ms between requests = 40 req/s) and adjust after observing production behavior.
- **Return file samples:** No real Itaú arquivo retorno sample was available during research. The return file parser must be written against the SISPAG spec and then validated against a real return file before go-live. Request a sample from Itaú during Phase 5.
- **CNAB encoding — Latin-1 vs CP1252:** STACK.md notes uncertainty between Latin-1 and CP1252. ARCHITECTURE.md and PITFALLS.md both specify Latin-1. SISPAG documentation confirms LATIN-1. Use `latin-1` and treat this as resolved.

---

## Sources

### Primary (HIGH confidence)
- `./Documents/sispag_cnab.md` — Itaú SISPAG CNAB 240 v085 official specification. All CNAB field positions, segment structures, PIX-specific notes (35-40), occurrence codes, layout version constants. The authoritative source for Phase 1 implementation.
- `./Documents/Vtex API Info.txt` — VTEX MasterData API response sample. Confirmed field names: `pixKey`, `document`, `firstName`, `lastName`, `email`, `homePhone`. Confirmed null/absent fields: `agency`, `bank`, `cpf`. Identified `complement: "null"` (string) anomaly.
- `./planning/PROJECT.md` — Project requirements, scope constraints, team size, out-of-scope items.

### Secondary (MEDIUM confidence)
- Python/Flask ecosystem training knowledge (cutoff August 2025) — Package versions and compatibility matrix. Needs pip verification before pinning.
- PySide6 Qt6 documentation (training knowledge) — Desktop application patterns. Well-documented; low validation risk.

### Tertiary (requires external confirmation)
- Itaú API transmission details — Authentication method, endpoint URL, file submission format. Unknown until credentials are provided.
- VTEX API rate limits — Not confirmed against live API. Apply conservative throttle and adjust empirically.

---

*Research completed: 2026-03-30*
*Stack note: Desktop (PySide6 + SQLite) — Flask references in source research files are superseded*
*Ready for roadmap: yes*
