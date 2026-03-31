# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-03-31
**Phases:** 4 | **Plans:** 8 | **Tasks:** 12

### What Was Built
- CNAB 240 byte-exact engine with PIX key detection and pre-generation validation (167 tests)
- Authentication, user management, and encrypted VTEX credentials storage
- Excel import with VTEX MasterData enrichment and per-row validation report
- Desktop application with dashboard, file detail drill-down, audit log, and CNAB download

### What Worked
- Risk-first phase ordering: building CNAB engine first (highest rejection risk) proved correct — byte-exact issues were caught by tests before any UI existed
- Service layer pattern (flush-never-commit) made transaction boundaries clean and testable
- Screen-as-QDialog with session param enabled consistent UI patterns across all 6 dialogs
- SQLAlchemy 2.0 Mapped[T] from day one avoided legacy migration debt

### What Was Inefficient
- Transmission feature (mock_transmit, TransmissionConfirmDialog) was built and then removed — Itau does not offer API for CNAB submission. Earlier discovery would have saved one dialog and service function
- Phase 1 CNAB engine checkbox in ROADMAP.md never marked complete despite all plans executing successfully

### Patterns Established
- `cnab_service.py` as service layer: functions flush but never commit, caller owns transaction
- QSettings("PrettyNew", "CNAB-PIX") for persisting UI preferences (Save As directory)
- Dashboard refresh pattern: _refresh_table() queries with filters and repopulates QTableWidget
- Audit log on every significant action (geracao, download, exclusao) with target_type/target_id

### Key Lessons
1. Validate business process assumptions (does the bank offer an API?) before planning transmission features
2. Service layer with no-commit pattern simplifies error handling — rollback stays in UI layer
3. PySide6 + SQLAlchemy 2.0 on Python 3.14 requires specific version pins (PySide6>=6.10.1, SQLAlchemy>=2.0.48)

### Cost Observations
- Model mix: ~40% opus (planning, execution), ~50% sonnet (research, verification, execution), ~10% orchestration
- Sessions: ~6 sessions across 2 days
- Notable: Phase 4 plans executed in ~5 minutes total (2 plans, 4 tasks) — service layer + UI wiring was straightforward thanks to well-defined models from Phase 2

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | ~6 | 4 | First milestone — established GSD workflow patterns |

### Cumulative Quality

| Milestone | Tests | UAT | Zero-Dep Additions |
|-----------|-------|-----|-------------------|
| v1.0 | 167 | 8/8 | 0 (all stdlib or pip) |

### Top Lessons (Verified Across Milestones)

1. Risk-first ordering pays off: build the hardest/riskiest component first
2. Validate external integration assumptions before building features around them
