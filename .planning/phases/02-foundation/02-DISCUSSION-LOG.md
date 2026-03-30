# Phase 2: Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-30
**Phase:** 02-foundation
**Areas discussed:** Session persistence, Credential storage, User management flow, Database schema scope

---

## Session Persistence

| Option | Description | Selected |
|--------|-------------|----------|
| Encrypted token file | Save signed session token to local file. Simple, portable, no OS dependency. | ✓ |
| OS keychain (keyring) | Use Windows Credential Manager via Python keyring. More secure but OS-dependent. | |
| SQLite session table | Store session in database. Simple but tied to DB location. | |
| You decide | Let Claude choose. | |

**User's choice:** Encrypted token file
**Notes:** None

### Follow-up: Token expiry

| Option | Description | Selected |
|--------|-------------|----------|
| 7 days | Good balance for daily-use internal tool. | |
| 30 days | Very long-lived. Convenient but less secure. | ✓ |
| 24 hours | Stricter security. Re-login once per day. | |
| You decide | Let Claude choose. | |

**User's choice:** 30 days
**Notes:** None

---

## Credential Storage

| Option | Description | Selected |
|--------|-------------|----------|
| Encrypted SQLite columns | Fernet encryption in DB. Everything in one place. | ✓ |
| OS keychain (keyring) | Windows Credential Manager. Most secure but OS-dependent. | |
| Encrypted config file | Separate .enc file. Portable but another file to manage. | |
| You decide | Let Claude choose. | |

**User's choice:** Encrypted SQLite columns
**Notes:** None

### Follow-up: Encryption key derivation

| Option | Description | Selected |
|--------|-------------|----------|
| Machine-specific secret | Auto-generate key on first run. No password to remember. | ✓ |
| Master password at startup | User enters password each time. More secure but friction. | |
| You decide | Let Claude choose. | |

**User's choice:** Machine-specific secret
**Notes:** None

---

## User Management Flow

### First admin creation

| Option | Description | Selected |
|--------|-------------|----------|
| First-run setup wizard | On first launch, show setup screen: create admin + company data. | ✓ |
| CLI seed command | Run command to create initial admin. Developer-friendly. | |
| Default admin credentials | Ship with admin/admin, force change on first login. | |
| You decide | Let Claude choose. | |

**User's choice:** First-run setup wizard
**Notes:** None

### Admin user management

| Option | Description | Selected |
|--------|-------------|----------|
| Settings panel with user table | Users tab in settings with add/edit/deactivate. Standard CRUD. | ✓ |
| Minimal: just add/remove | Simpler dialog. No edit, no roles. | |
| You decide | Let Claude choose. | |

**User's choice:** Settings panel with user table
**Notes:** None

### Roles

| Option | Description | Selected |
|--------|-------------|----------|
| Just admin and user | Admin manages everything. User can import/generate/download. | ✓ |
| Three roles: admin, operator, viewer | More granular. Viewer dashboard-only, operator generates. | |
| You decide | Let Claude choose. | |

**User's choice:** Just admin and user
**Notes:** None

---

## Database Schema Scope

### Schema strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Full schema upfront | All tables now. Avoids migration churn later. | ✓ |
| Incremental | Only what Phase 2 needs. More migrations later. | |
| You decide | Let Claude choose. | |

**User's choice:** Full schema upfront
**Notes:** None

### Database location

| Option | Description | Selected |
|--------|-------------|----------|
| App data directory | %APPDATA%/cnab-pix/data.db. Standard desktop app location. | ✓ |
| Project directory | ./data/cnab.db. Simpler but exposed. | |
| You decide | Let Claude choose. | |

**User's choice:** App data directory
**Notes:** None

---

## Claude's Discretion

- Password hashing strategy
- Alembic configuration and naming conventions
- Settings UI layout details
- Session token file format and signing mechanism
- Machine-specific key generation approach

## Deferred Ideas

None — discussion stayed within phase scope.
