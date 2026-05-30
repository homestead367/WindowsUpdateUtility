from flask import Blueprint, jsonify, request
from app.database import get_session
from app.models import Job, Server, get_or_create_settings
from app.services.crypto import decrypt
from app.services.winrm_worker import test_connection, immediate_restart, reschedule_restart

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.get('/jobs/<int:job_id>')
def job_status(job_id):
    session = get_session()
    try:
        job = session.get(Job, job_id)
        if not job:
            return jsonify({'error': 'Not found'}), 404
        return jsonify({
            'id': job.id,
            'status': job.status,
            'progress': job.progress(),
            'servers': [s.to_dict() for s in job.servers],
        })
    finally:
        session.close()


def _get_default_credentials(session):
    settings = get_or_create_settings(session)
    username = decrypt(settings.default_username_enc) if settings.default_username_enc else ''
    password = decrypt(settings.default_password_enc) if settings.default_password_enc else ''
    return username, password, settings.winrm_port


@bp.post('/servers/<int:server_id>/test')
def test_server_connection(server_id):
    session = get_session()
    try:
        server = session.get(Server, server_id)
        if not server:
            return jsonify({'success': False, 'message': 'Server not found'}), 404
        username, password, port = _get_default_credentials(session)
        actual_user = server.username or username
        ip = server.ip_address
    finally:
        session.close()

    success, message = test_connection(ip, port, actual_user, password)
    return jsonify({'success': success, 'message': message})


@bp.post('/servers/<int:server_id>/restart')
def manual_restart(server_id):
    session = get_session()
    try:
        server = session.get(Server, server_id)
        if not server:
            return jsonify({'success': False, 'message': 'Server not found'}), 404
        username, password, port = _get_default_credentials(session)
        actual_user = server.username or username
        ip = server.ip_address
    finally:
        session.close()

    success, message = immediate_restart(ip, port, actual_user, password)
    if success:
        session2 = get_session()
        try:
            srv = session2.get(Server, server_id)
            srv.status = 'restarting'
            srv.restart_scheduled_at = None
            session2.commit()
        finally:
            session2.close()
    return jsonify({'success': success, 'message': message})


@bp.post('/servers/<int:server_id>/reschedule')
def reschedule_server(server_id):
    data = request.get_json(silent=True) or {}
    new_window = data.get('restart_window', '').strip()
    if not new_window:
        return jsonify({'success': False, 'message': 'restart_window is required'})

    session = get_session()
    try:
        server = session.get(Server, server_id)
        if not server:
            return jsonify({'success': False, 'message': 'Server not found'}), 404
        username, password, port = _get_default_credentials(session)
        actual_user = server.username or username
        ip = server.ip_address
    finally:
        session.close()

    success, result = reschedule_restart(ip, port, actual_user, password, new_window)
    if success:
        from datetime import datetime
        session2 = get_session()
        try:
            srv = session2.get(Server, server_id)
            srv.restart_window = new_window
            srv.restart_scheduled_at = datetime.fromisoformat(result)
            srv.status = 'restart_scheduled'
            session2.commit()
        finally:
            session2.close()
        return jsonify({'success': True, 'restart_at': result})
    return jsonify({'success': False, 'message': result})
