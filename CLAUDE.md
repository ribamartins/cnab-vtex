<!-- GSD:project-start source:PROJECT.md -->
## Project

**CNAB PIX Payment System**

Aplicação desktop standalone para criação e transmissão de arquivos bancários CNAB 240 (SISPAG Itaú) para pagamentos PIX. O usuário importa uma planilha Excel com beneficiários, o sistema consulta a API VTEX para obter dados completos, gera o arquivo CNAB no formato exigido pelo Itaú, e transmite via API bancária. Destinado à equipe financeira da PrettyNew.

**Core Value:** Gerar arquivos CNAB PIX válidos e transmiti-los ao Itaú sem erros — cada pagamento deve chegar ao beneficiário correto com o valor correto.

### Constraints

- **Stack**: Python + PySide6 (Qt) — aplicação desktop standalone
- **Banco**: SQLite local para metadados e status dos arquivos
- **Segurança**: Credenciais VTEX e Itaú em arquivo de configuração local criptografado ou protegido, nunca hardcoded
- **CNAB**: Cada registro exatamente 240 bytes, encoding conforme padrão FEBRABAN, campos numéricos com zeros à esquerda, alfanuméricos com espaços à direita
- **Usuários**: Equipe pequena (1-5 pessoas), autenticação local simples
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Core Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.12.x | Runtime | Latest stable with significant performance improvements over 3.10/3.11; `tomllib` built-in; `typing` improvements reduce boilerplate |
| Flask | 3.0.x | Web framework | Constraint-mandated. Flask 3.0 dropped Python 3.8 support and cleaned legacy APIs. Minimal surface area is correct for this domain — no ORM opinions, no DI container complexity |
| Werkzeug | 3.0.x | WSGI utilities | Ships with Flask 3.0; do not pin separately unless you hit a specific bug |
| Jinja2 | 3.1.x | Templating | Ships with Flask; server-side rendering is correct for a small internal tool |
### Database
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| SQLite | 3.x (system) | Development and single-server production | Correct choice for 1–5 users with no concurrent write load. No ops overhead, file is portable, backups are `cp`. Zero-configuration. |
| Flask-SQLAlchemy | 3.1.x | ORM layer | Bridges Flask app context with SQLAlchemy sessions correctly. Avoid raw SQLAlchemy without it in Flask — context teardown is error-prone to manage manually |
| SQLAlchemy | 2.x | ORM core | SQLAlchemy 2.0 introduced the modern `mapped_column` / `Mapped[T]` API. Use it from day one — the legacy 1.x style still works but should not be started fresh |
| Alembic | 1.13.x | DB migrations | Even for SQLite, use Alembic from the start. Schema changes without migrations are painful at phase 2+ |
### Authentication
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Flask-Login | 0.6.x | Session-based auth | The standard for Flask user sessions. Provides `login_required`, `current_user`, `login_user`, `logout_user`. Minimal — doesn't force a user model shape |
| Werkzeug `generate_password_hash` / `check_password_hash` | (bundled) | Password hashing | Already in Werkzeug (Flask dependency). Uses PBKDF2-SHA256 by default. No additional library needed for 1–5 user internal tool |
| Flask-WTF | 1.2.x | CSRF protection + form validation | Even for internal tools, CSRF tokens on login forms are non-negotiable. Flask-WTF wraps WTForms with Flask integration and CSRF middleware |
### Excel Import
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| openpyxl | 3.1.x | Read `.xlsx` files | Direct `.xlsx` read without pandas overhead. For this use case (read 3 columns, validate, iterate rows) pandas is overkill — it adds 30MB of dependencies for what is fundamentally a loop over rows |
| WTForms `FileField` + Flask-WTF | (bundled) | File upload validation | Validates presence and extension before openpyxl sees the file |
### HTTP Client (VTEX API + Itaú API)
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| httpx | 0.27.x | HTTP client for VTEX MasterData and Itaú API | `requests` is synchronous only and has not received major updates. `httpx` has a compatible API to `requests` but supports both sync and async, has better timeout handling, and is actively maintained. For this project, sync mode is sufficient |
### CNAB File Generation
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python `struct` (stdlib) | — | Fixed-width byte packing | CNAB 240 records are exactly 240 bytes. Python's `struct` module handles byte-level packing correctly |
| Python `str.ljust` / `str.rjust` / `str.zfill` | — | Field formatting | Alfanumérico = `str.ljust(n)[:n]`, numérico = `str.zfill(n)[-n:]`. No library needed — implement a small `cnab_field()` helper |
| `codecs` (stdlib) | — | Encoding | FEBRABAN specifies CP1252 (Windows-1252) or ISO-8859-1 for CNAB files. Python's `codecs` or `.encode('cp1252')` handles this. Validate exact encoding requirement against Itaú SISPAG v085 documentation |
### File Storage
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Local filesystem | — | Store generated CNAB `.rem` files | For a single-server deployment, filesystem storage is correct. Store under a configurable `UPLOAD_FOLDER` / `OUTPUT_FOLDER` outside the app source tree. Record filepath in the database |
| Python `pathlib` (stdlib) | — | Path management | Use `pathlib.Path` exclusively — never `os.path.join` for new code |
### Configuration and Secrets
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| python-dotenv | 1.0.x | Load `.env` file in development | Standard Flask pattern. In production, set environment variables directly (systemd `EnvironmentFile`, Docker `--env-file`, etc.). Never commit `.env` |
| Flask config objects | — | Environment-specific config | Use `DevelopmentConfig`, `ProductionConfig` classes. `app.config.from_object()` pattern |
- `VTEX_APP_KEY` / `VTEX_APP_TOKEN`
- `SECRET_KEY` (Flask session signing)
- `DATABASE_URL`
- Itaú API credentials (when available)
### Frontend
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Jinja2 templates | (with Flask) | Server-side HTML rendering | Correct for an internal tool. No build pipeline, no npm, no SPA complexity |
| Bootstrap 5.3.x | CDN | CSS framework | Load from CDN. No build step. Provides the table, card, badge, and form components needed for the dashboard and upload forms |
| Vanilla JS | — | Minimal interactivity | File upload progress, form validation feedback. No framework. jQuery is not needed for this scope |
### Task Queue / Background Processing
### Testing
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pytest | 8.x | Test runner | Standard. `pytest` over `unittest` for less boilerplate and better fixtures |
| pytest-flask | 1.3.x | Flask test client fixture | Provides `app`, `client`, `live_server` fixtures. Avoids manual `app.test_client()` setup in every test |
### WSGI Server (Production)
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Gunicorn | 22.x | Production WSGI server | Standard for Flask production. 2–4 synchronous workers are sufficient for 1–5 concurrent users. Never use Flask's built-in development server in production |
## Alternatives Considered
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| HTTP client | httpx | requests | requests is maintenance-only; httpx has identical API and active development |
| Excel | openpyxl | pandas | pandas adds 30MB+ of transitive deps for a 3-column row iterator |
| Auth | Flask-Login + Werkzeug | Flask-Security | Flask-Security is 5x the code for registration/email/roles we don't need |
| DB | SQLite + SQLAlchemy | Raw sqlite3 | Raw sqlite3 loses migrations, ORM relationships, and type safety for minimal gain |
| DB | SQLite → PostgreSQL path | PostgreSQL from day one | PostgreSQL adds server ops overhead with no benefit at 1–5 users |
| CNAB | Custom module | python-cnab / febraban libs | Community CNAB libs target generic FEBRABAN; Itaú SISPAG v085 has bank-specific deviations that require manual layout control |
| Frontend | Jinja2 + Bootstrap | React/Vue SPA | SPA adds build pipeline, npm, separate deployment, API versioning for zero additional user value |
| Background | (none) | Celery + Redis | No async processing need identified; adds Redis dependency and worker management |
## Installation
# Create virtual environment
# Core
# Database
# HTTP client
# Excel
# Config
# Testing
# Production WSGI
## Encoding Note for CNAB
- **ISO-8859-1** (Latin-1) — older CNAB specs
- **CP1252** (Windows-1252) — common for Windows-generated files
- **UTF-8** — increasingly used in newer specs
## Sources
- Training knowledge (Python/Flask ecosystem, cutoff August 2025) — MEDIUM confidence for versions
- Project constraints from `.planning/PROJECT.md` — HIGH confidence (first-party)
- VTEX API structure from `./Documents/Vtex API Info.txt` — HIGH confidence (first-party)
- CNAB 240 SISPAG Itaú v085 spec from `./Documents/sispag_cnab.md` — HIGH confidence (first-party)
- Flask official docs at flask.palletsprojects.com — blocked in this session; version claims rely on training data
- NOTE: WebSearch, WebFetch, and Bash were denied in this research session. All version numbers must be verified with `pip index versions <package>` before being pinned in production requirements.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
