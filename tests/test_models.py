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
