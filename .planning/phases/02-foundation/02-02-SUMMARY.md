---
phase: 02-foundation
plan: 02
subsystem: ui
tags: [pyside6, qt, login, settings, user-management, vtex-credentials, setup-wizard]

# Dependency graph
requires:
  - phase: 02-foundation/02-01
    provides: auth service (login_with_session, restore_session, create_user, get_all_users), crypto (encrypt_value/decrypt_value), database (init_db), models (User, Company)
provides:
  - LoginDialog: PySide6 QDialog with PT-BR login form, loading state, error display, session persistence
  - SetupWizard: Two-step first-run wizard (admin creation + company data with all 12 CompanyConfig fields)
  - SettingsWindow: Three-tab settings (Dados da Empresa, Usuarios, Credenciais VTEX) with CRUD, encrypted VTEX keys
  - MainWindow: Shell QMainWindow with settings menu, status bar, logout
  - main.py: Application entry point with first-run wizard, session restore, and login flow
  - styles.py: Centralized QSS stylesheet with 60/30/10 color system
affects: [03-vtex-integration, 04-dashboard]

# Tech tracking
tech-stack:
  added:
    - PySide6==6.10.1 (upgraded from 6.8.1 — Python 3.14 requires >=6.10.1)
  patterns:
    - QDialog-based screens with session parameter injection
    - QStackedWidget for multi-step wizard flow
    - QTabWidget with unsaved changes guard on tab switch and close
    - PasswordEchoOnEdit for credential fields with 5-second show timer
    - QPushButton objectName="primary" for accent-color styling via QSS
    - Unicode escape sequences for PT-BR copy in Python source (e.g., \u00e1 for a-acute)

key-files:
  created:
    - src/ui/__init__.py
    - src/ui/styles.py
    - src/ui/login_dialog.py
    - src/ui/setup_wizard.py
    - src/ui/settings_window.py
    - src/ui/main_window.py
    - src/main.py
  modified:
    - requirements.txt (PySide6 version bump)

key-decisions:
  - "PySide6 upgraded to 6.10.1 — Python 3.14 requires >=6.10.1, 6.8.1 is incompatible"
  - "Unicode escapes used for PT-BR copy in Python source files for encoding safety"
  - "QScrollArea wraps long forms (setup wizard step 2, company tab) for small screen compatibility"
  - "AddUserDialog defined in settings_window.py for colocation with its sole parent"

patterns-established:
  - "Screen-as-QDialog: all screens are QDialog subclasses receiving session as constructor param"
  - "ObjectName-based QSS: use setObjectName('primary') / setObjectName('destructive') for button variants"
  - "Unsaved guard: track _has_unsaved_changes flag, show QMessageBox on tab change and closeEvent"

requirements-completed: [AUTH-01, AUTH-02, AUTH-03, CONF-01, CONF-02, CONF-03]

# Metrics
duration: 6min
completed: 2026-03-30
---

# Phase 02 Plan 02: PySide6 UI Screens Summary

**Login dialog, first-run setup wizard, and settings window (user CRUD + encrypted VTEX credentials) built in PySide6 with PT-BR copy, wired to Phase 01 auth and crypto services**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-30T22:03:36Z
- **Completed:** 2026-03-30T22:09:10Z
- **Tasks:** 1 of 2 (Task 2 is checkpoint:human-verify — awaiting verification)
- **Files modified:** 8

## Accomplishments

- Login dialog with "Verificando..." loading state, inline PT-BR error display, Enter-key submit, and session restore on restart
- Two-step setup wizard with admin creation (Step 1) + all 12 CompanyConfig fields (Step 2), inline validation for required fields and CNPJ format
- Settings window with three tabs: company data form (pre-populated from DB), user management table with edit/deactivate/reactivate actions and self-deactivation guard, VTEX credentials with Fernet encryption and 5-second show toggle
- Application entry point implementing the correct startup flow: first-run wizard → session restore → login dialog → main window

## Task Commits

1. **Task 1: PySide6 screens — Login, Setup Wizard, Settings Window, and Main Window** - `3f1e877` (feat)

**Plan metadata:** (pending — after checkpoint verification)

## Files Created/Modified

- `src/ui/__init__.py` - Package marker
- `src/ui/styles.py` - QSS stylesheet, color constants (COLOR_ACCENT, COLOR_BG, etc.), get_app_stylesheet()
- `src/ui/login_dialog.py` - LoginDialog with loading state, error label, session auth
- `src/ui/setup_wizard.py` - SetupWizard two-step flow with QStackedWidget
- `src/ui/settings_window.py` - SettingsWindow three-tab with AddUserDialog, user CRUD, encrypted VTEX creds
- `src/ui/main_window.py` - MainWindow shell with menu and status bar
- `src/main.py` - Application entry point with first-run wizard, session restore, login flow
- `requirements.txt` - PySide6 version updated from 6.8.1 to 6.10.1

## Decisions Made

- PySide6 6.10.1 required: Python 3.14 incompatible with 6.8.1 (requires Python <3.14). Updated requirements.txt to 6.10.1 which is the first version supporting Python 3.14.
- Unicode escape sequences used for all PT-BR accented characters in Python source files to ensure consistent encoding regardless of editor/platform settings.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] PySide6 version incompatible with Python 3.14**
- **Found during:** Task 1 verification (module import test)
- **Issue:** requirements.txt specified PySide6==6.8.1 but Python 3.14 requires PySide6>=6.10.1. The error: "Could not find a version that satisfies the requirement PySide6==6.8.1"
- **Fix:** Updated requirements.txt to PySide6==6.10.1, installed successfully
- **Files modified:** requirements.txt
- **Verification:** `pip install PySide6==6.10.1` succeeded; all UI modules import correctly
- **Committed in:** 3f1e877 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Required fix — PySide6 6.8.1 cannot run on Python 3.14. The upgrade to 6.10.1 is backwards-compatible for the PySide6 APIs used in this plan.

## Issues Encountered

- PySide6 was not installed in the environment. Installed as part of the blocking fix above.

## Known Stubs

None — all form fields are wired to DB models (Company) and auth service (User). No placeholder data.

## Next Phase Readiness

- All three Phase 2 UI screens are complete and wired to Phase 01 data layer
- Application can be launched with `PYTHONPATH=src python src/main.py`
- Ready for Task 2 human verification: first-run wizard, login, settings tabs, session persistence
- Phase 3 (VTEX integration) can use the VTEX credentials stored and encrypted in Phase 2 settings

---
*Phase: 02-foundation*
*Completed: 2026-03-30*
