# Phase 1: CNAB Engine - Research

**Researched:** 2026-03-30
**Domain:** CNAB 240 SISPAG Itaú v085 — byte-exact binary file generation in pure Python
**Confidence:** HIGH

---

## Summary

Phase 1 builds the pure-Python CNAB 240 engine with zero external dependencies beyond the Python stdlib. The spec
source is the first-party `./Documents/sispag_cnab.md` (Itaú SISPAG v085), which contains exact byte positions,
field pictures, and bank-specific notes for every record type needed. Every implementation decision can be
derived directly from that spec document.

The critical technical constraints are: every record is exactly 240 bytes encoded in LATIN-1 (confirmed by spec and
STATE.md blocker note), numeric fields are zero-padded on the left, alphanumeric fields are space-padded on the
right, and payment values must use `decimal.Decimal` arithmetic throughout to avoid float rounding. The CRLF
problem on Windows is a confirmed blocker — file must be opened with `newline='\n'` or every record becomes 241
bytes when read back.

For PIX Transferência, the minimum required records per payment are: Segmento A (mandatory) + Segmento B PIX
(mandatory per spec section on PIX, not the generic Seg B for DOC/TED). The Segmento B PIX layout is distinct from
the generic Segmento B layout and contains the PIX key type code and the key value. This phase covers all six
record types: Header Arquivo, Header Lote, Segmento A, Segmento B PIX, Trailer Lote, Trailer Arquivo.

**Primary recommendation:** Implement a `cnab_field(value, length, numeric=False)` helper plus one dataclass per
record type. Build the builder as a pure function `build_cnab(payments, company_config) -> bytes`. Keep all
encoding and byte-count assertions in a dedicated validator that runs on the output before returning.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CNAB-01 | Header de Arquivo: bank code 341, layout version 080 | Spec p. header-arquivo: positions confirmed, version 080 field pos 015-017 |
| CNAB-02 | Header de Lote: operation C, payment type (Nota 4), form 45 PIX, layout 040 | Spec header-lote for cheque/OP/DOC/TED/PIX; form 45 = PIX Transferência per Nota 5 |
| CNAB-03 | Segmento A: câmara 009, identification type 04 (Chave Pix), value with implicit decimal | Spec seg-A layout, Nota 35 (câmara 009 for PIX), Nota 36 (type 04 = Chave Pix) |
| CNAB-04 | Segmento B PIX: PIX key type code + key value up to 100 chars | Spec seg-B-PIX layout, Nota 37 (type codes), Nota 40 (key formats) |
| CNAB-05 | Trailer Lote: correct record count and value sum | Spec trailer-lote layout, Nota 17 (count = all type 1,3,5 records in lot) |
| CNAB-06 | Trailer Arquivo: lot count and total record count | Spec trailer-arquivo layout, Nota 17 (lot count = type-1 records; total = all 0,1,3,5,9) |
| CNAB-07 | Every record exactly 240 bytes, LATIN-1, numeric zero-left, alpha space-right | Spec section 2.2 field format rules; confirmed encoding in STATE.md |
| CNAB-08 | Decimal arithmetic (never float) for all payment values | Python `decimal.Decimal`; value field picture 9(13)V9(02) = 15-char string, implicit 2 decimal places |
| VALD-01 | PIX key type auto-detection (CPF/CNPJ → 03, phone → 01, email → 02, UUID → 04) | Nota 37 + Nota 40 define all four types and their formats |
| VALD-02 | CPF/CNPJ check digit validation | Standard Brazilian CPF (11 digits, mod-11) and CNPJ (14 digits, mod-11) algorithms |
| VALD-03 | Mandatory field validation: pixKey, document, name, value per row | Pre-generation guard; maps to Segmento A + Segmento B PIX required fields |
| VALD-04 | Consolidated validation report with all errors before generation | Collect all errors, return structured list; UI layer renders in Phase 4 |
</phase_requirements>

---

## Standard Stack

### Core (zero external dependencies)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `decimal` (stdlib) | — | Monetary arithmetic | Avoids float rounding; `Decimal('150.00')` → integer cents representation |
| `re` (stdlib) | — | PIX key type detection | Regex patterns for phone, email, UUID, CPF/CNPJ |
| `dataclasses` (stdlib) | — | Record field containers | Lightweight typed containers for payment input data |
| `struct` / `str.ljust` / `str.zfill` (stdlib) | — | Field padding | CNAB-07: alpha = `ljust(n)[:n]`, numeric = `str(n).zfill(w)[-w:]` |
| `codecs` / `.encode('latin-1')` (stdlib) | — | File encoding | LATIN-1 / ISO-8859-1 as confirmed by spec and STATE.md |
| `pathlib` (stdlib) | — | Path operations | Per CLAUDE.md: use `pathlib.Path` exclusively |
| `pytest` | 9.0.2 (installable) | Unit testing | Not currently installed; must be installed in project venv |

**Installation (test only):**
```bash
pip install pytest==9.0.2
```

The engine module itself has zero install-time dependencies.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `decimal.Decimal` | `float` | `float` introduces rounding errors at 0.1 cents; Decimal is correct |
| custom field helper | `struct.pack` | `struct` is good for binary; CNAB is text-in-bytes so string padding + encode is cleaner |
| `re` for key detection | Manual branching | `re` is cleaner and testable; patterns are well-defined per Nota 40 |

---

## Architecture Patterns

### Recommended Project Structure

```
src/
└── cnab/
    ├── __init__.py
    ├── fields.py          # cnab_alpha(), cnab_numeric(), cnab_value() helpers
    ├── records.py         # One function per record type (header_arquivo, header_lote, etc.)
    ├── builder.py         # build_cnab(payments, config) -> bytes  (orchestrates records.py)
    ├── validator.py       # validate_payments(rows) -> list[ValidationError]
    └── pix_key.py         # detect_pix_key_type(raw_key) -> str ("01"|"02"|"03"|"04")
tests/
└── cnab/
    ├── test_fields.py     # Unit tests for padding/encoding helpers
    ├── test_records.py    # Byte-exact assertions for each record type
    ├── test_builder.py    # End-to-end known-input/known-output integration test
    ├── test_pix_key.py    # All four type detections + edge cases
    └── test_validator.py  # Missing field, zero value, bad CPF/CNPJ
```

### Pattern 1: Field Helper

**What:** A pair of pure functions that format a value into a fixed-width CNAB field and return a `str`.
**When to use:** Every record-building function calls these; never inline string formatting.

```python
# Source: SISPAG v085 spec sec 2.2 — field format rules
def cnab_alpha(value: str, length: int) -> str:
    """Alfanumérico: left-aligned, space-padded right, truncated to length."""
    return str(value or '').upper().ljust(length)[:length]

def cnab_numeric(value: int | str, length: int) -> str:
    """Numérico: right-aligned, zero-padded left, truncated to length."""
    return str(int(value or 0)).zfill(length)[-length:]

def cnab_value(amount: Decimal, integer_digits: int, decimal_digits: int) -> str:
    """Picture 9(n)V9(d): amount as integer string without separator.
    R$ 150,00 with picture 9(13)V9(02) -> '000000000015000'
    """
    total_width = integer_digits + decimal_digits
    factor = Decimal(10) ** decimal_digits
    cents = int(amount * factor)
    return str(cents).zfill(total_width)[-total_width:]
```

### Pattern 2: Record Builder Functions

**What:** Each record type is a single function that takes typed inputs and returns a 240-character `str`.
**When to use:** `builder.py` calls these in order; each function must assert `len(result) == 240`.

```python
# Source: SISPAG v085 spec — Header de Arquivo layout (pos 001–240)
def header_arquivo(company: CompanyConfig, generation_dt: datetime) -> str:
    r = ''
    r += cnab_numeric(341, 3)            # 001-003 BANCO
    r += cnab_numeric(0, 4)              # 004-007 LOTE = 0000
    r += cnab_numeric(0, 1)              # 008     TIPO REG = 0
    r += cnab_alpha('', 6)               # 009-014 BRANCOS
    r += cnab_numeric(80, 3)             # 015-017 LAYOUT ARQUIVO = 080
    r += cnab_numeric(2, 1)              # 018     EMPRESA INSCRICAO TIPO = 2 (CNPJ)
    r += cnab_numeric(company.cnpj, 14)  # 019-032 CNPJ
    r += cnab_alpha('', 20)              # 033-052 BRANCOS
    r += cnab_numeric(company.agency, 5) # 053-057 AGENCIA
    r += cnab_alpha(' ', 1)              # 058     BRANCO
    r += cnab_numeric(company.account, 12) # 059-070 CONTA
    r += cnab_alpha(' ', 1)              # 071     BRANCO
    r += cnab_numeric(company.dac, 1)    # 072     DAC
    r += cnab_alpha(company.name, 30)    # 073-102 NOME EMPRESA
    r += cnab_alpha('ITAU UNIBANCO S.A.', 30) # 103-132 NOME BANCO
    r += cnab_alpha('', 10)              # 133-142 BRANCOS
    r += cnab_numeric(1, 1)              # 143     ARQUIVO-CODIGO = 1 (REMESSA)
    r += generation_dt.strftime('%d%m%Y') # 144-151 DATA GERACAO DDMMAAAA
    r += generation_dt.strftime('%H%M%S') # 152-157 HORA GERACAO HHMMSS
    r += cnab_numeric(0, 9)              # 158-166 ZEROS
    r += cnab_numeric(0, 5)              # 167-171 DENSIDADE = 00000 (teleprocessamento)
    r += cnab_alpha('', 69)              # 172-240 BRANCOS
    assert len(r) == 240, f"header_arquivo: got {len(r)}"
    return r
```

### Pattern 3: Segmento A for PIX (Chave)

The PIX Transferência path in Segmento A has specific values mandated by the spec. These are the
non-obvious ones that differ from TED/DOC:

| Field | Position | Value | Source |
|-------|----------|-------|--------|
| CAMARA | 018-020 | `009` | Nota 35: "Para pagamento através de PIX deve ser informado 009 (SPI)" |
| BANCO FAVORECIDO | 021-023 | `000` or beneficiary bank (optional for key-based) | Spec: optional when key-based |
| AGENCIA CONTA FAVORECIDO | 024-043 | all zeros/spaces or populated | Spec Nota 11: optional when IDENT.TRANSF = 04 |
| MOEDA TIPO | 102-104 | `BRL` or `009` | Spec: "REA ou 009" — use `BRL` (3 chars, alpha field) |
| CODIGO ISPB | 105-112 | zeros (8 chars) | Nota 35: zeros for non-TED-to-Corretora |
| IDENT. TRANSFERENCIA | 113-114 | `04` | Nota 36: "04 = Chave Pix" |
| ZEROS | 115-119 | `00000` | Spec padding |
| VALOR DO PAGTO | 120-134 | 15-char numeric, picture 9(13)V9(02) | CNAB-08 |
| NOSSO NUMERO | 135-149 | blanks (remessa) | Nota 12 |
| BRANCOS | 150-154 | spaces | Nota 42: agency for conta pagamento (optional) |
| DATA EFETIVA | 155-162 | zeros (remessa) | (*) retorno only |
| VALOR EFETIVO | 163-177 | zeros (remessa) | (*) retorno only |
| FINALIDADE DETALHE | 178-197 | blanks | Nota 13: blanks unless contracted |
| N DO DOCUMENTO | 198-203 | zeros (remessa) | (*) retorno only |
| N DE INSCRICAO | 204-217 | CPF/CNPJ (14 chars) | Nota 15: mandatory for PIX |
| FINALIDADE DOC/STATUS | 218-219 | spaces | Not used for PIX |
| FINALIDADE TED | 220-224 | spaces | Not used for PIX |
| BRANCOS | 225-229 | spaces | Padding |
| AVISO | 230 | `0` | Nota 16: no notice |
| OCORRENCIAS | 231-240 | spaces (remessa) | (*) retorno only |

### Pattern 4: Segmento B PIX (distinct from generic Seg B)

The spec has TWO Segmento B layouts:
1. Generic (pos 640–687): for DOC/TED/cheque — contains address fields and email
2. PIX-specific (pos 700–721): for PIX Transferência — contains PIX key type + key value

**Use the PIX-specific layout** for this project. Key fields:

| Field | Position | Size | Notes |
|-------|----------|------|-------|
| BANCO | 001-003 | 9(03) | 341 |
| LOTE | 004-007 | 9(04) | same as Seg A |
| TIPO REG | 008 | 9(01) | 3 |
| NUM REG | 009-013 | 9(05) | same sequential number as paired Seg A (Nota 9) |
| SEGMENTO | 014 | X(01) | B |
| TIPO CHAVE | 015-016 | X(02) | Nota 37: 01/02/03/04 |
| BRANCO | 017 | X(01) | 1 space |
| INSCRICAO TIPO | 018 | 9(01) | 1=CPF, 2=CNPJ |
| INSCRICAO NUM | 019-032 | 9(14) | CPF/CNPJ (14 digits, zero-left) |
| BRANCOS | 033-062 | X(30) | spaces |
| INFO ENTRE USUARIOS | 063-127 | 9(65) | Nota 39: optional message; zeros if unused |
| CHAVE PIX | 128-227 | X(100) | Nota 40: the actual key, left-aligned, space-padded |
| BRANCOS | 228-230 | X(03) | spaces |
| OCORRENCIAS | 231-240 | X(10) | spaces (remessa) |

**IMPORTANT:** The NUM REG (positions 009-013) in Segmento B PIX uses the SAME sequential number
as the paired Segmento A. It does NOT get its own sequence number. (Nota 9: "Para o Segmento B...
conterá o mesmo número atribuído no Segmento A correspondente.")

### Pattern 5: PIX Key Type Detection

```python
# Source: SISPAG v085 Nota 37 + Nota 40
import re

_CPF_RE = re.compile(r'^\d{11}$')
_CNPJ_RE = re.compile(r'^\d{14}$')
_PHONE_RE = re.compile(r'^\+\d{10,13}$')   # E.164: +55DDD9digits
_EMAIL_RE = re.compile(r'^[^@]+@[^@]+\.[^@]+$')
_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)

def detect_pix_key_type(raw_key: str) -> str:
    """Return SISPAG Nota 37 code for the PIX key type.

    Returns:
        '01' phone, '02' email, '03' CPF/CNPJ, '04' random UUID
    Raises:
        ValueError if key does not match any known format.
    """
    key = raw_key.strip()
    if _UUID_RE.match(key):
        return '04'
    if _PHONE_RE.match(key):
        return '01'
    if _EMAIL_RE.match(key):
        return '02'
    if _CPF_RE.match(key) or _CNPJ_RE.match(key):
        return '03'
    raise ValueError(f"Cannot detect PIX key type for: {raw_key!r}")
```

**Detection order matters:** UUID must be checked before CPF/CNPJ because a UUID with all-numeric
characters could theoretically match the digit-count patterns. The UUID regex uses `[0-9a-f]` with
hyphens, so it is unambiguous.

**VTEX pixKey field reality:** Based on the sample in `./Documents/Vtex API Info.txt`, the `pixKey`
field contains the raw value (e.g., `"51300907134"` — an 11-digit CPF). No type hint is present
in the VTEX response. The detector must infer from format alone.

### Pattern 6: Trailer Lote Record Count Formula

Per Nota 17: "Trailer de Lote: total de registros de tipo 1, 3 e 5 no lote."

For N payments (each with Seg A + Seg B): total records in lote = 1 (header lote) + 2N (Seg A + Seg B per payment) + 1 (trailer lote) = 2N + 2.

The success criterion states "Trailer counts match 2N+2 formula for N payments" — this is the
test assertion to write.

### Pattern 7: Trailer Arquivo Record Count Formula

Per Nota 17:
- TOTAL QTDE DE LOTES = count of type-1 records = 1 (for single PIX lot)
- TOTAL QTDE REGISTROS = all type 0,1,3,5,9 records = 1 + 1 + 2N + 1 + 1 = 2N + 4

### Anti-Patterns to Avoid

- **Float for monetary values:** `float('150.00') * 100` can return `14999.999999999998`. Use
  `Decimal('150.00') * 100` or `int(Decimal('150.00') * Decimal('100'))`.
- **String concatenation without width check:** Build each record field-by-field and `assert len == 240`
  before encoding. Never skip the assertion in tests.
- **CRLF on Windows:** Do NOT use default `open(path, 'w')` — it will add CR before every LF on
  Windows, making each line 241 bytes. Use `open(path, 'w', encoding='latin-1', newline='\n')` or
  write raw bytes with `open(path, 'wb')` and encode each line manually.
- **Inline `\n` at record end:** Records are 240 bytes. The newline is the line separator between
  records, not part of the record. When writing as bytes: `b'\n'.join(records)` + trailing `b'\n'`.
- **Generic Seg B for PIX:** The spec shows two distinct Segmento B layouts. Using the
  DOC/TED address layout (pos 033-062 = address) instead of the PIX layout (pos 033-062 = brancos,
  pos 063-127 = info entre usuarios, pos 128-227 = chave pix) will produce an invalid file.
- **Using Tipo de Movimento 000 vs blanks:** Nota 10 confirms `000` = "Inclusão de pagamento"
  (remessa). Positions 015-017 are numeric picture 9(03), so `000` is correct for new payments.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CPF check digits | Custom mod-11 loop | Well-known 2-weight algorithm (pure Python, 10 lines) | Standard mod-11 is documented by Receita Federal; edge cases are weight-reversal at 11 → 0, remainder of 10 → 0 |
| CNPJ check digits | Custom implementation | Same mod-11 with different weights (8-cycle repeating 2-9) | CNPJ has two check digits; both needed for VALD-02 |
| Value encoding | Custom formatting | `cnab_value()` helper using Decimal | The "V" (vírgula assumida) picture is a source of off-by-one bugs if hand-calculated |
| UUID detection | `try: uuid.UUID(key)` | Regex `r'^[0-9a-f]{8}-...'` | `uuid.UUID()` constructor normalizes; the regex is explicit about format expected by DICT |

**Key insight:** CPF/CNPJ validation is algorithmically trivial but has several documented edge
cases (all-zero CPFs like `000.000.000-00` are technically invalid; CNPJs starting with 5 zeros
need Seg B per Nota 15 observation). Implement once, test exhaustively with known-good/bad numbers.

---

## Critical Spec Details (field-by-field)

### Header de Arquivo — Confirmed Field Positions

| Field | Pos | Picture | Value (remessa) |
|-------|-----|---------|-----------------|
| BANCO | 001-003 | 9(03) | `341` |
| LOTE | 004-007 | 9(04) | `0000` |
| TIPO REG | 008 | 9(01) | `0` |
| BRANCOS | 009-014 | X(06) | spaces |
| LAYOUT ARQUIVO | 015-017 | 9(03) | `080` |
| EMPRESA INSCR TIPO | 018 | 9(01) | `2` (CNPJ) |
| CNPJ | 019-032 | 9(14) | company CNPJ |
| BRANCOS | 033-052 | X(20) | spaces |
| AGENCIA | 053-057 | 9(05) | company agency |
| BRANCO | 058 | X(01) | space |
| CONTA | 059-070 | 9(12) | company account |
| BRANCO | 071 | X(01) | space |
| DAC | 072 | 9(01) | company DAC |
| NOME EMPRESA | 073-102 | X(30) | company name |
| NOME BANCO | 103-132 | X(30) | `ITAU UNIBANCO S.A.` |
| BRANCOS | 133-142 | X(10) | spaces |
| ARQUIVO CODIGO | 143 | 9(01) | `1` (remessa) |
| DATA GERACAO | 144-151 | 9(08) | `DDMMAAAA` |
| HORA GERACAO | 152-157 | 9(06) | `HHMMSS` |
| ZEROS | 158-166 | 9(09) | `000000000` |
| DENSIDADE | 167-171 | 9(05) | `00000` (teleproc) |
| BRANCOS | 172-240 | X(69) | spaces |

### Header de Lote (PIX Transferência) — Key Fields

| Field | Pos | Picture | Value |
|-------|-----|---------|-------|
| BANCO | 001-003 | 9(03) | `341` |
| LOTE | 004-007 | 9(04) | `0001` (first lot) |
| TIPO REG | 008 | 9(01) | `1` |
| TIPO OPERACAO | 009 | X(01) | `C` (crédito) |
| TIPO PAGAMENTO | 010-011 | 9(02) | `20` (Fornecedores) — Nota 4 |
| FORMA PAGAMENTO | 012-013 | 9(02) | `45` (PIX Transferência) — Nota 5 |
| LAYOUT LOTE | 014-016 | 9(03) | `040` |
| BRANCO | 017 | X(01) | space |
| INSCRICAO TIPO | 018 | 9(01) | `2` (CNPJ) |
| CNPJ | 019-032 | 9(14) | debit company CNPJ |
| IDENT LANCAMENTO | 033-036 | X(04) | spaces (Nota 13: blancos unless contracted) |
| BRANCOS | 037-052 | X(16) | spaces |
| AGENCIA | 053-057 | 9(05) | debit agency |
| BRANCO | 058 | X(01) | space |
| CONTA | 059-070 | 9(12) | debit account |
| BRANCO | 071 | X(01) | space |
| DAC | 072 | 9(01) | DAC |
| NOME EMPRESA | 073-102 | X(30) | company name |
| FINALIDADE LOTE | 103-132 | X(30) | spaces (Nota 6: blancos unless contracted) |
| HISTORICO C/C | 133-142 | X(10) | spaces (Nota 7: blancos unless contracted) |
| ENDERECO | 143-172 | X(30) | company address |
| NUMERO | 173-177 | 9(05) | address number |
| COMPLEMENTO | 178-192 | X(15) | address complement |
| CIDADE | 193-212 | X(20) | city |
| CEP | 213-220 | 9(08) | postal code |
| ESTADO | 221-222 | X(02) | state abbrev |
| BRANCOS | 223-230 | X(08) | spaces |
| OCORRENCIAS | 231-240 | X(10) | spaces (remessa) |

**Note on TIPO PAGAMENTO:** The requirement says "payment type per Nota 4". For supplier payments (Fornecedores),
Nota 4 code is `20`. The system generates payments to beneficiaries (external people), which maps to
Fornecedores (20) or Diversos (98). `20` is the most common for this use case. This decision should be
configurable in company config so the operator can set it per their Itaú contract.

### Segmento A (PIX Chave) — Complete Field Map

| Field | Pos | Picture | Value (remessa) |
|-------|-----|---------|-----------------|
| BANCO | 001-003 | 9(03) | `341` |
| LOTE | 004-007 | 9(04) | lot number |
| TIPO REG | 008 | 9(01) | `3` |
| NUM REG | 009-013 | 9(05) | sequential within lot, starts at `00001` |
| SEGMENTO | 014 | X(01) | `A` |
| TIPO MOVIMENTO | 015-017 | 9(03) | `000` (inclusão) |
| CAMARA | 018-020 | 9(03) | `009` (SPI/PIX) |
| BANCO FAVORECIDO | 021-023 | 9(03) | `000` (optional for key-based PIX) |
| AGENCIA CONTA FAV | 024-043 | X(20) | zeros/spaces (optional for key-based PIX) |
| NOME FAVORECIDO | 044-073 | X(30) | beneficiary name |
| SEU NUMERO | 074-093 | X(20) | company document reference |
| DATA PAGTO | 094-101 | 9(08) | `DDMMAAAA` payment date |
| MOEDA TIPO | 102-104 | X(03) | `BRL` (3 alpha chars) |
| CODIGO ISPB | 105-112 | X(08) | spaces/zeros (Nota 35: zeros for non-TED-Corretora) |
| IDENT TRANSFERENCIA | 113-114 | X(02) | `04` (Chave Pix) per Nota 36 |
| ZEROS | 115-119 | 9(05) | `00000` |
| VALOR DO PAGTO | 120-134 | 9(13)V9(02) | 15-char, picture V = implicit decimal |
| NOSSO NUMERO | 135-149 | X(15) | spaces (remessa — bank fills on return) |
| BRANCOS | 150-154 | X(05) | spaces (Nota 42: optional agency for conta pagamento) |
| DATA EFETIVA | 155-162 | 9(08) | `00000000` (remessa) |
| VALOR EFETIVO | 163-177 | 9(13)V9(02) | zeros (remessa) |
| FINALIDADE DETALHE | 178-197 | X(20) | spaces (Nota 13) |
| N DO DOCUMENTO | 198-203 | 9(06) | zeros (remessa) |
| N DE INSCRICAO | 204-217 | 9(14) | CPF/CNPJ 14 digits |
| FINALIDADE DOC/STATUS | 218-219 | X(02) | spaces |
| FINALIDADE TED | 220-224 | X(05) | spaces |
| BRANCOS | 225-229 | X(05) | spaces |
| AVISO | 230 | X(01) | `0` (no notice) |
| OCORRENCIAS | 231-240 | X(10) | spaces (remessa) |

### Trailer de Lote

| Field | Pos | Picture | Value |
|-------|-----|---------|-------|
| BANCO | 001-003 | 9(03) | `341` |
| LOTE | 004-007 | 9(04) | lot number |
| TIPO REG | 008 | 9(01) | `5` |
| BRANCOS | 009-017 | X(09) | spaces |
| TOTAL QTDE REG | 018-023 | 9(06) | 2N+2 (header lote + N*Seg A + N*Seg B + trailer lote) |
| TOTAL VALOR PAGTOS | 024-041 | 9(16)V9(02) | sum of all payment values (18-char, picture V = implicit 2 dec) |
| ZEROS | 042-059 | 9(18) | zeros |
| BRANCOS | 060-230 | X(171) | spaces |
| OCORRENCIAS | 231-240 | X(10) | spaces (remessa) |

### Trailer de Arquivo

| Field | Pos | Picture | Value |
|-------|-----|---------|-------|
| BANCO | 001-003 | 9(03) | `341` |
| LOTE | 004-007 | 9(04) | `9999` |
| TIPO REG | 008 | 9(01) | `9` |
| BRANCOS | 009-017 | X(09) | spaces |
| TOTAL QTDE LOTES | 018-023 | 9(06) | number of lots (=1 for single PIX lot) |
| TOTAL QTDE REG | 024-029 | 9(06) | all records: 1 + (2N+2) + 1 = 2N+4 |
| BRANCOS | 030-240 | X(211) | spaces |

---

## Common Pitfalls

### Pitfall 1: Windows CRLF Makes Records 241 Bytes
**What goes wrong:** Opening the output file with `open(path, 'w', encoding='latin-1')` on Windows
causes Python to write `\r\n` (CRLF) at end of each line instead of `\n` (LF). The bank's validator
counts bytes per line and rejects any record not exactly 240 bytes.
**Why it happens:** Python's default text mode on Windows translates `\n` to `\r\n`.
**How to avoid:** Use `open(path, 'w', encoding='latin-1', newline='\n')` explicitly, OR write bytes:
`b'\n'.join(record.encode('latin-1') for record in records)`.
**Warning signs:** `len(line.rstrip('\n')) == 241` in a hex dump; file is larger than expected.

### Pitfall 2: Off-by-One in Value Encoding
**What goes wrong:** `R$ 150,00` → field picture `9(13)V9(02)` must produce `000000000015000`
(15 chars total, value × 100 as integer). Confusing the integer vs decimal split causes wrong amounts.
**Why it happens:** The `V` in the picture means "vírgula assumida" — the decimal point is assumed/implicit.
`9(13)V9(02)` means 13 integer digits + 2 decimal digits = 15 total characters.
**How to avoid:** Use `cnab_value(Decimal('150.00'), 13, 2)` → `'000000000015000'`. Write a dedicated
unit test asserting this exact output.
**Warning signs:** Payments are off by factor of 100 (100x too large or too small).

### Pitfall 3: Sequential Record Number Reuse Between Seg A and Seg B
**What goes wrong:** Assigning a new sequential number to Segmento B instead of reusing the number
from the paired Segmento A.
**Why it happens:** The builder increments a counter for every record including B segments.
**How to avoid:** Per Nota 9: "Para o Segmento B, C, D, E, F, W e Z, por se tratar de complemento de
informações, conterá o mesmo número atribuído no Segmento A correspondente." Track `seq_a = 1` and
emit both Seg A (seq=seq_a) and Seg B (seq=seq_a) before incrementing.
**Warning signs:** Trailer Lote count is 2N+2 but record numbers are not paired.

### Pitfall 4: Using Generic Segmento B Layout Instead of PIX Segmento B Layout
**What goes wrong:** The spec defines two distinct Segmento B layouts. The generic one (for DOC/TED/cheque)
has address fields at positions 033-127 and email at 128-227. The PIX one has `BRANCOS` at 033-062,
`INFORMACOES ENTRE USUARIOS` (numeric!) at 063-127, and `CHAVE PIX` at 128-227.
**Why it happens:** Both are labeled "Segmento B" in the spec; the PIX variant is a separate table.
**How to avoid:** Implement `segmento_b_pix()` as a distinct function. Reference spec page lines 700-721.
**Warning signs:** Key is placed at wrong byte position; bank returns error code `BI` (CNPJ/CPF inválido PIX).

### Pitfall 5: CPF/CNPJ Validation Edge Cases
**What goes wrong:** Accepting all-same-digit CPFs (e.g., `111.111.111-11`) which pass the check-digit
formula but are known-invalid.
**Why it happens:** The mod-11 algorithm produces valid digits for repeated sequences.
**How to avoid:** Add explicit rejection of all-same-digit patterns after the mod-11 check.
**Warning signs:** VTEX `document` field might contain these if a test beneficiary was created manually.

### Pitfall 6: LATIN-1 vs CP1252 Encoding
**What goes wrong:** Encoding as CP1252 instead of LATIN-1 (ISO-8859-1) causes bytes 0x80-0x9F to differ.
**Why it happens:** CP1252 maps bytes 0x80-0x9F to typographic characters; ISO-8859-1 maps them to
control characters.
**How to avoid:** Use `.encode('latin-1')` not `.encode('cp1252')`. The spec recommends uppercase ASCII
text only and discourages accented characters — this makes encoding practically equivalent, but use
`latin-1` as the canonical choice per STATE.md confirmation.
**Warning signs:** Encoding errors raised on beneficiary names with `ã`, `ç`, etc. — strip or replace
accents for CNAB text before encoding.

### Pitfall 7: Valor Total in Trailer Lote — Picture Width
**What goes wrong:** The Trailer Lote value sum field is picture `9(16)V9(02)` = 18 characters total,
but Header/Seg A value fields are `9(13)V9(02)` = 15 characters. Mixing up widths corrupts the trailer.
**Why it happens:** Copy-paste from Seg A value field definition.
**How to avoid:** `cnab_value(total, 16, 2)` for trailer (18 chars), `cnab_value(amount, 13, 2)` for Seg A (15 chars).

---

## Code Examples

### Value Encoding Verification

```python
# Source: SISPAG v085 spec — picture 9(13)V9(02), success criterion SC-2
from decimal import Decimal

def cnab_value(amount: Decimal, integer_digits: int, decimal_digits: int) -> str:
    total_width = integer_digits + decimal_digits
    factor = Decimal(10) ** decimal_digits
    cents = int(amount * factor)
    return str(cents).zfill(total_width)[-total_width:]

# Unit test assertion:
assert cnab_value(Decimal('150.00'), 13, 2) == '000000000015000'
assert cnab_value(Decimal('0.01'), 13, 2)   == '000000000000001'
assert cnab_value(Decimal('9999999999999.99'), 13, 2) == '999999999999999'
```

### CPF Validation

```python
# Source: Receita Federal Brazil standard mod-11 algorithm
def validate_cpf(cpf: str) -> bool:
    digits = re.sub(r'\D', '', cpf)
    if len(digits) != 11:
        return False
    if len(set(digits)) == 1:      # All same digit — reject
        return False
    # First check digit
    weights = range(10, 1, -1)
    s = sum(int(d) * w for d, w in zip(digits[:9], weights))
    r = (s * 10) % 11
    if r == 10:
        r = 0
    if int(digits[9]) != r:
        return False
    # Second check digit
    weights = range(11, 1, -1)
    s = sum(int(d) * w for d, w in zip(digits[:10], weights))
    r = (s * 10) % 11
    if r == 10:
        r = 0
    return int(digits[10]) == r
```

### CNPJ Validation

```python
# Source: Receita Federal Brazil CNPJ mod-11 algorithm
def validate_cnpj(cnpj: str) -> bool:
    digits = re.sub(r'\D', '', cnpj)
    if len(digits) != 14:
        return False
    if len(set(digits)) == 1:
        return False
    # First check digit — weights cycle 5,4,3,2,9,8,7,6,5,4,3,2
    weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    s = sum(int(d) * w for d, w in zip(digits[:12], weights1))
    r = s % 11
    first = 0 if r < 2 else (11 - r)
    if int(digits[12]) != first:
        return False
    # Second check digit — weights cycle 6,5,4,3,2,9,8,7,6,5,4,3,2
    weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    s = sum(int(d) * w for d, w in zip(digits[:13], weights2))
    r = s % 11
    second = 0 if r < 2 else (11 - r)
    return int(digits[13]) == second
```

### Builder Orchestration Pattern

```python
# Source: SISPAG v085 spec — file structure section 2.2
def build_cnab(payments: list[PaymentInput], config: CompanyConfig, payment_date: date) -> bytes:
    records = []
    records.append(header_arquivo(config, datetime.now()))
    records.append(header_lote(config, lot_number=1))
    total_value = Decimal('0')
    for seq, payment in enumerate(payments, start=1):
        records.append(segmento_a(config, payment, seq, payment_date))
        records.append(segmento_b_pix(config, payment, seq))  # seq SAME as Seg A
        total_value += payment.value
    records.append(trailer_lote(lot_number=1, record_count=len(records), total_value=total_value))
    records.append(trailer_arquivo(lot_count=1, total_records=len(records) + 1))

    # Each record is 240 chars; encode to bytes; join with LF
    for i, r in enumerate(records):
        assert len(r) == 240, f"Record {i} is {len(r)} chars, expected 240"

    content = '\n'.join(records) + '\n'
    return content.encode('latin-1')
```

**Note:** `trailer_arquivo` total record count must include itself. The pattern above computes
`len(records) + 1` before appending it. An alternative is to append the trailer with a placeholder,
then compute the total. Either approach is correct as long as the final count = 2N + 4.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| TED/DOC via CNAB | PIX Transferência via CNAB (Segmentos A+B) | ~2020-2021 Banco Central PIX launch | Seg B PIX is now mandatory; generic Seg B is for DOC/TED only |
| `9(03)` câmara = bank code | `009` for SPI (PIX) | PIX adoption | Câmara 009 is the SPI indicator, not a bank code |
| Segmento A MOEDA = `REA` (old text) | `BRL` or `009` both accepted | Ongoing | Spec says "REA ou 009"; use `BRL` as the 3-char alpha value |

---

## Open Questions

1. **TIPO DE PAGAMENTO for the lot (Nota 4 code)**
   - What we know: Nota 4 lists `20 = Fornecedores`, `98 = Diversos`. Both are used for external payments.
   - What's unclear: Which code does PrettyNew's Itaú contract expect? The spec is compatible with both.
   - Recommendation: Make `tipo_pagamento` a field in `CompanyConfig` (defaulting to `20`). Document in
     the settings screen (Phase 2) that the operator must match their contract.

2. **AGENCIA CONTA FAVORECIDO when using Chave PIX (key-based transfer)**
   - What we know: Per spec Nota 11 and Nota 36 section: "Se o campo COMPLEMENTO DE REGISTRO estiver
     preenchido com '04' (Chave Pix) nas posições 113 a 114, esse campo é Opcional."
   - What's unclear: Should the builder fill zeros or spaces in positions 024-043 when using key-based?
   - Recommendation: Fill with all zeros (`'0' * 20`) — numeric picture X(20) with zero fill is safer
     than spaces for a field adjacent to numeric fields.

3. **INFORMACOES ENTRE USUARIOS (Seg B PIX, pos 063-127) — numeric picture**
   - What we know: The spec declares this as `9(65)` (numeric, 65 chars). Filling with zeros is correct
     for an empty/unused message.
   - What's unclear: Whether some Itaú implementations accept spaces (alpha-style) despite numeric picture.
   - Recommendation: Fill with zeros per picture specification. Use `cnab_numeric('', 65)` → `'0' * 65`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | Yes | 3.14.3 | — |
| `decimal` (stdlib) | CNAB-08 | Yes | bundled | — |
| `re` (stdlib) | VALD-01 | Yes | bundled | — |
| `dataclasses` (stdlib) | Record types | Yes | bundled | — |
| `struct` / `codecs` (stdlib) | CNAB-07 | Yes | bundled | — |
| `pathlib` (stdlib) | File output | Yes | bundled | — |
| `pytest` | Test suite | No (not installed) | 9.0.2 available | Install: `pip install pytest==9.0.2` |

**Missing dependencies with no fallback:**
- None — the engine has zero runtime dependencies beyond Python stdlib.

**Missing dependencies with fallback:**
- `pytest`: Not installed in base Python 3.14.3 env. Must install in project venv before running
  tests. Wave 0 task: `pip install pytest==9.0.2`.

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 1 |
|-----------|-------------------|
| Stack: Python + PySide6 (Qt) | Phase 1 is pure Python — no UI, no PySide6 needed yet |
| SQLite for metadata | Not needed in Phase 1 (no DB layer) |
| Credentials never hardcoded | Not relevant yet (no credentials used in Phase 1) |
| CNAB: each record exactly 240 bytes | CNAB-07: assert `len(record) == 240` before encoding |
| Numeric fields zero-padded left | `cnab_numeric()` helper: `str(v).zfill(n)[-n:]` |
| Alphanumeric fields space-padded right | `cnab_alpha()` helper: `str(v).upper().ljust(n)[:n]` |
| FEBRABAN encoding | LATIN-1 confirmed per spec and STATE.md |
| `pathlib.Path` exclusively | Use for any file output in builder |
| No hardcoded paths | Output folder via config parameter |
| pytest for tests | Install `pytest==9.0.2` in project venv |

---

## Sources

### Primary (HIGH confidence)
- `./Documents/sispag_cnab.md` — Itaú SISPAG v085 spec: all record layouts, all field positions,
  Notes 1-42 including PIX-specific notes (35, 36, 37, 39, 40)
- `./Documents/Vtex API Info.txt` — VTEX API response schema showing `pixKey` field format
- `./CLAUDE.md` — Project constraints (encoding, field padding rules)
- `./planning/STATE.md` — Confirmed decisions: LATIN-1 encoding, CRLF blocker on Windows

### Secondary (MEDIUM confidence)
- Python `decimal` module docs (training knowledge, stdlib unchanged in 3.14) — Decimal arithmetic
- Receita Federal CPF/CNPJ validation algorithms — well-documented public domain algorithm, standard
  across all Brazilian financial software

### Tertiary (LOW confidence)
- None — all critical implementation details derive from the first-party spec

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero external deps; all stdlib; confirmed Python 3.14 available
- Architecture: HIGH — derived directly from spec byte positions and Nota definitions
- Pitfalls: HIGH (CRLF, value encoding) — confirmed in STATE.md + spec; MEDIUM (edge cases) — experience-based

**Research date:** 2026-03-30
**Valid until:** 2026-06-30 (spec is stable; Itaú releases new SISPAG versions infrequently)
