import winrm
from datetime import datetime
from .restart_window import parse_restart_window
from .ip_validator import is_allowed_ip

PS_ENSURE_MODULE = r"""
$module = Get-Module -ListAvailable -Name PSWindowsUpdate
if (-not $module) {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force -ErrorAction SilentlyContinue
    Install-Module -Name PSWindowsUpdate -Force -Confirm:$false
}
Write-Output "OK"
"""

PS_LIST_UPDATES = r"""
Import-Module PSWindowsUpdate -Force
$updates = Get-WUList -ErrorAction Stop
Write-Output ($updates | Measure-Object).Count
"""

PS_INSTALL_UPDATES = r"""
Import-Module PSWindowsUpdate -Force
$result = Install-WindowsUpdate -AcceptAll -AutoReboot:$false -Confirm:$false -ErrorAction Stop
Write-Output ($result | Where-Object { $_.Result -eq 'Installed' } | Measure-Object).Count
"""

PS_SCHEDULE_RESTART = r"""
param([string]$RestartAt)
$action = New-ScheduledTaskAction -Execute "shutdown.exe" -Argument "/r /f /t 60 /c `"Scheduled maintenance restart`""
$trigger = New-ScheduledTaskTrigger -Once -At $RestartAt
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "WinPatchRestart" -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force | Out-Null
Write-Output "OK"
"""

PS_DELETE_TASK = r"""
$task = Get-ScheduledTask -TaskName "WinPatchRestart" -ErrorAction SilentlyContinue
if ($task) {
    Unregister-ScheduledTask -TaskName "WinPatchRestart" -Confirm:$false
    Write-Output "DELETED"
} else {
    Write-Output "NOT_FOUND"
}
"""

PS_IMMEDIATE_RESTART = r'shutdown /r /f /t 60'


def _run_ps(session: winrm.Session, script: str):
    return session.run_ps(script)


def _update_server(server_id: int, **kwargs):
    from app.database import get_session
    from app.models import Server
    from datetime import timezone
    s = get_session()
    try:
        server = s.get(Server, server_id)
        for k, v in kwargs.items():
            setattr(server, k, v)
        server.updated_at = datetime.now(timezone.utc)
        s.commit()
    finally:
        s.close()


def run_server_worker(server_id: int, default_username: str, default_password: str,
                      per_server_password: str | None, winrm_port: int):
    """
    Worker function executed in a thread for a single server.
    per_server_password is passed in-memory; never written to DB.
    """
    from app.database import get_session
    from app.models import Server

    s = get_session()
    try:
        server = s.get(Server, server_id)
        username = server.username or default_username
        password = per_server_password or default_password
        ip = server.ip_address
        restart_window = server.restart_window
    finally:
        s.close()

    if not is_allowed_ip(ip):
        _update_server(server_id, status='error',
                       error_message=f'Blocked: {ip} is not a private network address')
        return

    _update_server(server_id, status='connecting')

    try:
        session = winrm.Session(
            f'http://{ip}:{winrm_port}/wsman',
            auth=(username, password),
            transport='ntlm',
            server_cert_validation='ignore',
        )
        result = _run_ps(session, 'Write-Output "ping"')
        if result.status_code != 0:
            raise ConnectionError(result.std_err.decode(errors='replace'))
    except Exception as e:
        _update_server(server_id, status='error', error_message=f'WinRM unreachable: {e}')
        return

    _update_server(server_id, status='checking_module')
    result = _run_ps(session, PS_ENSURE_MODULE)
    if result.status_code != 0:
        _update_server(server_id, status='error',
                       error_message='PSWindowsUpdate install failed: ' +
                       result.std_err.decode(errors='replace'))
        return

    _update_server(server_id, status='checking_updates')
    result = _run_ps(session, PS_LIST_UPDATES)
    if result.status_code != 0:
        _update_server(server_id, status='error',
                       error_message='Get-WUList failed: ' +
                       result.std_err.decode(errors='replace'))
        return

    update_count = int(result.std_out.decode(errors='replace').strip() or '0')
    if update_count == 0:
        _update_server(server_id, status='up_to_date', updates_installed=0)
        return

    _update_server(server_id, status='installing')
    result = _run_ps(session, PS_INSTALL_UPDATES)
    if result.status_code != 0:
        _update_server(server_id, status='error',
                       error_message='Install failed: ' +
                       result.std_err.decode(errors='replace'))
        return

    installed = int(result.std_out.decode(errors='replace').strip() or '0')

    _update_server(server_id, status='scheduling_restart', updates_installed=installed)

    try:
        restart_dt = parse_restart_window(restart_window)
    except ValueError as e:
        _update_server(server_id, status='error', error_message=str(e),
                       updates_installed=installed)
        return

    restart_iso = restart_dt.strftime('%Y-%m-%dT%H:%M:%S')
    script = PS_SCHEDULE_RESTART.replace(
        'param([string]$RestartAt)\n', ''
    ).replace('$RestartAt', f'"{restart_iso}"')
    result = _run_ps(session, script)
    if result.status_code != 0:
        _update_server(server_id, status='error',
                       error_message='Schedule task failed: ' +
                       result.std_err.decode(errors='replace'),
                       updates_installed=installed)
        return

    _update_server(server_id, status='restart_scheduled',
                   updates_installed=installed, restart_scheduled_at=restart_dt)


def test_connection(ip: str, port: int, username: str, password: str) -> tuple[bool, str]:
    """Test WinRM connectivity. Returns (success, message)."""
    if not is_allowed_ip(ip):
        return False, f'Blocked: {ip} is not a private network address'
    try:
        session = winrm.Session(
            f'http://{ip}:{port}/wsman',
            auth=(username, password),
            transport='ntlm',
            server_cert_validation='ignore',
        )
        result = session.run_ps('Write-Output "OK"')
        if result.status_code == 0:
            return True, 'Connected successfully'
        return False, result.std_err.decode(errors='replace')
    except Exception as e:
        return False, str(e)


def run_server_test_worker(server_id: int, default_username: str, default_password: str,
                           per_server_password: str | None, winrm_port: int):
    """
    Test-mode worker: connect, verify PSWindowsUpdate module, count available updates.
    Does NOT install updates or schedule restarts.
    Stores available update count in updates_installed.
    """
    from app.database import get_session
    from app.models import Server

    s = get_session()
    try:
        server = s.get(Server, server_id)
        username = server.username or default_username
        password = per_server_password or default_password
        ip = server.ip_address
    finally:
        s.close()

    if not is_allowed_ip(ip):
        _update_server(server_id, status='error',
                       error_message=f'Blocked: {ip} is not a private network address')
        return

    _update_server(server_id, status='connecting')

    try:
        session = winrm.Session(
            f'http://{ip}:{winrm_port}/wsman',
            auth=(username, password),
            transport='ntlm',
            server_cert_validation='ignore',
        )
        result = _run_ps(session, 'Write-Output "ping"')
        if result.status_code != 0:
            raise ConnectionError(result.std_err.decode(errors='replace'))
    except Exception as e:
        _update_server(server_id, status='error', error_message=f'WinRM unreachable: {e}')
        return

    _update_server(server_id, status='checking_module')
    result = _run_ps(session, PS_ENSURE_MODULE)
    if result.status_code != 0:
        _update_server(server_id, status='error',
                       error_message='PSWindowsUpdate install failed: ' +
                       result.std_err.decode(errors='replace'))
        return

    _update_server(server_id, status='checking_updates')
    result = _run_ps(session, PS_LIST_UPDATES)
    if result.status_code != 0:
        _update_server(server_id, status='error',
                       error_message='Get-WUList failed: ' +
                       result.std_err.decode(errors='replace'))
        return

    available = int(result.std_out.decode(errors='replace').strip() or '0')
    _update_server(server_id, status='test_complete', updates_installed=available)


def immediate_restart(ip: str, port: int, username: str, password: str) -> tuple[bool, str]:
    """Delete scheduled task and issue immediate restart."""
    if not is_allowed_ip(ip):
        return False, f'Blocked: {ip} is not a private network address'
    try:
        session = winrm.Session(
            f'http://{ip}:{port}/wsman',
            auth=(username, password),
            transport='ntlm',
            server_cert_validation='ignore',
        )
        _run_ps(session, PS_DELETE_TASK)
        _run_ps(session, PS_IMMEDIATE_RESTART)
        return True, 'Restart initiated'
    except Exception as e:
        return False, str(e)


def reschedule_restart(ip: str, port: int, username: str, password: str,
                       new_window: str) -> tuple[bool, str]:
    """Delete old task and register new restart task. Returns (success, iso_datetime_or_error)."""
    if not is_allowed_ip(ip):
        return False, f'Blocked: {ip} is not a private network address'
    try:
        restart_dt = parse_restart_window(new_window)
    except ValueError as e:
        return False, str(e)

    try:
        session = winrm.Session(
            f'http://{ip}:{port}/wsman',
            auth=(username, password),
            transport='ntlm',
            server_cert_validation='ignore',
        )
        _run_ps(session, PS_DELETE_TASK)
        restart_iso = restart_dt.strftime('%Y-%m-%dT%H:%M:%S')
        script = PS_SCHEDULE_RESTART.replace(
            'param([string]$RestartAt)\n', ''
        ).replace('$RestartAt', f'"{restart_iso}"')
        result = _run_ps(session, script)
        if result.status_code != 0:
            return False, result.std_err.decode(errors='replace')
        return True, restart_dt.isoformat()
    except Exception as e:
        return False, str(e)
