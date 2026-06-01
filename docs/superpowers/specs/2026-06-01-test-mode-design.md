# Test Mode Design

**Date:** 2026-06-01  
**Status:** Approved

## Overview

Add a "test mode" to the Windows patching application. When selected, a job runs full connectivity preflight (WinRM connect → PSWindowsUpdate module check → available update count) against all servers in the list, but stops before installing anything. Results are persisted as a first-class job record so they are browseable in history.

## Data Model

### `Job` model — new column

```python
job_type: Mapped[str] = mapped_column(String(10), default='patch')  # 'patch' | 'test'
```

- Existing jobs default to `'patch'` via column default; no migration data backfill needed.
- `Job.progress()` adds `'test_complete'` to its terminal-state set so progress bars work for test jobs.

### `Server` model — unchanged

The existing `updates_installed` integer field stores *available* update count for test jobs. The `job_type` on the parent job disambiguates semantics. Server status flow for test jobs:

```
pending → connecting → checking_module → checking_updates → test_complete | error
```

## Worker

New function `run_server_test_worker(server_id, default_username, default_password, per_server_password, winrm_port)` in `app/services/winrm_worker.py`.

Steps:
1. IP validation (same `is_allowed_ip` guard as existing worker)
2. WinRM connect + ping (`Write-Output "ping"`)
3. `PS_ENSURE_MODULE` — installs PSWindowsUpdate if missing
4. `PS_LIST_UPDATES` — counts available updates, stores in `updates_installed`
5. Sets `status='test_complete'`

Stops at step 4. No install, no restart scheduling. Error handling and `_update_server` calls are identical in structure to `run_server_worker`.

## Routes

### New route: `POST /jobs/new/test`

Handler in `app/routes/jobs.py`, structurally identical to `start_job`:
- Reads `filename`, `default_username`, `default_password` from form
- Parses server file
- Creates `Job(filename=filename, status='running', job_type='test')`
- Creates `Server` records
- Dispatches `run_server_test_worker` via thread pool
- Redirects to job detail page

The existing `POST /jobs/new/start` route is untouched.

## UI Changes

### `new_job.html` — confirm card footer

Two buttons side by side:
- **"Test Connectivity"** (outline-secondary) — `action="/jobs/new/test"`
- **"Start Patching"** (success) — `action="/jobs/new/start"` (existing)

Both share the same password field and CSRF token within a single form, distinguished by separate `<form>` tags each with their own `action`.

### `job_detail.html`

When `job.job_type == 'test'`:
- Info banner: "Test run — no patches were installed. This job checked connectivity and counted available updates only."
- Column header: "Updates Available" instead of "Updates Installed"
- `test_complete` status renders as a green success badge ("Ready")
- Restart action buttons hidden

### `dashboard.html`

Test jobs get a small "Test" badge (secondary/muted) next to the filename in the job list.

## Out of Scope

- No separate test-only nav item or page
- No automatic pre-flight gate blocking patch jobs (test mode is opt-in)
- No email/notification on test completion
