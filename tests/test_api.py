import pytest
from unittest.mock import patch
from app import create_app
from app.config import TestConfig
from app.database import get_session
from app.models import Job, Server

@pytest.fixture
def app():
    application = create_app(TestConfig.__dict__)
    yield application

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def job_with_server(app):
    s = get_session()
    job = Job(filename='test.csv', status='running')
    s.add(job)
    s.flush()
    server = Server(
        job_id=job.id,
        server_name='TEST-01',
        ip_address='10.0.0.1',
        restart_window='Sunday 02:00',
        status='restart_scheduled',
        updates_installed=5,
    )
    s.add(server)
    s.commit()
    job_id = job.id
    server_id = server.id
    yield {'job_id': job_id, 'server_id': server_id}
    s2 = get_session()
    srv = s2.get(Server, server_id)
    jb = s2.get(Job, job_id)
    if srv:
        s2.delete(srv)
    if jb:
        s2.delete(jb)
    s2.commit()
    s2.close()
    s.close()

def test_get_job_status(client, job_with_server):
    res = client.get(f'/api/jobs/{job_with_server["job_id"]}')
    assert res.status_code == 200
    data = res.get_json()
    assert 'servers' in data
    assert 'progress' in data
    assert data['servers'][0]['server_name'] == 'TEST-01'

def test_get_job_not_found(client):
    res = client.get('/api/jobs/99999')
    assert res.status_code == 404

def test_test_connection_endpoint(client, job_with_server):
    with patch('app.routes.api.test_connection', return_value=(True, 'Connected')):
        res = client.post(f'/api/servers/{job_with_server["server_id"]}/test')
    assert res.status_code == 200
    assert res.get_json()['success'] is True

def test_reschedule_bad_window(client, job_with_server):
    with patch('app.routes.api.reschedule_restart', return_value=(False, 'bad window')):
        res = client.post(
            f'/api/servers/{job_with_server["server_id"]}/reschedule',
            json={'restart_window': 'garbage'}
        )
    assert res.status_code == 200
    assert res.get_json()['success'] is False

def test_manual_restart_endpoint(client, job_with_server):
    with patch('app.routes.api.immediate_restart', return_value=(True, 'Restart initiated')):
        res = client.post(f'/api/servers/{job_with_server["server_id"]}/restart')
    assert res.status_code == 200
    assert res.get_json()['success'] is True

def test_server_not_found_returns_404(client):
    res = client.post('/api/servers/99999/test')
    assert res.status_code == 404
