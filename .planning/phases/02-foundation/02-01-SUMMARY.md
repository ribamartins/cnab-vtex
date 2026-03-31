---
phase: 02-foundation
plan: "01"
subsystem: data-layer
tags: [database, auth, crypto, sqlalchemy, alembic, fernet]
dependency_graph:
  requires: []
  provides:
    - src/app/models.py (SQLAlchemy models for all 5 tables)
    - src/app/database.py (init_db, get_session)
    - src/app/crypto.py (encrypt_value, decrypt_value, session tokens)
    - src/app/auth.py (authenticate_user, create_user, full user CRUD)
    - alembic/versions/001_baseline.py (baseline migration)
  affects:
    - Phase 02 Plan 02 (UI screens consume auth service)
    - Phase 03 (VTEX enrichment stores data via models)
    - Phase 04 (CNAB generation reads company config via to_company_config())
tech_stack:
  added:
    - SQLAlchemy==2.0.48 (upgraded from 2.0.36 for Python 3.14 compatibility)
    - Flask==3.0.3
    - Flask-SQLAlchemy==3.1.1
    - alembic==1.13.3
    - cryptography==43.0.3
    - Werkzeug==3.0.6
    - openpyxl==3.1.5
  patterns:
    - SQLAlchemy 2.0 mapped_column / Mapped[T] with Optional[T] for nullable
    - Fernet symmetric encryption with machine-specific auto-generated key
    - Session functions all accept SQLAlchemy session parameter (no global state)
    - TDD: RED -> GREEN for all implementation files
key_files:
  created:
    - src/app/__init__.py
    - src/app/models.py
    - src/app/database.py
    - src/app/crypto.py
    - src/app/auth.py
    - alembic.ini
    - alembic/env.py
    - alembic/script.py.mako
    - alembic/versions/001_baseline.py
    - requirements.txt
    - tests/app/__init__.py
    - tests/app/test_models.py
    - tests/app/test_crypto.py
    - tests/app/test_auth.py
  modified: []
decisions:
  - "SQLAlchemy upgraded to 2.0.48 from plan-specified 2.0.36 (Python 3.14 Union type compatibility)"
  - "Optional[T] typing used instead of T|None syntax for SQLAlchemy Mapped columns (Python 3.14)"
  - "datetime.utcnow() retained (DeprecationWarning in Python 3.14 but not yet removed)"
metrics:
  duration_minutes: 7
  completed_date: "2026-03-30"
  tasks_completed: 2
  files_created: 14
  tests_added: 46
  tests_total: 142
---

# Phase 02 Plan 01: Database Models, Crypto Layer, and Auth Service Summary

**One-liner:** SQLAlchemy 2.0 models for 5 tables, Fernet credential encryption with machine key, and session-based auth service with full user CRUD.

## What Was Built

### Task 1: Database models, Alembic baseline, and encryption service

**`src/app/models.py`** — Five SQLAlchemy 2.0 models using `mapped_column` / `Mapped[T]`:
- `Company` (`companies`): 12 fields matching `CompanyConfig` exactly, plus encrypted VTEX credential columns, `to_company_config()` method
- `User` (`users`): username/password_hash/role/is_active, `set_password()` with Werkzeug PBKDF2, `check_password()`
- `CnabFile` (`cnab_files`): file metadata + raw bytes content, status tracking, cents-based value storage
- `Payment` (`payments`): per-payment records mirroring `PaymentInput` dataclass fields
- `AuditLog` (`audit_logs`): action trail with nullable user_id for system entries

**`src/app/database.py`** — `init_db(db_path)` creates engine + tables, `get_session()` context manager with commit/rollback.

**`src/app/crypto.py`** — Fernet encryption layer:
- Machine-specific key auto-generated at `~/.cnab-pix/machine.key` (D-04)
- `encrypt_value` / `decrypt_value` for credential storage (D-03)
- `create_session_token` / `validate_session_token` with 30-day expiry (D-01, D-02)
- `save_session_to_disk` / `load_session_from_disk` / `clear_session_from_disk`

**Alembic configuration** — `alembic.ini`, `alembic/env.py`, `alembic/versions/001_baseline.py` creating all 5 tables.

### Task 2: Authentication service with user CRUD

**`src/app/auth.py`** — Session-parameterized auth functions:
- `authenticate_user`: query by username+is_active, verify password hash
- `create_user`: validate password length/role/uniqueness, hash password
- `update_user`: selective field updates (display_name, password, role)
- `deactivate_user` / `reactivate_user`: idempotent is_active toggle
- `get_all_users`, `get_user_by_id`: query helpers
- `has_any_users`: first-run wizard detection (D-05)
- `login_with_session`: authenticate + create token + save to disk
- `restore_session`: startup session restore from persisted token (D-01)
- `logout`: clear session from disk

## Test Results

```
142 passed, 53 warnings in 2.74s
  - 96 existing Phase 1 tests: all pass (no regressions)
  - 13 new test_models.py tests: all pass
  - 11 new test_crypto.py tests: all pass
  - 22 new test_auth.py tests: all pass
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SQLAlchemy 2.0.36 incompatible with Python 3.14 Union type syntax**
- **Found during:** Task 1 GREEN phase, first test run
- **Issue:** SQLAlchemy 2.0.36's `make_union_type()` in `util/typing.py` calls `Union.__getitem__(types)` which is broken in Python 3.14 (environment uses Python 3.14.3). Error: `TypeError: descriptor '__getitem__' requires a 'typing.Union' object but received a 'tuple'`
- **Fix 1 (insufficient):** Added `from __future__ import annotations` and `Optional[T]` — same error persisted because SQLAlchemy's internal type introspection also fails
- **Fix 2 (applied):** Upgraded `SQLAlchemy==2.0.36` to `SQLAlchemy==2.0.48` which contains a fix for Python 3.14 compatibility. `requirements.txt` updated accordingly.
- **Files modified:** `requirements.txt`, `src/app/models.py`
- **Commit:** 5cadff9

**Note:** `Optional[T]` typing was retained in `models.py` instead of `T | None` as defensive practice for SQLAlchemy Mapped column annotations.

## Known Stubs

None. All exported functions are fully implemented and wire to real behavior.

## Self-Check: PASSED

All created files verified present:
- src/app/__init__.py: FOUND
- src/app/models.py: FOUND
- src/app/database.py: FOUND
- src/app/crypto.py: FOUND
- src/app/auth.py: FOUND
- alembic.ini: FOUND
- alembic/env.py: FOUND
- alembic/script.py.mako: FOUND
- alembic/versions/001_baseline.py: FOUND
- requirements.txt: FOUND
- tests/app/__init__.py: FOUND
- tests/app/test_models.py: FOUND
- tests/app/test_crypto.py: FOUND
- tests/app/test_auth.py: FOUND

Commits verified:
- a3dfe91: test(02-01): add failing tests for models and crypto (TDD RED)
- 5cadff9: feat(02-01): database models, Alembic baseline migration, and crypto service (TDD GREEN)
- f672ba0: test(02-01): add failing tests for auth service (TDD RED)
- 5233170: feat(02-01): authentication service with user CRUD (TDD GREEN)
