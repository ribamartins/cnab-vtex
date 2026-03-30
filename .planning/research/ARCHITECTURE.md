# Architecture Patterns

**Domain:** CNAB PIX payment file generation and bank transmission system
**Researched:** 2026-03-30
**Confidence:** HIGH — based on official SISPAG v085 documentation, VTEX API spec, and project requirements

---

## Recommended Architecture

A layered pipeline architecture where data flows strictly forward through transformation stages: raw input → enriched domain objects → formatted file → transmitted artifact → tracked status. Each layer has one responsibility and one direction of dependency.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Web Layer (Flask)                        │
│   Routes / Auth / File Upload / Dashboard / Return Processing   │
└─────────────────────────────────────────────────────────────────┘
           │                              │
           ▼                              ▼
┌──────────────────────┐    ┌─────────────────────────────────┐
│  Excel Parser        │    │  Dashboard / Status Views       │
│  (openpyxl)          │    │  (reads DB only)                │
└──────────┬───────────┘    └─────────────────────────────────┘
           │ PaymentRow[]
           ▼
┌──────────────────────┐
│  VTEX Enrichment     │
│  Service             │◄── VTEX MasterData API (external)
│  (httpx/requests)    │    GET /api/dataentities/VV/search
└──────────┬───────────┘
           │ EnrichedPayment[] (pixKey, document, name, etc.)
           ▼
┌──────────────────────┐
│  PIX Key Detector    │
│  (pure function)     │
│  CPF/CNPJ/phone/     │
│  email/random        │
└──────────┬───────────┘
           │ EnrichedPayment[] with keyType resolved
           ▼
┌──────────────────────┐
│  Validator           │
│  (domain rules)      │
│  Pre-flight checks   │
└──────────┬───────────┘
           │ ValidationResult (pass/fail per row)
           ▼
┌──────────────────────┐
│  CNAB 240 Builder    │◄── Company Config (from DB / settings)
│  (pure, stateless)   │
│  Header Arquivo      │
│  Header Lote         │
│  Segmento A (PIX)    │
│  Segmento B (PIX)    │
│  Trailer Lote        │
│  Trailer Arquivo     │
└──────────┬───────────┘
           │ bytes (fixed 240-byte records, LATIN-1)
           ▼
┌──────────────────────┐
│  File Store          │
│  (filesystem +       │◄── SQLite/PostgreSQL (metadata)
│   DB metadata)       │    file_id, status, path, timestamps
└──────────┬───────────┘
           │ FileRecord
           ▼
┌──────────────────────┐
│  Bank Transmitter    │◄── Itaú API (external) — mock initially
│  (pluggable)         │
│  MockTransmitter     │
│  ItauTransmitter     │
└──────────┬───────────┘
           │ TransmissionResult
           ▼
┌──────────────────────┐
│  Status Tracker      │
│  + Audit Logger      │◄── DB writes (status, error log, user, timestamp)
└──────────────────────┘
           │
           ▼
┌──────────────────────┐
│  Return Processor    │◄── Upload of Itaú return file (arquivo retorno)
│  (reads retorno)     │    Updates payment status per ocorrências codes
└──────────────────────┘
```

---

## Component Boundaries

| Component | Responsibility | Input | Output | Talks To |
|-----------|---------------|-------|--------|----------|
| **Web Layer** | HTTP routing, auth, file uploads, HTML rendering | HTTP requests | HTTP responses | All service components |
| **Excel Parser** | Read .xlsx, extract named columns | File bytes | `PaymentRow[]` (name, referenceId, amount) | Nothing external |
| **VTEX Enrichment Service** | Look up beneficiary data via referenceId | `PaymentRow[]` | `EnrichedPayment[]` | VTEX MasterData API |
| **PIX Key Detector** | Classify pixKey type: CPF/CNPJ/phone/email/random | `pixKey: str` | `keyType: int (01-04)` | Nothing external |
| **Validator** | Pre-flight checks before CNAB generation | `EnrichedPayment[]` | `ValidationResult[]` | Nothing external |
| **CNAB 240 Builder** | Produce spec-compliant 240-byte records | `EnrichedPayment[]` + company config | `bytes` | Nothing external |
| **File Store** | Persist generated file, record metadata | `bytes` + metadata | `FileRecord` | Filesystem + DB |
| **Bank Transmitter** | Submit file to Itaú (or mock it) | `FileRecord` | `TransmissionResult` | Itaú API (or mock) |
| **Status Tracker / Audit Logger** | Record lifecycle events with actor and timestamp | events | DB rows | DB only |
| **Return Processor** | Parse Itaú retorno file, update payment statuses | Return file bytes | Status updates in DB | DB only |
| **Settings** | Store and retrieve company config (CNPJ, agency, account, DAC) | Form POST / GET | Config record | DB only |

---

## Data Flow

### Primary Flow: Excel → CNAB File

```
1. User uploads Excel
   └─► Excel Parser extracts rows: [{referenceId, name, amount}, ...]

2. For each row, VTEX Enrichment fetches:
   GET /api/dataentities/VV/search?_fields=_all&_where=referenceId={id}
   └─► Returns: pixKey, document, firstName, lastName, email, homePhone

3. PIX Key Detector classifies each pixKey:
   - 11 digits, all numeric → CPF (03)
   - 14 digits, all numeric → CNPJ (03)
   - starts with "+" or ~11 digits with DDD → telefone (01)
   - contains "@" → e-mail (02)
   - UUID pattern (8-4-4-4-12 hex) → chave aleatória (04)

4. Validator checks:
   - pixKey is present and non-empty
   - document (CPF/CNPJ) is present for Segmento B
   - amount > 0
   - payment date is a business day (or user-supplied)
   - company config (CNPJ, agency, account, DAC) is populated in settings

5. CNAB 240 Builder assembles file:
   Record 0: Header Arquivo (240 bytes)
     - banco=341, lote=0000, tipo=0
     - CNPJ empresa, agência, conta, DAC (from settings)
     - data/hora geração, código remessa=1

   Record 1: Header Lote (240 bytes)
     - lote=0001, tipo=1, operação=C
     - tipo pagamento from Nota 4, forma=45 (PIX Transferência)
     - layout lote versão=040

   For each payment (pair of records):
     Record 3 Segmento A (240 bytes)
       - câmara=009 (SPI/PIX), posições 018-020
       - identificação transferência="04" (Chave PIX), posições 113-114
       - nome favorecido, SEU NÚMERO, data pagamento
       - valor pagamento (13 digits + 2 decimal, no separator)
       - nº inscrição favorecido (CPF/CNPJ)

     Record 3 Segmento B PIX (240 bytes)
       - tipo chave (01/02/03/04), posições 015-016
       - nº inscrição favorecido, posições 018-032
       - chave PIX, posições 128-227 (up to 100 chars, space-padded right)

   Record 5: Trailer Lote (240 bytes)
     - quantidade de registros no lote
     - somatória dos valores

   Record 9: Trailer Arquivo (240 bytes)
     - quantidade de lotes=1
     - quantidade de registros (total)

   Each record is exactly 240 bytes, LATIN-1 encoded
   Numeric fields: right-aligned, zero-padded
   Alphanumeric fields: left-aligned, space-padded
   File ends with CRLF or LF per line

6. File Store:
   - Write bytes to disk: /files/{YYYYMMDD}/{uuid}.rem
   - Insert DB row: id, filename, path, created_by, created_at, status="Criado", payment_count, total_value

7. Status shown in dashboard immediately after generation
```

### Transmission Flow

```
1. User triggers transmission from dashboard
   └─► Bank Transmitter.transmit(file_record)
       ├─ MockTransmitter: log attempt, return success, update status
       └─ ItauTransmitter: POST multipart to Itaú API endpoint
          ├─ Success → status = "Transmitido", transmitted_at = now()
          └─ Failure → status = "Erro", error_log = response body
```

### Return Processing Flow

```
1. User uploads Itaú retorno file
   └─► Return Processor reads line by line
       - Header Arquivo: validate banco=341, código=2 (retorno)
       - For each Segmento A: read OCORRÊNCIAS (posições 231-240)
         - "00" = without occurrence (success)
         - Other codes = rejection codes, map to human-readable message
       - Update each payment row in DB with result code + description
       - Dashboard shows updated statuses per payment within file
```

---

## Component Build Order

Build in strict dependency order. Each phase should be independently testable.

```
Phase 1: Foundation (no external dependencies)
  └─► Settings model + DB schema
  └─► Excel Parser (openpyxl, no network)
  └─► PIX Key Detector (pure function, regex)
  └─► CNAB 240 Builder (pure function, bytes manipulation)
  └─► Unit tests for bytes output (assert len(record) == 240)

Phase 2: Persistence
  └─► DB models: File, Payment, AuditLog, Config
  └─► File Store (DB + filesystem)
  └─► Status Tracker

Phase 3: External Integration
  └─► VTEX Enrichment Service (requires API credentials in .env)
  └─► Mock Bank Transmitter (pluggable interface first)

Phase 4: Web Layer
  └─► Auth (Flask-Login, local user table)
  └─► Upload route → wires Excel Parser → VTEX Enrichment → Validator → Builder → File Store
  └─► Dashboard (list files, filter by status/date)
  └─► Transmission trigger route
  └─► Settings form

Phase 5: Return Processing + Real Transmitter
  └─► Return file parser
  └─► ItauTransmitter (replaces mock when credentials available)
  └─► Audit log viewer
```

---

## Patterns to Follow

### Pattern 1: Pure Builder for CNAB Records

The CNAB 240 Builder must be a pure function with zero side effects. It takes domain objects and returns bytes. No DB calls, no file I/O, no datetime.now() inside — pass the payment date as a parameter.

```python
def build_cnab_file(
    payments: list[EnrichedPayment],
    company: CompanyConfig,
    payment_date: date,
    file_sequence: int,
) -> bytes:
    records = []
    records.append(_build_header_arquivo(company, payment_date, file_sequence))
    records.append(_build_header_lote(company, lote_num=1))
    for seq, payment in enumerate(payments, start=1):
        records.append(_build_segmento_a(payment, seq * 2 - 1, payment_date))
        records.append(_build_segmento_b_pix(payment, seq * 2))
    records.append(_build_trailer_lote(payments))
    records.append(_build_trailer_arquivo(len(payments)))
    return b"\r\n".join(records)

def _pad_alpha(value: str, width: int) -> bytes:
    """Left-align, space-pad right, encode LATIN-1."""
    return value[:width].ljust(width).encode("latin-1")

def _pad_num(value: int | str, width: int) -> bytes:
    """Right-align, zero-pad left, numeric only."""
    return str(value)[:width].zfill(width).encode("latin-1")
```

**Why:** CNAB spec requires exact 240 bytes per record. A pure function is trivially testable with `assert len(record) == 240`. Any stateful dependency inside makes this hard to test and debug.

### Pattern 2: Pluggable Transmitter Interface

Define a protocol/interface for bank transmission. Switch between mock and real without touching application code.

```python
from abc import ABC, abstractmethod

class BankTransmitter(ABC):
    @abstractmethod
    def transmit(self, file_path: str, file_id: int) -> TransmissionResult:
        ...

class MockTransmitter(BankTransmitter):
    def transmit(self, file_path: str, file_id: int) -> TransmissionResult:
        return TransmissionResult(success=True, message="Mock: transmitted")

class ItauTransmitter(BankTransmitter):
    def __init__(self, client_id: str, client_secret: str):
        ...
    def transmit(self, file_path: str, file_id: int) -> TransmissionResult:
        # Real implementation when credentials are available
        ...
```

**Why:** Itaú credentials are not yet available. Building against an interface lets all other components be developed and tested without blocking on the bank integration.

### Pattern 3: PIX Key Type Detection as Isolated Function

PIX key classification is a well-defined, testable rule set. Isolate it completely.

```python
import re

PIX_TYPE_PHONE = "01"
PIX_TYPE_EMAIL = "02"
PIX_TYPE_CPF_CNPJ = "03"
PIX_TYPE_RANDOM = "04"

def detect_pix_key_type(key: str) -> str:
    key = key.strip()
    if re.fullmatch(r"\+\d{10,14}", key):
        return PIX_TYPE_PHONE
    if "@" in key:
        return PIX_TYPE_EMAIL
    if re.fullmatch(r"\d{11}", key):
        return PIX_TYPE_CPF_CNPJ  # CPF
    if re.fullmatch(r"\d{14}", key):
        return PIX_TYPE_CPF_CNPJ  # CNPJ
    if re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", key):
        return PIX_TYPE_RANDOM
    raise ValueError(f"Cannot classify PIX key: {key!r}")
```

### Pattern 4: Validation Before File Generation

Never generate a CNAB file from invalid data. Run all validation pre-flight and surface errors back to the user before any file I/O occurs.

```python
@dataclass
class ValidationError:
    row: int
    referenceId: str
    field: str
    message: str

def validate_payments(
    payments: list[EnrichedPayment],
    company: CompanyConfig,
) -> list[ValidationError]:
    errors = []
    if not company.is_complete():
        errors.append(ValidationError(row=0, referenceId="", field="company", message="Configurações da empresa incompletas"))
    for i, p in enumerate(payments):
        if not p.pix_key:
            errors.append(ValidationError(i+1, p.reference_id, "pixKey", "Chave PIX ausente"))
        if p.amount <= 0:
            errors.append(ValidationError(i+1, p.reference_id, "amount", "Valor deve ser maior que zero"))
        # etc.
    return errors
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Off-by-One in Field Positions

**What:** SISPAG documentation uses 1-based position indexes (e.g., "posição 001-003"). Python strings are 0-based. Mixing these causes silent data corruption — the file will be 240 bytes but fields will be in wrong positions.

**Why bad:** Itaú's validator rejects the file without a human-readable error. The generated file looks valid until Itaú processes it.

**Instead:** Define each field as a named slice with the correct 0-based offset. Document the SISPAG position in a comment on the same line.

```python
# SISPAG pos 001-003 → Python [0:3]
BANCO = slice(0, 3)
# SISPAG pos 004-007 → Python [3:7]
LOTE = slice(3, 7)
```

### Anti-Pattern 2: Encoding the File as UTF-8

**What:** Writing the CNAB file with UTF-8 encoding (Python default).

**Why bad:** CNAB FEBRABAN standard uses LATIN-1 (ISO-8859-1). Names with accents (e.g., "José", "Ângela") encode differently. The resulting bytes will be wrong length for accented chars in UTF-8, breaking the 240-byte record constraint.

**Instead:** Always `encode("latin-1")` for each record. Strip or transliterate accented characters that cannot be represented in LATIN-1 before encoding. SISPAG docs explicitly recommend avoiding special characters and accents.

### Anti-Pattern 3: Computing Record Counts/Sums in the Builder

**What:** Letting the CNAB Builder count records and sum values as a side effect.

**Why bad:** Trailer records (lote and arquivo) require the count of records in the batch and the total value sum. Computing these inside the builder makes the builder stateful and harder to test in isolation.

**Instead:** Compute counts and sums before calling the builder. Pass them as explicit parameters.

### Anti-Pattern 4: Storing API Credentials in DB or Code

**What:** Saving VTEX `AppKey`/`AppToken` or future Itaú credentials in the database or application config table.

**Why bad:** Database is included in backups and potentially accessible to more people. Credentials in code are exposed in version control.

**Instead:** Load all credentials exclusively from environment variables at application startup. Fail loud and early if required variables are missing.

### Anti-Pattern 5: Mixing PIX and Non-PIX Payments in One Lote

**What:** Including PIX and non-PIX payment types in the same batch or same lote.

**Why bad:** SISPAG documentation explicitly states: "Os lotes de serviços de pagamentos na forma de PIX devem ser enviados obrigatoriamente em arquivo separado das demais formas de pagamento." Itaú will reject the file.

**Instead:** Since this system is PIX-only (per scope), only generate the PIX lote structure. Document this constraint prominently.

---

## Database Schema (Minimum Viable)

```
companies (settings)
  id, cnpj, agency, account, dac, company_name, address, city, state, cep

users
  id, username, password_hash, created_at

cnab_files
  id, filename, file_path, created_by (FK users), created_at,
  status (CRIADO|TRANSMITIDO|ERRO), transmitted_at, error_message,
  payment_count, total_value_cents

payments (within a file)
  id, file_id (FK cnab_files), row_number, reference_id,
  beneficiary_name, pix_key, pix_key_type, document,
  amount_cents, return_code, return_description

audit_logs
  id, file_id (FK), user_id (FK), action, detail, occurred_at
```

---

## Scalability Considerations

This system serves a small finance team (1-5 users) processing batch payments. Scale is not a primary concern.

| Concern | Current scope | If scale increases |
|---------|--------------|-------------------|
| VTEX API rate limiting | Sequential calls, small batches | Add async/concurrent fetching with rate limit backoff |
| CNAB file size | Hundreds of rows per file | Already handled — each row is just 2 x 240-byte records |
| Concurrent file generation | Single user at a time | Add job queue (Celery/RQ) only if needed |
| DB | SQLite sufficient for <1000 files/year | Migrate to PostgreSQL (schema unchanged) |

---

## Sources

- **SISPAG CNAB 240 v085** — `./Documents/sispag_cnab.md` (official Itaú documentation, converted from PDF)
  - Section 2.2: File structure, lote rules, PIX separation requirement
  - Section 3: Record layouts for Header Arquivo, Header Lote, Segmento A (PIX), Segmento B (PIX), Trailers
  - Notas 35-40: PIX-specific field rules (câmara=009, identificação=04, key type codes, key format)
  - Chapter 5: Implantação — test/production environment notes
- **VTEX MasterData API** — `./Documents/Vtex API Info.txt` (live API response sample)
  - Endpoint: `GET /api/dataentities/VV/search?_fields=_all&_where=referenceId={id}`
  - Fields used: `pixKey`, `document`, `firstName`, `lastName`, `email`, `homePhone`
- **PROJECT.md** — constraints (Python + Flask, SQLite/PostgreSQL, LATIN-1 encoding, single bank/company)
