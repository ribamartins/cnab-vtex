# Technology Stack

**Project:** CNAB PIX Payment File Generation System (PrettyNew / Itaú SISPAG)
**Researched:** 2026-03-30
**Confidence note:** WebSearch, WebFetch, and Bash are restricted in this environment. All version claims are from training knowledge (cutoff August 2025). Flag versions for pip-based verification before pinning in requirements.txt.

---

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.12.x | Runtime | Latest stable with significant performance improvements over 3.10/3.11; `tomllib` built-in; `typing` improvements reduce boilerplate |
| Flask | 3.0.x | Web framework | Constraint-mandated. Flask 3.0 dropped Python 3.8 support and cleaned legacy APIs. Minimal surface area is correct for this domain — no ORM opinions, no DI container complexity |
| Werkzeug | 3.0.x | WSGI utilities | Ships with Flask 3.0; do not pin separately unless you hit a specific bug |
| Jinja2 | 3.1.x | Templating | Ships with Flask; server-side rendering is correct for a small internal tool |

**Confidence:** MEDIUM — Flask 3.0 released late 2023 and was stable by mid-2024. Python 3.12 was the current stable as of August 2025. Verify exact patch versions before pinning.

---

### Database

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| SQLite | 3.x (system) | Development and single-server production | Correct choice for 1–5 users with no concurrent write load. No ops overhead, file is portable, backups are `cp`. Zero-configuration. |
| Flask-SQLAlchemy | 3.1.x | ORM layer | Bridges Flask app context with SQLAlchemy sessions correctly. Avoid raw SQLAlchemy without it in Flask — context teardown is error-prone to manage manually |
| SQLAlchemy | 2.x | ORM core | SQLAlchemy 2.0 introduced the modern `mapped_column` / `Mapped[T]` API. Use it from day one — the legacy 1.x style still works but should not be started fresh |
| Alembic | 1.13.x | DB migrations | Even for SQLite, use Alembic from the start. Schema changes without migrations are painful at phase 2+ |

**PostgreSQL upgrade path:** If the team grows or the system is deployed to a server shared with other apps, swap `sqlite:///` for `postgresql+psycopg2://` in `DATABASE_URL`. Flask-SQLAlchemy and Alembic are database-agnostic — no code changes required.

**Confidence:** HIGH — SQLAlchemy 2.x has been stable since 2023; Flask-SQLAlchemy 3.x aligns with it. This is the canonical Flask persistence pattern.

---

### Authentication

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Flask-Login | 0.6.x | Session-based auth | The standard for Flask user sessions. Provides `login_required`, `current_user`, `login_user`, `logout_user`. Minimal — doesn't force a user model shape |
| Werkzeug `generate_password_hash` / `check_password_hash` | (bundled) | Password hashing | Already in Werkzeug (Flask dependency). Uses PBKDF2-SHA256 by default. No additional library needed for 1–5 user internal tool |
| Flask-WTF | 1.2.x | CSRF protection + form validation | Even for internal tools, CSRF tokens on login forms are non-negotiable. Flask-WTF wraps WTForms with Flask integration and CSRF middleware |

**Do NOT use:** Flask-Security, Flask-User, or Authlib. All are over-engineered for 1–5 users. Flask-Security pulls in Flask-Mail, Flask-Principal, and a registration flow you don't need. Simple username/password with Flask-Login is the right scope.

**Confidence:** HIGH — Flask-Login 0.6.x has been the unchanged standard for years; this is extremely well-established.

---

### Excel Import

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| openpyxl | 3.1.x | Read `.xlsx` files | Direct `.xlsx` read without pandas overhead. For this use case (read 3 columns, validate, iterate rows) pandas is overkill — it adds 30MB of dependencies for what is fundamentally a loop over rows |
| WTForms `FileField` + Flask-WTF | (bundled) | File upload validation | Validates presence and extension before openpyxl sees the file |

**Do NOT use pandas** for Excel import here. Pandas is appropriate when you need vectorized operations, groupbys, or statistical analysis. Reading three columns from an uploaded Excel file is not that use case. openpyxl is lighter, faster to import, and produces a simpler error model.

**Confidence:** HIGH — openpyxl 3.x is stable; this recommendation is unambiguous for this use case.

---

### HTTP Client (VTEX API + Itaú API)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| httpx | 0.27.x | HTTP client for VTEX MasterData and Itaú API | `requests` is synchronous only and has not received major updates. `httpx` has a compatible API to `requests` but supports both sync and async, has better timeout handling, and is actively maintained. For this project, sync mode is sufficient |

**Do NOT use `requests`** as the primary HTTP client for new code. It remains functional but `httpx` is the forward-looking choice and its API is nearly identical — the migration cost is zero for new code.

**Confidence:** MEDIUM — httpx 0.27.x is the current stable as of my knowledge cutoff. Verify current version.

---

### CNAB File Generation

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python `struct` (stdlib) | — | Fixed-width byte packing | CNAB 240 records are exactly 240 bytes. Python's `struct` module handles byte-level packing correctly |
| Python `str.ljust` / `str.rjust` / `str.zfill` | — | Field formatting | Alfanumérico = `str.ljust(n)[:n]`, numérico = `str.zfill(n)[-n:]`. No library needed — implement a small `cnab_field()` helper |
| `codecs` (stdlib) | — | Encoding | FEBRABAN specifies CP1252 (Windows-1252) or ISO-8859-1 for CNAB files. Python's `codecs` or `.encode('cp1252')` handles this. Validate exact encoding requirement against Itaú SISPAG v085 documentation |

**Architecture note:** CNAB generation should be a pure Python module with zero Flask dependencies. It receives a Python dataclass/dict and returns `bytes`. This makes it independently testable without a running app.

**Confidence:** HIGH — CNAB 240 is a fixed-width text format; stdlib string and bytes operations are the correct tool. No third-party CNAB library should be trusted — the Itaú SISPAG v085 layout is bank-specific and community libraries often target generic FEBRABAN, not Itaú's extensions.

---

### File Storage

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Local filesystem | — | Store generated CNAB `.rem` files | For a single-server deployment, filesystem storage is correct. Store under a configurable `UPLOAD_FOLDER` / `OUTPUT_FOLDER` outside the app source tree. Record filepath in the database |
| Python `pathlib` (stdlib) | — | Path management | Use `pathlib.Path` exclusively — never `os.path.join` for new code |

**Do NOT use** object storage (S3, MinIO) yet. Premature infrastructure for a 1–5 user internal tool on a single server. Add only if the system moves to a cloud-hosted multi-instance deployment.

---

### Configuration and Secrets

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| python-dotenv | 1.0.x | Load `.env` file in development | Standard Flask pattern. In production, set environment variables directly (systemd `EnvironmentFile`, Docker `--env-file`, etc.). Never commit `.env` |
| Flask config objects | — | Environment-specific config | Use `DevelopmentConfig`, `ProductionConfig` classes. `app.config.from_object()` pattern |

**Secrets that must be environment variables (never in code):**
- `VTEX_APP_KEY` / `VTEX_APP_TOKEN`
- `SECRET_KEY` (Flask session signing)
- `DATABASE_URL`
- Itaú API credentials (when available)

**Confidence:** HIGH — python-dotenv 1.0.x is stable and this pattern is canonical Flask.

---

### Frontend

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Jinja2 templates | (with Flask) | Server-side HTML rendering | Correct for an internal tool. No build pipeline, no npm, no SPA complexity |
| Bootstrap 5.3.x | CDN | CSS framework | Load from CDN. No build step. Provides the table, card, badge, and form components needed for the dashboard and upload forms |
| Vanilla JS | — | Minimal interactivity | File upload progress, form validation feedback. No framework. jQuery is not needed for this scope |

**Do NOT use React, Vue, or any SPA framework.** The interactivity requirements (upload file, view table, submit form) do not justify a separate frontend build pipeline. This would add weeks to the project for zero user-facing value.

**Confidence:** HIGH — this is the correct scope decision for an internal financial tool with 1–5 users.

---

### Task Queue / Background Processing

**Not needed at this stage.** CNAB file generation is fast (milliseconds for hundreds of records). VTEX API calls are synchronous and fast. The Itaú API transmission can be triggered via a button click with a synchronous HTTP call. If transmission takes >30 seconds (unlikely for a single file), revisit with Celery + Redis, but do not add this complexity speculatively.

---

### Testing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pytest | 8.x | Test runner | Standard. `pytest` over `unittest` for less boilerplate and better fixtures |
| pytest-flask | 1.3.x | Flask test client fixture | Provides `app`, `client`, `live_server` fixtures. Avoids manual `app.test_client()` setup in every test |

**Critical test focus:** The CNAB byte-level output. Every field offset and length must be covered by unit tests with known-good expected bytes. This is the highest-risk area for silent bugs.

**Confidence:** MEDIUM — pytest 8.x was current as of my knowledge cutoff. Verify.

---

### WSGI Server (Production)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Gunicorn | 22.x | Production WSGI server | Standard for Flask production. 2–4 synchronous workers are sufficient for 1–5 concurrent users. Never use Flask's built-in development server in production |

**Confidence:** MEDIUM — Gunicorn 22.x was current as of mid-2025. Verify.

---

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

---

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Core
pip install Flask==3.0.* Flask-SQLAlchemy==3.1.* Flask-Login==0.6.* Flask-WTF==1.2.*

# Database
pip install SQLAlchemy==2.* alembic==1.13.*

# HTTP client
pip install httpx==0.27.*

# Excel
pip install openpyxl==3.1.*

# Config
pip install python-dotenv==1.0.*

# Testing
pip install pytest==8.* pytest-flask==1.3.*

# Production WSGI
pip install gunicorn==22.*
```

**Verify all versions against PyPI before pinning in `requirements.txt`.** Exact patch versions (e.g., `Flask==3.0.3`) should be confirmed with `pip index versions Flask` or checked at pypi.org. The minor versions above (3.0.x, 3.1.x) are validated against my training knowledge cutoff of August 2025 but may have newer patches available.

---

## Encoding Note for CNAB

FEBRABAN standard and Itaú SISPAG v085 documentation must be read to confirm the exact encoding. The most common encodings for Brazilian bank files are:

- **ISO-8859-1** (Latin-1) — older CNAB specs
- **CP1252** (Windows-1252) — common for Windows-generated files
- **UTF-8** — increasingly used in newer specs

Check section 2 ("Informações Técnicas") of `./Documents/sispag_cnab.md` for the declared encoding. Use `'cp1252'` as the safe default if the document is silent, as this is what most Brazilian banking software produces. Implement encoding as a single constant (`CNAB_ENCODING = 'cp1252'`) so it can be changed in one place.

---

## Sources

- Training knowledge (Python/Flask ecosystem, cutoff August 2025) — MEDIUM confidence for versions
- Project constraints from `.planning/PROJECT.md` — HIGH confidence (first-party)
- VTEX API structure from `./Documents/Vtex API Info.txt` — HIGH confidence (first-party)
- CNAB 240 SISPAG Itaú v085 spec from `./Documents/sispag_cnab.md` — HIGH confidence (first-party)
- Flask official docs at flask.palletsprojects.com — blocked in this session; version claims rely on training data
- NOTE: WebSearch, WebFetch, and Bash were denied in this research session. All version numbers must be verified with `pip index versions <package>` before being pinned in production requirements.
