# WinPatch

A web-based tool for patching Windows servers over WinRM. Upload a CSV or Excel file with your server list, preview it, then either run a connectivity test or start patching — all from a browser.

## What it does

1. **Upload** a server list (CSV or XLSX) with IP addresses, restart windows, and optional per-server credentials
2. **Preview** the parsed servers and validate restart window formats
3. **Test Connectivity** (optional) — connects to every server, verifies the PSWindowsUpdate module, and counts available updates without installing anything
4. **Start Patching** — installs all available Windows updates on every server concurrently, then schedules a restart within the configured window
5. **Monitor** progress in real time as each server moves through connecting → installing → restart scheduled
6. **Manage** individual servers from the job detail page — trigger immediate restarts, reschedule restart windows, or re-test connectivity

---

## Quick Start

### 1. Prerequisites

- Python 3.12+ or Docker
- WinRM enabled on each target Windows server (see [SETUP.md](SETUP.md) for the one-time server config)
- A service account with local Administrator rights on the targets

### 2. Run with Docker

```bash
cp .env.example .env          # edit SECRET_KEY if you have one; one is auto-generated on first run
docker compose up -d
```

App is available at **http://localhost:5000**

### 3. Run with Python

```bash
pip install -r requirements.txt
python run.py
```

---

## Server List Format

Upload a `.csv` or `.xlsx` file with these columns:

| Column | Required | Example |
|---|---|---|
| `server_name` | Yes | `PROD-WEB-01` |
| `ip_address` | Yes | `192.168.1.10` |
| `restart_window` | Yes | `Sunday 02:00` |
| `username` | No | `DOMAIN\svcpatch` |
| `password` | No | *(per-server override)* |

**Restart window formats:**
- `Sunday 02:00` — next occurrence of that weekday/time
- `Sat 03:30` — abbreviated day name
- `2026-06-15 02:00` — specific date/time

A [sample template](app/static/sample_servers.csv) is available for download from the new job page.

---

## Test Mode

Before committing to a full patch run, use **Test Connectivity** to do a dry-run preflight:

- Connects to each server via WinRM and validates credentials
- Verifies the `PSWindowsUpdate` module is installed (installs it if missing)
- Counts available updates on each server — without installing anything
- Reports results as a job record, visible in the dashboard history

Test jobs are marked with a **Test** badge in the dashboard and show an info banner on the detail page. The "Updates Available" column shows how many patches are waiting on each server.

---

## Workflow

```
Upload CSV → Preview servers → [Test Connectivity] → Start Patching → Monitor progress
```

Each server in a job goes through these statuses:

| Status | Meaning |
|---|---|
| `pending` | Queued, not started yet |
| `connecting` | Opening WinRM session |
| `checking_module` | Verifying PSWindowsUpdate |
| `checking_updates` | Counting available updates |
| `installing` | Installing updates (patch jobs only) |
| `scheduling_restart` | Registering restart task (patch jobs only) |
| `restart_scheduled` | Done — restart queued within window |
| `up_to_date` | No updates needed |
| `test_complete` | Test run finished — see update count |
| `error` | Failed — hover the icon for details |

---

## Settings

Navigate to **Settings** to configure:

- **Default credentials** — username and password used when no per-server override is set (stored encrypted)
- **WinRM port** — default `5985`
- **Max concurrent workers** — how many servers to patch in parallel (default `10`)

---

## Security

- **No built-in authentication.** Intended for internal/private network use. Place behind a reverse proxy (nginx, Caddy) with authentication for any team-facing deployment. Do not expose port 5000 to the internet.
- **IP validation.** Only RFC1918 (private) addresses are reachable. Public IPs are blocked at the connection layer.
- **Credentials at rest** are encrypted with Fernet. Back up your `SECRET_KEY` — without it, stored credentials cannot be decrypted.
- **CSRF protection** is enabled on all forms.
- **WinRM over HTTP** (port 5985) uses NTLM auth. For higher-security environments, see [SETUP.md](SETUP.md) for HTTPS/5986 configuration.

---

## Project Structure

```
app/
  routes/         # Flask blueprints (dashboard, jobs, api, settings)
  services/       # WinRM worker, file parser, crypto, IP validator
  templates/      # Jinja2 HTML templates
  static/         # app.js (live polling), sample CSV
  models.py       # SQLAlchemy models (Job, Server, AppSettings)
  database.py     # SQLAlchemy engine init
tests/            # pytest suite
docs/             # Design specs and implementation plans
```

See [SETUP.md](SETUP.md) for WinRM prerequisites, deployment details, and security hardening notes.
