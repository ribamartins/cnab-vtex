# Requirements: CNAB PIX Payment System

**Defined:** 2026-03-30
**Core Value:** Gerar arquivos CNAB PIX válidos e transmiti-los ao Itaú sem erros — cada pagamento deve chegar ao beneficiário correto com o valor correto.

## v1 Requirements

### Authentication

- [ ] **AUTH-01**: User can log in with username and password (local authentication)
- [ ] **AUTH-02**: Admin can create, edit, and deactivate user accounts
- [ ] **AUTH-03**: User session persists across application restarts (remember me)

### Settings

- [ ] **CONF-01**: Admin can configure company data (CNPJ, agency, account, DAC Itaú)
- [ ] **CONF-02**: Admin can configure VTEX API credentials (AppKey, AppToken)
- [ ] **CONF-03**: Settings are stored securely in the local database

### Excel Import

- [ ] **IMPT-01**: User can import Excel file (.xlsx) with columns: Nome do Beneficiário, Código (referenceId), Valor
- [ ] **IMPT-02**: System validates Excel structure before processing (required columns, data types)
- [ ] **IMPT-03**: System displays import preview with row count and total value before proceeding

### VTEX Integration

- [ ] **VTEX-01**: System queries VTEX MasterData API for each referenceId and retrieves beneficiary data (pixKey, document, name, email, phone)
- [ ] **VTEX-02**: System handles VTEX API errors gracefully (timeout, not found, rate limit) with per-row error reporting
- [ ] **VTEX-03**: System displays enrichment results with success/failure status per row before CNAB generation

### Validation

- [ ] **VALD-01**: System detects PIX key type automatically (CPF/CNPJ, phone, email, random key) from raw pixKey string
- [ ] **VALD-02**: System validates CPF/CNPJ check digits before CNAB generation
- [ ] **VALD-03**: System validates all mandatory CNAB fields are present (pixKey, document, name, value) and reports missing data per row
- [ ] **VALD-04**: System presents a consolidated validation report with all errors/warnings before allowing CNAB generation

### CNAB Generation

- [ ] **CNAB-01**: System generates Header de Arquivo (type 0) with company data, bank code 341, layout version 080
- [ ] **CNAB-02**: System generates Header de Lote (type 1) with operation C, payment type per Nota 4, form 45 (PIX Transferência), layout 040
- [ ] **CNAB-03**: System generates Segmento A for each payment with câmara 009 (PIX/SPI), identification type 04 (Chave Pix), payment value with implicit decimal
- [ ] **CNAB-04**: System generates Segmento B PIX (mandatory) for each payment with PIX key type code and key value (up to 100 chars)
- [ ] **CNAB-05**: System generates Trailer de Lote (type 5) with correct record count and value sum
- [ ] **CNAB-06**: System generates Trailer de Arquivo (type 9) with lot count and total record count
- [ ] **CNAB-07**: Every record is exactly 240 bytes encoded in LATIN-1, with numeric fields zero-padded left and alpha fields space-padded right
- [ ] **CNAB-08**: System uses Decimal arithmetic (never float) for all payment values

### File Management

- [ ] **FILE-01**: Generated CNAB file is saved to database with status "Criado" and metadata (creation date, user, row count, total value)
- [ ] **FILE-02**: User can download the generated CNAB file as .txt for manual upload to Itaú Empresas
- [ ] **FILE-03**: User can trigger transmission (mock/stub) which moves status to "Transmitido" or "Erro"
- [ ] **FILE-04**: On transmission error, system saves error details alongside the file record

### Dashboard

- [ ] **DASH-01**: User can view list of all generated CNAB files with status, date, value, and row count
- [ ] **DASH-02**: User can filter files by status (Criado, Transmitido, Erro) and date range
- [ ] **DASH-03**: User can view file details including individual payment rows and their status

### Audit

- [ ] **AUDT-01**: System logs all significant actions (file generation, transmission attempt, status change) with user, timestamp, and details
- [ ] **AUDT-02**: User can view audit log with filters by date and action type

## v2 Requirements

### Return File Processing

- **RETN-01**: User can upload Itaú return file (arquivo retorno) for processing
- **RETN-02**: System parses return file occurrence codes and maps to readable status (Agendado, Efetivado, Rejeitado)
- **RETN-03**: System updates individual payment status based on return file data
- **RETN-04**: Dashboard shows reconciliation status per payment (matched vs pending)

### Real Transmission

- **TRNS-01**: System transmits CNAB file to Itaú via real bank API (when credentials available)
- **TRNS-02**: System handles Itaú API authentication (mTLS or OAuth per contract)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Pagamento via boleto/DOC/TED | Apenas PIX Transferência nesta versão |
| Multi-empresa / multi-banco | Apenas Itaú, uma empresa por instalação |
| App web ou mobile | Aplicação desktop standalone apenas |
| Geração de arquivo retorno | Apenas leitura/processamento do retorno recebido do Itaú |
| PIX via QR Code | Apenas PIX Transferência via chave |
| Agendamento automático de pagamentos | Geração e transmissão são ações manuais do usuário |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 2 | Pending |
| AUTH-02 | Phase 2 | Pending |
| AUTH-03 | Phase 2 | Pending |
| CONF-01 | Phase 2 | Pending |
| CONF-02 | Phase 2 | Pending |
| CONF-03 | Phase 2 | Pending |
| IMPT-01 | Phase 3 | Pending |
| IMPT-02 | Phase 3 | Pending |
| IMPT-03 | Phase 3 | Pending |
| VTEX-01 | Phase 3 | Pending |
| VTEX-02 | Phase 3 | Pending |
| VTEX-03 | Phase 3 | Pending |
| VALD-01 | Phase 1 | Pending |
| VALD-02 | Phase 1 | Pending |
| VALD-03 | Phase 1 | Pending |
| VALD-04 | Phase 1 | Pending |
| CNAB-01 | Phase 1 | Pending |
| CNAB-02 | Phase 1 | Pending |
| CNAB-03 | Phase 1 | Pending |
| CNAB-04 | Phase 1 | Pending |
| CNAB-05 | Phase 1 | Pending |
| CNAB-06 | Phase 1 | Pending |
| CNAB-07 | Phase 1 | Pending |
| CNAB-08 | Phase 1 | Pending |
| FILE-01 | Phase 4 | Pending |
| FILE-02 | Phase 4 | Pending |
| FILE-03 | Phase 4 | Pending |
| FILE-04 | Phase 4 | Pending |
| DASH-01 | Phase 4 | Pending |
| DASH-02 | Phase 4 | Pending |
| DASH-03 | Phase 4 | Pending |
| AUDT-01 | Phase 4 | Pending |
| AUDT-02 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 33 total
- Mapped to phases: 33
- Unmapped: 0

---
*Requirements defined: 2026-03-30*
*Last updated: 2026-03-30 — traceability populated after roadmap creation*
