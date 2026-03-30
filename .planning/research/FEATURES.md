# Feature Landscape

**Domain:** CNAB 240 PIX Payment File Generation and Bank Transmission (Itaú SISPAG)
**Researched:** 2026-03-30
**Sources:** SISPAG CNAB v085 official documentation, VTEX MasterData API spec, PROJECT.md

---

## Table Stakes

Features the finance team requires for the system to be usable at all. Missing any of these
means the system cannot do its core job.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Excel upload with beneficiary rows | Primary input mechanism — finance team works in Excel | Low | Columns: Nome, Código (referenceId), Valor |
| VTEX MasterData lookup per row | Fetches pixKey, document, firstName, lastName, email, homePhone using referenceId | Low-Med | API: `/api/dataentities/VV/search?_fields=_all&_where=referenceId={id}` |
| PIX key type auto-detection | CNAB Segmento B requires explicit type code (01=Tel, 02=Email, 03=CPF/CNPJ, 04=Aleatória) — system must classify correctly | Med | CPF=11 digits; CNPJ=14 digits; Tel=starts with "+"; Email=contains "@"; UUID format = aleatória |
| CNAB 240 file generation (PIX Transferência) | Core output. Itaú SISPAG requires exact 240-byte records | High | Header Arquivo (type 0), Header Lote (type 1, forma 45), Segmento A + Segmento B PIX (type 3), Trailer Lote (type 5), Trailer Arquivo (type 9) |
| Correct Segmento A for PIX | Câmara=009 (SPI/PIX), posições 113-114="04" (Chave PIX), campo ISPB, CPF/CNPJ do favorecido obrigatório | High | Per SISPAG Note 35/36/15; bank rejects if these fields are wrong |
| Correct Segmento B for PIX | Obrigatório para PIX via chave. Tipo de chave (posições 15-16), CPF/CNPJ (posições 18-32), Chave PIX (posições 128-227, 100 chars) | High | Per SISPAG spec; Segmento B is OPTIONAL for DOC/TED but MANDATORY for PIX Transferência via chave |
| 240-byte precision enforcement | Each record must be exactly 240 bytes; alpha fields padded right with spaces; numeric fields padded left with zeros | High | Any deviation causes Itaú to reject the entire file |
| Pre-generation data validation | Check pixKey format, CPF/CNPJ validity, required fields present, valor > 0, data pagamento valid — before generating file | Med | Prevents wasted file generation and transmission attempts |
| File storage with status tracking | Persist generated files and metadata. States: Criado, Transmitido, Erro | Med | SQLite/PostgreSQL; enables dashboard and audit |
| File status lifecycle management | Criado → Transmitido (success) or Erro (failure), with error log stored | Low-Med | Atomic state transitions; log message captured |
| Bank transmission (Itaú API) | Transmit file to Itaú via API; mock initially, real integration when credentials are available | High | Credentials not yet available; design for pluggable transport |
| Return file processing (arquivo retorno) | Read Itaú return file to confirm which payments were effected, rejected, or pending | High | Return file uses same CNAB 240 layout; ocorrência "00" = payment made, "RJ" = rejected, others = various errors |
| Dashboard with file list | View all generated files, their statuses, timestamps; filter by date and status | Med | Core operational view for finance team |
| Audit log | Record who generated each file, when it was transmitted, and any errors | Low-Med | Per-file entries at minimum; supports accountability |
| Settings page — payer company data | Store CNPJ, Agência, Conta, DAC — used in Header Arquivo and Header Lote | Low | Must be configurable without code changes |
| Simple authentication | Login with user/password for the 1-5 person finance team | Low | Local credential store; no OAuth or SSO needed |

---

## Differentiators

Features that make the system markedly better than manual file construction, beyond
the bare minimum.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Validation error report before generation | Display a table of rows with specific errors (row N: pixKey missing, row M: valor zero) rather than just "file has errors" | Med | Saves the team from iterating blind; shows exactly which beneficiaries need fixing in the Excel |
| Row-level error isolation | If row N has an invalid pixKey but rows 1-50 are valid, allow generating a partial file for the valid rows and flag the invalid ones | Med | Finance team can pay the valid set today and fix failures separately |
| Duplicate payment detection | Warn if the same referenceId + valor combination appears more than once in the same upload session or was already transmitted recently | Low-Med | Prevents accidental double-payment |
| Download generated CNAB file | Allow the finance team to download the .txt/.rem file for manual submission to Itaú web portal as a fallback | Low | Critical safety net when API credentials are unavailable or API transmission fails |
| Return file upload and reconciliation UI | Upload the Itaú arquivo retorno through the browser; parse and show which payments succeeded, which were rejected with the rejection reason code translated to Portuguese | High | Return codes from SISPAG spec: "RJ"=Registro Rejeitado, "SS"=Saldo insuficiente, "BI"=CPF/CNPJ favorecido inválido PIX, etc. |
| Human-readable rejection reason mapping | Map the 2-char SISPAG ocorrência codes to plain Portuguese descriptions | Low | 80+ codes in the spec; done once, saves team from looking up the PDF |
| VTEX lookup failure report | When a referenceId is not found in VTEX or returns no pixKey, show a clear list of the missing ones so the team can investigate | Low | VTEX query returns empty array for unknown IDs |
| File naming convention | Generate meaningful filenames: `PIX_YYYYMMDD_HHMMSS_N_pagamentos.rem` | Low | Reduces confusion when multiple files are generated per day |
| Transmission timestamp and Itaú response storage | Store the HTTP response (or mock response) from the Itaú API alongside the file record | Low | Needed for troubleshooting failed transmissions |

---

## Anti-Features

Features to deliberately NOT build. Each would add complexity without serving the stated scope.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Boleto, DOC, TED payment support | Out of scope per PROJECT.md; adds multiple new segment types (Segmentos J, J-52, N, O) and validation rules | If needed later, add as a separate lote type behind a feature flag |
| PIX QR-Code support | Different segment structure (Segmento J + J-52 PIX); out of scope | Implement only PIX Transferência via chave (forma 45) |
| Multi-bank support | Every bank has its own CNAB dialect; generalizing early creates a leaky abstraction | Single hard-coded Itaú SISPAG v085 implementation |
| Multi-company / multi-tenant support | PROJECT.md explicitly single-company; adds auth complexity for no current benefit | Company data in settings page, one set of credentials |
| Generating arquivo retorno | PROJECT.md explicitly out of scope; Itaú generates the return file, not the client | Process the return file received from Itaú only |
| Mobile / responsive layout | Small internal tool used on desktop by 1-5 people; responsive CSS is extra effort with no stated need | Desktop-first, minimal CSS |
| Scheduled / automatic transmission | No stated requirement; transmission is a manual action by the finance team | Manual "Transmit" button per file |
| Approval workflow / payment authorization | Team is small; no multi-step approval stated; adds state machine complexity | Simple generate-then-transmit flow; one person acts |
| Direct integration with accounting systems (SAP, Totvs, etc.) | No stated requirement; external systems introduce coupling and change risk | Excel import is the integration boundary |
| Email notifications on transmission | No stated requirement; dashboard provides status visibility | Dashboard polling or page refresh is sufficient |

---

## Feature Dependencies

The following ordering is forced by logical dependency:

```
Settings (CNPJ, Agência, Conta, DAC)
  → CNAB generation (Header Arquivo fields require company data)

Authentication
  → All other features (must log in first)

Excel upload
  → VTEX lookup (need referenceId per row to query VTEX)
    → PIX key type detection (need pixKey from VTEX response)
      → Pre-generation validation (need type-classified pixKey and all fields)
        → CNAB 240 file generation (Segmentos A + B built from validated data)
          → File storage with status Criado
            → Dashboard display
            → File download (fallback)
            → Bank transmission (Itaú API)
              → Status update: Criado → Transmitido or Erro
              → Audit log entry

Return file upload
  → Return file parsing (CNAB 240 retorno format)
    → Reconciliation display (ocorrência code mapping)
    → Status update on original payment records
```

---

## MVP Recommendation

The minimum that makes the system genuinely usable (not a toy):

**Must have in v1:**
1. Authentication (gate everything)
2. Settings page (company data — required by every generated file)
3. Excel upload + VTEX lookup
4. PIX key type detection
5. Pre-generation validation with per-row error report
6. CNAB 240 file generation (Segmentos A + B, all 240-byte records correct)
7. File download (manual submission fallback — critical while API credentials are unavailable)
8. File storage with status (Criado)
9. Dashboard (list of files with status and date)
10. Bank transmission via mock stub (so the UI flow is complete; swap to real API later)
11. Return file processing (Itaú will send return files; must handle them or team cannot confirm payments)
12. Audit log (basic — who generated, when transmitted)

**Defer to v2:**
- Row-level error isolation / partial file generation — useful but adds generation complexity; v1 validates all-or-nothing
- Duplicate payment detection — valuable but not blocking
- Human-readable rejection code mapping — can start with raw codes and add mapping incrementally
- Transmission response storage — nice to have; audit log covers the essential record

---

## Complexity Notes

**High complexity items requiring careful implementation:**

1. **CNAB 240 byte-exact generation** — The most failure-prone part. Every field has a fixed position, picture format, and padding rule. The SISPAG spec has ~40 footnotes covering edge cases. Off-by-one errors in field positions cause the bank to reject the entire file with no partial processing. Requires thorough unit tests against known-good byte sequences.

2. **Return file processing** — The retorno uses the same 240-byte layout but with fields populated that are blank in the remessa (OCORRÊNCIAS, DATA EFETIVA, VALOR EFETIVO, NOSSO NÚMERO). Parser must handle all segment types that may appear in a return (Segmento A, B, Z and potentially others).

3. **Itaú API integration** — No credentials and no sandbox documentation available yet. Design the transmission layer as a swappable adapter (mock + real) from the start. The mock must return plausible responses so the rest of the flow (status update, audit log) can be developed and tested.

4. **PIX key type detection** — Must handle edge cases: a pixKey that is a 11-digit number could be a CPF; a 14-digit number is a CNPJ. Phone format starts with "+". UUID format with dashes is aleatória. Email contains "@". The classification must be unambiguous because the wrong type code in Segmento B causes payment rejection (SISPAG code "BI").

---

## Sources

- SISPAG CNAB Versão 085 — `./Documents/sispag_cnab.md` (official Itaú specification, converted from PDF)
  - Chapter 2: File structure and encoding rules
  - Chapter 3: Segment layouts (Header Arquivo, Header Lote, Segmento A, Segmento B PIX, Trailer Lote, Trailer Arquivo)
  - Chapter 4: Notes 8, 9, 10, 15, 35, 36, 37, 39, 40 (PIX-specific rules)
  - Ocorrência code table (return file processing)
- VTEX MasterData API — `./Documents/Vtex API Info.txt` (response schema showing pixKey, document, firstName, lastName fields)
- PROJECT.md — Requirements, constraints, out-of-scope items
