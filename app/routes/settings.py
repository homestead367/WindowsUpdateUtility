from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.database import get_session
from app.models import get_or_create_settings
from app.services.crypto import encrypt, decrypt

bp = Blueprint('settings', __name__)

@bp.get('/settings')
def settings_form():
    session = get_session()
    try:
        s = get_or_create_settings(session)
        username = decrypt(s.default_username_enc) if s.default_username_enc else ''
        return render_template('settings.html',
                               username=username,
                               winrm_port=s.winrm_port,
                               max_workers=s.max_workers)
    finally:
        session.close()


@bp.post('/settings')
def save_settings():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    try:
        winrm_port = int(request.form.get('winrm_port', 5985))
        max_workers = int(request.form.get('max_workers', 10))
    except ValueError:
        flash('Port and max workers must be integers.', 'danger')
        return redirect(url_for('settings.settings_form'))

    if winrm_port < 1 or winrm_port > 65535:
        flash('WinRM port must be between 1 and 65535.', 'danger')
        return redirect(url_for('settings.settings_form'))

    if max_workers < 1 or max_workers > 50:
        flash('Max workers must be between 1 and 50.', 'danger')
        return redirect(url_for('settings.settings_form'))

    session = get_session()
    try:
        s = get_or_create_settings(session)
        if username:
            s.default_username_enc = encrypt(username)
        if password:
            s.default_password_enc = encrypt(password)
        s.winrm_port = winrm_port
        s.max_workers = max_workers
        session.commit()
    finally:
        session.close()

    flash('Settings saved.', 'success')
    return redirect(url_for('settings.settings_form'))
