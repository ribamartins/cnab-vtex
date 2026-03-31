# Phase 2: Foundation - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers the application foundation: SQLite database with full schema, user authentication (login/logout with session persistence), admin user management (CRUD), company settings screen, and secure credential storage. No CNAB generation UI — that's Phase 4. No Excel import or VTEX integration — that's Phase 3.

</domain>

<decisions>
## Implementation Decisions

### Session Persistence (AUTH-03)
- **D-01:** Login sessions persist via encrypted token file stored locally (~/.cnab-pix/session.json or equivalent Windows path). Signed token, validated at startup.
- **D-02:** Session token expires after 30 days. After expiry, user must re-login.

### Credential Storage (CONF-03)
- **D-03:** VTEX API keys (AppKey, AppToken) and sensitive company data stored as encrypted columns in SQLite using Fernet symmetric encryption (from `cryptography` library).
- **D-04:** Encryption key is machine-specific: auto-generated on first run and stored in a protected local file alongside the session token directory. No master password required — transparent to users.

### User Management (AUTH-01, AUTH-02)
- **D-05:** First admin created via first-run setup wizard. On first launch (no users in DB), app shows a setup screen: create admin username/password + enter initial company data. Natural onboarding.
- **D-06:** Admin manages users via a "Users" tab in settings — table with add/edit/deactivate actions. Standard CRUD.
- **D-07:** Two roles only: admin and user. Admin manages users + settings + all operations. User can import, generate, download CNAB files. No viewer or operator roles.

### Database Schema (All requirements)
- **D-08:** Full schema created upfront in Phase 2: companies, users, cnab_files, payments, audit_logs. All tables present from the start even if some remain empty until Phases 3-4. Avoids migration churn.
- **D-09:** SQLite database file lives in platform app data directory: `%APPDATA%/cnab-pix/data.db` on Windows. Standard desktop app location, survives app updates.
- **D-10:** Alembic manages migrations from day one, even for SQLite. Baseline migration creates all tables.

### Claude's Discretion
- Password hashing strategy (Werkzeug PBKDF2 per CLAUDE.md stack recommendation)
- Exact Alembic configuration and naming conventions
- Settings UI layout details (tab arrangement, field grouping)
- Session token file format and signing mechanism
- Machine-specific key generation approach (UUID, random bytes, etc.)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### CNAB Engine (Phase 1 output — CompanyConfig interface)
- `src/cnab/builder.py` — Defines `CompanyConfig` dataclass with all fields the settings screen must populate (cnpj, agency, account, dac, name, address, city, cep, state, tipo_pagamento)

### Project Specs
- `Documents/sispag_cnab.md` — CNAB 240 SISPAG Itau v085 spec (company header field positions)
- `Documents/Vtex API Info.txt` — VTEX API credentials format (AppKey, AppToken structure)

### Stack Decisions
- `CLAUDE.md` — Technology stack (Flask-SQLAlchemy, Alembic, Werkzeug auth, PySide6) and coding conventions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/cnab/builder.py:CompanyConfig` — Dataclass with all company fields. Settings screen must produce objects matching this interface.
- `src/cnab/builder.py:PaymentInput` — Reference for payment data fields (needed when designing cnab_files/payments tables).

### Established Patterns
- Pure Python modules in `src/cnab/` — no framework dependencies yet. Phase 2 introduces Flask + SQLAlchemy + PySide6 as the first framework layer.
- Dataclass-based data contracts (PaymentInput, CompanyConfig) — maintain this pattern for new models.

### Integration Points
- Settings screen must produce a `CompanyConfig` object that `build_cnab()` consumes.
- Database `companies` table fields must map 1:1 to `CompanyConfig` dataclass attributes.
- The `users` table and auth system will be consumed by PySide6 GUI in Phase 4.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for the PySide6 settings UI and Flask/SQLAlchemy integration.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-foundation*
*Context gathered: 2026-03-30*
