const STATUS_COLORS = {
  pending: 'secondary',
  connecting: 'primary',
  checking_module: 'primary',
  checking_updates: 'primary',
  installing: 'primary',
  scheduling_restart: 'primary',
  up_to_date: 'success',
  restart_scheduled: 'success',
  test_complete: 'success',
  restarting: 'warning',
  error: 'danger',
};

const STATUS_LABELS = {
  pending: 'Pending',
  connecting: 'Connecting...',
  checking_module: 'Checking module...',
  checking_updates: 'Checking updates...',
  installing: 'Installing updates...',
  scheduling_restart: 'Scheduling restart...',
  up_to_date: 'Up to date',
  restart_scheduled: 'Restart scheduled',
  test_complete: 'Ready',
  restarting: 'Restarting...',
  error: 'Error',
};

let pollInterval = null;

function startPolling() {
  pollInterval = setInterval(pollStatus, 5000);
}

async function pollStatus() {
  try {
    const res = await fetch(`/api/jobs/${JOB_ID}`);
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById('progress-label').textContent =
      `${data.progress.done} / ${data.progress.total} servers complete`;
    document.getElementById('progress-pct').textContent = `${data.progress.pct}%`;
    document.getElementById('progress-bar').style.width = `${data.progress.pct}%`;

    for (const server of data.servers) {
      updateRow(server);
    }

    if (data.progress.pct === 100) {
      clearInterval(pollInterval);
      document.getElementById('progress-bar').classList.remove(
        'progress-bar-striped', 'progress-bar-animated'
      );
    }
  } catch (e) {
    console.error('Poll failed', e);
  }
}

function updateRow(s) {
  const row = document.getElementById(`row-${s.id}`);
  if (!row) return;

  const badge = row.querySelector('.status-badge');
  const color = STATUS_COLORS[s.status] || 'secondary';
  badge.className = `badge text-white status-badge bg-${color}`;
  badge.textContent = STATUS_LABELS[s.status] || s.status.replace(/_/g, ' ');

  const cells = row.querySelectorAll('td');
  cells[3].textContent = s.updates_installed != null ? s.updates_installed : '—';
  cells[4].textContent = s.restart_scheduled_at
    ? s.restart_scheduled_at.replace('T', ' ').substring(0, 16)
    : '—';
}

async function testConnection(serverId, btn) {
  btn.disabled = true;
  btn.textContent = 'Testing...';
  try {
    const res = await fetch(`/api/servers/${serverId}/test`, { method: 'POST' });
    const data = await res.json();
    alert(data.success ? `Connected: ${data.message}` : `Failed: ${data.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Test';
  }
}

async function manualRestart(serverId) {
  if (!confirm('Trigger an immediate restart on this server?')) return;
  const res = await fetch(`/api/servers/${serverId}/restart`, { method: 'POST' });
  const data = await res.json();
  alert(data.success ? 'Restart initiated.' : `Error: ${data.message}`);
  pollStatus();
}

async function reschedule(serverId) {
  const newWindow = prompt('New restart window (e.g. "Sunday 02:00" or "2026-06-15 02:00"):');
  if (!newWindow) return;
  const res = await fetch(`/api/servers/${serverId}/reschedule`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ restart_window: newWindow }),
  });
  const data = await res.json();
  alert(data.success ? `Rescheduled for ${data.restart_at}` : `Error: ${data.message}`);
  pollStatus();
}

document.addEventListener('DOMContentLoaded', () => {
  startPolling();
  const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltips.forEach(el => new bootstrap.Tooltip(el));
});
