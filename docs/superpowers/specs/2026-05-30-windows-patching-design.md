# Windows Patch Management App — Design Spec

**Date:** 2026-05-30  
**Status:** Approved

---

## Overview

A Flask-based web application that reads a list of Windows servers (names + IP addresses) from an uploaded Excel or CSV file, remotely pushes all available Windows updates via WinRM/PowerShell, and schedules controlled restarts per server based on maintenance windows defined in the spreadsheet.

---

## Architecture

```
Browser (Bootstrap UI)
        │
        ▼
Flask Web Server (Python)
   ├── File upload + job creation
   ├── REST API for status polling (/api/jobs/<id>)
   └── ThreadPoolExecutor (1 thread per server, max 10 concurrent)
              │
              ▼
        WinRM Session (pywinrm, port 5985, NTLM auth)
              │
              ▼
        PowerShell on target Windows server
           ├── Install PSWindowsUpdate module (if missing)
           ├── Download + install all updates (no auto-reboot)
           └── Register scheduled task for restart at defined window
```

**State storage:** SQLite via SQLAlchemy. No external services required.  
**Deployment:** Runs directly on the Linux host or in Docker. Communicates outbound over TCP 5985/5986 to target Windows servers.

---

## Spreadsheet Format

Accepts `.xlsx` or `.csv`. Column names are case-insensitive. Extra columns are ignored.

| Column | Required | Example | Notes |
|---|---|---|---|
| `server_name` | Yes | `PROD-WEB-01` | Display label only |
| `ip_address` | Yes | `192.168.1.10` | Used for WinRM connection |
| `restart_window` | Yes | `Sunday 02:00` or `2026-06-01 02:00` | Day+time = next occurrence; datetime = exact |
| `username` | No | `DOMAIN\svcaccount` | Overrides default credential |
| `password` | No | `s3cr3t` | Overrides default; in-memory only, never persisted |

**Restart window formats:**
- `Sunday 02:00` / `Sat 03:30` — next upcoming occurrence of that weekday + time
- `2026-06-15 02:00` — exact date and time

A sample template file is bundled with the app and available for download from the UI.

---

## Web UI

### Pages

**Dashboard (`/`)**
- Table of all jobs: filename, started time, server count, progress bar, overall status
- "New Job" button

**New Job (`/jobs/new`)**
- File upload input (`.xlsx` / `.csv`)
- Default credentials form (username + password)
- File preview: validates format and shows parsed server list before confirming
- "Start Patching" button

**Job Detail (`/jobs/<id>`)**
- Auto-refreshing table (polls `/api/jobs/<id>` every 5 seconds)
- Per-server columns: Server Name, IP, Status badge, Updates Installed, Restart Scheduled
- Per-server actions: "Test Connection", "Manual Restart Now", "Reschedule"
- Status badge colors: grey=pending, blue=in progress, green=complete, yellow=restart scheduled, red=error

**Settings (`/settings`)**
- Default credentials (encrypted at rest)
- WinRM port (default: 5985)
- Max concurrent connections (default: 10)

---

## Worker Flow (per server thread)

1. **Open WinRM session** — HTTP port 5985, NTLM auth using per-server or default credentials  
   → Failure: status = "Error: WinRM unreachable", thread exits

2. **Ensure PSWindowsUpdate** — check if module exists; install via `Install-Module PSWindowsUpdate -Force` if not

3. **List available updates** — run `Get-WUList`  
   → If none: status = "Up to date", no restart scheduled, thread exits

4. **Install all updates, no auto-reboot** — `Install-WindowsUpdate -AcceptAll -AutoReboot:$false`  
   → Failure: status = "Error: Install failed", PowerShell output logged

5. **Parse restart window** — calculate next absolute datetime from the spreadsheet value

6. **Register scheduled restart task** — `Register-ScheduledTask` running `shutdown.exe /r /t 60`  
   → Uses server's local timezone; task named `WinPatchRestart` (idempotent overwrite)

7. **Complete** — status = "Restart scheduled for \<datetime\>"

**Concurrency:** `ThreadPoolExecutor(max_workers=10)` (configurable). Servers queue and workers pick up as slots free.  
**Progress writes:** Each step updates SQLite so UI polling reflects real-time state.

---

## Error Handling

| Scenario | Behavior |
|---|---|
| WinRM unreachable | Mark server error, continue remaining servers |
| PSWindowsUpdate install fails | Mark error with PowerShell stderr captured |
| Update install fails mid-run | Mark error, record count of updates that succeeded |
| Invalid restart window in spreadsheet | Flagged at preview stage before job starts |
| Duplicate scheduled task | Overwritten (idempotent) |
| Manual restart while task scheduled | Delete scheduled task, issue immediate `shutdown /r` |

---

## Security

- **Credential encryption:** Default credentials stored in SQLite encrypted with Fernet (from `cryptography` library). Key derived from `SECRET_KEY` env var (auto-generated on first run, saved to `.env`).
- **Per-server passwords:** Used in-memory only during the WinRM session. Never written to disk or database.
- **Transport:** WinRM over HTTP (5985) by default. HTTPS (5986) supported via settings for environments that require it.
- **No auth on the web UI** — this app is intended for internal/private network use. If exposed, place behind a reverse proxy with authentication.

---

## Dependencies

| Package | Purpose |
|---|---|
| `flask` | Web framework |
| `pywinrm` | WinRM / PowerShell remoting |
| `openpyxl` | Excel file parsing |
| `pandas` | CSV + Excel parsing and validation |
| `sqlalchemy` | ORM / SQLite state storage |
| `cryptography` | Fernet encryption for stored credentials |
| `python-dotenv` | `.env` file loading |

---

## Out of Scope

- WSUS integration
- Active Directory / GPO management
- Update rollback
- Multi-tenant / multi-user auth on the web UI
- HTTPS termination (delegate to reverse proxy)
