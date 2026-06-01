from datetime import datetime
from app.models import Job, Server, AppSettings
from app.database import get_session

def test_create_job(session):
    job = Job(filename='servers.csv')
    session.add(job)
    session.commit()
    assert job.id is not None
    assert job.status == 'pending'
    assert isinstance(job.created_at, datetime)

def test_create_server(session):
    job = Job(filename='servers.csv')
    session.add(job)
    session.flush()
    server = Server(
        job_id=job.id,
        server_name='PROD-WEB-01',
        ip_address='192.168.1.10',
        restart_window='Sunday 02:00',
    )
    session.add(server)
    session.commit()
    assert server.id is not None
    assert server.status == 'pending'
    assert server.updates_installed == 0

def test_job_servers_relationship(session):
    job = Job(filename='servers.csv')
    session.add(job)
    session.flush()
    session.add(Server(job_id=job.id, server_name='A', ip_address='1.1.1.1', restart_window='Sun 02:00'))
    session.add(Server(job_id=job.id, server_name='B', ip_address='1.1.1.2', restart_window='Sun 02:00'))
    session.commit()
    session.refresh(job)
    assert len(job.servers) == 2

def test_app_settings_defaults(session):
    from app.models import get_or_create_settings
    settings = get_or_create_settings(session)
    assert settings.winrm_port == 5985
    assert settings.max_workers == 10

def test_job_type_defaults_to_patch(session):
    job = Job(filename='test.csv')
    session.add(job)
    session.commit()
    assert job.job_type == 'patch'

def test_job_type_can_be_set_to_test(session):
    job = Job(filename='test.csv', job_type='test')
    session.add(job)
    session.commit()
    assert job.job_type == 'test'

def test_progress_counts_test_complete_as_done(session):
    job = Job(filename='test.csv', status='running')
    session.add(job)
    session.flush()
    session.add(Server(job_id=job.id, server_name='A', ip_address='10.0.0.1',
                       restart_window='Sun 02:00', status='test_complete'))
    session.add(Server(job_id=job.id, server_name='B', ip_address='10.0.0.2',
                       restart_window='Sun 02:00', status='pending'))
    session.commit()
    session.refresh(job)
    p = job.progress()
    assert p['done'] == 1
    assert p['total'] == 2
    assert p['pct'] == 50
