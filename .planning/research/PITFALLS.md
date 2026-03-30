# Domain Pitfalls: CNAB PIX Payment File Generation

**Domain:** CNAB 240 SISPAG Itaú — PIX Transferência via Chave
**Researched:** 2026-03-30
**Sources:** Official SISPAG CNAB v085 documentation (sispag_cnab.md), VTEX MasterData API response (Vtex API Info.txt), PROJECT.md

---

## Critical Pitfalls

Mistakes that cause file rejection by the bank, payments to wrong recipients, or silent money loss.

---

### Pitfall 1: Record Not Exactly 240 Bytes

**What goes wrong:** Each record written to the CNAB file is not precisely 240 bytes. The bank validator rejects the entire file with no per-payment detail — every payment in the batch fails.

**Why it happens:** Python string operations work in characters, not bytes. When writing a record, if any field overflows its declared width or padding is calculated against character length instead of encoded byte length, the final record will be the wrong length. Newline handling is a second vector: writing `\r\n` (CRLF) instead of `\n` (LF) adds one byte per record, immediately breaking byte-count arithmetic on a 240-byte record boundary.

**Consequences:** Full file rejection. The bank returns error HM (ERRO NO REGISTRO HEADER DE ARQUIVO) or AG (NÚMERO DO LOTE INVÁLIDO) depending on where the first malformed record appears. All payments are blocked with no partial success.

**Prevention:**
- Assert `len(record.encode('latin-1')) == 240` for every record immediately before writing to file. Raise hard exceptions during development; log and abort in production.
- Open the output file with `open(path, 'w', encoding='latin-1', newline='\n')` — specify newline explicitly to prevent platform-specific CRLF on Windows.
- Build records field-by-field using a helper that enforces field width: `field.ljust(width)[:width]` for alphanumeric and `str(value).zfill(width)[-width:]` for numeric. Never concatenate raw strings without width enforcement.
- Write a unit test that reads back the generated file and asserts every line is exactly 240 characters followed by `\n`.

**Detection warning signs:**
- A generated file whose size in bytes is not `(record_count * 241)` — 240 chars + LF per record.
- Bank returns HM on first submission.
- Running `wc -c` on the file divided by number of lines does not equal 241.

**Phase:** Phase 1 (Core CNAB generation). Must be established before any other work.

---

### Pitfall 2: Wrong Character Encoding — Using UTF-8 Instead of Latin-1

**What goes wrong:** The CNAB file is written in UTF-8. Accented characters (ã, é, ç, ô) and some special characters encode to multi-byte sequences in UTF-8, silently expanding field byte-widths beyond 240. Even if names are "safe", the file encoding declaration itself causes issues with the bank's mainframe-era parser.

**Why it happens:** Python 3 defaults to UTF-8 everywhere. Developers forget to specify encoding when opening files. The FEBRABAN standard (and Itaú's SISPAG documentation) specifies that alphanumeric fields should avoid special characters and accents; when they appear anyway (as they will in beneficiary names from VTEX), encoding must be Latin-1, not UTF-8.

**Consequences:**
- Records silently exceed 240 bytes if any name contains characters above ASCII 127.
- Bank rejects file due to unrecognized byte sequences or wrong record length.
- Worst case: a name with two accented characters in a 30-byte name field produces a record that is 32 bytes and the remaining fields of the record shift left, corrupting every subsequent field position — the bank may process a payment to wrong account data.

**Prevention:**
- Always write: `open(path, 'w', encoding='latin-1', newline='\n')`.
- Before placing any name or text in a CNAB field, sanitize it: strip accents using `unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')` and uppercase it.
- The documentation explicitly states: "Preferencialmente, todos os caracteres devem ser maiúsculos. Aconselha-se a não utilização de caracteres especiais (ex.: 'Ç', '?', etc.) e acentuação gráfica."
- Unit test: encode the name "João da Silva" through the sanitizer and verify it produces exactly the expected byte count and content.

**Detection warning signs:**
- Any beneficiary name from VTEX that contains Portuguese accents (common in Brazilian names).
- VTEX response for `firstName`/`lastName`/`receiverName` often contains lowercase accented text (e.g., `"fabio michels"` — this is mild, but `"João"` or `"Conceição"` will be present in production data).

**Phase:** Phase 1. Sanitization must be part of the field-building utility, not an afterthought.

---

### Pitfall 3: Wrong PIX Key Type Code in Segmento B

**What goes wrong:** The TIPO CHAVE field (positions 15-16 of Segmento B PIX) is set to the wrong type code for the key being sent. For example, a CPF key `51300907134` is sent with type `04` (Chave Aleatória) instead of `03` (CPF/CNPJ). The bank rejects the payment with occurrence `BI` (CNPJ/CPF DO FAVORECIDO INVÁLIDO / DOCUMENTO FAVORECIDO INVÁLIDO PIX) or the SPI infrastructure fails to route.

**Why it happens:** The VTEX MasterData field `pixKey` is a raw string with no metadata about key type. The system must detect the type from the key's content. This detection logic is easy to get wrong for edge cases.

**Key type detection rules (from CNAB documentation, Note 37 and Note 40):**
- `01` = Telefone: key begins with `+` followed by country code, DDD, and 9-digit number.
- `02` = E-mail: key contains `@`, max 77 characters.
- `03` = CPF/CNPJ: CPF is exactly 11 digits (no formatting); CNPJ is exactly 14 digits (no formatting). Both digits only, no dots or dashes.
- `04` = Chave Aleatória: UUID format — 32 hex digits in 5 blocks `XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX` (36 chars total including hyphens).

**Consequences:** Payment rejected. Occurrence code `BI` in the return file. Payment does not reach beneficiary.

**Prevention:**
- Implement a `detect_pix_key_type(key: str) -> tuple[str, str]` function that returns `(type_code, normalized_key)`. Normalize the key as part of detection (strip spaces, validate format).
- Exact detection logic:
  - If key matches `^\+\d{10,15}$`: type `01`.
  - If `@` present and len <= 77: type `02`.
  - If key is 36 chars matching UUID pattern `[0-9a-fA-F]{8}-...-[0-9a-fA-F]{12}`: type `04`.
  - If key is exactly 11 digits: type `03` (CPF).
  - If key is exactly 14 digits: type `03` (CNPJ).
  - Anything else: validation error — do not generate CNAB record, surface to user.
- Unit test each pattern with real examples including edge cases (CNPJ starting with zeros, phone with country code 55 vs +55).
- The VTEX sample data shows `pixKey: "51300907134"` — this is an 11-digit CPF, type `03`. Validate this assumption against production data before go-live.

**Detection warning signs:**
- VTEX `pixKey` field contains a formatted value like `"051.300.907-13"` — must be stripped before encoding.
- Return file shows occurrence `BI` or `IO`.

**Phase:** Phase 1 validation and generation. Also requires pre-generation validation UI in Phase 2.

---

### Pitfall 4: Decimal Encoding of Payment Values — The Implicit Decimal (Picture V)

**What goes wrong:** A payment value of R$ 150.00 is encoded as `000000000015000` (correct) but coded as `000000000150000` (extra zero, becomes R$ 1,500.00) or `000000000001500` (missing zero, becomes R$ 1.50). The value field uses an implicit decimal: `9(13)V9(02)` means 13 digits of integer part + 2 decimal digits, all 15 chars wide, no decimal point character in the file.

**Why it happens:**
- Misunderstanding of "picture V" (vírgula assumida — assumed comma). The CNAB documentation states: "num campo com picture '9(5)V9(2)', o número '876,54' será representado por '0087654'." There is no decimal separator in the field — the position of the decimal is implicit in the field definition.
- Floating point arithmetic in Python: `150.00 * 100` may produce `14999.999999999998` due to float representation. Using `round()` incorrectly or converting from `float` directly introduces cents-off errors.
- Excel import: the value column from the uploaded spreadsheet may come in as a float `150.0`, a string `"150,00"` (Brazilian locale with comma), or a string `"R$ 150.00"`. Each requires different parsing.

**Consequences:** Wrong payment amounts. Overpayment or underpayment. If underpayment, the bank may still process it (Itaú does not always validate amounts against DICT). Silent financial loss.

**Prevention:**
- Use Python's `decimal.Decimal` for all monetary values throughout the system. Never use `float` for money.
- Parse Excel values with explicit handling: strip `R$`, replace `,` with `.`, then `Decimal(cleaned_string)`.
- To encode: `int(value * 100)` — but do this as `int(Decimal(str(value)) * 100)` or `value.quantize(Decimal('0.01'))` then multiply.
- Encode as: `str(cents_integer).zfill(15)` — exactly 15 digits, zero-padded left.
- The Trailer de Lote field TOTAL VALOR PAGTOS is `9(16)V9(2)` — 18 digits total. Same logic applies, just wider.
- Unit test: `R$ 150,50` → `000000000015050`; `R$ 1.234,56` → `000000000123456`; `R$ 0,01` → `000000000000001`.

**Detection warning signs:**
- Payment values in Excel use Brazilian locale (comma as decimal separator).
- Values arrive from VTEX `payment` field as integer (e.g., `3` in sample data — this is a count, not a currency value).
- Any float arithmetic in value handling code.

**Phase:** Phase 1 (core generation). Must be validated with real Excel samples before release.

---

### Pitfall 5: Segmento B PIX Is Mandatory, Not Optional

**What goes wrong:** Developer reads the general Segmento B description ("OPTIONAL") and skips it for PIX payments. The bank rejects every PIX record.

**Why it happens:** The CNAB documentation has two different Segmento B layouts — one for non-PIX (optional) and one specifically for PIX Transferência (mandatory). The section header for the PIX Segmento B explicitly states "OBRIGATÓRIO PARA PIX" but the general summary table says "Segmento B - (Opcional)" before adding the caveat "Obrigatório para a forma PIX Transferência no modelo 'Chave'".

**Consequences:** All PIX payments rejected. The bank returns `RJ` (REGISTRO REJEITADO) for every detalhe without a Segmento B.

**Prevention:**
- Every Segmento A for PIX (Câmara 009, IDENTI. TRANSFERENCIA = "04") must be immediately followed by exactly one Segmento B PIX.
- The Segmento B PIX layout is different from the standard Segmento B: positions 15-16 = TIPO CHAVE, not blank; position 63-127 = INFORMAÇÕES ENTRE USUÁRIOS (optional); positions 128-227 = CHAVE PIX (100 chars, left-aligned, space-padded right).
- Register sequence numbering: Segmento B carries the same NÚMERO DO REGISTRO as its Segmento A (same sequence number — they are a pair).
- The Trailer de Lote TOTAL QTDE REGISTROS counts all records including Segmento B. For N payments: Header Lote (1) + N Segmento A + N Segmento B + Trailer Lote (1) = 2N + 2 total records in the lote count.

**Detection warning signs:**
- Only Segmento A records exist in the output file.
- Trailer Lote count does not match `2N + 2`.

**Phase:** Phase 1. This is a structural requirement, not an edge case.

---

### Pitfall 6: Record Sequence Numbers Not Matching Between Segmento A and Segmento B

**What goes wrong:** The NÚMERO DO REGISTRO in Segmento B is incremented separately from Segmento A, giving Segmento A record `00001` and Segmento B record `00002` for the first payment. The bank expects both to carry `00001`.

**Why it happens:** The documentation states (Note 9): "Para o Segmento 'J-52', 'B', 'C', 'D', 'E', 'F', 'W' e 'Z', por se tratar de complemento de informações, conterá o mesmo número atribuído no Segmento 'A', 'J' e 'N' correspondente." Complement segments share the sequence number of their primary segment. Developers implementing a naive counter increment it for every record written.

**Consequences:** Occurrence AH (NÚMERO SEQUENCIAL DO REGISTRO NO LOTE INVÁLIDO). Payment rejected.

**Prevention:**
- Maintain two counters: `payment_seq` (increments per payment, i.e., per A+B pair) and `record_count` (increments for every record for the Trailer total count).
- Segmento A gets `payment_seq`; Segmento B gets the same `payment_seq`; then `payment_seq` increments for the next payment.
- `record_count` increments for both A and B.

**Phase:** Phase 1.

---

### Pitfall 7: Trailer de Lote Total Count Includes Header and Trailer Records

**What goes wrong:** TOTAL QTDE REGISTROS in the Trailer de Lote is set to only the number of detalhe (type 3) records, not including the Header de Lote (type 1) and Trailer de Lote (type 5) records themselves.

**Why it happens:** Note 17 states: "Trailer de Lote: total de registros de tipo 1, 3 e 5 no lote." Developers naturally assume "total detalhe records" but the count includes the header and trailer records of the lote.

**Consequences:** Occurrence TA (LOTE NÃO ACEITO - TOTAIS DO LOTE COM DIFERENÇA). The entire lote is rejected.

**Prevention:**
- For a PIX lote with N payments: type 1 (header) = 1, type 3 (A+B) = 2N, type 5 (trailer) = 1. Total = 2N + 2.
- Similarly, Trailer de Arquivo TOTAL QTDE REGISTROS includes type 0 (file header) + all type 1 + all type 3 + all type 5 + type 9 (file trailer).
- Implement trailer totals as a final calculation after all records are built, not as a running counter.

**Phase:** Phase 1.

---

### Pitfall 8: Forma de Pagamento "45" Not Set for PIX — Using Wrong Lote Type

**What goes wrong:** The Header de Lote FORMA DE PAGAMENTO field is set to a value other than `45` (PIX Transferência). Common mistakes: using `41` (TED outro titular) or `01` (Crédito em Conta Corrente).

**Why it happens:** Developer builds a generic lote generator and does not map PIX to code 45. The mapping is only in Note 5 of the documentation.

**Consequences:** Occurrence IM (TIPO X FORMA NÃO COMPATÍVEL) or the payment is processed as a TED/credit transfer instead of PIX, potentially with different fees, limits, or routing.

**Prevention:**
- For this project, the only lote type needed is: TIPO DE PAGAMENTO `98` (DIVERSOS) or `20` (FORNECEDORES) + FORMA DE PAGAMENTO `45` (PIX TRANSFERÊNCIA). Hard-code these values.
- The PIX file must be a separate file from any other payment type. PIX cannot coexist with other formas in the same file: "Os lotes de serviços de pagamentos na forma de PIX devem ser enviados obrigatoriamente em arquivo separado das demais formas de pagamento."

**Phase:** Phase 1.

---

### Pitfall 9: CPF/CNPJ of Beneficiary Filled Incorrectly in Segmento A

**What goes wrong:** The N DE INSCRIÇÃO field (positions 204-217, 14 digits) is left as zeros, or the `document` field from VTEX (which may be an 11-digit CPF) is placed in a 14-digit field without left-padding with zeros.

**Why it happens:** The VTEX sample data shows `document: "51300907134"` — an 11-digit CPF. The CNAB field is 14 digits wide (numeric, zero-padded left). An 11-digit CPF must be zero-padded to 14 positions: `"00051300907134"`. If placed as-is without padding, it becomes `"51300907134000"` — completely wrong.

**Additionally:** Note 15 states that for PIX Transferência, identification of CPF/CNPJ is mandatory by BACEN regulation. If `null`, the payment will be rejected (occurrence `BI`).

**Special case from documentation:** "Quando o CNPJ do favorecido for iniciado com 5 zeros (00000), deve-se acrescentar o segmento B do arquivo de pagamentos para confirmar que se trata de um CNPJ e não um CPF." — already satisfied by PIX (Segmento B is always present), but the type indicator in Segmento B (EMPRESA-INSCRIÇÃO, position 18: `1`=CPF, `2`=CNPJ) must be correct.

**Prevention:**
- Detect CPF vs CNPJ from the `document` field length: 11 digits = CPF, 14 digits = CNPJ.
- Pad with `document.zfill(14)` — zero-pad left to 14 digits.
- Set EMPRESA-INSCRIÇÃO type in Segmento B: `1` if CPF, `2` if CNPJ.
- If VTEX returns `document: null`, block the payment and surface an error to the user before file generation.

**Phase:** Phase 1 and pre-validation (Phase 2 UI).

---

### Pitfall 10: VTEX MasterData `pixKey` Field May Be Null or Stale

**What goes wrong:** A beneficiary row in VTEX has `pixKey: null` (not every customer registers a PIX key), or has an outdated key that no longer exists in the BACEN DICT. The CNAB file is generated with an empty or invalid PIX key. The bank rejects the payment with `IO` (IDENTIFICAÇÃO DO QR CODE INVÁLIDO) or `BI`.

**Why it happens:**
- VTEX is a CRM/ecommerce platform — PIX keys are stored as user-entered fields, not validated at the time of entry.
- The VTEX sample shows `pixKey: "51300907134"` (a CPF used as key) — but customers may have changed their PIX key registration since this was saved.
- Null check is easy to miss when iterating many rows.

**Consequences:** Payments fail silently (return file rejection) or the CNAB file cannot be generated at all.

**Prevention:**
- During pre-validation (before generating the CNAB file), check every row: if `pixKey` is null or empty, flag that row with an actionable error message for the finance team.
- Validate key format against the detection rules (Pitfall 3) at validation time.
- Do not generate the CNAB file if any row has a missing or format-invalid key. Surface all errors at once, not one at a time.
- Store the original `pixKey` value alongside the generated CNAB record in the database for audit trail.

**Phase:** Phase 1 (validation logic), Phase 2 (pre-validation UI showing errors per row).

---

### Pitfall 11: PIX Key Format in CNAB Does Not Match BACEN DICT Requirements

**What goes wrong:** The PIX key is stored in VTEX in a formatted form (e.g., `"051.300.907-13"` for CPF) and is placed in the CHAVE PIX field of Segmento B without normalization. The bank rejects it because DICT expects the normalized form.

**Key format rules from CNAB documentation (Note 40):**
- CPF: `XXXXXXXXXXX` — 11 digits only, no dots or dashes.
- CNPJ: `XXXXXXXXXXXXXX` — 14 digits only, no punctuation.
- Phone: `+XXXXXXXXXXXXX` — must start with `+`, then country code (55 for Brazil), DDD, 9-digit number. E.g., VTEX `homePhone: "5561999810561"` should become `+5561999810561`.
- Email: as-is, max 77 characters.
- Chave Aleatória: UUID with hyphens, 36 chars: `XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`.

**The VTEX `homePhone` field returns `"5561999810561"` without the `+` prefix.** If this is used as a phone PIX key, it must be prefixed with `+`.

**Prevention:**
- Normalize the key as part of the type detection function. Return a normalized key alongside the type code.
- Strip formatting from CPF/CNPJ (remove `.`, `-`, `/`).
- Prepend `+` to phone keys that don't already have it.
- The CHAVE PIX field is 100 chars, alphanumeric, left-aligned, space-padded right — `key.ljust(100)`.

**Phase:** Phase 1.

---

### Pitfall 12: VTEX API Rate Limiting With Batch Excel Processing

**What goes wrong:** An Excel file with 200+ beneficiaries triggers 200+ sequential calls to VTEX MasterData. VTEX API rate limits (typically 40 requests/second per app key) cause HTTP 429 responses. The batch fails partway through with incomplete data.

**Why it happens:** No throttling implemented in the VTEX fetch loop. The requests are made as fast as Python can iterate.

**Consequences:**
- Partial data fetch — some beneficiaries have data, others have errors.
- The finance team does not know which rows are incomplete.
- If generation proceeds with partial data, wrong or empty values land in the CNAB file.

**Prevention:**
- Implement a simple request throttle: `time.sleep(0.025)` between requests (40 req/s limit gives 25ms spacing).
- Implement retry with exponential backoff for HTTP 429 responses: retry after `retry_after` header or 1s default.
- Fetch in batches using VTEX `_where` with multiple `OR` conditions if the API supports it — reduces total call count.
- Show the finance team a per-row progress indicator and abort cleanly if more than N consecutive failures occur.
- Cache VTEX responses in the database: if the same `referenceId` was fetched in the last 24 hours, use the cached result.

**Detection warning signs:**
- HTTP 429 errors in logs.
- VTEX `X-VTEX-API-AppKey` has per-minute/per-hour rate limits documented in their developer portal.

**Phase:** Phase 2 (VTEX integration).

---

### Pitfall 13: Agência/Conta do Favorecido in Segmento A for PIX via Chave

**What goes wrong:** Positions 24-43 (AGÊNCIA CONTA FAVORECIDO) in Segmento A are left as zeros for PIX via chave, but the bank uses them for validation against the DICT resolution of the key.

**From the documentation (Note 11 and Note 36):** "Caso o campo 'COMPLEMENTO DE REGISTRO' estiver preenchido com '04' (Chave Pix) nas posições 113 a 114, esse campo é Opcional, e caso esteja preenchido será utilizado para validação contra os dados bancários resgatados da chave Pix no DICT."

This means: for PIX via chave (identifier `04`), the account fields are optional. If they are filled in and do not match the DICT result, the payment may be rejected with `AN` (CONTA CORRENTE DO FAVORECIDO INVÁLIDA). **Leave them as zeros/spaces for PIX via Chave unless explicitly providing validated account data.**

**Prevention:**
- For PIX via Chave (IDENTI. TRANSFERENCIA = `04`), fill AGÊNCIA CONTA FAVORECIDO (positions 24-43) with appropriate zeros/spaces per the layout — do not populate from VTEX's `agency`/`bank` fields (which are `null` in the sample data anyway).
- Set CÂMARA (positions 18-20) to `009` (SPI/PIX).
- Set CÓDIGO ISPB (positions 105-112) to spaces/zeros — for PIX via chave, the ISPB is resolved by the bank via DICT.
- Set BANCO FAVORECIDO (positions 21-23) to `000` or spaces — not required for PIX via chave.

**Phase:** Phase 1.

---

### Pitfall 14: Header de Arquivo Layout Version — Using Wrong Version Number

**What goes wrong:** The LAYOUT DE ARQUIVO field (positions 15-17) is set to `085` but the SISPAG documentation for this project is v085. Getting this wrong means `080` (older version) which is still accepted, but specific newer fields like the PIX-specific segments may be interpreted differently.

**From documentation:** Header de Arquivo position 015-017 LAYOUT DE ARQUIVO = `080`.

**Note:** Confusingly, the documentation is titled "Versão 085" but the Header de Arquivo field content is `080`. These are different version numbers — the document version and the file layout version are not the same.

**Prevention:**
- Header de Arquivo: LAYOUT DE ARQUIVO = `080` (three digits).
- Header de Lote for PIX (forma 45): LAYOUT DO LOTE = `040` (three digits).
- These are constants. Hard-code them.

**Phase:** Phase 1.

---

### Pitfall 15: Mixing PIX Payments With Other Payment Types in the Same File

**What goes wrong:** PIX payments are included in the same CNAB file as other payment types (e.g., TED or credit transfers). The bank rejects the entire file or processes the non-PIX lotes and ignores the PIX lote.

**From documentation:** "Os lotes de serviços de pagamentos na forma de PIX devem ser enviados obrigatoriamente em arquivo separado das demais formas de pagamento."

**Why it happens:** This is explicitly stated in the documentation but easy to overlook if building a general-purpose CNAB generator. The project scope is PIX-only, so this is not a concern now — but it becomes a pitfall if the system is extended later.

**Prevention:**
- The system generates PIX-only files. Document this constraint prominently in the configuration screen.
- If any future requirement introduces non-PIX payments, a separate generation pipeline is required — not a second lote in the same file.

**Phase:** Phase 1 design constraint (document, not code).

---

## Moderate Pitfalls

### Pitfall 16: Date Format Must Be DDMMAAAA — Not ISO 8601

**What goes wrong:** The DATA DE PAGTO field in Segmento A (positions 94-101) is encoded as `2026-03-30` (ISO format) instead of `30032026` (DDMMAAAA format). The bank rejects the record with occurrence AP (DATA DE PAGAMENTO INVÁLIDA).

**Prevention:**
- All date fields in CNAB use `DDMMAAAA` format: `date.strftime('%d%m%Y')`.
- The DATA DE GERAÇÃO in Header de Arquivo (positions 144-151) also uses `DDMMAAAA`.
- HORA DA GERAÇÃO (positions 152-157) uses `HHMMSS`.
- Never use ISO 8601 anywhere in CNAB output.

**Phase:** Phase 1.

---

### Pitfall 17: CODIGO DO LOTE Must Be Sequential Starting at 0001, Not 0000

**What goes wrong:** The first (and only, for PIX) lote gets CODIGO DO LOTE = `0000` instead of `0001`. The Header de Arquivo uses `0000` for its lote code (this is correct), which causes developers to copy this and also use `0000` for actual lotes.

**From documentation (Note 3):** "É sequencial, iniciando-se em 0001." The Header de Arquivo always has `0000`. Lotes start at `0001`.

**Consequences:** Occurrence AG (NÚMERO DO LOTE INVÁLIDO).

**Prevention:**
- Header de Arquivo: CODIGO DO LOTE = `0000`.
- First (PIX) lote: CODIGO DO LOTE = `0001`.
- Trailer de Arquivo: CODIGO DO LOTE = `9999`.
- Hard-code these since there will only ever be one lote per PIX file in this system.

**Phase:** Phase 1.

---

### Pitfall 18: SEU NÚMERO Field — Duplicate Values Break Reconciliation

**What goes wrong:** The SEU NÚMERO field (positions 74-93, 20 chars, in Segmento A) is a document number assigned by the company to identify each payment. If all records use the same value (e.g., `"00000000000000000001"` or the file name), reconciliation against the return file becomes impossible.

**Why it matters:** The return file uses SEU NÚMERO to match processed payments back to their source. If duplicated, you cannot tell which payment was accepted or rejected.

**Prevention:**
- Generate SEU NÚMERO as a unique identifier per payment: `referenceId + sequence_number` or a database-assigned payment ID.
- Keep SEU NÚMERO in the database linked to the payment record, so the return file processor can look it up.

**Phase:** Phase 1 (generation), Phase 3 (return file processing).

---

### Pitfall 19: Return File Processing — Treating "BD" (PAGAMENTO AGENDADO) as Success

**What goes wrong:** The return file processor treats any non-error occurrence code as "payment completed". Occurrence `BD` means PAGAMENTO AGENDADO (scheduled, not yet executed). Treating it as "Transmitido" when the actual debit has not yet occurred leads to false positive status in the dashboard.

**The complete success/failure taxonomy from CNAB documentation:**
- `00` = PAGAMENTO EFETUADO — final success.
- `BD` = PAGAMENTO AGENDADO — pending (normal for future-dated payments).
- `BE` = PAGAMENTO AGENDADO COM FORMA ALTERADA PARA OP — bank changed the payment method.
- `AE` = DATA DE PAGAMENTO ALTERADA — bank changed the payment date.
- `RJ` = REGISTRO REJEITADO — hard rejection.
- `SS` = CANCELADO POR INSUFICIÊNCIA DE SALDO — insufficient funds.
- `NA` = CANCELADO POR FALTA DE AUTORIZAÇÃO.
- `CE` = PAGAMENTO CANCELADO.

**Prevention:**
- Status model: `Criado` → `Transmitido` (file sent) → `Agendado` (BD) → `Efetivado` (00) or `Rejeitado` (any error code).
- Store the raw occurrence code(s) in the database alongside the status.
- Parse up to 5 occurrence codes per record (the field is 10 chars for 5 x 2-char codes).

**Phase:** Phase 3 (return file processing).

---

### Pitfall 20: Itaú API Certificate Authentication — Using Wrong Certificate Type

**What goes wrong:** When implementing the Itaú API transmission, the wrong TLS certificate is used for mutual TLS (mTLS) authentication. Itaú's Open Finance/Banking API requires a client certificate issued by ICP-Brasil — a self-signed certificate or a standard SSL certificate will be rejected at the TLS handshake layer.

**Why it happens:** Itaú's corporate banking API (distinct from Open Finance) typically uses either:
- A client certificate (.p12/.pfx) issued and distributed by Itaú directly to the corporate account holder, or
- OAuth 2.0 with client_credentials flow for newer API versions.
The specific mechanism depends on the contract with Itaú and the API version. Without credentials, it is impossible to know which applies.

**Consequences:** Authentication fails permanently until the correct certificate type is obtained, potentially blocking the transmission phase entirely.

**Prevention:**
- Begin the Itaú API integration phase by first confirming the authentication method with the Itaú account manager.
- Implement the transmission layer behind an interface with a mock: `class BankTransmitter(ABC): def send(self, file_path) -> TransmissionResult`.
- The mock implementation (used for all phases before credentials are available) returns a realistic response.
- The real implementation is swapped in once the certificate type and credentials are confirmed.
- Python's `requests` library supports mTLS via the `cert=` parameter: `requests.post(url, cert=('client.pem', 'key.pem'), ...)`.

**Phase:** Phase 4 (Itaú API integration). Flag for deeper research at that phase.

---

### Pitfall 21: Excel Value Column Locale — Comma as Decimal Separator

**What goes wrong:** The Brazilian locale uses commas as decimal separators and periods as thousand separators: `"1.234,56"` means one thousand two hundred thirty-four reais and fifty-six centavos. `pandas.read_excel()` or `openpyxl` may interpret this as string `"1.234,56"` or, worse, as `1234.56` or `1.234` depending on Excel's internal storage.

**Prevention:**
- Read the value column as string, not float: `dtype={'Valor': str}` in pandas.
- Clean: remove `R$`, `.` (thousand separator), replace `,` with `.`, then parse as `Decimal`.
- Unit test with: `"1.234,56"` → `Decimal('1234.56')`; `"150"` → `Decimal('150.00')`; `"R$ 50,00"` → `Decimal('50.00')`.
- If the value arrives as a float from Excel (no formatting), use `Decimal(str(round(value, 2)))` — round first to avoid float noise.

**Phase:** Phase 2 (Excel upload).

---

### Pitfall 22: VTEX API Returns `null` for Multiple Fields — No Defensive Handling

**What goes wrong:** The VTEX MasterData record for a beneficiary has `null` values for `document`, `pixKey`, `firstName`, or `lastName`. The code accesses these without null checks, raising `AttributeError` or `TypeError` mid-batch, aborting the entire batch without processing remaining rows.

**From VTEX sample data:** `agency: null`, `bank: null`, `cpf: null`, `complement: "null"` (string "null", not JSON null) are all present in the sample.

**Prevention:**
- Treat every VTEX field as potentially null.
- Build a `VTEXBeneficiary` dataclass with Optional fields and explicit validation: a beneficiary is "complete" if it has non-null `document`, `pixKey`, and at least one of `firstName`/`receiverName`.
- Note the `complement: "null"` anomaly — VTEX stores the string `"null"` in some fields. Strip and normalize.
- Validation pass before generation: collect all incomplete beneficiaries and return them to the user in one response, not one error at a time.

**Phase:** Phase 2 (VTEX integration).

---

## Minor Pitfalls

### Pitfall 23: NOME DA EMPRESA in Headers Must Match Exactly

**What goes wrong:** The NOME DA EMPRESA field in Header de Arquivo and Header de Lote (positions 73-102, 30 chars) is filled with a slightly different value in each record. While the bank typically does not reject on this, inconsistency between the header fields may cause issues with the bank's automated reconciliation.

**Prevention:** Store the company name, CNPJ, agency, account, and DAC in a configuration table (settings screen). Load them once at file generation time and use the same values in every header record.

**Phase:** Phase 1 (settings screen).

---

### Pitfall 24: File Name Convention for CNAB Transmission

**What goes wrong:** The CNAB file is named arbitrarily (e.g., `output.txt` or `cnab_file.ret`). The Itaú transmission portal may expect a specific naming convention or reject files with non-standard names.

**Prevention:**
- Use a naming convention based on date and sequential number: `SISPAG_YYYYMMDD_NNN.txt` or as instructed by the Itaú account manager.
- Store the generated file name in the database for audit trail.
- The file must be plain text, no compression — the documentation explicitly states "Não deve ser utilizado nenhum tipo de compactador de arquivos."

**Phase:** Phase 4 (transmission).

---

### Pitfall 25: Duplicate File Submission — Same File Sent Twice

**What goes wrong:** A generated CNAB file is transmitted to Itaú, then transmitted again (network retry, user error, or bug). Itaú may process the second submission as new payments, resulting in duplicate debits.

**Prevention:**
- Track transmission status in the database. Once a file reaches status `Transmitido`, block re-transmission unless explicitly overridden by an administrator.
- Store a file hash (SHA-256 of the CNAB file content) in the database. Reject transmission if the same hash was already successfully transmitted.
- The Itaú API may also have idempotency controls — investigate during Phase 4.

**Phase:** Phase 3 (status management), Phase 4 (transmission).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Core CNAB generation | Record not 240 bytes (P1), wrong encoding (P2), Segmento B missing (P5) | Assert byte count per record; test with bank validator tool |
| PIX key handling | Wrong key type code (P3), key not normalized (P11) | Unit test all key formats; detection function with validation |
| Payment value encoding | Implicit decimal encoding error (P4), float arithmetic (P4) | Use Decimal throughout; unit test value encoding |
| Record sequencing | Sequence shared between A and B (P6), trailer count wrong (P7) | Separate sequence counter from record counter |
| Lote structure | Forma 45 not set (P8), wrong layout version (P14) | Hard-coded constants for PIX lote structure |
| CPF/CNPJ handling | Wrong padding (P9), null document (P9) | zfill(14); validation before generation |
| VTEX integration | Null pixKey (P10), rate limiting (P12), null fields (P22) | Pre-validation pass; throttle; defensive null handling |
| Excel import | Comma decimal separator (P21), float precision (P4) | Parse as string; use Decimal |
| Dates | ISO format instead of DDMMAAAA (P16) | strftime('%d%m%Y') always |
| Return file processing | BD treated as success (P19), duplicate occurrence codes | Full occurrence code taxonomy; multi-code parsing |
| Itaú API transmission | Certificate type unknown (P20) | Mock behind interface; confirm auth method before Phase 4 |
| File transmission | Duplicate submission (P25) | Hash-based dedup; status gate |

---

## Sources

- SISPAG CNAB v085 official documentation: `./Documents/sispag_cnab.md` (converted from Itaú PDF)
- VTEX MasterData API response sample: `./Documents/Vtex API Info.txt`
- Confidence: HIGH for CNAB format pitfalls (based directly on official spec); MEDIUM for VTEX rate limits (standard VTEX behavior, credentials not yet tested); LOW for Itaú API authentication (no credentials available — confirmed unknown)
