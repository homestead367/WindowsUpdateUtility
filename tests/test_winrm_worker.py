import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from app.config import TestConfig
from app.database import get_session
from app.models import Job, Server


@pytest.fixture
def app():
    return create_app(TestConfig.__dict__)


@pytest.fixture
def test_server(app):
    s = get_session()
    job = Job(filename='test.csv', status='running', job_type='test')
    s.add(job)
    s.flush()
    server = Server(
        job_id=job.id,
        server_name='TEST-01',
        ip_address='10.0.0.1',
        restart_window='Sunday 02:00',
    )
    s.add(server)
    s.commit()
    server_id = server.id
    job_id = job.id
    s.close()
    yield server_id
    s2 = get_session()
    srv = s2.get(Server, server_id)
    jb = s2.get(Job, job_id)
    if srv:
        s2.delete(srv)
    if jb:
        s2.delete(jb)
    s2.commit()
    s2.close()


def _ps(stdout=b'', status_code=0):
    r = MagicMock()
    r.status_code = status_code
    r.std_out = stdout
    r.std_err = b''
    return r


def test_test_worker_happy_path(app, test_server):
    mock_session = MagicMock()
    mock_session.run_ps.side_effect = [
        _ps(b'ping'),   # connectivity ping
        _ps(b'OK'),     # PS_ENSURE_MODULE
        _ps(b'5'),      # PS_LIST_UPDATES — 5 available
    ]
    with patch('app.services.winrm_worker.winrm.Session', return_value=mock_session):
        from app.services.winrm_worker import run_server_test_worker
        run_server_test_worker(test_server, 'admin', 'pass', None, 5985)

    s = get_session()
    try:
        server = s.get(Server, test_server)
        assert server.status == 'test_complete'
        assert server.updates_installed == 5
    finally:
        s.close()


def test_test_worker_zero_updates(app, test_server):
    mock_session = MagicMock()
    mock_session.run_ps.side_effect = [_ps(b'ping'), _ps(b'OK'), _ps(b'0')]
    with patch('app.services.winrm_worker.winrm.Session', return_value=mock_session):
        from app.services.winrm_worker import run_server_test_worker
        run_server_test_worker(test_server, 'admin', 'pass', None, 5985)

    s = get_session()
    try:
        server = s.get(Server, test_server)
        assert server.status == 'test_complete'
        assert server.updates_installed == 0
    finally:
        s.close()


def test_test_worker_blocked_ip(app, test_server):
    with patch('app.services.winrm_worker.is_allowed_ip', return_value=False):
        from app.services.winrm_worker import run_server_test_worker
        run_server_test_worker(test_server, 'admin', 'pass', None, 5985)

    s = get_session()
    try:
        server = s.get(Server, test_server)
        assert server.status == 'error'
        assert 'Blocked' in server.error_message
    finally:
        s.close()


def test_test_worker_connection_failure(app, test_server):
    with patch('app.services.winrm_worker.winrm.Session', side_effect=Exception('refused')):
        from app.services.winrm_worker import run_server_test_worker
        run_server_test_worker(test_server, 'admin', 'pass', None, 5985)

    s = get_session()
    try:
        server = s.get(Server, test_server)
        assert server.status == 'error'
        assert 'WinRM unreachable' in server.error_message
    finally:
        s.close()


def test_test_worker_module_failure(app, test_server):
    mock_session = MagicMock()
    fail = MagicMock()
    fail.status_code = 1
    fail.std_err = b'module error'
    mock_session.run_ps.side_effect = [_ps(b'ping'), fail]
    with patch('app.services.winrm_worker.winrm.Session', return_value=mock_session):
        from app.services.winrm_worker import run_server_test_worker
        run_server_test_worker(test_server, 'admin', 'pass', None, 5985)

    s = get_session()
    try:
        server = s.get(Server, test_server)
        assert server.status == 'error'
        assert 'PSWindowsUpdate install failed' in server.error_message
    finally:
        s.close()
