# Phase 4: Desktop Application - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-31
**Phase:** 04-desktop-application
**Areas discussed:** CNAB generation flow, Dashboard layout, Mock transmission UX, Audit log viewer

---

## CNAB Generation Flow

| Option | Description | Selected |
|--------|-------------|----------|
| Generate + auto-download | Generate CNAB, save to DB, immediately open Save As dialog for .txt | ✓ |
| Generate + confirm + manual download | Generate, show success dialog, user downloads later from dashboard | |
| Generate + preview bytes | Show byte preview before saving (power-user flow) | |

**User's choice:** Generate + auto-download
**Notes:** One-click flow preferred — fewest steps for finance team

### Filename Convention

| Option | Description | Selected |
|--------|-------------|----------|
| CNAB_YYYYMMDD_NNN.txt | Date + sequential number per day | ✓ |
| CNAB_YYYYMMDD_HHMMSS.txt | Date + timestamp | |
| You decide | Claude picks | |

**User's choice:** CNAB_YYYYMMDD_NNN.txt

### Save Path Behavior

**User's choice:** "Voce pode definir isso" — deferred to Claude's discretion

### Re-download

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, download button on each file | Dashboard file list has download button per row | ✓ |
| No, only at generation time | File only downloadable during initial flow | |

**User's choice:** Yes, download button on each file

---

## Dashboard Layout

| Option | Description | Selected |
|--------|-------------|----------|
| File list table | Main area is a table of CNAB files with filters above | ✓ |
| Summary cards + file list | Top row summary cards + file list table below | |
| You decide | Claude picks layout | |

**User's choice:** File list table

### File Detail Drill-down

| Option | Description | Selected |
|--------|-------------|----------|
| Detail dialog | Click row opens QDialog with file info + payments table | ✓ |
| Inline expand | Row expands in-place showing details below | |
| Separate screen | Navigate to full detail screen replacing dashboard | |

**User's choice:** Detail dialog

### Dashboard Filters

| Option | Description | Selected |
|--------|-------------|----------|
| Dropdown + date range | Status dropdown + date range pickers, apply immediately | ✓ |
| Filter chips | Colored badges that toggle on/off + date range | |
| You decide | Claude picks filter approach | |

**User's choice:** Dropdown + date range

---

## Mock Transmission UX

### Trigger Location

| Option | Description | Selected |
|--------|-------------|----------|
| File detail dialog | Transmitir button in detail dialog, only for Criado files | ✓ |
| Dashboard row action | Transmit button on each dashboard row | |
| Both places | Available in both dashboard and detail dialog | |

**User's choice:** File detail dialog

### Mock Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Always succeed | Mock always returns success, error flow tested in dev | ✓ |
| Configurable success rate | Settings toggle to randomly fail ~20% | |
| You decide | Claude picks mock behavior | |

**User's choice:** Always succeed

---

## Audit Log Viewer

### Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Menu item -> separate dialog | Arquivo menu > Log de Auditoria opens QDialog | ✓ |
| Tab in dashboard | Dashboard has Arquivos and Auditoria tabs | |
| You decide | Claude picks placement | |

**User's choice:** Menu item -> separate dialog

### Audit Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Core actions only | Generation, download, transmission, status changes | ✓ |
| Everything | All actions including login, logout, settings | |
| You decide | Claude picks scope | |

**User's choice:** Core actions only

---

## Claude's Discretion

- Save As dialog default folder behavior
- Spinner/progress during generation
- Table column widths and default sort order
- Success message wording
- Audit log detail text format
- Date picker widget choice

## Deferred Ideas

None — discussion stayed within phase scope.
