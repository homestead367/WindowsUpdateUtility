import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from app.config import TestConfig
from app.database import get_session
from app.models import Job


@pytest.fixture
def app():
    return create_app(TestConfig.__dict__)


@pytest.fixture
def client(app):
    return app.test_client()


def test_test_job_route_creates_test_type_job(client, tmp_path, monkeypatch):
    upload_dir = str(tmp_path)
    monkeypatch.setenv('UPLOAD_FOLDER', upload_dir)
    (tmp_path / 'servers.csv').write_text('dummy')

    server_data = [{
        'server_name': 'SRV-01',
        'ip_address': '10.0.0.1',
        'restart_window': 'Sunday 02:00',
        'username': '',
        'password': '',
    }]

    with patch('app.routes.jobs.parse_server_file', return_value=server_data), \
         patch('app.routes.jobs.get_executor') as mock_exec:
        mock_exec.return_value.submit = MagicMock()
        res = client.post('/jobs/new/test', data={
            'filename': 'servers.csv',
            'default_username': 'admin',
            'default_password': 'pass',
        })

    assert res.status_code == 302

    s = get_session()
    try:
        job = s.query(Job).filter_by(job_type='test').first()
        assert job is not None
        assert job.status == 'running'
    finally:
        s.close()


def test_test_job_route_dispatches_test_worker(client, tmp_path, monkeypatch):
    upload_dir = str(tmp_path)
    monkeypatch.setenv('UPLOAD_FOLDER', upload_dir)
    (tmp_path / 'servers.csv').write_text('dummy')

    server_data = [{
        'server_name': 'SRV-01',
        'ip_address': '10.0.0.1',
        'restart_window': 'Sunday 02:00',
        'username': '',
        'password': '',
    }]

    submitted_fn = []

    def capture_submit(fn, *args, **kwargs):
        submitted_fn.append(fn)

    with patch('app.routes.jobs.parse_server_file', return_value=server_data), \
         patch('app.routes.jobs.get_executor') as mock_exec:
        mock_exec.return_value.submit = capture_submit
        client.post('/jobs/new/test', data={
            'filename': 'servers.csv',
            'default_username': 'admin',
            'default_password': 'pass',
        })

    from app.services.winrm_worker import run_server_test_worker
    assert len(submitted_fn) == 1
    assert submitted_fn[0] is run_server_test_worker


def test_test_job_missing_filename_redirects(client):
    res = client.post('/jobs/new/test', data={
        'filename': '',
        'default_username': 'admin',
        'default_password': 'pass',
    })
    assert res.status_code == 302
    assert '/jobs/new' in res.headers['Location']


def test_job_detail_exposes_job_type(client, tmp_path, monkeypatch):
    upload_dir = str(tmp_path)
    monkeypatch.setenv('UPLOAD_FOLDER', upload_dir)
    (tmp_path / 'servers.csv').write_text('dummy')

    server_data = [{
        'server_name': 'SRV-01', 'ip_address': '10.0.0.1',
        'restart_window': 'Sunday 02:00', 'username': '', 'password': '',
    }]

    with patch('app.routes.jobs.parse_server_file', return_value=server_data), \
         patch('app.routes.jobs.get_executor') as mock_exec:
        mock_exec.return_value.submit = MagicMock()
        res = client.post('/jobs/new/test', data={
            'filename': 'servers.csv',
            'default_username': 'admin',
            'default_password': 'pass',
        })

    # Follow redirect to job detail
    location = res.headers['Location']
    detail_res = client.get(location)
    assert detail_res.status_code == 200
    assert b'Test run' in detail_res.data
